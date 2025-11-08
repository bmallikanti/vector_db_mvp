# Vector Database with Temporal

A minimal vector database with FastAPI and Temporal workflows.

## Quick Start (Docker)

### 1) Set environment

Create a `.env` with your Cohere key:
```bash
echo "COHERE_API_KEY=your_api_key_here" > .env
```
Note: No API keys are baked into the Docker images. Set your own `COHERE_API_KEY` via environment if you want activities/CLI to auto-embed with Cohere. If you prefer not to use Cohere, provide embeddings explicitly in chunk requests and search requests.

### 2) Start everything with Docker Compose

```bash
docker compose up -d --build
```

Services:
- API: http://localhost:8000
- Temporal UI: http://localhost:8080
- Temporal Server: temporal:7233 (internal)

### 3) Smoke test (CRUD + search)

```bash
# Create library
LIB=$(curl -s -X POST http://localhost:8000/vector_db/libraries \
  -H 'Content-Type: application/json' \
  -d '{"name":"My Library"}' | jq -r '.id')
echo "LIB=$LIB"

# Create document
DOC=$(curl -s -X POST http://localhost:8000/vector_db/libraries/$LIB/documents \
  -H 'Content-Type: application/json' \
  -d '{"title":"Paris Guide","metadata":{"category":"travel"}}' | jq -r '.id')
echo "DOC=$DOC"

# Add chunk (provide your own embedding if you prefer)
curl -s -X POST http://localhost:8000/vector_db/libraries/$LIB/documents/$DOC/chunks \
  -H 'Content-Type: application/json' \
  -d '{"text":"The Louvre is in Paris.","embedding":[0.9,0.1]}' | jq .

# Direct search (non-Temporal)
curl -s -X POST "http://localhost:8000/vector_db/libraries/$LIB/search" \
  -H 'Content-Type: application/json' \
  -d '{"query_embedding":[1.0,0.0],"k":3,"index":"brute"}' | jq .
```

### 4) Temporal-backed search (durable)

```bash
# Using the API with durable execution
curl -s -X POST "http://localhost:8000/vector_db/libraries/$LIB/search?use_temporal=true" \
  -H 'Content-Type: application/json' \
  -d '{"query_text":"Paris museum","k":3,"index":"brute"}' | jq .
```

### 5) Interactive session (CLI)

```bash
python interactive_cli.py
```
- The CLI will:
  - Start a Temporal interactive workflow session
  - Let you add libraries, documents, chunks (Cohere embeddings auto-generated)
  - Show available libraries (by name) and documents (by title) for selection
  - Configure k/index/filters and start queries
    - Filters apply to chunk metadata (e.g., type). The CLI can show available keys/values per library.
    - Enter filters either as key=value, comma-separated (e.g., `type=text,lang=en`) or JSON (e.g., `{ "type":"text" }`).
  - Wait for and display results immediately, reranked and trimmed to k
    - Shows both requested `index` and actual `index_used` (may fall back to brute on tiny datasets)
  - Show results and status any time
  - Pause ~3 seconds after each action
  - Provide shortcuts to list libraries/documents
  - Edit resources via REST PUT:
    - Edit library (name/description/tags)
    - Edit document (title/category)
    - Edit chunk (text/type)
  - Print the exact curl used for each action
  - Finish session (no separate cancel in CLI)

## Architecture

### What Uses What

```
┌─────────────────────────────────────────────────────────┐
│                    API Layer                             │
│  FastAPI (app/main.py)                                  │
│    ↓                                                     │
│  Routers (app/api/routers/*)                           │
│    ↓                                                     │
│  Services (app/services/*)                              │
└─────────────────────────────────────────────────────────┘
                    │
                    ├─────────────────┬───────────────────┐
                    ▼                 ▼                   ▼
        ┌──────────────────┐           ┌──────────────────┐
        │  In-Memory       │           │   Temporal       │
        │  (default)       │           │  (workflows)     │
        │                  │           │                  │
        │ LibraryRepo      │           │ QueryWorkflow    │
        │ DocumentRepo     │           │   ↓              │
        │ ChunkRepo        │           │ Activities       │
        └──────────────────┘           │   ↓              │
                                       │ Services         │
                                       │   ↓              │
                                       │ In-Memory Repos  │
                                       └──────────────────┘
```

### Storage Mode

**In-Memory:**
- Fast, no persistence
- Data lost on restart
- Good for testing and demos

### Temporal Workflows

Two flows:
- QueryWorkflow (request/response): orchestrates validate → embed → search → rerank for one request
- InteractiveDBWorkflow (signal-driven): long-running session that:
  - Receives signals to add libraries, documents, chunks (all embedding via Cohere)
  - Accepts query parameters and query requests
  - Exposes queries to fetch live status and partial results
  - Pauses ~3 seconds after each action for user-driven control

## Key Components

### Services (`app/services/`)
- `LibraryService` - Manages libraries
- `DocumentService` - Manages documents
- `ChunkService` - Manages chunks
- `SearchService` - Vector search (brute force or LSH)

### Repositories (`app/repositories/`)
- `memory/` - In-memory storage

### Temporal (`app/temporal_workflows/`)
- `worker.py` - Worker process (runs activities)
- `client.py` - Client to start workflows
- `query_workflow.py` - Query workflow and activities
- `interactive_workflow.py` - Interactive workflow and activities

## API Endpoints

- `POST /vector_db/libraries` - Create library
- `GET /vector_db/libraries` - List libraries
- `GET /vector_db/libraries/{id}` - Get library
- `PUT /vector_db/libraries/{id}` - Update library
- `DELETE /vector_db/libraries/{id}` - Delete library
- `POST /vector_db/libraries/{id}/documents` - Add document
- `GET /vector_db/libraries/{id}/documents` - List documents
- `GET /vector_db/libraries/{id}/documents/{doc_id}` - Get document
- `PUT /vector_db/libraries/{id}/documents/{doc_id}` - Update document
- `DELETE /vector_db/libraries/{id}/documents/{doc_id}` - Delete document
- `POST /vector_db/libraries/{id}/documents/{doc_id}/chunks` - Add chunk
- `GET /vector_db/libraries/{id}/documents/{doc_id}/chunks` - List chunks
- `PUT /vector_db/libraries/{id}/documents/{doc_id}/chunks/{chunk_id}` - Update chunk
- `DELETE /vector_db/libraries/{id}/documents/{doc_id}/chunks/{chunk_id}` - Delete chunk
- `POST /vector_db/libraries/{id}/search?use_temporal=true` - Search (durable when query param set)

Interactive workflow control:
- `POST /interactive/start` → { workflow_id }
- `GET /interactive/{workflow_id}/status`
- `GET /interactive/{workflow_id}/results`
- `POST /interactive/{workflow_id}/signal/add_library`
- `POST /interactive/{workflow_id}/signal/add_document`
- `POST /interactive/{workflow_id}/signal/add_chunk`
- `POST /interactive/{workflow_id}/signal/set_query_params`
- `POST /interactive/{workflow_id}/signal/start_query`
- `POST /interactive/{workflow_id}/signal/finish`
- `POST /interactive/{workflow_id}/signal/cancel` (optional; CLI uses finish)

## Interactive Workflow API (Examples)

Below are minimal curl examples for the interactive session.

- Start a session
  - `POST /interactive/start`
  - Response: `{ "workflow_id": "interactive-session-...", "run_id": "..." }`

- Add a library
  - `POST /interactive/{workflow_id}/signal/add_library`
  - Body: `{ "name": "My Library", "description": "optional" }`

- Check status (to find IDs/names)
  - `GET /interactive/{workflow_id}/status`
  - Useful fields:
    - `created_library_ids`, `created_libraries_by_id`
    - `created_document_ids_by_library`, `created_document_titles_by_library`
    - `chunk_metadata_catalog_by_library` (suggested filter keys/values)
    - `query_params`, `timeline_tail`

- Add a document to a library
  - `POST /interactive/{workflow_id}/signal/add_document`
  - Body: `{ "lib_id": "<LIB_ID>", "title": "Doc Title", "metadata": { "category": "optional" } }`

- Add a chunk to a document
  - `POST /interactive/{workflow_id}/signal/add_chunk`
  - Body: `{ "lib_id": "<LIB_ID>", "doc_id": "<DOC_ID>", "text": "Chunk text", "metadata": { "type": "paragraph" } }`

- Set query parameters
  - `POST /interactive/{workflow_id}/signal/set_query_params`
  - Body: `{ "k": 3, "index": "brute", "filters": { "type": "text" } }`
  - Notes:
    - `index`: `brute` or `lsh` (`lsh` may fall back to `brute` on tiny datasets)
    - `filters`: exact match on chunk metadata keys (e.g., `type`)

- Start a query
  - `POST /interactive/{workflow_id}/signal/start_query`
  - Body (text): `{ "lib_id": "<LIB_ID>", "query_text": "Paris museum" }`
  - Or (embedding): `{ "lib_id": "<LIB_ID>", "query_embedding": [1.0, 0.0] }`

- Get results
  - `GET /interactive/{workflow_id}/results`
  - Returns: `{ "hits": [...], "index": "requested", "index_used": "actual", "library_version": n, "reranked": true }`

- Finish the session
  - `POST /interactive/{workflow_id}/signal/finish`

- (Optional) Cancel the session
  - `POST /interactive/{workflow_id}/signal/cancel`

## CRUD API (Examples)

- Update library
  - `PUT /vector_db/libraries/{lib_id}`
  - Body: `{ "name": "New Name", "description": "optional", "metadata": { "tags": "tag1,tag2" } }`

- Update document
  - `PUT /vector_db/libraries/{lib_id}/documents/{doc_id}`
  - Body: `{ "title": "New Title", "metadata": { "category": "guide" } }`

- Update chunk
  - `PUT /vector_db/libraries/{lib_id}/documents/{doc_id}/chunks/{chunk_id}`
  - Body: `{ "text": "new text", "metadata": { "type": "paragraph" } }`
  - Behavior: if `text` is changed and `embedding` omitted, server re-embeds via Cohere (when configured).

## Temporal UI

View workflow executions: http://localhost:8080 (New UI v2)

## Environment Variables

- `COHERE_API_KEY` - Cohere API key for embeddings
- `TEMPORAL_ADDRESS` - Address of Temporal server (default inside Docker: `temporal:7233`)

## Project Structure

```
app/
├── api/              # FastAPI routes
├── core/             # Configuration
├── models/           # Pydantic models
├── repositories/     # Data storage (memory)
├── services/         # Business logic
├── indexing/         # Vector indexes (brute/lsh)
├── temporal_workflows/ # Temporal workflows & activities
└── main.py           # FastAPI app
```
