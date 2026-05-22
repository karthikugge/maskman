"""
agents.py — Production-grade agent layer.

Improvements over the original:
- ProductUnderstandingAgent: uses the async embedding path so it never blocks
  the event loop; re-raises with a domain-specific error type for clean
  handling upstream.
- MatchingAgent: supports configurable similarity metric (cosine / L2), returns
  richer result dicts including the similarity score, and handles the
  "no embedding found" case cleanly.
- RecommendationAgent: implements a real two-phase strategy — collaborative
  filtering via offer overlap + semantic similarity fallback — with a
  result dataclass instead of a bare dict.
- All agents: structured logging, typed signatures, and docstrings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

# Broken imports removed (not used in raw SQL queries)
# from app.models.domain import Product, ProductEmbedding, Offer
from backend.services.embeddings import embeddings_service

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------

SimilarityMetric = Literal["cosine", "l2"]

_METRIC_OP: dict[SimilarityMetric, str] = {
    "cosine": "<=>",   # pgvector cosine distance (lower = more similar)
    "l2":     "<->",   # pgvector L2 distance
}


class AgentError(RuntimeError):
    """Base error for all agent failures."""


@dataclass
class SimilarProduct:
    id: str
    name: str
    distance: float
    similarity_score: float  # 1 - distance for cosine; convenient for ranking UI


@dataclass
class RecommendationResult:
    product_id: str
    product_name: str
    score: float
    reason: str  # "collaborative" | "semantic" | "trending"


# ---------------------------------------------------------------------------
# ProductUnderstandingAgent
# ---------------------------------------------------------------------------

class ProductUnderstandingAgent:
    """
    Generates and persists product embeddings.

    Changes from original:
    - Uses `generate_product_embedding_async` to avoid blocking the event loop.
    - Wraps the DB interaction in a try/except so callers always get an
      `AgentError` on failure (not a raw SQLAlchemy exception).
    - Returns the stored embedding so callers can chain operations without a
      second DB round-trip.
    """

    @staticmethod
    async def process_new_product(
        product_id: str,
        name: str,
        description: str,
        db: AsyncSession,
    ) -> list[float]:
        """
        Generate an embedding for `(name, description)` and upsert it into
        `product_embeddings`.

        Returns the generated embedding vector.
        Raises `AgentError` on failure.
        """
        logger.info("Generating embedding for product_id=%s name=%r", product_id, name)

        try:
            embedding = await embeddings_service.generate_product_embedding_async(
                name, description
            )
        except Exception as exc:
            raise AgentError(
                f"Embedding generation failed for product {product_id!r}: {exc}"
            ) from exc

        vector_str = "[" + ",".join(str(x) for x in embedding) + "]"

        upsert_stmt = text("""
            INSERT INTO product_embeddings (product_id, embedding)
            VALUES (:product_id, :embedding::vector)
            ON CONFLICT (product_id)
            DO UPDATE SET embedding = EXCLUDED.embedding,
                          updated_at = now()
        """)

        try:
            await db.execute(upsert_stmt, {"product_id": product_id, "embedding": vector_str})
            await db.commit()
        except Exception as exc:
            await db.rollback()
            raise AgentError(
                f"DB upsert failed for product {product_id!r}: {exc}"
            ) from exc

        logger.info("Embedding stored for product_id=%s (dim=%d)", product_id, len(embedding))
        return embedding

    @staticmethod
    async def process_batch(
        products: list[dict],  # [{"id": str, "name": str, "description": str}, ...]
        db: AsyncSession,
    ) -> dict[str, list[float]]:
        """
        Encode and upsert a batch of products in a single model forward pass.
        Much faster than calling `process_new_product` in a loop.

        Returns a mapping of product_id -> embedding.
        """
        if not products:
            return {}

        texts = [f"{p['name']}. {p.get('description', '')}" for p in products]
        embeddings = await embeddings_service.generate_batch_async(texts)

        rows = []
        result: dict[str, list[float]] = {}
        for p, emb in zip(products, embeddings):
            vec_str = "[" + ",".join(str(x) for x in emb) + "]"
            rows.append({"product_id": p["id"], "embedding": vec_str})
            result[p["id"]] = emb

        batch_upsert = text("""
            INSERT INTO product_embeddings (product_id, embedding)
            VALUES (:product_id, :embedding::vector)
            ON CONFLICT (product_id)
            DO UPDATE SET embedding = EXCLUDED.embedding,
                          updated_at = now()
        """)

        try:
            await db.execute(batch_upsert, rows)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            raise AgentError(f"Batch upsert failed: {exc}") from exc

        logger.info("Batch upsert complete: %d products", len(products))
        return result


# ---------------------------------------------------------------------------
# MatchingAgent
# ---------------------------------------------------------------------------

class MatchingAgent:
    """
    Vector similarity search using pgvector.

    Changes from original:
    - Configurable similarity metric (cosine or L2).
    - Returns `SimilarProduct` dataclasses with both raw distance and a
      normalised similarity score.
    - Early return with a clear log message when no embedding exists.
    - Optional `min_similarity` threshold so callers can filter noise.
    """

    @staticmethod
    async def find_similar_products(
        db: AsyncSession,
        product_id: str,
        limit: int = 5,
        metric: SimilarityMetric = "cosine",
        min_similarity: float = 0.0,
    ) -> list[SimilarProduct]:
        """
        Return up to `limit` products most similar to `product_id`.

        Parameters
        ----------
        metric:
            "cosine" (default) or "l2".  Cosine is recommended for text
            embeddings because the vectors are already L2-normalised.
        min_similarity:
            Discard results whose similarity score is below this threshold
            (0.0 = keep everything, 1.0 = only exact matches).
        """
        op = _METRIC_OP[metric]

        # 1. Fetch the query embedding
        fetch_stmt = text(
            "SELECT embedding::text FROM product_embeddings WHERE product_id = :pid"
        )
        res = await db.execute(fetch_stmt, {"pid": product_id})
        query_vec_str = res.scalar()

        if not query_vec_str:
            logger.warning("No embedding found for product_id=%s; returning empty list.", product_id)
            return []

        # 2. Search — note the operator is interpolated at *query build* time,
        #    not via bind params, which is safe here because `op` comes from
        #    a hard-coded mapping, not user input.
        search_stmt = text(f"""
            SELECT
                p.id,
                p.name,
                (e.embedding {op} :query_embedding::vector) AS distance
            FROM products p
            JOIN product_embeddings e ON p.id = e.product_id
            WHERE p.id != :pid
            ORDER BY distance ASC
            LIMIT :limit
        """)

        rows = await db.execute(
            search_stmt,
            {"query_embedding": query_vec_str, "pid": product_id, "limit": limit},
        )

        results: list[SimilarProduct] = []
        for row in rows:
            # For cosine distance: similarity = 1 - distance (range [0, 2] → [−1, 1])
            sim_score = round(1.0 - row.distance, 4) if metric == "cosine" else round(1.0 / (1.0 + row.distance), 4)
            if sim_score >= min_similarity:
                results.append(
                    SimilarProduct(
                        id=str(row.id),
                        name=row.name,
                        distance=round(row.distance, 6),
                        similarity_score=sim_score,
                    )
                )

        logger.debug(
            "find_similar_products: product_id=%s metric=%s results=%d",
            product_id, metric, len(results),
        )
        return results

    @staticmethod
    async def find_similar_to_text(
        db: AsyncSession,
        query_text: str,
        limit: int = 5,
        metric: SimilarityMetric = "cosine",
    ) -> list[SimilarProduct]:
        """
        Ad-hoc semantic search: find products similar to an arbitrary text query.
        Useful for search bars and chatbot integrations.
        """
        op = _METRIC_OP[metric]
        embedding = await embeddings_service.generate_embedding_async(query_text)
        query_vec_str = "[" + ",".join(str(x) for x in embedding) + "]"

        stmt = text(f"""
            SELECT
                p.id,
                p.name,
                (e.embedding {op} :query_embedding::vector) AS distance
            FROM products p
            JOIN product_embeddings e ON p.id = e.product_id
            ORDER BY distance ASC
            LIMIT :limit
        """)

        rows = await db.execute(stmt, {"query_embedding": query_vec_str, "limit": limit})
        results = []
        for row in rows:
            sim = round(1.0 - row.distance, 4) if metric == "cosine" else round(1.0 / (1.0 + row.distance), 4)
            results.append(
                SimilarProduct(id=str(row.id), name=row.name, distance=round(row.distance, 6), similarity_score=sim)
            )

        return results


# ---------------------------------------------------------------------------
# RecommendationAgent
# ---------------------------------------------------------------------------

class RecommendationAgent:
    """
    Multi-strategy recommendation engine.

    Strategy 1 — Collaborative filtering (offer overlap):
        Find products that frequently appear in the same offers/carts as
        products the user has previously interacted with.

    Strategy 2 — Semantic similarity fallback:
        If collaborative data is sparse (cold-start), fall back to finding
        products semantically similar to the user's most recently viewed item.

    Strategy 3 — Trending fallback:
        If no user history exists at all, surface globally trending products.
    """

    @staticmethod
    async def recommend(
        user_id: str,
        db: AsyncSession,
        limit: int = 10,
    ) -> list[RecommendationResult]:
        """
        Return up to `limit` personalised product recommendations for `user_id`.
        """
        # ---- Strategy 1: collaborative filtering via offer co-occurrence ----
        collab_stmt = text("""
            SELECT
                o2.product_id,
                p.name,
                COUNT(*) AS co_occurrence_count
            FROM offers o1
            JOIN offers o2
                ON  o1.user_id    != o2.user_id          -- different users
                AND o1.product_id != o2.product_id        -- different products
                AND o2.product_id NOT IN (               -- user hasn't seen it
                    SELECT product_id FROM offers WHERE user_id = :uid
                )
            JOIN products p ON p.id = o2.product_id
            WHERE o1.user_id = :uid
            GROUP BY o2.product_id, p.name
            ORDER BY co_occurrence_count DESC
            LIMIT :limit
        """)

        collab_rows = await db.execute(collab_stmt, {"uid": user_id, "limit": limit})
        collab_results = collab_rows.fetchall()

        if collab_results:
            max_count = max(r.co_occurrence_count for r in collab_results)
            return [
                RecommendationResult(
                    product_id=str(r.product_id),
                    product_name=r.name,
                    score=round(r.co_occurrence_count / max_count, 4),
                    reason="collaborative",
                )
                for r in collab_results
            ]

        # ---- Strategy 2: semantic similarity on most-recently-viewed item ----
        logger.info(
            "No collaborative data for user_id=%s; falling back to semantic similarity.", user_id
        )

        last_product_stmt = text("""
            SELECT product_id
            FROM offers
            WHERE user_id = :uid
            ORDER BY created_at DESC
            LIMIT 1
        """)
        res = await db.execute(last_product_stmt, {"uid": user_id})
        last_product_id = res.scalar()

        if last_product_id:
            similar = await MatchingAgent.find_similar_products(
                db, str(last_product_id), limit=limit, metric="cosine", min_similarity=0.3
            )
            return [
                RecommendationResult(
                    product_id=s.id,
                    product_name=s.name,
                    score=s.similarity_score,
                    reason="semantic",
                )
                for s in similar
            ]

        # ---- Strategy 3: global trending fallback ----
        logger.info("No user history for user_id=%s; returning trending products.", user_id)

        trending_stmt = text("""
            SELECT p.id, p.name, COUNT(o.id) AS offer_count
            FROM products p
            JOIN offers o ON o.product_id = p.id
            WHERE o.created_at > now() - interval '7 days'
            GROUP BY p.id, p.name
            ORDER BY offer_count DESC
            LIMIT :limit
        """)
        trending_rows = await db.execute(trending_stmt, {"limit": limit})
        trending = trending_rows.fetchall()

        if not trending:
            return []

        max_count = max(r.offer_count for r in trending)
        return [
            RecommendationResult(
                product_id=str(r.id),
                product_name=r.name,
                score=round(r.offer_count / max_count, 4),
                reason="trending",
            )
            for r in trending
        ]
