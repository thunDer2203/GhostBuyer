import os
import time
import requests
from smolagents import Tool
from dotenv import load_dotenv

load_dotenv()


class PayPalClient:
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        env = os.getenv("PAYPAL_ENVIRONMENT", "SANDBOX").upper()
        self.base = (
            "https://api-m.sandbox.paypal.com"
            if env == "SANDBOX"
            else "https://api-m.paypal.com"
        )
        self._token = None
        self._expires_at = 0.0
        self._http = requests.Session()


    def _get_token(self, force=False) -> str:
        if not force and self._token and time.time() < self._expires_at - 60:
            return self._token
        r = self._http.post(
            f"{self.base}/v1/oauth2/token",
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 300)
        return self._token

    def request(self, method: str, path: str, json=None):
        for attempt in range(2):
            r = self._http.request(
                method,
                f"{self.base}{path}",
                json=json,
                headers={"Authorization": f"Bearer {self._get_token(force=attempt == 1)}"},
                timeout=30,
            )
            if r.status_code != 401:
                break
        return r


class CreateOrderTool(Tool):
    name = "create_order"
    description = (
        "Creates a new PayPal checkout order. Use when a customer wants to purchase "
        "a product. Creating an order does NOT charge the customer; they must approve "
        "it first. Returns the order ID and approval URL."
    )
    inputs = {
        "purchase_units": {
            "type": "array",
            "description": "List of purchase units, e.g. "
            "[{'amount': {'currency_code': 'USD', 'value': '25.00'}}]",
        },
        "intent": {
            "type": "string",
            "description": "Always 'CAPTURE'.",
            "nullable": True,
        },
    }
    output_type = "string"  


    def __init__(self, client: PayPalClient):
        super().__init__()
        self.client = client

    def forward(self, purchase_units, intent="CAPTURE") -> str:
        BACKEND_URL = os.environ.get("BACKEND_URL", "localhost:8000")

        RETURN_URL = f"{BACKEND_URL}/checkout/return"
        CANCEL_URL = f"{BACKEND_URL}/checkout/cancel"
        body = {
            "intent": intent or "CAPTURE",
            "purchase_units": purchase_units,
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": RETURN_URL,
                        "cancel_url": CANCEL_URL,
                        "user_action": "PAY_NOW",
                        "shipping_preference": "NO_SHIPPING",
                        "brand_name": "GhostBuyer",
                    }
                }
            },
        }
        r = self.client.request("POST", "/v2/checkout/orders", json=body)

def get_paypal_tools():
    client = PayPalClient()
    return [CreateOrderTool(client)]