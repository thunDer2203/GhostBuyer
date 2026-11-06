import os
import numpy as np
from huggingface_hub import InferenceClient
from pydantic import BaseModel, Field

_client = InferenceClient(token=os.environ["HF_TOKEN"], timeout=30)
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"


class ProductEmbeddingRequest(BaseModel):
    productId: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)
    category: str | None = None


class ProductEmbeddingResponse(BaseModel):
    productId: str
    embedding: list[float]
    dimensions: int


def generate_embedding(text: str) -> list[float]:
    out = _client.feature_extraction(text, model=MODEL_ID)
    return np.asarray(out, dtype=float).reshape(-1).tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch version: one API call for many products (use this when seeding)."""
    out = _client.feature_extraction(texts, model=MODEL_ID)
    return np.asarray(out, dtype=float).tolist()


def build_product_search_text(name: str, description: str, category: str | None = None) -> str:
    return (
        f"Product: {name}. "
        f"Description: {description}. "
        f"Category: {category or 'Not specified'}."
    )