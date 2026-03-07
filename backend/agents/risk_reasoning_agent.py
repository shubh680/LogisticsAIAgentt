"""
Risk Reasoning Agent for Logistics Platform
--------------------------------------------
Analyzes shipment operational signals and determines delay risk using
the Groq API with the Llama3 model. Designed to be integrated into an
Agentic AI workflow (e.g., LangGraph).
"""

import json
import re
import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Groq client using GROQ_API_KEY from .env
client = Groq(api_key=os.environ["GROQ_API_KEY"])

MODEL = "llama-3.1-8b-instant"


def _build_prompt(event: dict) -> str:
    """Construct the LLM prompt from the shipment event signals."""
    delay_prob = event.get("delay_probability")
    ml_line = (
        f"- ML Predicted Delay Probability (XGBoost model, 0–1): {delay_prob:.4f}"
        if delay_prob is not None
        else ""
    )
    ml_instruction = (
        "5. Interpret the ML Predicted Delay Probability — explain whether it aligns "
        "with or contradicts the operational signals, and factor it into your risk score."
        if delay_prob is not None
        else ""
    )
    ml_field = (
        f'"ml_delay_probability": {delay_prob},\n  '
        f'"ml_interpretation": "<one sentence explaining what the ML score means in context>",'
        if delay_prob is not None
        else ""
    )

    return f"""You are a logistics risk analyst AI. Analyze the following shipment signals and return a structured risk assessment.

Shipment Signals:
- Shipment ID: {event["shipment_id"]}
- Warehouse Load (0–1, higher = more congested): {event["warehouse_load"]}
- Carrier Reliability (0–1, higher = more reliable): {event["carrier_reliability"]}
- Traffic Delay Index (0–1, higher = worse traffic): {event["traffic_delay"]}
- Estimated Time of Arrival (hours): {event["eta_hours"]}
{ml_line}

Based on these signals:
1. Determine the overall risk level: "low", "medium", or "high"
2. Identify the root causes of potential delay (list of short phrases)
3. Estimate a numeric risk score between 0.0 and 1.0
4. Recommend a specific logistics intervention to mitigate the risk
{ml_instruction}

Respond ONLY with valid JSON in exactly this format — no extra text, no markdown:
{{
  "shipment_id": "{event["shipment_id"]}",
  {ml_field}
  "risk_level": "<low|medium|high>",
  "risk_score": <float between 0.0 and 1.0>,
  "root_causes": ["<cause 1>", "<cause 2>"],
  "recommended_action": "<actionable recommendation>"
}}"""


def risk_reasoning_agent(event: dict) -> dict:
    """
    Analyze a shipment event and return a structured delay risk assessment.

    Args:
        event: Dictionary containing shipment operational signals:
               - shipment_id (str)
               - warehouse_load (float, 0–1)
               - carrier_reliability (float, 0–1)
               - traffic_delay (float, 0–1)
               - eta_hours (int or float)

    Returns:
        Dictionary with risk_level, risk_score, root_causes, and recommended_action.
    """
    prompt = _build_prompt(event)

    # Call Groq's Llama3 model
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a logistics risk analyst. Always respond with valid JSON only. "
                    "No explanations, no markdown, no code blocks — raw JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,  # Low temperature for consistent, deterministic output
        max_tokens=512,
    )

    raw_content = response.choices[0].message.content.strip()

    # Strip markdown code fences if the model wraps the JSON anyway
    raw_content = re.sub(r"^```(?:json)?\s*", "", raw_content)
    raw_content = re.sub(r"\s*```$", "", raw_content)

    try:
        result = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"LLM returned non-JSON content for shipment {event.get('shipment_id')}: "
            f"{raw_content}"
        ) from exc

    # Enforce required fields and types
    result["shipment_id"] = event["shipment_id"]
    result["risk_score"] = float(result.get("risk_score", 0.0))
    result["risk_level"] = str(result.get("risk_level", "unknown")).lower()
    result["root_causes"] = list(result.get("root_causes", []))
    result["recommended_action"] = str(result.get("recommended_action", ""))

    return result


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    event = {
        "shipment_id": "S123",
        "warehouse_load": 0.9,
        "carrier_reliability": 0.6,
        "traffic_delay": 0.4,
        "eta_hours": 6,
    }

    result = risk_reasoning_agent(event)
    print(json.dumps(result, indent=2))
