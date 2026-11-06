from typing import TypedDict, Optional, Tuple, List, Dict, Any
from .config import (
    MERCHANT_LOW_RISK_THRESHOLD,
    MERCHANT_MEDIUM_RISK_THRESHOLD,
    PRODUCT_LOW_RISK_RATING,
    PRODUCT_MEDIUM_RISK_RATING,
    PRODUCT_CONFIDENCE_HIGH,
    PRODUCT_CONFIDENCE_MEDIUM
)

class MerchantScoreResult(TypedDict):
    merchantScore: int
    merchantRisk: str
    merchantConfidence: str
    merchantReason: str

class ProductScoreResult(TypedDict):
    productScore: int
    productRisk: str
    reviewRating: Optional[float]
    reviewCount: int
    reviewConfidence: str
    productRiskReason: str

class TrustScoreResult(TypedDict):
    trustScore: int
    trustReasons: List[str]

def _first(item: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first non-None value from alternative dictionary keys."""
    for key in keys:
        if item.get(key) is not None:
            return item[key]
    return default

def calculate_merchant_score(product: Dict[str, Any]) -> MerchantScoreResult:
    """Score the merchant from the stored merchant rating attached to the product."""
    rating = product.get("merchantRating")

    if rating is None:
        return {
            "merchantScore": 50,
            "merchantRisk": "MEDIUM",
            "merchantConfidence": "LOW",
            "merchantReason": "No merchant rating available.",
        }

    try:
        score = max(0, min(100, round(float(rating))))
    except (TypeError, ValueError):
        score = 50

    risk = "LOW" if score >= MERCHANT_LOW_RISK_THRESHOLD else "MEDIUM" if score >= MERCHANT_MEDIUM_RISK_THRESHOLD else "HIGH"
    return {
        "merchantScore": score,
        "merchantRisk": risk,
        "merchantConfidence": "MEDIUM",
        "merchantReason": f"Stored merchant rating: {score}/100.",
    }

def _extract_review_data(product: Dict[str, Any]) -> Tuple[Optional[float], int]:
    reviews = product.get("reviews")
    rating = _first(product, "rating", "averageRating", "average_rating", default=None)
    count = _first(product, "reviewCount", "review_count", "reviewsCount", default=None)

    if isinstance(reviews, list):
        ratings = [
            float(r.get("rating"))
            for r in reviews
            if isinstance(r, dict) and r.get("rating") is not None
        ]
        if ratings:
            rating = sum(ratings) / len(ratings)
        if count is None:
            count = len(reviews)

    try:
        rating = float(rating) if rating is not None else None
    except (TypeError, ValueError):
        rating = None
    try:
        count = max(int(count), 0) if count is not None else 0
    except (TypeError, ValueError):
        count = 0

    return rating, count

def calculate_product_score(product: Dict[str, Any]) -> ProductScoreResult:
    rating, review_count = _extract_review_data(product)
    is_new = bool(_first(product, "isNewProduct", "is_new_product", default=False))

    if review_count == 0 and rating is None:
        is_new = True

    if is_new:
        risk = "MEDIUM"
        confidence = "LOW"
        score = 55
        reason = "New or unreviewed product; medium initial risk because there is little evidence."
    elif rating is None:
        risk = "MEDIUM"
        confidence = "LOW"
        score = 55
        reason = "Product rating is unavailable; review confidence is low."
    else:
        rating_score = max(0, min(100, (rating / 5) * 100))
        evidence_factor = min(1.0, review_count / PRODUCT_CONFIDENCE_HIGH)
        score = round(50 + (rating_score - 50) * evidence_factor)
        confidence = "HIGH" if review_count >= PRODUCT_CONFIDENCE_HIGH else ("MEDIUM" if review_count >= PRODUCT_CONFIDENCE_MEDIUM else "LOW")

        if rating >= PRODUCT_LOW_RISK_RATING and review_count >= 10:
            risk = "LOW"
        elif rating >= PRODUCT_MEDIUM_RISK_RATING:
            risk = "MEDIUM"
        else:
            risk = "HIGH"
        reason = f"Average rating {rating:.1f}/5 from {review_count} review(s)."

    return {
        "productScore": int(score),
        "productRisk": risk,
        "reviewRating": rating,
        "reviewCount": review_count,
        "reviewConfidence": confidence,
        "productRiskReason": reason,
    }

def calculate_trust_score(price_ratio: float, scam_hits: int, reference_found: bool) -> TrustScoreResult:
    """Compute a deterministic listing trust score from 0 to 100."""
    score, reasons = 100, []
    if not reference_found:
        score = 60
        reasons.append("No reference price found; price could not be verified.")
    elif price_ratio < 0.6:
        score -= 25
        reasons.append("Price is unusually low compared with the reference market.")
    elif price_ratio > 1.5:
        score -= 10
        reasons.append("Price is substantially above the reference market.")

    if scam_hits:
        score -= min(10 * scam_hits, 25)
        reasons.append(f"{scam_hits} suspicious sales phrase(s) found.")

    return {"trustScore": max(int(score), 0), "trustReasons": reasons}
