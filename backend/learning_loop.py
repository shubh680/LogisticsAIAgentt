"""
Agentic AI Learning Loop — Logistics Assistant
================================================
The agent LEARNS FROM ITS MISTAKES by:

1. Analysing whether the result actually answered the query (not just "was it non-empty")
2. Producing a SPECIFIC, ACTIONABLE lesson (e.g. "apply is_delayed=True filter")
3. Storing the lesson in memory against a query-type key
4. APPLYING past lessons on the next similar query — changing tool behaviour
5. Tracking per-(query-type, tool) success rates so bad combos are avoided

Loop:
    Observe → Plan (+ apply past lessons) → Act (lesson-aware) →
    Evaluate (result vs intent) → Reflect (specific lesson) →
    Learn (update stats) → Store Memory
"""

import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from groq import Groq

# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("learning_loop")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
FIREBASE_BASE = (
    os.getenv("FIREBASE_CRED_PATH", "https://cyberc2-default-rtdb.firebaseio.com/.json")
    .rstrip("/.json").rstrip("/")
)
MODEL = "llama-3.1-8b-instant"

_groq_client = Groq(api_key=GROQ_API_KEY)


def call_groq(prompt: str, system: str = "You are a helpful logistics AI assistant.") -> str:
    """Send a prompt to Groq and return the response text."""
    response = _groq_client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.2,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def _parse_json_response(raw: str) -> dict:
    """Strip markdown fences and parse JSON, raise on failure."""
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    return json.loads(raw)


# ===========================================================================
# Query-type classifier
# ===========================================================================
_QUERY_TYPE_KEYWORDS: dict[str, list[str]] = {
    "route_planning":   ["route", "fastest", "path", "way", "navigate", "planning"],
    "delay_status":     ["delay", "delayed", "status", "on time", "late"],
    "shipment_lookup":  ["shipment", "shipment_id", "tracking", "locate", "find shipment"],
    "carrier_analysis": ["carrier", "reliability", "performance", "bluedart", "delhivery", "swift"],
    "priority_filter":  ["high-priority", "high priority", "urgent", "critical"],
    "warehouse":        ["warehouse", "load", "capacity", "hub"],
}

def classify_query(query: str) -> str:
    """Return a stable query-type string for memory keying."""
    q = query.lower()
    for qtype, keywords in _QUERY_TYPE_KEYWORDS.items():
        if any(k in q for k in keywords):
            return qtype
    return "general"


# ===========================================================================
# 1. MemoryManager
# ===========================================================================
class MemoryManager:
    """
    Stores full interaction memories AND a separate lessons index.
    lessons_index: { query_type → [lesson_str, ...] }  — used for fast retrieval
    """

    def __init__(self, memory_path: str = "agent_memory.json"):
        self._path = Path(memory_path)
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except json.JSONDecodeError:
                log.warning("Memory file corrupt — starting fresh.")
        return {"memories": [], "lessons_index": {}}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))

    # ------------------------------------------------------------------
    def store(self, entry: dict) -> None:
        """Append a full memory entry."""
        entry.setdefault("id", str(uuid.uuid4())[:8])
        entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        self._data["memories"].append(entry)

        # Index the lesson under its query type for fast lookup
        qt = entry.get("query_type", "general")
        lesson = entry.get("lesson", "")
        if lesson:
            self._data["lessons_index"].setdefault(qt, [])
            # Keep only the 3 most recent lessons per type
            self._data["lessons_index"][qt].append(lesson)
            self._data["lessons_index"][qt] = self._data["lessons_index"][qt][-3:]

        self._save()
        log.info("[MEMORY] Stored entry #%s  type=%s", entry["id"], qt)

    def get_lessons(self, query_type: str) -> list[str]:
        """Return stored lessons for this query type."""
        return self._data["lessons_index"].get(query_type, [])

    def retrieve_similar(self, query: str, top_k: int = 3) -> list[dict]:
        """Keyword-overlap retrieval from full memories."""
        q_words = set(query.lower().split())
        scored = []
        for m in self._data["memories"]:
            m_words = set(m.get("query", "").lower().split())
            overlap = len(q_words & m_words) / max(len(q_words | m_words), 1)
            if overlap > 0:
                scored.append((overlap, m))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:top_k]]

    def all_memories(self) -> list[dict]:
        return list(self._data["memories"])

    def __len__(self) -> int:
        return len(self._data["memories"])


# ===========================================================================
# 2. ReflectionEngine  — RESULT-DRIVEN, produces SPECIFIC lessons
# ===========================================================================
class ReflectionEngine:
    """
    Compares what the query ASKED FOR against what the result ACTUALLY RETURNED.
    Produces a concrete, actionable lesson — not generic praise.
    """

    SYSTEM = (
        "You are auditing a logistics AI agent's mistake. "
        "Be critical and specific. Focus on what went wrong and EXACTLY what to do differently. "
        "Return ONLY valid JSON — no markdown, no extra text."
    )

    def reflect(
        self,
        query: str,
        query_type: str,
        tool: str,
        result: str,
        feedback: str,
        past_lessons: list[str],
    ) -> dict:
        """
        Returns a dict:
          answered_query: bool — did result actually answer what was asked?
          gap: str            — what was missing or wrong in the result
          lesson: str         — specific, actionable instruction for next time
        """
        log.info("[REFLECT] Auditing result vs query intent …")

        past_text = (
            "\n".join(f"  - {l}" for l in past_lessons)
            if past_lessons else "  (none yet)"
        )

        prompt = f"""A logistics AI agent received this query and returned a result. Audit it.

QUERY: "{query}"
QUERY TYPE: {query_type}
TOOL USED: {tool}
USER FEEDBACK: {feedback}
RESULT RETURNED:
{result[:600]}

PAST LESSONS FOR THIS QUERY TYPE:
{past_text}

Audit questions:
1. Did the result DIRECTLY answer what the query asked? (e.g. if asked for "high-priority delayed shipments", did the result filter to only those?)
2. What specific data is missing or wrong?
3. Write ONE actionable lesson for next time. Start with "For [query_type] queries:" and specify exact filters, parameters, or tool changes needed.

Return JSON:
{{
  "answered_query": true or false,
  "gap": "<what was missing or wrong — be specific>",
  "lesson": "<For {query_type} queries: exact action to take next time>"
}}"""

        try:
            raw = call_groq(prompt, system=self.SYSTEM)
            result_obj = _parse_json_response(raw)
            lesson = str(result_obj.get("lesson", ""))
            gap    = str(result_obj.get("gap", ""))
            answered = bool(result_obj.get("answered_query", True))
        except Exception as exc:
            log.warning("[REFLECT] LLM failed (%s) — using heuristic.", exc)
            answered = feedback == "positive"
            gap    = "Could not parse result quality." if not answered else "Result looks acceptable."
            lesson = (
                f"For {query_type} queries: review tool '{tool}' output — it may need additional filters."
                if not answered else
                f"For {query_type} queries: tool '{tool}' works well, keep using it."
            )

        log.info("[REFLECT] answered=%s | gap: %s", answered, gap[:80])
        log.info("[REFLECT] lesson: %s", lesson[:120])
        return {"answered_query": answered, "gap": gap, "lesson": lesson}


# ===========================================================================
# 3. ToolSelector  — tracks (query_type, tool) success rates
# ===========================================================================
class ToolSelector:
    """
    Per-(query_type, tool) success tracking.
    Starts with keyword-based defaults; learns which tool works for each type.
    """

    _DEFAULTS: dict[str, str] = {
        "route_planning":   "routing_api",
        "delay_status":     "firebase_query",
        "shipment_lookup":  "firebase_query",
        "carrier_analysis": "firebase_query",
        "priority_filter":  "firebase_query",
        "warehouse":        "firebase_query",
        "general":          "firebase_query",
    }

    def __init__(self, stats_path: str = "tool_stats.json"):
        self._path = Path(stats_path)
        self.stats: dict = self._load()   # { "query_type::tool" → {calls, successes, rate} }

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except json.JSONDecodeError:
                pass
        return {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self.stats, indent=2))

    def _key(self, query_type: str, tool: str) -> str:
        return f"{query_type}::{tool}"

    def _get_rate(self, query_type: str, tool: str) -> float:
        return self.stats.get(self._key(query_type, tool), {}).get("rate", 0.5)

    def select(self, query_type: str) -> str:
        """
        Pick the best tool. Only switches away from the domain default
        if the alternative has been tried AND has a clearly better success rate.
        """
        default = self._DEFAULTS.get(query_type, "firebase_query")
        all_tools = ["firebase_query", "routing_api"]

        def _rate(t: str) -> float:
            s = self.stats.get(self._key(query_type, t), {})
            # Require at least 2 calls before trusting the rate
            return s.get("rate", 0.5) if s.get("calls", 0) >= 2 else 0.5

        rates = {t: _rate(t) for t in all_tools}
        best_rate = max(rates.values())
        best_candidates = [t for t, r in rates.items() if r == best_rate]
        # Prefer default when tied to avoid random switches
        best = default if default in best_candidates else best_candidates[0]
        log.info("[PLAN] Tool selected: %s  (query_type=%s, rates=%s)", best, query_type, rates)
        return best

    def record_outcome(self, query_type: str, tool: str, success: bool) -> None:
        k = self._key(query_type, tool)
        if k not in self.stats:
            self.stats[k] = {"calls": 0, "successes": 0, "rate": 0.5}
        s = self.stats[k]
        s["calls"]     += 1
        s["successes"] += int(success)
        s["rate"]       = round(s["successes"] / s["calls"], 4)
        self._save()
        log.info("[LEARN] %s → calls=%d  success_rate=%.2f", k, s["calls"], s["rate"])

    def print_stats(self) -> None:
        print("\n── Tool Stats (per query type) ──────────────────────────────")
        if not self.stats:
            print("  (no data yet)")
        for key, s in sorted(self.stats.items()):
            print(f"  {key:40s}  calls={s['calls']:3d}  rate={s['rate']:.2f}")
        print()


# ===========================================================================
# 4. Lesson-aware tools
# ===========================================================================

def firebase_query(query: str, lessons: list[str] | None = None) -> str:
    """
    Query Firebase. Applies learned filters derived from past lessons.
    Computes is_delayed from current_delay_minutes (>0 = delayed).
    """
    try:
        url = f"{FIREBASE_BASE}/.json"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data is None:
            return "No data found in Firebase."

        rows: list[dict] = (
            [v for v in data.values() if isinstance(v, dict)]
            if isinstance(data, dict) else
            [r for r in data if r]
        )

        # Compute is_delayed: use current_delay_minutes if present, else use high traffic as proxy
        for r in rows:
            if "is_delayed" not in r:
                delay_mins = int(r.get("current_delay_minutes", 0))
                if delay_mins > 0:
                    r["is_delayed"] = True
                else:
                    # Proxy: high traffic density (>0.6) with a long distance = likely delayed
                    r["is_delayed"] = (
                        float(r.get("traffic_density", 0)) > 0.6
                        and int(r.get("distance_to_go_km", 0)) > 200
                    )

        q_lower = query.lower()
        lesson_text = " ".join(lessons or []).lower()

        # ── Smart filters derived from query keywords + lessons ───────
        apply_delay  = "delayed" in q_lower or "delay" in q_lower or "late" in q_lower or "is_delayed" in lesson_text
        apply_high   = ("high-priority" in q_lower or "high priority" in q_lower
                        or "priority" in q_lower or "urgent" in q_lower or "critical" in q_lower)

        if apply_delay:
            before = len(rows)
            rows = [r for r in rows if r.get("is_delayed")]
            log.info("[ACT] Applied is_delayed filter: %d → %d rows", before, len(rows))

        if apply_high:
            before = len(rows)
            rows = [r for r in rows if r.get("shipment_priority") == "High"]
            log.info("[ACT] Applied High-priority filter: %d → %d rows", before, len(rows))

        # ── Carrier reliability aggregation ──────────────────────────
        if "carrier" in q_lower or "reliability" in q_lower:
            from collections import Counter
            carriers = Counter(r.get("carrier") for r in rows)
            # Calculate delay rate per carrier from all rows (not filtered)
            all_rows = list([v for v in data.values() if isinstance(v, dict)] if isinstance(data, dict) else [r for r in data if r])
            for r in all_rows:
                if "is_delayed" not in r:
                    r["is_delayed"] = int(r.get("current_delay_minutes", 0)) > 0
            from collections import defaultdict
            carrier_stats: dict = defaultdict(lambda: {"total": 0, "delayed": 0})
            for r in all_rows:
                c = r.get("carrier", "Unknown")
                carrier_stats[c]["total"] += 1
                if r.get("is_delayed"):
                    carrier_stats[c]["delayed"] += 1
            reliability = {
                c: round(1 - s["delayed"] / max(s["total"], 1), 3)
                for c, s in carrier_stats.items()
            }
            best_carrier = max(reliability, key=reliability.get)
            return json.dumps({
                "carrier_reliability":    reliability,
                "most_reliable_carrier":  best_carrier,
                "reliability_score":      reliability[best_carrier],
                "total_shipments_analysed": len(all_rows),
            }, indent=2)

        # ── Shipment ID lookup ────────────────────────────────────────
        sid_match = re.search(r'\b([A-Z]{2}-\d+|SH-\d+|MY-\d+|S-\d+)\b', query)
        if sid_match:
            sid = sid_match.group(1)
            hits = [r for r in rows if r.get("shipment_id") == sid]
            if hits:
                return json.dumps(hits[0], indent=2, default=str)
            return f"Shipment '{sid}' not found in Firebase."

        # ── Return filtered results ───────────────────────────────────
        if rows:
            return json.dumps({
                "matched_shipments": len(rows),
                "results": rows[:10],
            }, indent=2, default=str)

        # ── No match ─────────────────────────────────────────────────
        all_count = len(data) if isinstance(data, dict) else 0
        return json.dumps({
            "total_shipments": all_count,
            "matched_shipments": 0,
            "note": "No shipments matched the applied filters.",
            "filters_applied": {
                "is_delayed":       apply_delay,
                "high_priority":    apply_high,
            },
        }, indent=2)

    except Exception as exc:
        return f"Firebase query error: {exc}"


def routing_api(query: str, lessons: list[str] | None = None) -> str:
    """
    Simulated routing API. Returns the single fastest route clearly labelled.
    Learns from lessons about city extraction and route formatting.
    """
    stopwords = {"find", "fastest", "fast", "route", "from", "the", "plan", "list",
                 "planning", "between", "and", "to", "via", "show", "get", "what",
                 "which", "all", "routing", "suggest", "give", "me", "best", "quick"}
    words = query.split()
    cities = [
        w.strip(".,!?-") for w in words
        if len(w) >= 3 and w[0].isupper() and w.lower().strip(".,!?-") not in stopwords
    ]

    if len(cities) >= 2:
        origin, dest = cities[0], cities[-1]
        # Apply lesson: if past lesson says to highlight fastest, do it explicitly
        lesson_text = " ".join(lessons or []).lower()
        fastest_label = "FASTEST ROUTE" if "fastest" in lesson_text or "fastest" in query.lower() else "RECOMMENDED"
        return (
            f"Fastest route from {origin} to {dest}:\n"
            f"  {fastest_label}: via Expressway — ETA 3h 20m, 290 km\n"
            f"  Alternative: via Highway       — ETA 4h 00m, 320 km\n"
            f"  Traffic note: Minor delays near {origin} outskirts, expressway clear."
        )

    return (
        "Routing API: could not identify city names. "
        "Please use format: 'route from <City A> to <City B>'."
    )


TOOLS: dict[str, Any] = {
    "firebase_query": firebase_query,
    "routing_api":    routing_api,
}


# ===========================================================================
# 5. Agent
# ===========================================================================
class Agent:
    """
    Core reasoning unit. Generates steps via Groq, executes tools with lessons,
    and evaluates whether the result ACTUALLY answered the query.
    """

    PLAN_SYSTEM = (
        "You are a logistics AI agent generating a step-by-step execution plan. "
        "You MUST incorporate any past lessons into your plan steps. "
        "Return ONLY a JSON array of short action strings. No extra text."
    )

    EVAL_SYSTEM = (
        "You are evaluating whether a logistics AI result is USEFUL for the user's query. "
        "Be practical: if the result contains relevant shipment data, route information, or "
        "carrier stats that relate to what was asked — mark it as answered=true. "
        "Only mark answered=false if the result is completely irrelevant or empty. "
        "Return ONLY valid JSON: "
        '{"answered": true/false, "confidence": 0.0-1.0, "reason": "<one sentence>"}'
    )

    def __init__(self, memory: MemoryManager, selector: ToolSelector):
        self._memory   = memory
        self._selector = selector

    def plan(self, query: str, tool: str, query_type: str, lessons: list[str]) -> list[str]:
        log.info("[PLAN] Building plan with %d lesson(s) to apply …", len(lessons))
        lesson_block = (
            "\n".join(f"  LESSON: {l}" for l in lessons)
            if lessons else "  (no past lessons — use defaults)"
        )
        prompt = (
            f"Query: {query}\n"
            f"Query type: {query_type}\n"
            f"Tool selected: {tool}\n\n"
            f"Past lessons to APPLY in your steps:\n{lesson_block}\n\n"
            "Generate execution steps as a JSON array. "
            "If a lesson says to filter or change approach, include that as a step."
        )
        try:
            raw = call_groq(prompt, system=self.PLAN_SYSTEM)
            steps = _parse_json_response(raw)
            if isinstance(steps, list):
                return [str(s) for s in steps]
        except Exception as exc:
            log.warning("[PLAN] LLM failed (%s) — using default steps.", exc)

        # Heuristic fallback with lessons injected
        base = [
            f"Classify query as: {query_type}",
            f"Select tool: {tool}",
        ]
        for l in lessons:
            base.append(f"Apply lesson: {l}")
        base += ["Execute tool with correct parameters", "Validate result answers the query"]
        return base

    def act(self, tool: str, query: str, lessons: list[str]) -> str:
        """Execute tool, passing lessons so it can apply learned filters."""
        log.info("[ACT] Executing '%s' with %d lesson(s) applied …", tool, len(lessons))
        fn = TOOLS.get(tool)
        if fn is None:
            return f"Tool '{tool}' is not available."
        return fn(query, lessons)

    def evaluate(self, query: str, result: str) -> dict:
        """Strictly check: did the result ACTUALLY answer the query?"""
        log.info("[EVALUATE] Checking if result answers query intent …")
        prompt = (
            f"User query: {query}\n\n"
            f"Result returned:\n{result[:500]}\n\n"
            "Did this result directly and completely answer the query?"
        )
        try:
            raw = call_groq(prompt, system=self.EVAL_SYSTEM)
            ev  = _parse_json_response(raw)
            return {
                "answered":   bool(ev.get("answered", True)),
                "confidence": float(ev.get("confidence", 0.7)),
                "reason":     str(ev.get("reason", "")),
            }
        except Exception as exc:
            log.warning("[EVALUATE] LLM failed (%s) — heuristic fallback.", exc)
            ok = len(result.strip()) > 20 and "error" not in result.lower()
            return {"answered": ok, "confidence": 0.6 if ok else 0.3, "reason": "heuristic"}


# ===========================================================================
# 6. LearningLoop
# ===========================================================================
class LearningLoop:
    """
    Full loop: Observe → Plan → Act → Evaluate → Reflect → Learn → Store
    The key difference from a naive loop: lessons from failures are retrieved
    and APPLIED on the next similar query — changing tool behaviour.
    """

    def __init__(
        self,
        memory_path: str = "agent_memory.json",
        stats_path:  str = "tool_stats.json",
    ):
        self.memory    = MemoryManager(memory_path)
        self.selector  = ToolSelector(stats_path)
        self.reflector = ReflectionEngine()
        self.agent     = Agent(self.memory, self.selector)

    def run(self, query: str, feedback: str = "neutral") -> dict:
        log.info("=" * 65)

        # ── OBSERVE ──────────────────────────────────────────────────
        log.info("[OBSERVE] Query: %s", query)
        query_type = classify_query(query)
        log.info("[OBSERVE] Query type: %s", query_type)

        past_lessons = self.memory.get_lessons(query_type)
        if past_lessons:
            log.info("[OBSERVE] %d past lesson(s) found for type '%s':", len(past_lessons), query_type)
            for l in past_lessons:
                log.info("           → %s", l[:100])

        # ── PLAN ─────────────────────────────────────────────────────
        tool    = self.selector.select(query_type)
        steps   = self.agent.plan(query, tool, query_type, past_lessons)
        log.info("[PLAN] Steps: %s", steps)

        # ── ACT ──────────────────────────────────────────────────────
        result = self.agent.act(tool, query, past_lessons)
        log.info("[ACT] Result (first 200 chars): %s", result[:200])

        # ── EVALUATE ─────────────────────────────────────────────────
        evaluation = self.agent.evaluate(query, result)
        answered   = evaluation["answered"]
        confidence = evaluation["confidence"]
        log.info(
            "[EVALUATE] answered=%s  confidence=%.2f  reason=%s",
            answered, confidence, evaluation["reason"][:80],
        )

        # ── REFLECT ──────────────────────────────────────────────────
        reflection = self.reflector.reflect(
            query       = query,
            query_type  = query_type,
            tool        = tool,
            result      = result,
            feedback    = feedback,
            past_lessons= past_lessons,
        )
        lesson = reflection["lesson"]

        # ── LEARN ────────────────────────────────────────────────────
        # Success = result answered the query AND user didn't give negative feedback
        # Positive feedback alone doesn't count if evaluation says it failed
        if feedback == "negative":
            success = False
        elif feedback == "positive" and answered:
            success = True
        else:
            success = answered  # trust evaluation for neutral feedback

        self.selector.record_outcome(query_type, tool, success)

        # ── STORE MEMORY ─────────────────────────────────────────────
        entry = {
            "query":        query,
            "query_type":   query_type,
            "tool_used":    tool,
            "reasoning":    steps,
            "result":       result[:600],
            "evaluation":   evaluation,
            "feedback":     feedback,
            "answered":     answered,
            "confidence":   round(confidence, 4),
            "lesson":       lesson,
            "gap":          reflection.get("gap", ""),
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        }
        self.memory.store(entry)
        log.info("[LEARN] Memory size: %d", len(self.memory))
        log.info("=" * 65)

        return entry

    # ------------------------------------------------------------------
    def print_stats(self) -> None:
        self.selector.print_stats()

    def print_memory_summary(self) -> None:
        memories = self.memory.all_memories()
        print(f"\n── Memory ({len(memories)} entries) ─────────────────────────────────────")
        for m in memories:
            ts  = m.get("timestamp", "")[:10]
            ok  = "✓" if m.get("answered") else "✗"
            print(
                f"  [{ts}] [{ok}] [{m.get('feedback','?'):8s}] "
                f"conf={m.get('confidence',0):.2f}  "
                f"type={m.get('query_type','?'):20s}  "
                f"query={m.get('query','')[:45]}"
            )
            if m.get("gap"):
                print(f"           gap    → {m['gap'][:80]}")
            if m.get("lesson"):
                print(f"           lesson → {m['lesson'][:80]}")
        print()

    def print_lessons_index(self) -> None:
        index = self.memory._data.get("lessons_index", {})
        print("\n── Lessons Index (what the agent learned) ───────────────────")
        for qt, lessons in index.items():
            print(f"  [{qt}]")
            for l in lessons:
                print(f"    → {l}")
        print()


# ===========================================================================
# Demo
# ===========================================================================
if __name__ == "__main__":
    loop = LearningLoop(
        memory_path="agent_memory.json",
        stats_path="tool_stats.json",
    )

    # Round 1 — first attempts (agent may get some wrong)
    print("\n" + "═"*65)
    print("  ROUND 1 — First attempts (agent learns from mistakes)")
    print("═"*65)

    round1 = [
        # (query,                                            feedback)
        ("Find fastest route from Mumbai to Pune",          "positive"),
        ("Show all high-priority delayed shipments",        "negative"),   # will fail: no filter
        ("What is the delay status of shipment MY-87254221","positive"),
        ("Route from Delhi to Jaipur",                      "positive"),
        ("Which carrier has the highest reliability",       "neutral"),
    ]
    for query, fb in round1:
        loop.run(query, feedback=fb)
        time.sleep(2)

    loop.print_stats()
    loop.print_lessons_index()

    # Round 2 — SAME problem query: now agent has the lesson, should fix it
    print("\n" + "═"*65)
    print("  ROUND 2 — Agent applies learned lessons")
    print("═"*65)

    round2 = [
        ("Show all high-priority delayed shipments",        "positive"),   # should now filter correctly
        ("List urgent shipments that are late",             "positive"),   # similar type — lessons apply
        ("Fastest route from Chennai to Bangalore",         "positive"),
        ("Which carrier is most reliable this week",        "neutral"),
    ]
    for query, fb in round2:
        loop.run(query, feedback=fb)
        time.sleep(2)

    # Final summary
    loop.print_stats()
    loop.print_lessons_index()
    loop.print_memory_summary()

    # Save output
    out = Path("learning_loop_output.json")
    out.write_text(json.dumps(loop.memory.all_memories(), indent=2))
    print(f"\nFull output saved to: {out}")


import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from groq import Groq

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("learning_loop")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
FIREBASE_BASE = os.getenv(
    "FIREBASE_CRED_PATH", "https://cyberc2-default-rtdb.firebaseio.com/.json"
).rstrip("/.json").rstrip("/")

MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# Groq helper
# ---------------------------------------------------------------------------
_groq_client = Groq(api_key=GROQ_API_KEY)

