from __future__ import annotations
from typing import List
import httpx
from app.core.config import settings

class CohereProvider:
    """Minimal Cohere embedder for this project."""
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.COHERE_API_KEY
        self._client = httpx.Client(timeout=10.0)

    def embed_text(self, text: str, dim: int = 384) -> List[float]:
        if not self.api_key:
            raise ValueError("COHERE_API_KEY not configured")
        r = self._client.post(
            "https://api.cohere.ai/v1/embed",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "texts": [text],
                "model": "embed-english-v3.0",
                "input_type": "search_document",  # Required for v3.0 models
            },
        )
        r.raise_for_status()
        emb = r.json()["embeddings"][0]
        return emb  # keep as-is; don't resize here
