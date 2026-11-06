import os
import psycopg
from pgvector.psycopg import register_vector
from smolagents import tool
from .embedding import generate_embedding
from dotenv import load_dotenv
from pgvector import Vector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


@tool
def search_products_by_similarity(
    query: str,
    budget: float | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Search for products matching a natural language user query using semantic search,
    optionally restricted to a maximum price.
    Useful when customers describe features, uses, or types of products they want.
    Args:
        query: Keywords describing what the customer wants, such as "running shoes". Do not include the price here.
        budget: Maximum price (in USD) a product may cost. Products above it are excluded. Omit for no price limit.
        limit: Maximum number of matching products to return. Defaults to 5.
    """
    query_vector = Vector(generate_embedding(query))
    max_price = float(budget) if budget is not None else None

    sql = """
        SELECT
            "id",
            "name",
            "description",
            "price",
            "merchantId",
            1 - ("embeddedString" <=> %s) AS similarity_score
        FROM "Product"
        WHERE "embeddedString" IS NOT NULL
          AND (%s::float IS NULL OR "price" <= %s::float)
        ORDER BY "embeddedString" <=> %s ASC
        LIMIT %s;
    """

    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(sql, (query_vector, max_price, max_price, query_vector, limit))
            rows = cur.fetchall()

    return [
        {
            "id": row[0],
            "title": row[1],
            "description": row[2],
            "price": float(row[3]) if row[3] is not None else None,
            "merchant": row[4],
            "similarity": round(float(row[5]), 3),
        }
        for row in rows
    ]


if __name__ == "__main__":
    print(search_products_by_similarity("Kitchen Accessories", budget=1000))