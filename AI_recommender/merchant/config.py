# Order Statuses
STATUS_DELIVERED = "delivered"
STATUS_RETURNED = "returned"
STATUS_PENDING = "pending"
STATUS_CANCELLED = "cancelled"

KNOWN_STATUSES = {STATUS_DELIVERED, STATUS_RETURNED, STATUS_PENDING, STATUS_CANCELLED}

# Scoring Weights
# How much each metric contributes to the final reliability score (0-100)
RELIABILITY_WEIGHTS = {
    "fulfillment_rate": 0.7,
    "return_rate_penalty": 0.3,
}

# Scoring Thresholds
MIN_ORDERS_FOR_HIGH_CONFIDENCE = 20
MIN_ORDERS_FOR_MEDIUM_CONFIDENCE = 5
