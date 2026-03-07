"""
Policy Engine
-------------
Evaluates the output of the Risk Reasoning Agent and decides whether
a recommended action can be auto-executed or requires human approval.

Rules are explicit and auditable — no LLM involved in the decision itself.
The LLM is only used to generate a natural-language explanation of the ruling.
"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

_client = Groq(api_key=os.environ["GROQ_API_KEY"])
_MODEL  = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# Policy rules — thresholds that trigger human review
# ---------------------------------------------------------------------------
POLICY_RULES = {
    "high_risk_score":        0.80,   # risk_score >= this → review
    "high_delay_probability": 0.85,   # ml_delay_probability >= this → review
    "auto_approve_max_score": 0.50,   # risk_score <= this → always auto-approve
    "critical_weather":       {"Cyclone"},  # these weather conditions → review
}


def _evaluate_rules(assessment: dict) -> tuple[bool, list[str]]:
    """
    Apply policy rules to the risk assessment.

    Returns:
        (human_required: bool, triggered_rules: list[str])
    """
    triggered = []

    risk_level       = assessment.get("risk_level", "").lower()
    risk_score       = float(assessment.get("risk_score", 0))
    delay_prob       = assessment.get("delay_probability")
    ml_prob          = assessment.get("ml_delay_probability") or delay_prob or 0
    weather          = assessment.get("weather", "")
    priority         = assessment.get("priority", "")

    # Rule 1: Risk level is high
    if risk_level == "high":
        triggered.append("Risk level is HIGH")

    # Rule 2: Risk score exceeds threshold
    if risk_score >= POLICY_RULES["high_risk_score"]:
        triggered.append(f"Risk score {risk_score:.2f} ≥ threshold {POLICY_RULES['high_risk_score']}")

    # Rule 3: ML model predicts high delay probability
    if float(ml_prob) >= POLICY_RULES["high_delay_probability"]:
        triggered.append(f"ML delay probability {float(ml_prob):.4f} ≥ threshold {POLICY_RULES['high_delay_probability']}")

    # Rule 4: Dangerous weather condition
    if weather in POLICY_RULES["critical_weather"]:
        triggered.append(f"Critical weather condition: {weather}")

    # Rule 5: High priority shipment with any delay risk
    if priority == "High" and risk_level in ("medium", "high"):
        triggered.append("High-priority shipment with medium/high risk")

    human_required = len(triggered) > 0
    return human_required, triggered


def _llm_explanation(assessment: dict, human_required: bool, triggered_rules: list[str]) -> str:
    """Ask the LLM to write a clear, concise explanation of the policy decision."""
    rule_text = "\n".join(f"  - {r}" for r in triggered_rules) if triggered_rules else "  - No rules triggered."
    decision  = "HUMAN REVIEW REQUIRED" if human_required else "AUTO-APPROVED"

    prompt = f"""You are a logistics policy officer. A risk assessment has been evaluated against company policy rules.

Shipment ID: {assessment.get("shipment_id")}
Risk Level:  {assessment.get("risk_level")}
Risk Score:  {assessment.get("risk_score")}
ML Delay Probability: {assessment.get("ml_delay_probability") or assessment.get("delay_probability")}
Weather:     {assessment.get("weather")}
Priority:    {assessment.get("priority")}
Recommended Action: {assessment.get("recommended_action")}

Policy Decision: {decision}
Triggered Rules:
{rule_text}

Write a single concise paragraph (2–3 sentences) explaining this policy decision to a logistics manager.
Be direct and actionable. Do not use bullet points."""

    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )
    return response.choices[0].message.content.strip()


def evaluate_policy(assessment: dict) -> dict:
    """
    Evaluate a single risk assessment against company policy.

    Args:
        assessment: Output dict from risk_reasoning_agent(), enriched with
                    delay_probability, weather, priority, carrier fields.

    Returns:
        policy_result dict with:
            - shipment_id
            - human_required  (bool)
            - decision        ("HUMAN_REVIEW" | "AUTO_APPROVED")
            - triggered_rules (list of rule descriptions that fired)
            - recommended_action (passed through from risk agent)
            - explanation     (LLM-generated natural language reasoning)
    """
    human_required, triggered_rules = _evaluate_rules(assessment)

    explanation = _llm_explanation(assessment, human_required, triggered_rules)

    return {
        "shipment_id":        assessment.get("shipment_id"),
        "human_required":     human_required,
        "decision":           "HUMAN_REVIEW" if human_required else "AUTO_APPROVED",
        "triggered_rules":    triggered_rules,
        "recommended_action": assessment.get("recommended_action"),
        "risk_level":         assessment.get("risk_level"),
        "risk_score":         assessment.get("risk_score"),
        "delay_probability":  assessment.get("ml_delay_probability") or assessment.get("delay_probability"),
        "explanation":        explanation,
    }


def evaluate_policy_batch(assessments: list[dict]) -> list[dict]:
    """
    Evaluate a list of risk assessments and return policy decisions for all.

    Args:
        assessments: List of risk_reasoning_agent() outputs.

    Returns:
        List of policy_result dicts.
    """
    return [evaluate_policy(a) for a in assessments]


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Simulate a high-risk assessment output from risk_reasoning_agent
    sample = {
        "shipment_id":         "am-86301020",
        "risk_level":          "high",
        "risk_score":          0.95,
        "ml_delay_probability": 0.9938,
        "delay_probability":   0.9938,
        "root_causes":         ["High ML delay probability", "Warehouse congestion"],
        "recommended_action":  "Reroute shipment and switch to backup carrier immediately.",
        "weather":             "Cyclone",
        "carrier":             "BlueDart",
        "priority":            "High",
        "is_delayed":          False,
    }

    result = evaluate_policy(sample)
    print(json.dumps(result, indent=2))
