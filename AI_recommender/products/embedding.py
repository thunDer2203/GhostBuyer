from functools import lru_cache
from pydantic import BaseModel, Field

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


@lru_cache(maxsize=1)
def _get_model():
    # Imported and loaded lazily so the server opens its port fast
    from fastembed import TextEmbedding
    return TextEmbedding(MODEL_ID, cache_dir="./models")


def generate_embedding(text: str) -> list[float]:
    return next(iter(_get_model().embed([text]))).tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    return [v.tolist() for v in _get_model().embed(texts)]


def build_product_search_text(name: str, description: str, category: str | None = None) -> str:
    return (
        f"Product: {name}. "
        f"Description: {description}. "
        f"Category: {category or 'Not specified'}."
    )