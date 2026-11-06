
"""
retrieval.py - similarity-first product retrieval and deterministic ranking.

Flow:
    1. Retrieve products using embedding similarity.
    2. Fetch catalog details and precomputed scores from PostgreSQL.
    3. Apply trust, freshness, and price checks.
    4. Keep only products sufficiently close to the best similarity.
    5. Use product / merchant / trust / value scores to rank that group.

Similarity is the primary relevance criterion.
Quality scores are secondary and cannot compensate for poor similarity.

Price and title always come from the catalog, never from search output.
"""

import json
import logging
import os

from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import TRUST_THRESHOLD, WEIGHTS
from .search import search_products_by_similarity


log = logging.getLogger(__name__)

DATABASE_URL = os.environ["DATABASE_URL"]

TOP_N = 3
CANDIDATES_K = 10

BUDGET_SLACK = 1.2
SCORE_VERSION = 2

MAX_SCORE_AGE = timedelta(
    hours=int(os.environ.get("MAX_SCORE_AGE_HOURS", "72"))
)

# Products must be within this distance of the best similarity
# to be considered relevant.
#
# Example:
# Best similarity = 0.342
# Minimum eligible similarity = 0.342 - 0.05 = 0.292
#
# Configure through the SIMILARITY_GAP environment variable.
SIMILARITY_GAP = float(
    os.environ.get("SIMILARITY_GAP", "0.05")
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _to_float(value: Any) -> float:
    """Safely convert a value to float."""

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        try:
            return float(
                value.replace("$", "").replace(",", "").strip()
            )
        except ValueError:
            return 0.0

    return 0.0


def _pid(product: dict) -> str | None:
    """Support both productId and id from embedding search."""

    pid = product.get("productId", product.get("id"))

    return str(pid) if pid is not None else None


def _connect():
    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


def _is_fresh(computed_at) -> bool:
    """Check whether the precomputed score is recent enough."""

    try:
        ts = (
            computed_at
            if isinstance(computed_at, datetime)
            else datetime.fromisoformat(computed_at)
        )

        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        return (
            datetime.now(timezone.utc) - ts
            <= MAX_SCORE_AGE
        )

    except (TypeError, ValueError):
        return False


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------

def fetch_products(product_ids: list[str]) -> dict[str, dict]:
    """
    Fetch product details and precomputed scores.

    Product table is the source of truth for product information.
    Merchant rating is fetched from the Merchant table.
    """

    if not product_ids:
        return {}

    sql = """
    SELECT
        p."id",
        p."name",
        p."description",
        p."category",
        p."price",
        p."trustScore",
        p."productScore",
        p."priceValue",
        p."scamHits",
        p."contentHash",
        p."scoreVersion",
        p."scoredAt",
        p."merchantId",
        COALESCE(m."rating", 50) AS "merchantScore"
    FROM "Product" p
    LEFT JOIN "Merchant" m
        ON p."merchantId" = m."id"
    WHERE
        p."id" = ANY(%s)
        AND p."scoreVersion" = %s
    """

    with _connect() as conn:
        rows = conn.execute(
            sql,
            (product_ids, SCORE_VERSION),
        ).fetchall()

    return {
        row["id"]: row
        for row in rows
    }


# --------------------------------------------------------------------------
# Similarity search
# --------------------------------------------------------------------------

def similarity_search(
    search_text: str,
    budget: float,
    k: int = CANDIDATES_K,
) -> list[dict]:
    """
    Retrieve embedding search candidates.

    Similarity must be preserved because it is used as the
    primary relevance criterion during ranking.
    """

    raw = search_products_by_similarity(
        query=search_text,
        budget=budget * BUDGET_SLACK,
    )

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            log.exception("Could not parse similarity search response")
            return []

    products = (
        raw.get("products", [])
        if isinstance(raw, dict)
        else raw
    )

    results = []

    for product in products or []:
        if not isinstance(product, dict):
            continue

        pid = _pid(product)

        if not pid:
            continue

        similarity = product.get("similarity")

        if similarity is None:
            continue

        try:
            similarity = float(similarity)
        except (ValueError, TypeError):
            continue

        results.append({
            **product,
            "productId": pid,
            "similarity": similarity,
        })

    # Keep the most similar candidates first.
    results.sort(
        key=lambda item: item["similarity"],
        reverse=True,
    )

    return results[:k]


# --------------------------------------------------------------------------
# Ranking
# --------------------------------------------------------------------------

def rank_candidates(
    candidates: list[dict],
    budget: float,
    top_n: int = TOP_N,
) -> list[dict]:
    """
    Similarity-first ranking.

    Stage 1:
        Apply database, trust, freshness, and price checks.

    Stage 2:
        Filter out candidates that are too far below the
        highest embedding similarity.

    Stage 3:
        Rank the remaining candidates using precomputed
        quality scores and budget-dependent value.
    """

    budget = _to_float(budget)

    if not candidates:
        return []

    # Preserve the highest similarity if a product appears
    # more than once in the search results.
    similarity_by_id = {}

    for candidate in candidates:
        pid = _pid(candidate)

        if not pid:
            continue

        similarity = candidate.get("similarity")

        if similarity is None:
            continue

        try:
            similarity = float(similarity)
        except (ValueError, TypeError):
            continue

        similarity_by_id[pid] = max(
            similarity_by_id.get(pid, float("-inf")),
            similarity,
        )

    if not similarity_by_id:
        return []

    ids = list(similarity_by_id.keys())

    products = fetch_products(ids)

    eligible = []

    # ------------------------------------------------------
    # Stage 1: Validate candidates and calculate quality
    # ------------------------------------------------------

    for pid in ids:

        product = products.get(pid)

        if product is None:
            log.warning(
                "Skipping %s: no current score in Product table",
                pid,
            )
            continue

        if not _is_fresh(product["scoredAt"]):
            log.warning(
                "Skipping %s: score is stale",
                pid,
            )
            continue

        trust = _to_float(product["trustScore"])

        if trust < TRUST_THRESHOLD:
            log.info(
                "Skipping %s: trust score %.1f is below threshold",
                pid,
                trust,
            )
            continue

        price = _to_float(product["price"])

        if price <= 0:
            continue

        similarity = similarity_by_id[pid]

        merchant = _to_float(product["merchantScore"])
        quality = _to_float(product["productScore"])
        price_value = _to_float(product["priceValue"])

        budget_value = (
            100.0
            if price <= budget
            else max(
                0.0,
                100 - (
                    (price - budget) / max(budget, 1)
                ) * 100,
            )
        )

        value_score = (
            0.7 * price_value
            + 0.3 * budget_value
        )

        # This score is only used AFTER similarity filtering.
        quality_score = (
            WEIGHTS["trust"] * trust
            + WEIGHTS["merchant"] * merchant
            + WEIGHTS["product"] * quality
            + WEIGHTS["value"] * value_score
        )

        item = {
            "productId": pid,
            "title": product["name"],
            "price": price,

            # Primary relevance score.
            "similarity": round(similarity, 4),

            # Secondary quality scores.
            "trustScore": trust,
            "merchantScore": merchant,
            "productScore": quality,
            "rankScore": round(quality_score, 1),

            "rankingReasons": [
                f"Embedding similarity: {similarity:.4f}.",
                f"Listing trust score: {trust:.0f}/100.",
                f"Merchant score: {merchant:.0f}/100.",
                f"Product score: {quality:.0f}/100.",
                f"Price competitiveness: {price_value:.0f}/100.",
            ],
        }

        if price > budget:
            item["budgetNote"] = (
                f"${price:.2f} is ${price - budget:.2f} "
                f"over the ${budget:.2f} budget."
            )

        eligible.append(item)

    if not eligible:
        return []

    # ------------------------------------------------------
    # Stage 2: Similarity-first filtering
    # ------------------------------------------------------

    best_similarity = max(
        item["similarity"]
        for item in eligible
    )

    minimum_similarity = (
        best_similarity - SIMILARITY_GAP
    )

    relevant_candidates = [
        item
        for item in eligible
        if item["similarity"] >= minimum_similarity
    ]

    log.info(
        "Similarity filtering: best=%.4f, minimum=%.4f, "
        "eligible=%d, relevant=%d",
        best_similarity,
        minimum_similarity,
        len(eligible),
        len(relevant_candidates),
    )

    # ------------------------------------------------------
    # Stage 3: Quality ranking within relevant candidates
    # ------------------------------------------------------

    # Similarity has already established relevance.
    # Quality scores now decide between similarly relevant items.
    relevant_candidates.sort(
        key=lambda item: (
            -item["rankScore"],
            -item["similarity"],
            item["price"],
        )
    )

    return relevant_candidates[:top_n]


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------

def find_best(
    search_text: str,
    budget: float,
    top_n: int = TOP_N,
) -> dict:
    """
    Similarity search -> database validation -> similarity-first ranking.

    Returns:
        {
            "status": "ok" | "no_match",
            "ranked": [...]
        }
    """

    candidates = similarity_search(
        search_text,
        budget,
    )

    ranked = (
        rank_candidates(
            candidates,
            budget,
            top_n,
        )
        if candidates
        else []
    )

    return {
        "status": "ok" if ranked else "no_match",
        "ranked": ranked,
    }
