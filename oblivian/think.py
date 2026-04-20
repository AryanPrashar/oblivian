import json
from typing import Any, Dict

from openai import OpenAI


SYSTEM_PROMPT = (
    'You are an autonomous billing agent. If the user wants a refund and provides an '
    'order ID starting with pi_, output {"action": "refund", "stripe_id": "pi_12345"}. '
    'If not, output {"action": "ignore", "stripe_id": "none"}.'
)


def analyze_email(email_text: str) -> Dict[str, Any]:
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": email_text},
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    return json.loads(content)
