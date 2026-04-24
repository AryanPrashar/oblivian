import json
from typing import Any, Dict


from openai import OpenAI




SYSTEM_PROMPT = (
    "You are an email triage classifier for billing support. "
    "Decide exactly one action from: refund, human_review, ignore. "
    "Follow these rules strictly and in order: "
    "1) refund: choose this ONLY when the sender explicitly asks for their money back/refund "
    "AND includes a clear order/payment ID that starts with 'pi_'. Extract that exact ID into stripe_id. "
    "2) human_review: choose this when the sender is angry, upset, complaining, threatening chargeback, "
    "or asking for a discount/deal/price reduction, AND they do NOT provide a clear valid 'pi_' order ID. "
    "3) ignore: choose this for newsletters, promotions, obvious spam/phishing, irrelevant/casual chatter, "
    "or anything that does not meet refund/human_review criteria. "
    "Output must be valid JSON with exactly these keys and no extras: "
    '{"action":"refund|human_review|ignore","stripe_id":"pi_12345|none","reason":"one brief sentence"}'
    "Formatting requirements: "
    "- If action is refund, stripe_id must be the extracted 'pi_' ID from the email. "
    "- If action is human_review or ignore, stripe_id must be 'none'. "
    "- reason must be a single short sentence that references the key evidence from the email. "
    "Do not include markdown, code fences, or additional text outside the JSON object."
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



