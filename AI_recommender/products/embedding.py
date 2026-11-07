from functools import lru_cache
from pydantic import BaseModel, Field
import threading
from pathlib import Path

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_DIR = str(Path(__file__).parent / "models") 


_model = None
_lock = threading.Lock()

class ProductEmbeddingRequest(BaseModel):
    productId: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=500)
    description: str = Field(min_length=1, max_length=10000)
    category: str | None = None


class ProductEmbeddingResponse(BaseModel):
    productId: str
    embedding: list[float]
    dimensions: int


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed import TextEmbedding
                _model = TextEmbedding(MODEL_ID, cache_dir=CACHE_DIR, threads=1)
    return _model


def generate_embedding(text: str) -> list[float]:
    return next(iter(_get_model().embed([text[:4000]], batch_size=1))).tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _get_model().embed(texts, batch_size=8)]


def build_product_search_text(name: str, description: str, category: str | None = None) -> str:
    return (
        f"Product: {name}. "
        f"Description: {description}. "
        f"Category: {category or 'Not specified'}."
    )