"""
FastAPI backend for Logistics AI Agent
---------------------------------------
Exposes a REST API consumed by the React frontend.
Run with: uvicorn main:app --reload --port 8000
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.ingestion import IngestionAgent

load_dotenv()

app = FastAPI(title="Logistics AI Agent API")

# Allow the Vite dev server and any local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory store (reset on server restart)
# ---------------------------------------------------------------------------
_agent = IngestionAgent()
_analysis_results: list[dict] = []        # cached risk assessments
_review_decisions: dict[str, dict] = {}   # review_id → {status, reviewedAt, reviewedBy}
_is_analyzing: bool = False
_analysis_total: int = 0                  # how many shipments are queued in current run
_analysis_errors: int = 0                 # how many failed in current run


# ---------------------------------------------------------------------------
# Data-mapping helpers: backend assessment → frontend types
# ---------------------------------------------------------------------------

def _order_status(assessment: dict) -> str:
    """Map a risk assessment to a frontend OrderStatus string."""
    if assessment.get("is_delayed"):
        return "failed"
    if assessment.get("policy", {}).get("human_required"):
        return "in_progress"
    risk = assessment.get("risk_level", "low").lower()
    if risk == "high":
        return "in_progress"
    if risk == "medium":
        return "in_progress"
    return "completed"


def _assessment_to_order(assessment: dict) -> dict:
    """Convert a risk assessment (or an error entry) to an Order object."""
    now = datetime.now(timezone.utc).isoformat()
    shipment_id = assessment.get("shipment_id", "UNKNOWN")

    # Error entries have no risk data — return a minimal failed order
    if "error" in assessment and "risk_level" not in assessment:
        return {
            "id": shipment_id,
            "title": f"Shipment {shipment_id} — analysis failed",
            "description": assessment["error"][:200],
            "status": "failed",
            "agentId": "risk-agent",
            "agentName": "Risk Reasoning Agent",
            "createdAt": now,
            "updatedAt": now,
            "thoughts": [],
            "actions": [],
            "inputData": {"shipment_id": shipment_id},
            "outputData": {"error": assessment["error"]},
        }

    policy = assessment.get("policy", {})
    risk_score = float(assessment.get("risk_score", 0.5))
    confidence = round(1.0 - risk_score, 2)

    delay_prob = assessment.get("ml_delay_probability") or assessment.get("delay_probability")

    thoughts = [
        {
            "id": "t1",
            "timestamp": now,
            "thought": (
                f"[Ingestion Agent] Live shipment data fetched from Firebase: "
                f"carrier={assessment.get('carrier', 'N/A')}, weather={assessment.get('weather', 'N/A')}, "
                f"priority={assessment.get('priority', 'N/A')}."
            ),
            "reasoning": "IngestionAgent connected to Firebase Realtime DB and retrieved the latest shipment record.",
            "confidence": 1.0,
        },
    ]

    if delay_prob is not None:
        thoughts.append(
            {
                "id": "t2",
                "timestamp": now,
                "thought": f"[Delay Predictor] XGBoost ML model predicted delay probability: {float(delay_prob):.1%}.",
                "reasoning": assessment.get(
                    "ml_interpretation",
                    "XGBoost model trained on historical logistics data evaluated carrier reliability, weather, warehouse load, and traffic density.",
                ),
                "confidence": round(1.0 - float(delay_prob), 2),
            }
        )

    thoughts.append(
        {
            "id": "t3",
            "timestamp": now,
            "thought": (
                f"[Risk Reasoning Agent] Risk level assessed as {assessment.get('risk_level', 'unknown').upper()} "
                f"(score: {risk_score:.2f}). Root causes: {', '.join(assessment.get('root_causes', []))}."
            ),
            "reasoning": (
                f"Groq LLM (Llama-3.1-8b) analyzed operational signals and ML prediction. "
                f"Recommended action: {assessment.get('recommended_action', 'N/A')}."
            ),
            "confidence": confidence,
        }
    )

    triggered_rules = policy.get("triggered_rules", [])
    thoughts.append(
        {
            "id": "t4",
            "timestamp": now,
            "thought": (
                f"[Policy Engine] Decision: {policy.get('decision', 'N/A')}. "
                f"Human review {'required' if policy.get('human_required') else 'not required'}."
            ),
            "reasoning": policy.get("explanation", "Rule-based policy evaluation complete."),
            "confidence": confidence,
        }
    )

    action_type = "escalated" if policy.get("human_required") else "verification"
    actions = [
        {
            "id": "a1",
            "type": "api_call",
            "description": "Ingestion Agent: Fetched live shipment data from Firebase",
            "timestamp": now,
            "status": "completed",
            "input": {"shipment_id": shipment_id, "source": "Firebase Realtime DB"},
            "output": {
                "carrier": assessment.get("carrier"),
                "weather": assessment.get("weather"),
                "priority": assessment.get("priority"),
                "warehouse_load": assessment.get("warehouse_load"),
                "traffic_delay": assessment.get("traffic_delay"),
                "eta_hours": assessment.get("eta_hours"),
                "is_delayed": assessment.get("is_delayed"),
            },
            "confidence": 1.0,
        },
        {
            "id": "a2",
            "type": "data_updated",
            "description": "Delay Predictor: XGBoost model estimated delay probability",
            "timestamp": now,
            "status": "completed",
            "input": {
                "carrier": assessment.get("carrier"),
                "weather": assessment.get("weather"),
                "warehouse_load": assessment.get("warehouse_load"),
                "traffic_delay": assessment.get("traffic_delay"),
            },
            "output": {
                "delay_probability": delay_prob,
                "ml_interpretation": assessment.get("ml_interpretation", "N/A"),
            },
            "confidence": round(1.0 - float(delay_prob), 2) if delay_prob is not None else 0.5,
        },
        {
            "id": "a3",
            "type": "verification",
            "description": "Risk Reasoning Agent: LLM analyzed signals and scored risk",
            "timestamp": now,
            "status": "completed",
            "input": {
                "warehouse_load": assessment.get("warehouse_load"),
                "traffic_delay": assessment.get("traffic_delay"),
                "eta_hours": assessment.get("eta_hours"),
                "delay_probability": delay_prob,
            },
            "output": {
                "risk_level": assessment.get("risk_level"),
                "risk_score": assessment.get("risk_score"),
                "root_causes": assessment.get("root_causes", []),
                "recommended_action": assessment.get("recommended_action"),
            },
            "confidence": confidence,
        },
        {
            "id": "a4",
            "type": action_type,
            "description": (
                f"Policy Engine: {policy.get('recommended_action') or assessment.get('recommended_action', 'Monitor shipment')}"
            ),
            "timestamp": now,
            "status": "in_progress" if policy.get("human_required") else "completed",
            "input": {
                "risk_score": assessment.get("risk_score"),
                "risk_level": assessment.get("risk_level"),
                "weather": assessment.get("weather"),
                "priority": assessment.get("priority"),
            },
            "output": {
                "decision": policy.get("decision"),
                "human_required": policy.get("human_required"),
                "triggered_rules": triggered_rules,
                "explanation": policy.get("explanation", ""),
            },
            "confidence": confidence,
        },
    ]

    pipeline_steps = [
        {
            "id": "step-1",
            "agentName": "Ingestion Agent",
            "status": "completed",
            "input": {"shipment_id": shipment_id, "source": "Firebase Realtime DB"},
            "output": {
                "carrier": assessment.get("carrier"),
                "weather": assessment.get("weather"),
                "priority": assessment.get("priority"),
                "warehouse_load": assessment.get("warehouse_load"),
                "traffic_delay": assessment.get("traffic_delay"),
                "eta_hours": assessment.get("eta_hours"),
                "is_delayed": assessment.get("is_delayed"),
            },
            "summary": (
                f"Fetched shipment from Firebase — "
                f"carrier: {assessment.get('carrier', 'N/A')}, "
                f"weather: {assessment.get('weather', 'N/A')}, "
                f"ETA: {assessment.get('eta_hours', 'N/A')}h"
            ),
        },
        {
            "id": "step-2",
            "agentName": "Delay Predictor",
            "status": "completed" if delay_prob is not None else "skipped",
            "input": {
                "carrier": assessment.get("carrier"),
                "weather": assessment.get("weather"),
                "warehouse_load": assessment.get("warehouse_load"),
                "traffic_delay": assessment.get("traffic_delay"),
            },
            "output": {
                "delay_probability": delay_prob,
                "ml_interpretation": assessment.get("ml_interpretation", "N/A"),
            },
            "summary": (
                f"XGBoost predicted delay probability: {float(delay_prob):.1%}"
                if delay_prob is not None
                else "ML prediction skipped"
            ),
        },
        {
            "id": "step-3",
            "agentName": "Risk Reasoning Agent",
            "status": "completed",
            "input": {
                "warehouse_load": assessment.get("warehouse_load"),
                "traffic_delay": assessment.get("traffic_delay"),
                "eta_hours": assessment.get("eta_hours"),
                "delay_probability": delay_prob,
            },
            "output": {
                "risk_level": assessment.get("risk_level"),
                "risk_score": assessment.get("risk_score"),
                "root_causes": assessment.get("root_causes", []),
                "recommended_action": assessment.get("recommended_action"),
                "ml_interpretation": assessment.get("ml_interpretation"),
            },
            "summary": (
                f"Risk: {assessment.get('risk_level', 'N/A').upper()} "
                f"(score {risk_score:.2f}) — "
                f"{assessment.get('recommended_action', 'N/A')}"
            ),
        },
        {
            "id": "step-4",
            "agentName": "Policy Engine",
            "status": "completed",
            "input": {
                "risk_level": assessment.get("risk_level"),
                "risk_score": assessment.get("risk_score"),
                "weather": assessment.get("weather"),
                "priority": assessment.get("priority"),
            },
            "output": {
                "decision": policy.get("decision"),
                "human_required": policy.get("human_required"),
                "triggered_rules": triggered_rules,
                "explanation": policy.get("explanation", ""),
            },
            "summary": (
                f"Decision: {policy.get('decision', 'N/A')} — "
                f"{'Human review required' if policy.get('human_required') else 'Auto-approved'}. "
                f"{len(triggered_rules)} rule(s) triggered."
            ),
        },
    ]

    return {
        "id": shipment_id,
        "title": f"Shipment {shipment_id} — {assessment.get('carrier', 'Unknown')}",
        "description": (
            f"Weather: {assessment.get('weather', 'N/A')} | "
            f"Priority: {assessment.get('priority', 'N/A')} | "
            f"Risk: {assessment.get('risk_level', 'N/A').upper()}"
        ),
        "status": _order_status(assessment),
        "agentId": "risk-agent",
        "agentName": "Risk Reasoning Agent",
        "createdAt": now,
        "updatedAt": now,
        "thoughts": thoughts,
        "actions": actions,
        "inputData": {
            "shipment_id": shipment_id,
            "carrier": assessment.get("carrier"),
            "weather": assessment.get("weather"),
            "priority": assessment.get("priority"),
            "is_delayed": assessment.get("is_delayed"),
            "warehouse_load": assessment.get("warehouse_load"),
            "traffic_delay": assessment.get("traffic_delay"),
            "eta_hours": assessment.get("eta_hours"),
        },
        "outputData": {
            "risk_level": assessment.get("risk_level"),
            "risk_score": assessment.get("risk_score"),
            "delay_probability": delay_prob,
            "recommended_action": assessment.get("recommended_action"),
            "decision": policy.get("decision"),
        },
        "pipelineSteps": pipeline_steps,
    }


def _is_overdue(row: dict) -> bool:
    """Derive delay status from planned_arrival since Firebase has no is_delayed field."""
    planned_str = row.get("planned_arrival", "")
    try:
        planned = datetime.fromisoformat(planned_str)
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)
        return (planned - datetime.now(timezone.utc)).total_seconds() < 0
    except (ValueError, TypeError):
        return False


def _raw_shipment_to_order(s: dict) -> dict:
    """Convert a raw Firebase shipment row to an Order (analysis not yet run)."""
    now = datetime.now(timezone.utc).isoformat()
    overdue = _is_overdue(s)
    return {
        "id": s["shipment_id"],
        "title": f"Shipment {s['shipment_id']} — {s.get('carrier', 'Unknown')}",
        "description": (
            f"Weather: {s.get('weather', 'N/A')} | "
            f"Priority: {s.get('shipment_priority', 'N/A')} | "
            f"Delayed: {overdue}"
        ),
        "status": "failed" if overdue else "pending",
        "agentId": "ingestion-agent",
        "agentName": "Ingestion Agent",
        "createdAt": s.get("planned_arrival", now),
        "updatedAt": now,
        "thoughts": [],
        "actions": [],
        "inputData": s,
        "outputData": {},
    }


def _assessment_to_review(assessment: dict) -> dict | None:
    """Return a HumanReviewItem if the policy requires human review, else None."""
    # Skip error entries
    if "error" in assessment and "risk_level" not in assessment:
        return None
    policy = assessment.get("policy", {})
    if not policy.get("human_required"):
        return None

    shipment_id = assessment["shipment_id"]
    review_id = f"REV-{shipment_id}"
    now = datetime.now(timezone.utc).isoformat()
    risk_score = float(assessment.get("risk_score", 0.5))
    confidence = round(1.0 - risk_score, 2)

    stored = _review_decisions.get(review_id, {})

    action = {
        "id": f"a-{shipment_id}",
        "type": "escalated",
        "description": (
            policy.get("recommended_action")
            or assessment.get("recommended_action", "Manual intervention required")
        ),
        "timestamp": now,
        "status": "in_progress" if stored.get("status") == "pending" or not stored else "completed",
        "input": {
            "risk_level": assessment.get("risk_level"),
            "risk_score": assessment.get("risk_score"),
            "triggered_rules": policy.get("triggered_rules", []),
        },
        "output": {},
        "confidence": confidence,
    }

    delay_prob = assessment.get("ml_delay_probability") or assessment.get("delay_probability")
    warehouse_load = assessment.get("warehouse_load")
    traffic_delay = assessment.get("traffic_delay")

    return {
        "id": review_id,
        "orderId": shipment_id,
        "orderTitle": f"Shipment {shipment_id} — {assessment.get('carrier', 'Unknown')}",
        "action": action,
        "agentReasoning": policy.get("explanation", "Human review required based on policy rules."),
        "confidence": confidence,
        "status": stored.get("status", "pending"),
        "createdAt": now,
        "reviewedAt": stored.get("reviewedAt"),
        "reviewedBy": stored.get("reviewedBy"),
        "shipmentDetails": {
            "carrier": assessment.get("carrier"),
            "weather": assessment.get("weather"),
            "priority": assessment.get("priority"),
            "isDelayed": assessment.get("is_delayed"),
            "etaHours": assessment.get("eta_hours"),
            "warehouseLoad": round(float(warehouse_load) * 100) if warehouse_load is not None else None,
            "trafficDelay": round(float(traffic_delay) * 100) if traffic_delay is not None else None,
            "delayProbability": round(float(delay_prob) * 100) if delay_prob is not None else None,
            "riskLevel": assessment.get("risk_level"),
            "riskScore": assessment.get("risk_score"),
            "rootCauses": assessment.get("root_causes", []),
            "recommendedAction": assessment.get("recommended_action"),
            "triggeredRules": policy.get("triggered_rules", []),
        },
    }


def _build_performance() -> dict:
    # Only use successfully analysed entries (skip error entries)
    valid = [a for a in _analysis_results if "risk_level" in a]
    total = len(valid)
    if total == 0:
        return {
            "totalOrders": 0,
            "autoCompleted": 0,
            "humanInLoop": 0,
            "failedOrders": 0,
            "avgConfidence": 0.0,
            "avgProcessingTime": 0.0,
            "actionBreakdown": [],
            "dailyPerformance": [],
            "confidenceDistribution": [],
        }

    auto_completed = sum(
        1
        for a in valid
        if not a.get("policy", {}).get("human_required") and not a.get("is_delayed")
    )
    human_in_loop = sum(
        1 for a in valid if a.get("policy", {}).get("human_required")
    )
    failed = sum(1 for a in valid if a.get("is_delayed"))

    risk_scores = [float(a.get("risk_score", 0.5)) for a in valid]
    avg_confidence = round(1.0 - (sum(risk_scores) / len(risk_scores)), 2)

    action_breakdown = [
        {"type": "verification", "count": auto_completed},
        {"type": "escalated", "count": human_in_loop},
        {"type": "api_call", "count": total},
    ]

    confidence_dist = [
        {"range": "0.0–0.2 (High Risk)", "count": sum(1 for s in risk_scores if s >= 0.8)},
        {"range": "0.2–0.4 (Med-High)", "count": sum(1 for s in risk_scores if 0.6 <= s < 0.8)},
        {"range": "0.4–0.6 (Medium)", "count": sum(1 for s in risk_scores if 0.4 <= s < 0.6)},
        {"range": "0.6–0.8 (Med-Low)", "count": sum(1 for s in risk_scores if 0.2 <= s < 0.4)},
        {"range": "0.8–1.0 (Low Risk)", "count": sum(1 for s in risk_scores if s < 0.2)},
    ]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_performance = [
        {
            "date": today,
            "completed": auto_completed,
            "failed": failed,
            "humanReview": human_in_loop,
        }
    ]

    return {
        "totalOrders": total,
        "autoCompleted": auto_completed,
        "humanInLoop": human_in_loop,
        "failedOrders": failed,
        "avgConfidence": avg_confidence,
        "avgProcessingTime": 10.0,
        "actionBreakdown": action_breakdown,
        "dailyPerformance": daily_performance,
        "confidenceDistribution": confidence_dist,
    }


# ---------------------------------------------------------------------------
# Background analysis runner
# ---------------------------------------------------------------------------

def _run_analysis_sync() -> None:
    """
    Full analysis pipeline — runs in a background thread via FastAPI BackgroundTasks.
    Results are appended incrementally so the status endpoint shows live progress.
    """
    global _analysis_results, _is_analyzing, _analysis_total, _analysis_errors
    _is_analyzing = True
    _analysis_errors = 0
    # fetch fresh data and record total shipment count
    _agent.fetch_live()
    _analysis_total = len(_agent._live_data)
    _analysis_results = []            # clear previous run
    try:
        for result in _agent.analyze_risks_iter():
            _analysis_results.append(result)
            if "error" in result and "risk_level" not in result:
                _analysis_errors += 1
    finally:
        _is_analyzing = False


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/shipments")
async def get_shipments():
    """Return all shipments as Order objects. Uses cached analysis if available."""
    if _analysis_results:
        return [_assessment_to_order(a) for a in _analysis_results]
    # Fall back to raw Firebase data while analysis hasn't run yet
    raw = await asyncio.to_thread(_agent.fetch_live)
    return [_raw_shipment_to_order(s) for s in raw]


@app.get("/api/shipments/{shipment_id}")
async def get_shipment(shipment_id: str):
    """Return a single shipment Order by ID."""
    for a in _analysis_results:
        if a.get("shipment_id") == shipment_id:
            return _assessment_to_order(a)
    # Fall back to raw data
    await asyncio.to_thread(_agent.fetch_live)
    raw = _agent.get_shipment(shipment_id)
    if raw:
        return _raw_shipment_to_order(raw)
    raise HTTPException(status_code=404, detail="Shipment not found")


@app.post("/api/analyze")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """Kick off a full risk analysis run (Groq + XGBoost) in the background."""
    if _is_analyzing:
        return {"message": "Analysis already in progress", "is_analyzing": True}
    background_tasks.add_task(_run_analysis_sync)
    return {"message": "Analysis started", "is_analyzing": True}


@app.get("/api/analyze/status")
async def analysis_status():
    """Poll to check whether a background analysis is running."""
    return {
        "is_analyzing": _is_analyzing,
        "analyzed_count": len(_analysis_results),
        "total_count": _analysis_total,
        "error_count": _analysis_errors,
    }


@app.get("/api/reviews")
async def get_reviews():
    """Return all shipments that require human review."""
    reviews = []
    for a in _analysis_results:
        review = _assessment_to_review(a)
        if review:
            reviews.append(review)
    return reviews


class ReviewAction(BaseModel):
    status: str  # "approved" | "rejected"
    reviewedBy: Optional[str] = "human-operator"


@app.patch("/api/reviews/{review_id}")
async def update_review(review_id: str, body: ReviewAction):
    """Approve or reject a human-review item."""
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status must be 'approved' or 'rejected'")
    _review_decisions[review_id] = {
        "status": body.status,
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "reviewedBy": body.reviewedBy,
    }
    return {"id": review_id, "status": body.status}


@app.get("/api/performance")
async def get_performance():
    """Return aggregated performance statistics."""
    return _build_performance()


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
