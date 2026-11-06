import ast
import re
import json


def parse_agent_output(result) -> list[dict]:
    """Extract and normalize JSON from agent output."""

    data = result

    if not isinstance(data, (dict, list)):
        text = str(result).strip()

        # 1. Extract JSON from ```json ... ``` block
        match = re.search(
            r"```json\s*(.*?)\s*```",
            text,
            flags=re.DOTALL | re.IGNORECASE
        )

        if match:
            text = match.group(1).strip()
        else:
            # 2. Remove Final answer prefix
            text = re.sub(r"^Final answer:\s*", "", text)

            # 3. Remove generic markdown code fences
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.M).strip()

        # 4. Parse JSON
        data = None

        for loader in (json.loads, ast.literal_eval):
            try:
                data = loader(text)
                break
            except (ValueError, SyntaxError, TypeError):
                continue

        # 5. Fallback: extract outermost object or array
        if data is None:
            for open_c, close_c in (("{", "}"), ("[", "]")):
                start = text.find(open_c)
                end = text.rfind(close_c)

                if start != -1 and end > start:
                    extracted = text[start:end + 1]

                    for loader in (json.loads, ast.literal_eval):
                        try:
                            data = loader(extracted)
                            break
                        except (ValueError, SyntaxError, TypeError):
                            continue

                if data is not None:
                    break

        if data is None:
            raise ValueError(
                f"No JSON object or array found in agent output: {text!r}"
            )

    # 6. Normalize response
    if isinstance(data, dict):
        if data.get("status") == "no_match" or not data.get("productId"):
            return []
        return [data]

    if isinstance(data, list):
        return [
            d for d in data
            if isinstance(d, dict)
            and d.get("productId")
            and d.get("status") != "no_match"
        ]

    raise ValueError("Agent output must be a JSON object or array")