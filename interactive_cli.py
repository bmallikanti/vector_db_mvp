#!/usr/bin/env python3
"""
Interactive CLI to drive the InteractiveDBWorkflow via REST endpoints.
Prereqs:
- API server running at http://localhost:8000
- Temporal worker running
- Temporal services (docker compose) running
- .env has COHERE_API_KEY
"""
from __future__ import annotations

import json
import sys
import time
from typing import Any, Dict, Optional, List, Tuple

import httpx

API_BASE = "http://localhost:8000"


def prompt(msg: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    val = input(f"{msg}{suffix}: ").strip()
    if not val and default is not None:
        return default
    return val


def pretty(obj: Any) -> str:
    try:
        return json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        return str(obj)

def _escape_single_quotes(s: str) -> str:
    # Safely embed JSON in single-quoted shell string: 'foo'\''bar'
    return s.replace("'", "'\"'\"'")

def curl_post(url: str, body: Dict[str, Any]) -> str:
    body_str = json.dumps(body, ensure_ascii=False)
    return f"curl -s -X POST {url} -H 'Content-Type: application/json' -d '{_escape_single_quotes(body_str)}' | jq ."

def curl_get(url: str) -> str:
    return f"curl -s {url} | jq ."

def curl_put(url: str, body: Dict[str, Any]) -> str:
    body_str = json.dumps(body, ensure_ascii=False)
    return f"curl -s -X PUT {url} -H 'Content-Type: application/json' -d '{_escape_single_quotes(body_str)}' | jq ."


def start_session(client: httpx.Client) -> str:
    url = f"{API_BASE}/interactive/start"
    print("\n$ " + curl_post(url, {}))
    r = client.post(url)
    r.raise_for_status()
    data = r.json()
    wf = data["workflow_id"]
    print(f"\n✓ Session started. workflow_id={wf}\n")
    return wf


def get_status(client: httpx.Client, wf: str, *, echo: bool = False) -> Dict[str, Any]:
    url = f"{API_BASE}/interactive/{wf}/status"
    if echo:
        print("\n$ " + curl_get(url))
    r = client.get(url)
    r.raise_for_status()
    return r.json()


def get_results(client: httpx.Client, wf: str, *, echo: bool = False) -> Dict[str, Any]:
    url = f"{API_BASE}/interactive/{wf}/results"
    if echo:
        print("\n$ " + curl_get(url))
    r = client.get(url)
    r.raise_for_status()
    return r.json()


def signal(client: httpx.Client, wf: str, path: str, body: Dict[str, Any]) -> None:
    url = f"{API_BASE}/interactive/{wf}/signal/{path}"
    print("\n$ " + curl_post(url, body))
    r = client.post(url, json=body)
    if r.status_code >= 400:
        print(f"✗ Error: {r.status_code} {r.text}")
        r.raise_for_status()
    print("✓ Signal accepted.")
    time.sleep(3)  # pause 3 seconds after user's input/action


def choose_from_list(name: str, items: list[str]) -> Optional[str]:
    if not items:
        print(f"No {name} available.")
        return None
    print(f"Available {name}:")
    for i, v in enumerate(items, 1):
        print(f"  {i}. {v}")
    choice = prompt(f"Choose {name} by number (or blank to cancel)")
    if not choice:
        return None
    try:
        idx = int(choice)
        if 1 <= idx <= len(items):
            return items[idx - 1]
    except Exception:
        pass
    print("Invalid choice.")
    return None


def _libraries_from_status(st: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Return list of (display, lib_id) from workflow status.
    Prefers names if available; falls back to IDs.
    """
    libs_by_id: Dict[str, str] = st.get("created_libraries_by_id") or {}
    lib_ids: List[str] = st.get("created_library_ids") or []
    pairs: List[Tuple[str, str]] = []
    if libs_by_id:
        for lid, name in libs_by_id.items():
            pairs.append((f"{name} ({lid})", lid))
    else:
        for lid in lib_ids:
            pairs.append((lid, lid))
    return pairs


def _documents_from_status(st: Dict[str, Any], lib_id: str) -> List[Tuple[str, str]]:
    """Return list of (display, doc_id) for a given library from workflow status.
    Prefers titles if available; falls back to IDs.
    """
    titles_map: Dict[str, Dict[str, str]] = st.get("created_document_titles_by_library") or {}
    ids_map: Dict[str, List[str]] = st.get("created_document_ids_by_library") or {}
    chunk_counts: Dict[str, int] = st.get("created_chunk_counts_by_doc") or {}
    pairs: List[Tuple[str, str]] = []
    if lib_id in titles_map and titles_map[lib_id]:
        for did, title in titles_map[lib_id].items():
            count = chunk_counts.get(did)
            label = f"{title} ({did})" if count is None else f"{title} ({did}) — chunks: {count}"
            pairs.append((label, did))
    else:
        for did in ids_map.get(lib_id, []) or []:
            count = chunk_counts.get(did)
            label = f"{did}" if count is None else f"{did} — chunks: {count}"
            pairs.append((label, did))
    return pairs


def choose_library(client: httpx.Client, wf: str) -> Optional[str]:
    st = get_status(client, wf, echo=True)
    pairs = _libraries_from_status(st)
    if not pairs:
        print("No libraries available yet.")
        return None
    labels = [p[0] for p in pairs]
    sel = choose_from_list("libraries", labels)
    if not sel:
        return None
    # map back to id
    for lbl, lid in pairs:
        if lbl == sel:
            return lid
    return None


def choose_document(client: httpx.Client, wf: str, lib_id: str) -> Optional[str]:
    # Try immediate status, then poll a few times if empty
    st = get_status(client, wf, echo=True)
    pairs = _documents_from_status(st, lib_id)
    if not pairs:
        for _ in range(5):
            time.sleep(2)
            st = get_status(client, wf, echo=False)
            pairs = _documents_from_status(st, lib_id)
            if pairs:
                break
    if not pairs:
        print("No documents available for the selected library.")
        return None
    labels = [p[0] for p in pairs]
    sel = choose_from_list("documents", labels)
    if not sel:
        return None
    for lbl, did in pairs:
        if lbl == sel:
            return did
    return None


def _print_filter_suggestions(client: httpx.Client, wf: str, lib_id: str) -> None:
    """Print available chunk metadata filter keys and sample values for a library."""
    st = get_status(client, wf, echo=True)
    catalog = (st.get("chunk_metadata_catalog_by_library") or {}).get(lib_id) or {}
    if not catalog:
        print("No filterable chunk metadata observed yet. Add chunks with metadata to enable filters.")
        return
    print("\nAvailable filters (chunk metadata):")
    example: Optional[str] = None
    for k, values in catalog.items():
        if values:
            joined = ", ".join(map(str, values[:10]))
            more = "…" if len(values) > 10 else ""
            print(f"  - {k}: {joined}{more}")
            if example is None:
                example = f"{k}={values[0]}"
        else:
            print(f"  - {k}")
            if example is None:
                example = f"{k}=<value>"
    if example:
        print(f"Example: {example}  (or JSON: {{\"{example.split('=')[0]}\": \"{example.split('=')[1]}\"}})")


def menu() -> None:
    print("\n=== Interactive Vector DB (Temporal) ===")
    print("1) Add library")
    print("2) Add document")
    print("3) Add chunk")
    print("4) Set query params (k/index/filters)")
    print("5) Start query")
    print("6) Show results")
    print("7) Show status")
    print("8) Finish session")
    print("10) List libraries")
    print("11) List documents (choose library)")
    print("12) Edit library (PUT)")
    print("13) Edit document (PUT)")
    print("14) Edit chunk (PUT)")
    print("q) Quit CLI (does not finish the session)")


def main() -> None:
    print("Checking API server...")
    try:
        with httpx.Client(timeout=10.0) as client:
            ping = client.get(f"{API_BASE}/docs")
            if ping.status_code != 200:
                print("API is not reachable. Start it first: uvicorn app.main:app --reload")
                sys.exit(1)

            wf = start_session(client)

            while True:
                try:
                    menu()
                    choice = input("Select: ").strip().lower()
                    if choice == "q":
                        print("Bye. (Workflow continues until you finish or cancel via API.)")
                        break
                    elif choice == "1":
                        name = prompt("Library name")
                        desc = prompt("Description", "")
                        signal(client, wf, "add_library", {"name": name, "description": (desc or None)})
                        # Show status after creation to surface the new library ID
                        st = get_status(client, wf, echo=True)
                        lib_pairs = _libraries_from_status(st)
                        if lib_pairs:
                            print("\n✓ Libraries available now:")
                            for i, (label, _lid) in enumerate(lib_pairs, 1):
                                print(f"  {i}. {label}")
                        else:
                            print("\n… Library creation is pending. Choose '7) Show status' in a moment.")
                    elif choice == "2":
                        # Pick library (by name if available)
                        lib_id = choose_library(client, wf)
                        if not lib_id:
                            continue
                        title = prompt("Document title")
                        category = prompt("Document category (optional)", "")
                        body = {"lib_id": lib_id, "title": title}
                        if category:
                            body["metadata"] = {"category": category}
                        signal(client, wf, "add_document", body)
                        # Show status after to reveal document IDs
                        st = get_status(client, wf, echo=True)
                    elif choice == "3":
                        lib_id = choose_library(client, wf)
                        if not lib_id:
                            continue
                        doc_id = choose_document(client, wf, lib_id)
                        if not doc_id:
                            continue
                        text = prompt("Chunk text")
                        ctype = prompt("Chunk type (optional)", "")
                        body = {"lib_id": lib_id, "doc_id": doc_id, "text": text}
                        if ctype:
                            body["metadata"] = {"type": ctype}
                        signal(client, wf, "add_chunk", body)
                        # Show status after to reflect chunk counts
                        st = get_status(client, wf, echo=True)
                    elif choice == "4":
                        # Optionally pick a library to show filter suggestions (based on chunk metadata)
                        print("Optionally pick a library to view available filters (from chunk metadata).")
                        lib_for_filters = choose_library(client, wf)
                        if lib_for_filters:
                            _print_filter_suggestions(client, wf, lib_for_filters)
                        k = prompt("k (top-k)", "5")
                        index = prompt("index (brute|lsh) — tip: use 'brute' for small datasets", "brute").strip().lower()
                        if index not in {"brute", "lsh"}:
                            print("Unknown index. Using 'brute'.")
                            index = "brute"
                        print("Enter filters as key=value pairs (comma-separated), or JSON (e.g., {\"type\":\"text\"}). Filters apply to chunk metadata keys.")
                        fil = prompt("filters", "")
                        filters: Optional[Dict[str, Any]] = None
                        if fil:
                            # Try JSON first
                            try:
                                maybe = json.loads(fil)
                                if isinstance(maybe, dict):
                                    filters = maybe
                                else:
                                    print("Filters JSON must be an object with key/value pairs. Ignoring JSON input.")
                            except Exception:
                                # Fallback to key=value, comma-separated
                                filters = {}
                                for part in fil.split(","):
                                    part = part.strip()
                                    if not part:
                                        continue
                                    if "=" in part:
                                        kf, vf = part.split("=", 1)
                                        filters[kf.strip()] = vf.strip()
                                if not filters:
                                    filters = None
                        signal(client, wf, "set_query_params", {"k": int(k), "index": index, "filters": filters})
                    elif choice == "5":
                        # Choose library first
                        lib_id = choose_library(client, wf)
                        if not lib_id:
                            continue
                        # Get current k from status and allow inline override
                        st = get_status(client, wf)
                        qp = (st.get("query_params") or {})
                        cur_k = int(qp.get("k", 5))
                        k_in = prompt("How many results (k)", str(cur_k))
                        try:
                            new_k = int(k_in)
                        except Exception:
                            print("Invalid number for k. Using current value.")
                            new_k = cur_k
                        if new_k != cur_k:
                            signal(
                                client,
                                wf,
                                "set_query_params",
                                {"k": new_k, "index": qp.get("index", "brute"), "filters": qp.get("filters")},
                            )
                        # Prompt for query text
                        qtext = prompt("Query text (leave blank to cancel)", "")
                        if not qtext:
                            continue
                        signal(client, wf, "start_query", {"lib_id": lib_id, "query_text": qtext})
                        # Immediately wait for results and display before returning to menu
                        print("Waiting for results (up to 15s)…")
                        hits = None
                        index_used = None
                        version = None
                        last_res: Optional[Dict[str, Any]] = None
                        for _ in range(15):
                            time.sleep(1)
                            try:
                                res = get_results(client, wf, echo=True)
                                last_res = res
                                hits = res.get("hits")
                                index_used = res.get("index_used") or res.get("index")
                                version = res.get("library_version")
                                # Results may be empty (no chunks). If last_results is set, stop waiting.
                                if hits is not None:
                                    break
                            except Exception:
                                pass
                        print("\n=== Results ===")
                        if hits is None:
                            print("No results available yet. Try '6) Show results' or check status.")
                        elif len(hits) == 0:
                            print("No matches. Add chunks or adjust filters and try again.")
                        else:
                            requested_index = (last_res or {}).get("index")
                            payload = {
                                "hits": hits,
                                "index": requested_index,
                                "index_used": index_used,
                                "library_version": version,
                            }
                            print(pretty(payload))
                            # Friendly hint if fallback happened (requested lsh, used brute)
                            if requested_index == "lsh" and index_used == "brute":
                                print("Note: requested LSH but fell back to brute-force due to no LSH candidates.")
                    elif choice == "6":
                        res = get_results(client, wf, echo=True)
                        print("\n=== Results ===")
                        print(pretty(res))
                    elif choice == "7":
                        st = get_status(client, wf, echo=True)
                        print("\n=== Status ===")
                        print(pretty(st))
                    elif choice == "8":
                        signal(client, wf, "finish", {})
                        print("Session finished.")
                    elif choice == "10":
                        st = get_status(client, wf, echo=True)
                        pairs = _libraries_from_status(st)
                        if not pairs:
                            print("No libraries yet.")
                        else:
                            print("\nLibraries:")
                            for i, (label, _lid) in enumerate(pairs, 1):
                                print(f"  {i}. {label}")
                    elif choice == "11":
                        lib_id = choose_library(client, wf)
                        if not lib_id:
                            continue
                        st = get_status(client, wf, echo=True)
                        pairs = _documents_from_status(st, lib_id)
                        if not pairs:
                            print("No documents for that library.")
                        else:
                            print("\nDocuments:")
                            for i, (label, _did) in enumerate(pairs, 1):
                                print(f"  {i}. {label}")
                    elif choice == "12":
                        # Edit library via REST PUT
                        url_list = f"{API_BASE}/vector_db/libraries"
                        print("\n$ " + curl_get(url_list))
                        r = client.get(url_list)
                        r.raise_for_status()
                        libs_json = r.json() or []
                        if not libs_json:
                            print("No libraries to edit.")
                            continue
                        # Present choices by name (id)
                        labels = [f"{lib.get('name','(no-name)')} ({lib.get('id')})" for lib in libs_json]
                        sel = choose_from_list("libraries", labels)
                        if not sel:
                            continue
                        idx = labels.index(sel)
                        lib = libs_json[idx]
                        new_name = prompt("New name", lib.get("name", ""))
                        new_desc = prompt("New description (optional)", lib.get("description") or "")
                        tags = prompt("Tags metadata (comma-separated, optional)", (lib.get("metadata") or {}).get("tags", ""))
                        payload: Dict[str, Any] = {
                            "name": new_name,
                            "description": new_desc or None,
                            "metadata": {"tags": (tags or None)},
                        }
                        url_put = f"{API_BASE}/vector_db/libraries/{lib['id']}"
                        print("\n$ " + curl_put(url_put, payload))
                        pr = client.put(url_put, json=payload)
                        if pr.status_code >= 400:
                            print(f"✗ Error: {pr.status_code} {pr.text}")
                        else:
                            print("✓ Library updated.")
                    elif choice == "13":
                        # Edit document via REST PUT
                        # Choose library (use REST for consistency)
                        url_list = f"{API_BASE}/vector_db/libraries"
                        print("\n$ " + curl_get(url_list))
                        r = client.get(url_list)
                        r.raise_for_status()
                        libs_json = r.json() or []
                        if not libs_json:
                            print("No libraries available.")
                            continue
                        labels = [f"{lib.get('name','(no-name)')} ({lib.get('id')})" for lib in libs_json]
                        sel = choose_from_list("libraries", labels)
                        if not sel:
                            continue
                        lib = libs_json[labels.index(sel)]
                        lib_id = lib["id"]
                        # List documents in chosen library
                        url_docs = f"{API_BASE}/vector_db/libraries/{lib_id}/documents"
                        print("\n$ " + curl_get(url_docs))
                        dr = client.get(url_docs)
                        dr.raise_for_status()
                        docs_json = dr.json() or []
                        if not docs_json:
                            print("No documents to edit.")
                            continue
                        doc_labels = [f"{d.get('title','(no-title)')} ({d.get('id')})" for d in docs_json]
                        dsel = choose_from_list("documents", doc_labels)
                        if not dsel:
                            continue
                        doc = docs_json[doc_labels.index(dsel)]
                        doc_id = doc["id"]
                        new_title = prompt("New title (leave blank to keep)", doc.get("title", ""))
                        new_cat = prompt("New category (optional)", (doc.get("metadata") or {}).get("category", ""))
                        payload: Dict[str, Any] = {}
                        if new_title:
                            payload["title"] = new_title
                        if new_cat:
                            payload["metadata"] = {"category": new_cat}
                        if not payload:
                            print("Nothing to update.")
                            continue
                        url_put = f"{API_BASE}/vector_db/libraries/{lib_id}/documents/{doc_id}"
                        print("\n$ " + curl_put(url_put, payload))
                        pr = client.put(url_put, json=payload)
                        if pr.status_code >= 400:
                            print(f"✗ Error: {pr.status_code} {pr.text}")
                        else:
                            print("✓ Document updated.")
                    elif choice == "14":
                        # Edit chunk via REST PUT
                        # Choose library
                        url_list = f"{API_BASE}/vector_db/libraries"
                        print("\n$ " + curl_get(url_list))
                        r = client.get(url_list)
                        r.raise_for_status()
                        libs_json = r.json() or []
                        if not libs_json:
                            print("No libraries available.")
                            continue
                        labels = [f"{lib.get('name','(no-name)')} ({lib.get('id')})" for lib in libs_json]
                        sel = choose_from_list("libraries", labels)
                        if not sel:
                            continue
                        lib = libs_json[labels.index(sel)]
                        lib_id = lib["id"]
                        # Choose document
                        url_docs = f"{API_BASE}/vector_db/libraries/{lib_id}/documents"
                        print("\n$ " + curl_get(url_docs))
                        dr = client.get(url_docs)
                        dr.raise_for_status()
                        docs_json = dr.json() or []
                        if not docs_json:
                            print("No documents available.")
                            continue
                        doc_labels = [f"{d.get('title','(no-title)')} ({d.get('id')})" for d in docs_json]
                        dsel = choose_from_list("documents", doc_labels)
                        if not dsel:
                            continue
                        doc = docs_json[doc_labels.index(dsel)]
                        doc_id = doc["id"]
                        # Choose chunk
                        url_chunks = f"{API_BASE}/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks"
                        print("\n$ " + curl_get(url_chunks))
                        cr = client.get(url_chunks)
                        cr.raise_for_status()
                        chunks_json = cr.json() or []
                        if not chunks_json:
                            print("No chunks to edit.")
                            continue
                        def _label_chunk(c: Dict[str, Any]) -> str:
                            text = c.get("text", "")
                            if len(text) > 40:
                                text_disp = text[:37] + "…"
                            else:
                                text_disp = text
                            ctype = (c.get("metadata") or {}).get("type")
                            return f"{text_disp} [{ctype or 'n/a'}] ({c.get('id')})"
                        chunk_labels = [_label_chunk(c) for c in chunks_json]
                        csel = choose_from_list("chunks", chunk_labels)
                        if not csel:
                            continue
                        chunk = chunks_json[chunk_labels.index(csel)]
                        chunk_id = chunk["id"]
                        # Prompt updates
                        new_text = prompt("New text (leave blank to keep)", chunk.get("text", ""))
                        new_type = prompt("New type (optional)", (chunk.get("metadata") or {}).get("type", ""))
                        payload: Dict[str, Any] = {}
                        if new_text:
                            payload["text"] = new_text
                        if new_type:
                            payload["metadata"] = {"type": new_type}
                        if not payload:
                            print("Nothing to update.")
                            continue
                        url_put = f"{API_BASE}/vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk_id}"
                        print("\n$ " + curl_put(url_put, payload))
                        pr = client.put(url_put, json=payload)
                        if pr.status_code >= 400:
                            print(f"✗ Error: {pr.status_code} {pr.text}")
                        else:
                            print("✓ Chunk updated.")
                    else:
                        print("Invalid choice.")
                except KeyboardInterrupt:
                    print("\nInterrupted. Type 'q' to quit.")
                except Exception as e:
                    print(f"\n✗ Error: {e}\n")
    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
