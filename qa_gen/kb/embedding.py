# V2 ONLY — not used in v1 (flat-file KB, no embeddings)
# Restore in v2 when upgrading to Supabase + Voyage AI semantic search.

import time

import voyageai


_MODEL = "voyage-3-large"
_RETRIES = 3
_BACKOFF = [1, 2, 4]


class EmbeddingClient:
    def __init__(self, api_key: str) -> None:
        self._client = voyageai.Client(api_key=api_key)

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        last_exc: Exception | None = None
        for attempt, delay in enumerate(_BACKOFF):
            try:
                result = self._client.embed(texts, model=_MODEL, input_type=input_type)
                return result.embeddings
            except Exception as e:
                last_exc = e
                if attempt < _RETRIES - 1:
                    retry_after = delay
                    if hasattr(e, "response") and e.response is not None:
                        try:
                            retry_after = int(e.response.headers.get("Retry-After", 30))
                        except (ValueError, TypeError):
                            retry_after = 30
                    time.sleep(retry_after)
        raise last_exc  # type: ignore[misc]

    def embed_document(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "document")

    def embed_query(self, phrase: str) -> list[float]:
        return self._embed([phrase], "query")[0]
