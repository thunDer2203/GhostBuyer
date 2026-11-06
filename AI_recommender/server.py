
import threading
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from json_parser import parse_agent_output

app = FastAPI(title="Shopping agent service")

_run_lock = threading.Lock()


class RecommendRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    auto_pay: bool = False


class Recommendation(BaseModel):
    status: Optional[str] = None
    productId: str
    title: str
    price: float
    rankingReasons: list[str]
    paypal_order_id: Optional[str] = None
    approval_url: Optional[str] = None


def run_pipeline(query: str, auto_pay: bool):
    # Load agent dependencies only when recommendation is requested.
    from products.agents import run_shopping_request
    return run_shopping_request(query, auto_pay)


@app.post("/ai/recommend", response_model=list[Recommendation])
def recommend(req: RecommendRequest):
    with _run_lock:
        attempts = 1 if req.auto_pay else 2
        last_error = None

        for _ in range(attempts):
            result = run_pipeline(req.query, req.auto_pay)

            try:
                items = parse_agent_output(result)
                return [Recommendation(**item) for item in items]
            except Exception as e:
                last_error = e

        raise HTTPException(
            status_code=502,
            detail=f"Agent returned invalid output: {last_error}"
        )


@app.post("/ai/embed-product")
def embed_product(req: dict):
    from products.embedding import (
        ProductEmbeddingRequest,
        ProductEmbeddingResponse,
        generate_embedding,
        build_product_search_text,
    )

    validated = ProductEmbeddingRequest(**req)

    product_text = build_product_search_text(
        validated.name,
        validated.description,
        validated.category
    )

    vector = generate_embedding(product_text)

    return ProductEmbeddingResponse(
        productId=validated.productId,
        embedding=vector,
        dimensions=len(vector),
    )


@app.get("/health")
def health():
    return {"ok": True}
