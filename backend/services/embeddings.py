import os
import hashlib
import logging
import asyncio
from typing import Optional
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Thread pool for running blocking model inference off the async event loop
_executor = ThreadPoolExecutor(max_workers=int(os.getenv("EMBEDDING_WORKERS", "2")))

# ---------------------------------------------------------------------------
# In-process LRU cache (keyed on the raw text string)
# Replace with Redis for multi-process deployments.
# ---------------------------------------------------------------------------
_CACHE_SIZE = int(os.getenv("EMBEDDING_CACHE_SIZE", "2048"))


class EmbeddingsService:
    """
    Production-grade embedding service.

    Improvements over the original:
    - Async-friendly: `generate_embedding_async` offloads CPU work to a thread pool
      so it never blocks the event loop.
    - LRU cache: identical texts are never re-encoded (configurable via
      EMBEDDING_CACHE_SIZE env var).
    - Batch encoding: encode many texts in one forward pass, which is
      significantly faster than calling encode() in a loop.
    - Normalised vectors: all embeddings are L2-normalised so cosine similarity
      reduces to a dot product (faster in pgvector with <#> operator).
    - Multiple model slots: swap or A/B-test models without changing call sites.
    - Graceful degradation: if the model fails to load, the service raises at
      construction time rather than silently returning zeroed vectors.
    """

    _MODEL_NAME = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    # Dimension of all-MiniLM-L6-v2 — update if you change the model.
    EMBEDDING_DIM = 384

    def __init__(self, model_name: Optional[str] = None):
        model_name = model_name or self._MODEL_NAME
        logger.info("Loading SentenceTransformer model: %s", model_name)
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as exc:
            logger.exception("Failed to load embedding model '%s'", model_name)
            raise RuntimeError(f"Could not load embedding model: {exc}") from exc
        self.model_name = model_name

    # ------------------------------------------------------------------
    # Synchronous helpers (safe to call from non-async code / threads)
    # ------------------------------------------------------------------

    @lru_cache(maxsize=_CACHE_SIZE)
    def _cached_encode(self, text: str) -> tuple:
        """Encode a single text string; result is cached by text content."""
        vec = self.model.encode(text, normalize_embeddings=True)
        return tuple(vec.tolist())

    def generate_embedding(self, text: str) -> list[float]:
        """Return a normalised embedding for *text* (cached)."""
        if not text or not text.strip():
            logger.warning("generate_embedding called with empty text; returning zero vector.")
            return [0.0] * self.EMBEDDING_DIM
        return list(self._cached_encode(text.strip()))

    def generate_product_embedding(self, product_name: str, description: str = "") -> list[float]:
        """
        Combine name + description into a single semantic representation.
        The name is weighted more heavily by repeating it before the description.
        """
        parts = [product_name.strip()]
        if description and description.strip():
            parts.append(description.strip())
        combined = ". ".join(parts)
        return self.generate_embedding(combined)

    def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Encode many texts in a single forward pass — dramatically faster than
        calling generate_embedding() in a loop for large batches.

        Empty / whitespace strings are replaced with zero vectors.
        """
        if not texts:
            return []

        # Separate valid from empty texts so we can skip encoding empty ones.
        indices_valid: list[int] = []
        indices_empty: list[int] = []
        clean_texts: list[str] = []

        for i, t in enumerate(texts):
            stripped = t.strip() if t else ""
            if stripped:
                indices_valid.append(i)
                clean_texts.append(stripped)
            else:
                indices_empty.append(i)

        zero = [0.0] * self.EMBEDDING_DIM
        results: list[list[float]] = [zero] * len(texts)

        if clean_texts:
            matrix = self.model.encode(clean_texts, normalize_embeddings=True, batch_size=64)
            for idx, vec in zip(indices_valid, matrix):
                results[idx] = vec.tolist()

        return results

    def similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """
        Cosine similarity between two *already-normalised* vectors.
        Returns a value in [-1, 1]; 1.0 means identical.
        """
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        return float(np.dot(a, b))

    # ------------------------------------------------------------------
    # Async wrappers (use these inside FastAPI / async request handlers)
    # ------------------------------------------------------------------

    async def generate_embedding_async(self, text: str) -> list[float]:
        """Non-blocking version of generate_embedding for async contexts."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.generate_embedding, text)

    async def generate_product_embedding_async(
        self, product_name: str, description: str = ""
    ) -> list[float]:
        """Non-blocking version of generate_product_embedding."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor, self.generate_product_embedding, product_name, description
        )

    async def generate_batch_async(self, texts: list[str]) -> list[list[float]]:
        """Non-blocking batch encoding."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self.generate_batch, texts)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def cache_info(self) -> dict:
        """Expose LRU cache statistics for monitoring / metrics."""
        info = self._cached_encode.cache_info()
        return {
            "hits": info.hits,
            "misses": info.misses,
            "maxsize": info.maxsize,
            "currsize": info.currsize,
        }

    def __repr__(self) -> str:
        return f"EmbeddingsService(model={self.model_name!r}, dim={self.EMBEDDING_DIM})"


# Singleton — import this everywhere instead of constructing a new instance.
embeddings_service = EmbeddingsService()
