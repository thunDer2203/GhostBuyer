import json
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg
from smolagents import CodeAgent, LogLevel, OpenAIModel, tool

from .scoring import calculate_metrics, calculate_reliability_score

# from phoenix.otel import register
# from openinference.instrumentation.smolagents import SmolagentsInstrumentor

# # Register Phoenix as the trace destination
# tracer_provider = register(
#     project_name="paypal-hackathon-manager-agent"
# )

# # Instrument smolagents
# SmolagentsInstrumentor().instrument(
#     tracer_provider=tracer_provider
# )

def fetch_json(url: str) -> dict | list:
    import urllib.request
    import urllib.error

    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"API request failed: {url}") from exc

@tool
def fetch_merchants_to_refresh() -> list[dict]:
    """
    Fetch merchants whose reliability scores need refreshing.

    Returns:
        A list of merchant records, each containing a merchant ID.
    """
    api_url = os.getenv("API_URL")
    if not api_url:
        raise ValueError("API_URL is not configured.")

    data = fetch_json(f"{api_url}/merchants/getMerchantToRefresh")

    if not isinstance(data, list):
        raise ValueError("Expected a list of merchants.")

    return data


def update_merchant_rating(merchant_id: str, rating: int) -> None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL is not configured.")

    query = """
        UPDATE "Merchant"
        SET
            "rating" = %s,
            "lastRatingDate" = CURRENT_TIMESTAMP
        WHERE "id" = %s;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, (rating, merchant_id))

            if cursor.rowcount == 0:
                raise ValueError(
                    f"Merchant not found: {merchant_id}"
                )


@tool
def collect_merchant_order_evidence(merchant_id: str) -> dict:
    """
    Fetch a merchant's orders and calculate order-performance metrics.

    Args:
        merchant_id: The unique ID of the merchant whose orders
            need to be fetched and analyzed.

    Returns:
        A dictionary containing order metrics and product metrics.
    """
    api_url = os.getenv("API_URL")
    if not api_url:
        raise ValueError("API_URL is not configured.")

    orders = fetch_json(
        f"{api_url}/orders/getOrdersFromMerchantId?merchantId={merchant_id}"
    )

    if not isinstance(orders, list):
        raise ValueError("Expected a list of orders.")

    merchant_metrics, product_metrics = calculate_metrics(orders)

    return {
        "merchantId": merchant_id,
        "orderMetrics": merchant_metrics,
        "productMetrics": product_metrics,
    }





@tool
def score_merchant_reliability(metrics: dict) -> dict:
    """
    Calculate a merchant's reliability score and save it
    to PostgreSQL.

    Args:
        metrics: Complete evidence returned by
            collect_merchant_order_evidence.
    """
    merchant_id = metrics["merchantId"]

    # Extract the actual MerchantMetrics dictionary.
    order_metrics = metrics["orderMetrics"]

    # Calculate reliability.
    result = calculate_reliability_score(order_metrics)

    # Persist the score.
    update_merchant_rating(
        merchant_id=merchant_id,
        rating=result["score"]
    )

    return {
        "merchantId": merchant_id,
        "orderMetrics": order_metrics,
        "productMetrics": metrics["productMetrics"],
        "reliability": result,
        "ratingSaved": result["score"],
        "databaseUpdated": True
    }



def build_merchant_agent():
    skill_path = Path(__file__).with_name("skill.md")
    skill_instructions = skill_path.read_text(encoding="utf-8")

    model = OpenAIModel(
            model_id="gpt-oss:120b",
            api_base="https://ollama.com/v1",
            api_key=os.environ["OLLAMA_API_KEY"],
        )

    return CodeAgent(
        tools=[fetch_merchants_to_refresh, collect_merchant_order_evidence, score_merchant_reliability],
        model=model,
        additional_authorized_imports=["collections", "json", "pathlib", "urllib"],
        verbosity_level=LogLevel.OFF,
        instructions=f"""
        {skill_instructions}

        ## Execution requirements

        1. Start by calling fetch_merchants_to_refresh().
        2. For every returned merchant:
           a. Call collect_merchant_order_evidence(merchant_id) to get metrics.
           b. Pass those metrics to score_merchant_reliability() to get the final score, risk, and confidence.
        3. Do not invent unavailable product quantities, tenure, or other metrics.
        4. Return one valid JSON result per merchant containing both the raw metrics and the final reliability score.
        5. The score_merchant_reliability() tool automatically saves
           the calculated score into the merchant's rating column.
           Do not attempt to update the rating separately.
        6. Only report a merchant as successfully processed if the
           database update succeeds.
        """,
    )

if __name__ == "__main__":
    load_dotenv()
    agent = build_merchant_agent()
    result = agent.run("Give merchant reliability scores.")
    print(json.dumps(result, indent=2))
