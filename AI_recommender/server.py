"""
server.py - HTTP wrapper so the TypeScript backend can call the agent pipeline.

Run (from the folder containing agents.py and products.json):
    pip install fastapi uvicorn
    uvicorn server:app --host 127.0.0.1 --port 8000

Endpoints:
    POST /ai/recommend   body: {"query": "running shoes", "budget": 100}
    GET  /health
"""

import threading
from typing import Optional


from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from products.agents import run_shopping_request
from products.embedding import ProductEmbeddingRequest, ProductEmbeddingResponse,generate_embedding,build_product_search_text
from json_parser import parse_agent_output
app = FastAPI(title="Shopping agent service")

# The free Ollama plan allows one concurrent cloud model, and agent runs are slow.
# Serialize runs so two requests don't collide or burn the quota twice as fast.
_run_lock = threading.Lock()


class RecommendRequest(BaseModel):
    query: str = Field(min_length=2, max_length=200)
    auto_pay: bool = False


class Recommendation(BaseModel):
    status: Optional[str]=None
    productId: str
    title: str
    price: float
    # trustScore: float
    rankingReasons: list[str]
    paypal_order_id: Optional[str] = None
    approval_url: Optional[str] = None




def run_pipeline(query: str, auto_pay: bool):
    return run_shopping_request(query,auto_pay)


@app.post("/ai/recommend", response_model=list[Recommendation])
def recommend(req: RecommendRequest):
    with _run_lock:
        last_error = None
        # Retrying re-runs the pipeline, so only do it when no PayPal order can exist yet.
        attempts = 1 if req.auto_pay else 2
        for _ in range(attempts):
            result = run_pipeline(req.query, req.auto_pay)
            print(result)
            try:
                items = parse_agent_output(result)
                return [Recommendation(**item) for item in items]  # [] = no matching product
            except Exception as e:
                last_error = e
        raise HTTPException(status_code=502, detail=f"Agent returned invalid output: {last_error}")



@app.post("/ai/embed-product", response_model=ProductEmbeddingResponse)
def embed_product(req: ProductEmbeddingRequest):
    product_text = build_product_search_text(req.name, req.description, req.category)
    vector = generate_embedding(product_text)

    return ProductEmbeddingResponse(
        productId=req.productId,
        embedding=vector,
        dimensions=len(vector),
    )


@app.get("/health")
def health():
    return {"ok": True}

# @app.post("/ai/capture")
# def capture_payment(order_id: str):
#     with _run_lock:
#         manager = build_manager()
#         prompt = f"The user has approved payment for order {order_id}. Please capture the payment now."
#         try:
#             result = manager.run(prompt)
#             return {"status": "success", "result": result}
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))