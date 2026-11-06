import asyncio
import os
from typing import Any, Dict, List, Optional

import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from smolagents import Tool
from dotenv import load_dotenv
import json

load_dotenv()

# JSON Schema type -> smolagents authorized type
_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
    "null": "null",
}


def _convert_schema(details: Dict[str, Any]) -> Dict[str, Any]:
    schema_type = details.get("type")

    if isinstance(schema_type, list):
        schema_type = next(
            (t for t in schema_type if t != "null"),
            "any"
        )

    result = {
        "type": _TYPE_MAP.get(schema_type, "any"),
        "description": details.get(
            "description",
            "No description provided."
        ),
    }

    # Preserve array item definitions
    if schema_type == "array" and "items" in details:
        result["items"] = _convert_schema(details["items"])

    # Preserve nested object definitions
    if schema_type == "object":
        properties = details.get("properties", {})
        required = set(details.get("required", []))

        result["properties"] = {
            name: _convert_schema(prop)
            for name, prop in properties.items()
        }

        result["required"] = list(required)

    return result


def _result_to_text(result) -> str:
    """Convert an MCP CallToolResult into a plain string for the LLM."""
    parts = []
    for item in getattr(result, "content", []) or []:
        if getattr(item, "type", None) == "text":
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts)


class PayPalMCPTool(Tool):
    skip_forward_signature_validation = True

    def __init__(
        self,
        client: "PayPalMCPClient",
        name: str,
        description: str,
        inputs: Dict[str, Dict[str, Any]],
    ):
        self.client = client
        self.name = name
        self.description = description
        self.inputs = inputs
        self.output_type = "string"
        super().__init__()

    def forward(self, **kwargs) -> str:
        arguments = {k: v for k, v in kwargs.items() if v is not None}
        result = asyncio.run(
            self.client.call_tool(self.name, arguments)
        )
        return _result_to_text(result)


class PayPalMCPClient:
    def __init__(self):
        # Configuration from environment variables
        self.client_id = os.getenv("PAYPAL_CLIENT_ID")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
        self.env = os.getenv("PAYPAL_ENVIRONMENT", "SANDBOX").upper()
        self._cached_token: Optional[str] = None

        # Base URL for OAuth
        self.auth_url = (
            "https://api-m.sandbox.paypal.com/v1/oauth2/token"
            if self.env == "SANDBOX"
            else "https://api-m.paypal.com/v1/oauth2/token"
        )

    # ------------------------------------------------------------------ auth
    def _fetch_access_token(self) -> str:
        """Requests a new access token from PayPal using Client ID and Secret."""
        if not self.client_id or not self.client_secret:
            raise ValueError("PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET must be set in environment variables.")

        response = requests.post(
            self.auth_url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "client_credentials"},
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to fetch PayPal token: {response.text}")

        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("PayPal token response did not contain an access_token.")

        self._cached_token = token
        return token

    def get_current_token(self) -> str:
        """Returns the cached token or fetches a new one if necessary."""
        if not self._cached_token:
            return self._fetch_access_token()
        return self._cached_token

    @property
    def server_params(self) -> StdioServerParameters:
        """Generates server parameters with the most current token."""
        # Merge with the current environment so npx can find node/PATH
        env = {
            **os.environ,
            "PAYPAL_ACCESS_TOKEN": self.get_current_token(),
            "PAYPAL_ENVIRONMENT": self.env,
        }
        return StdioServerParameters(
            command="npx",
            args=["-y", "@paypal/mcp", "--tools=all"],
            env=env,
        )

    # -------------------------------------------------------------- MCP calls
    @staticmethod
    def _looks_unauthorized(text: str) -> bool:
        text = text.lower()
        return "401" in text or "unauthorized" in text or "expired" in text

    async def _call_once(self, tool_name: str, arguments: dict):
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool(tool_name, arguments)

    async def call_tool(self, tool_name: str, arguments: dict):
        """
        Low-level call to the MCP server.
        Connects, initializes, executes the tool, and closes the session.
        Retries once with a fresh token if the call looks unauthorized.
        """
        try:
            result = await self._call_once(tool_name, arguments)
            # MCP servers often report errors in the result instead of raising
            if getattr(result, "isError", False) and self._looks_unauthorized(_result_to_text(result)):
                self._cached_token = None
                return await self._call_once(tool_name, arguments)
            return result
        except Exception as e:
            if self._looks_unauthorized(str(e)):
                # Token might have expired, clear cache and retry once
                self._cached_token = None
                return await self._call_once(tool_name, arguments)
            raise

    
    def get_dynamic_tools(self) -> List[Tool]:
        """
        Fetch only create_order and capture_order from PayPal MCP.
        Preserve their original MCP input schemas.
        """

        ALLOWED_TOOLS = {
            "create_order",
            "pay_order",
        }

        TOOL_DESCRIPTIONS = {
            "create_order": (
                "Creates a new PayPal checkout order. "
                "Use this when a customer wants to purchase a product. "
                "Requires intent and purchase_units containing amount details. "
                "Use intent='CAPTURE'. Returns an order ID and approval URL. "
                "Creating an order does NOT charge the customer. "
                "The customer must approve the order before it can be captured."
            ),
            "pay_order": (
                "Captures payment for an existing PayPal order after the buyer "
                "has approved it. Requires order_id, which is the ID returned "
                "by create_order. Only call this after receiving confirmation "
                "that the buyer has approved the order. Returns capture details "
                "including payment status and capture ID."
            ),
        }

        async def fetch_tools():
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    return await session.list_tools()

        try:
            tools_response = asyncio.run(fetch_tools())
            mcp_tools = tools_response.tools
        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch PayPal MCP tools: {e}"
            ) from e

        generated_tools: List[Tool] = []
        # print(mcp_tools)
        for mcp_tool in mcp_tools:
            if mcp_tool.name not in ALLOWED_TOOLS:
                continue

            schema = getattr(mcp_tool, "inputSchema", None) or {}
            properties = schema.get("properties", {}) or {}
            required = set(schema.get("required", []) or [])

            inputs: Dict[str, Dict[str, Any]] = {}

            for arg_name, details in properties.items():
                spec = _convert_schema(details)

                if arg_name not in required:
                    spec["nullable"] = True

                inputs[arg_name] = spec

            generated_tools.append(
                PayPalMCPTool(
                    client=self,
                    name=mcp_tool.name,
                    description=TOOL_DESCRIPTIONS[mcp_tool.name],
                    inputs=inputs,
                )
            )

        found = {tool.name for tool in generated_tools}
        missing = ALLOWED_TOOLS - found

        if missing:
            raise RuntimeError(
                f"PayPal MCP is missing required tools: {missing}"
            )

        return generated_tools


if __name__ == "__main__":

    client = PayPalMCPClient()

    tools = client.get_dynamic_tools()

    for tool in tools:
        if tool.name == "create_order":
            print(json.dumps(tool.inputs, indent=2))