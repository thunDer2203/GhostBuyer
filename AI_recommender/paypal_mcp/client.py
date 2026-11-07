import json
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
        "Creates ONE PayPal checkout order for a single product. Creating an order does "
        "NOT charge the buyer; they must approve it on PayPal first. Returns a JSON string: "
        'on success {"paypal_order_id": "...", "approval_url": "..."}, '
        'on failure {"status": "payment_failed", "message": "..."}.'
    )
    inputs = {
        "product_id": {"type": "string", "description": "The productId exactly as given."},
        "title": {"type": "string", "description": "The product title exactly as given."},
        "price": {"type": "number", "description": "Price in USD as a plain number, e.g. 25.5."},
    }
    output_type = "string"

    def __init__(self, client):
        super().__init__()
        self.client = client

    def forward(self, product_id: str, title: str, price: float) -> str:
        backend = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
        body = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": product_id,
                "custom_id": product_id,
                "description": title[:127],
                "amount": {"currency_code": "USD", "value": f"{float(price):.2f}"},
            }],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": f"{backend}/checkout/return",
                        "cancel_url": f"{backend}/checkout/cancel",
                        "user_action": "PAY_NOW",
                        "shipping_preference": "NO_SHIPPING",
                    }
                }
            },
        }
        r = self.client.request("POST", "/v2/checkout/orders", json=body)
        if not r.ok:
            print("PAYPAL ERROR:", r.status_code, r.text, flush=True)
            return json.dumps({"status": "payment_failed",
                               "message": f"PayPal error {r.status_code}: {r.text}"})
        data = r.json()
        approve = next(
            (l["href"] for l in data.get("links", []) if l["rel"] in ("payer-action", "approve")),
            None,
        )
        return json.dumps({"paypal_order_id": data["id"], "approval_url": approve})

    
def get_paypal_tools():
    client = PayPalClient()
    return [CreateOrderTool(client)]