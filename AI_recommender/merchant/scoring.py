from typing import TypedDict, List, Dict, Any, Optional, Tuple
from .config import (
    STATUS_DELIVERED,
    STATUS_RETURNED,
    STATUS_PENDING,
    STATUS_CANCELLED,
    KNOWN_STATUSES,
    RELIABILITY_WEIGHTS,
    MIN_ORDERS_FOR_HIGH_CONFIDENCE,
    MIN_ORDERS_FOR_MEDIUM_CONFIDENCE
)

class MerchantMetrics(TypedDict):
    totalOrders: int
    fulfilledOrders: int
    returnedOrders: int
    pendingOrders: int
    cancelledOrders: int
    unknownStatusOrders: int
    fulfillmentRate: Optional[float]
    returnRate: Optional[float]

class ProductMetrics(TypedDict):
    totalProducts: int
    deliveredProducts: int
    returnedProducts: int
    cancelledProducts: int
    pendingProducts: int
    unknownStatusProducts: int

class MerchantReliabilityScore(TypedDict):
    score: int
    risk: str
    confidence: str
    reason: str

def calculate_metrics(orders: List[Dict[str, Any]]) -> Tuple[MerchantMetrics, ProductMetrics]:
    """Calculate order and product metrics from raw order data."""
    if not orders:
        return {
            "totalOrders": 0, "fulfilledOrders": 0, "returnedOrders": 0,
            "pendingOrders": 0, "cancelledOrders": 0, "unknownStatusOrders": 0,
            "fulfillmentRate": None, "returnRate": None
        }, {
            "totalProducts": 0, "deliveredProducts": 0, "returnedProducts": 0,
            "cancelledProducts": 0, "pendingProducts": 0, "unknownStatusProducts": 0
        }

    from collections import Counter
    statuses = Counter(
        str(order.get("orderStatus", "unknown")).strip().lower()
        for order in orders
    )

    total = len(orders)
    fulfilled = statuses[STATUS_DELIVERED]
    returned = statuses[STATUS_RETURNED]
    pending = statuses[STATUS_PENDING]
    cancelled = statuses[STATUS_CANCELLED]

    known_count = sum(statuses[s] for s in KNOWN_STATUSES)
    unknown = total - known_count

    resolved = fulfilled + returned + cancelled

    metrics: MerchantMetrics = {
        "totalOrders": total,
        "fulfilledOrders": fulfilled,
        "returnedOrders": returned,
        "pendingOrders": pending,
        "cancelledOrders": cancelled,
        "unknownStatusOrders": unknown,
        "fulfillmentRate": round(fulfilled / resolved, 4) if resolved else None,
        "returnRate": round(returned / resolved, 4) if resolved else None,
    }

    quantities = Counter()
    for order in orders:
        status = str(order.get("orderStatus", "unknown")).strip().lower()
        quantity = order.get("quantity", 0)
        if isinstance(quantity, int) and not isinstance(quantity, bool) and quantity >= 0:
            quantities[status] += quantity

    total_products = sum(quantities.values())

    prod_metrics: ProductMetrics = {
        "totalProducts": total_products,
        "deliveredProducts": quantities[STATUS_DELIVERED],
        "returnedProducts": quantities[STATUS_RETURNED],
        "cancelledProducts": quantities[STATUS_CANCELLED],
        "pendingProducts": quantities[STATUS_PENDING],
        "unknownStatusProducts": total_products - sum(quantities[s] for s in KNOWN_STATUSES),
    }

    return metrics, prod_metrics

def calculate_reliability_score(metrics: MerchantMetrics) -> MerchantReliabilityScore:
    """Convert raw metrics into a 0-100 reliability score."""
    total = metrics["totalOrders"]
    f_rate = metrics["fulfillmentRate"] or 0.0
    r_rate = metrics["returnRate"] or 0.0

    # Determine Confidence
    if total >= MIN_ORDERS_FOR_HIGH_CONFIDENCE:
        confidence = "HIGH"
    elif total >= MIN_ORDERS_FOR_MEDIUM_CONFIDENCE:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # Calculate Base Score
    # High fulfillment increases score, high return rate decreases it.
    # Fulfillment weight: 70%, Return rate penalty: 30%
    fulfillment_component = f_rate * 100 * RELIABILITY_WEIGHTS["fulfillment_rate"]
    return_penalty = r_rate * 100 * RELIABILITY_WEIGHTS["return_rate_penalty"]

    score = round(fulfillment_component - return_penalty + 30) # Start with a base of 30
    score = max(0, min(100, score))

    # Risk assessment
    if score >= 75:
        risk = "LOW"
    elif score >= 50:
        risk = "MEDIUM"
    else:
        risk = "HIGH"

    reason = f"Score based on {metrics['totalOrders']} orders, fulfillment rate {f_rate:.2%}, return rate {r_rate:.2%}."

    return {
        "score": int(score),
        "risk": risk,
        "confidence": confidence,
        "reason": reason
    }
