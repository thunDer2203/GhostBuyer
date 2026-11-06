from typing import List, Dict, Any

SCAM_PHRASES = [
    "today only", "hurry", "limited stock", "no returns", "pay within",
    "contact seller", "chat to confirm", "same as the top brands",
]

MARKETPLACE_DOMAINS = {"DummyJSON Store": ["dummyjson.com"]}

# Ranking Weights
WEIGHTS = {
    "trust": 0.30,
    "merchant": 0.25,
    "product": 0.20,
    "value": 0.25
}

# Scoring Thresholds
TRUST_THRESHOLD = 35
MERCHANT_LOW_RISK_THRESHOLD = 75
MERCHANT_MEDIUM_RISK_THRESHOLD = 50
PRODUCT_LOW_RISK_RATING = 4.2
PRODUCT_MEDIUM_RISK_RATING = 3.3
PRODUCT_CONFIDENCE_HIGH = 50
PRODUCT_CONFIDENCE_MEDIUM = 10
