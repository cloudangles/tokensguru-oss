"""Load a saved TokenGuru prompt, render {{variables}}, and call its model.

Required environment variables: TOKENGURU_URL, TOKENGURU_API_KEY,
TOKENGURU_PROMPT_ID. TOKENGURU_MODEL is only needed when the prompt version
does not have a model selected.
"""

from __future__ import annotations

import os
import re
from typing import Mapping

import tokenguru_client as tg


VARIABLE = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_.-]*)\s*\}\}")


def render_prompt(template: str, values: Mapping[str, object]) -> str:
    """Replace supported {{name}} placeholders and fail on missing values."""
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise KeyError(f"Missing prompt variable: {name}")
        value = values[name]
        if not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"Prompt variable {name!r} must be a scalar value")
        return str(value)

    rendered = VARIABLE.sub(replace, template)
    unresolved = VARIABLE.search(rendered)
    if unresolved:
        raise ValueError(f"Unsupported prompt variable syntax: {unresolved.group(0)}")
    return rendered


def main() -> None:
    tg.connect(os.environ["TOKENGURU_URL"], os.environ["TOKENGURU_API_KEY"])
    prompt = tg.prompts.get_active_version(os.environ["TOKENGURU_PROMPT_ID"])

    # Replace these values with data from your application request.
    values = {
        "customer_name": "Jordan",
        "order_id": "ORD-1042",
        "order_data": "Status: shipped. Estimated delivery: Friday.",
        "question": "When should the order arrive?",
    }
    system_prompt = render_prompt(prompt["system_prompt"], values)
    user_prompt = render_prompt(prompt["user_prompt"], values)

    messages = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt})
    if user_prompt.strip():
        messages.append({"role": "user", "content": user_prompt})
    if not messages:
        raise ValueError("The saved prompt has no system or user content")

    model = prompt.get("model") or os.environ["TOKENGURU_MODEL"]
    response = tg.chat.completions.create(model=model, messages=messages)
    print(response.choices[0].message.content)
    print(f"trace id: {response.tokensight.trace_id}")


if __name__ == "__main__":
    main()
