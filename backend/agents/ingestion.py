import os
import json
import re
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
from groq import Groq
from .firebase_client import FirebaseManager
from .risk_reasoning_agent import risk_reasoning_agent
from .delay_predictor import predict_delay
from .policy_engine import evaluate_policy

# Carrier name → reliability score (0–1)
_CARRIER_RELIABILITY = {
    "BlueDart":  0.88,
    "Swift":     0.72,
    "Delhivery": 0.76,
}


def _to_risk_event(row: dict) -> dict:
    """Map a Firebase shipment row to risk_reasoning_agent input fields."""
    planned_str = row.get("planned_arrival", "")
    try:
        planned = datetime.fromisoformat(planned_str)
        if planned.tzinfo is None:
            planned = planned.replace(tzinfo=timezone.utc)
        eta_hours = max((planned - datetime.now(timezone.utc)).total_seconds() / 3600, 0)
    except (ValueError, TypeError):
        eta_hours = 0.0

    return {
        "shipment_id":        row["shipment_id"],
        "warehouse_load":     round(int(row.get("warehouse_load_pct", 0)) / 100, 2),
        "carrier_reliability": _CARRIER_RELIABILITY.get(row.get("carrier", ""), 0.75),
        "traffic_delay":      float(row.get("traffic_density", 0)),
        "eta_hours":          round(eta_hours, 2),
    }

load_dotenv()

MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = (
    "You are the Ingestion & Observation Agent in a multi-agent logistics AI system. "
    "Your sole responsibility is to fetch live shipment data from Firebase using your tools "
    "and then produce a concise, structured observation of the current logistics state. "
    "When asked to observe, you MUST: "
    "1. Call fetch_live_data to load the data. "
    "2. Call get_summary_stats for an overview. "
    "3. Call get_delayed to identify delayed shipments. "
    "4. Call get_high_priority to identify urgent shipments. "
    "5. Return a JSON object with keys: summary, total_shipments, delayed_shipments, "
    "high_priority_shipments, alerts, and observations. "
    "alerts is a list of shipment_ids that are both delayed AND high priority. "
    "observations is a list of short insight strings about the current data. "
    "Always ground every field in the actual data returned by the tools. "
    "For ad-hoc queries, use whichever tools are relevant and respond in plain text."
)


class IngestionAgent:
    """
    Observation agent in a multi-agent logistics AI system.
    Fetches live shipment data from Firebase Realtime Database using Groq
    tool-calling and produces structured observations for downstream agents.
    """

    def __init__(self, live_collection: str = ""):
        self.db = FirebaseManager(live_collection)
        self._live_data: list[dict] = []
        self._client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self._tools, self._tool_map = self._build_tools()


    def fetch_live(self) -> list[dict]:
        """Fetch all records from the live shipments ."""
        self._live_data = self.db.fetch_live()
        return self._live_data

    def ingest(self) -> dict:
        """Pull live shipments from Firebase and cache them locally."""
        self._live_data = self.db.fetch_live()
        return {"live_count": len(self._live_data)}


    def get_shipment(self, shipment_id: str) -> dict | None:
        """Look up a single shipment by ID."""
        for row in self._live_data:
            if row.get("shipment_id") == shipment_id:
                return row
        return None

    def get_delayed_shipments(self) -> list[dict]:
        """Return all shipments currently flagged as delayed."""
        return [row for row in self._live_data if row.get("is_delayed")]

    def get_high_priority_shipments(self) -> list[dict]:
        """Return all high-priority shipments."""
        return [
            row for row in self._live_data if row.get("shipment_priority") == "High"
        ]

    def analyze_risks(self, delay_between_calls: float = 10.0) -> list[dict]:
        """
        Run risk_reasoning_agent on every shipment in the live cache.
        Returns a list of risk assessment dicts, one per shipment.

        delay_between_calls: seconds to wait between LLM calls (default 10s).
        Groq free tier = 6 000 TPM / ~800 tokens per call ≈ 7.5 calls/min max.
        """
        if not self._live_data:
            self.fetch_live()

        results = []
        for row in self._live_data:
            event = _to_risk_event(row)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Step 1: ML model — predict delay probability
                    event["delay_probability"] = predict_delay(row)

                    # Step 2: LLM Risk Reasoning Agent — reasons on signals + ML score
                    assessment = risk_reasoning_agent(event)
                    assessment["delay_probability"] = event["delay_probability"]
                    assessment["carrier"]        = row.get("carrier")
                    assessment["weather"]        = row.get("weather")
                    assessment["priority"]       = row.get("shipment_priority")
                    assessment["shipment_value"] = row.get("shipment_value")
                    assessment["last_checkpoint"] = row.get("last_checkpoint")

                    # Compute is_delayed from planned_arrival
                    # (Firebase live data has no is_delayed field)
                    planned_str = row.get("planned_arrival", "")
                    try:
                        planned = datetime.fromisoformat(planned_str)
                        if planned.tzinfo is None:
                            planned = planned.replace(tzinfo=timezone.utc)
                        assessment["is_delayed"] = (
                            planned - datetime.now(timezone.utc)
                        ).total_seconds() < 0
                    except (ValueError, TypeError):
                        assessment["is_delayed"] = False

                    # Forward event signals so callers can display them
                    assessment["warehouse_load"] = event["warehouse_load"]
                    assessment["traffic_delay"]  = event["traffic_delay"]
                    assessment["eta_hours"]       = event["eta_hours"]

                    # Step 3: Policy Engine — decides if human approval is needed
                    assessment["policy"] = evaluate_policy(assessment)

                    results.append(assessment)
                    break  # success — exit retry loop

                except Exception as exc:
                    err_str = str(exc)
                    # If Groq returned a rate-limit error, honour the retry-after
                    match = re.search(r"try again in ([\d.]+)s", err_str)
                    if match and attempt < max_retries - 1:
                        wait = float(match.group(1)) + 1.0
                        time.sleep(wait)
                        continue
                    results.append({"shipment_id": event["shipment_id"], "error": err_str})
                    break

            time.sleep(delay_between_calls)  # respect Groq TPM rate limit

        return results

    def analyze_risks_iter(self, delay_between_calls: float = 10.0):
        """
        Generator variant of analyze_risks.
        Yields one result dict per shipment so callers can update their store
        incrementally rather than waiting for the full batch to finish.
        """
        if not self._live_data:
            self.fetch_live()

        for row in self._live_data:
            event = _to_risk_event(row)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    event["delay_probability"] = predict_delay(row)
                    assessment = risk_reasoning_agent(event)
                    assessment["delay_probability"] = event["delay_probability"]
                    assessment["carrier"]        = row.get("carrier")
                    assessment["weather"]        = row.get("weather")
                    assessment["priority"]       = row.get("shipment_priority")
                    assessment["shipment_value"] = row.get("shipment_value")
                    assessment["last_checkpoint"] = row.get("last_checkpoint")
                    planned_str = row.get("planned_arrival", "")
                    try:
                        planned = datetime.fromisoformat(planned_str)
                        if planned.tzinfo is None:
                            planned = planned.replace(tzinfo=timezone.utc)
                        assessment["is_delayed"] = (
                            planned - datetime.now(timezone.utc)
                        ).total_seconds() < 0
                    except (ValueError, TypeError):
                        assessment["is_delayed"] = False
                    assessment["warehouse_load"] = event["warehouse_load"]
                    assessment["traffic_delay"]  = event["traffic_delay"]
                    assessment["eta_hours"]       = event["eta_hours"]
                    assessment["policy"] = evaluate_policy(assessment)
                    yield assessment
                    break
                except Exception as exc:
                    err_str = str(exc)
                    match = re.search(r"try again in ([\d.]+)s", err_str)
                    if match and attempt < max_retries - 1:
                        time.sleep(float(match.group(1)) + 1.0)
                        continue
                    yield {"shipment_id": event["shipment_id"], "error": err_str}
                    break
            time.sleep(delay_between_calls)

    def _build_tools(self) -> tuple[list[dict], dict]:
        """Return Groq-compatible tool schemas and a dispatch map."""

        def _ensure_live():
            if not self._live_data:
                self.fetch_live()

        def fetch_live_data() -> str:
            result = self.ingest()
            return json.dumps(result)

        def get_live_shipments() -> str:
            _ensure_live()
            return json.dumps(self._live_data, default=str)

        def lookup_shipment(shipment_id: str) -> str:
            _ensure_live()
            row = self.get_shipment(shipment_id)
            if row is None:
                return f"No shipment found with ID '{shipment_id}'."
            return json.dumps(row, default=str)

        def get_delayed() -> str:
            _ensure_live()
            return json.dumps(self.get_delayed_shipments(), default=str)

        def get_high_priority() -> str:
            _ensure_live()
            return json.dumps(self.get_high_priority_shipments(), default=str)

        def get_summary_stats() -> str:
            _ensure_live()
            rows = self._live_data
            if not rows:
                return "No live shipment data available."
            delayed = [r for r in rows if r.get("is_delayed")]
            carriers: dict = {}
            for r in rows:
                c = r.get("carrier", "Unknown")
                carriers[c] = carriers.get(c, 0) + 1
            return json.dumps(
                {
                    "total_shipments": len(rows),
                    "delayed_shipments": len(delayed),
                    "delay_rate": round(len(delayed) / len(rows), 3),
                    "carrier_distribution": carriers,
                },
                default=str,
            )

        def get_risk_analysis() -> str:
            """Run risk reasoning agent on all live shipments and return results."""
            assessments = self.analyze_risks()
            return json.dumps(assessments, default=str)

        def predict_delay_for_shipment(shipment_id: str) -> str:
            """Predict ML delay probability for a single shipment by ID."""
            _ensure_live()
            row = self.get_shipment(shipment_id)
            if row is None:
                return f"No shipment found with ID '{shipment_id}'."
            prob = predict_delay(row)
            return json.dumps({"shipment_id": shipment_id, "delay_probability": prob})

        tool_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "fetch_live_data",
                    "description": "Fetch / refresh live shipment data from Firebase and return the count.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_live_shipments",
                    "description": "Return all current live shipments.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "lookup_shipment",
                    "description": "Look up a specific shipment by its ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shipment_id": {
                                "type": "string",
                                "description": "The shipment ID to look up.",
                            }
                        },
                        "required": ["shipment_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_delayed",
                    "description": "Return all shipments that are currently delayed.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_high_priority",
                    "description": "Return all high-priority shipments.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_summary_stats",
                    "description": "Return summary statistics of the live shipments.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_risk_analysis",
                    "description": (
                        "Run the Risk Reasoning Agent on all live shipments. "
                        "Returns a risk assessment (risk_level, risk_score, root_causes, "
                        "recommended_action, delay_probability) for every shipment."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "predict_delay_for_shipment",
                    "description": (
                        "Use the ML model to predict the delay probability (0–1) "
                        "for a specific shipment by its ID."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "shipment_id": {
                                "type": "string",
                                "description": "The shipment ID to predict delay for.",
                            }
                        },
                        "required": ["shipment_id"],
                    },
                },
            },
        ]

        tool_map = {
            "fetch_live_data":             fetch_live_data,
            "get_live_shipments":          get_live_shipments,
            "lookup_shipment":             lookup_shipment,
            "get_delayed":                 get_delayed,
            "get_high_priority":           get_high_priority,
            "get_summary_stats":           get_summary_stats,
            "get_risk_analysis":           get_risk_analysis,
            "predict_delay_for_shipment":  predict_delay_for_shipment,
        }

        return tool_schemas, tool_map

    def observe(self) -> dict:
        """
        Primary agent entrypoint for multi-agent pipelines.
        Step 1: LLM fetches live data and builds a structured observation.
        Step 2: Python runs risk analysis separately and attaches results.
        This avoids token overflow from feeding 100 shipments back into the LLM.
        """
        observation_prompt = (
            "Observe the current state of live shipments. "
            "Fetch the data, analyze it fully, and return your observation "
            "as a valid JSON object with keys: "
            "summary, total_shipments, delayed_shipments, high_priority_shipments, "
            "alerts, and observations. "
            "Return ONLY the JSON object, no extra text."
        )
        raw = self.run(observation_prompt)
        # Strip markdown code fences if the model wraps the JSON
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            observation = json.loads(raw.strip())
        except json.JSONDecodeError:
            observation = {"raw_observation": raw}

        # Step 2: Risk analysis runs in Python — outside the LLM context window
        observation["risk_assessments"] = self.analyze_risks()
        levels = [r.get("risk_level") for r in observation["risk_assessments"] if "risk_level" in r]
        observation["risk_summary"] = {
            "low":    levels.count("low"),
            "medium": levels.count("medium"),
            "high":   levels.count("high"),
        }

        return observation

    def run(self, query: str, chat_history: list | None = None) -> str:
        """Send a natural-language query to the agent using Groq tool-calling."""
        messages = (
            [{"role": "system", "content": SYSTEM_PROMPT}]
            + (chat_history or [])
            + [{"role": "user", "content": query}]
        )

        while True:
            response = self._client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=self._tools,
                tool_choice="auto",
                temperature=0,
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                return msg.content

            # Serialize assistant message to a plain dict (SDK objects are not JSON-serializable)
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )

            # Execute each tool call and append results
            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments or "{}") or {}
                fn = self._tool_map.get(fn_name)
                result = fn(**fn_args) if fn else f"Unknown tool: {fn_name}"
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )


if __name__ == "__main__":
    agent = IngestionAgent()
    observation = agent.observe()
    print(json.dumps(observation, indent=2))
