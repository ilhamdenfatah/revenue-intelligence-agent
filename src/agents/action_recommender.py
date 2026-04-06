"""Agent 3: Action Recommender - generates prioritized, actionable recommendations."""

import json
import logging
from typing import Any

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strategic business advisor for an e-commerce company.

You receive detected revenue signals and their diagnosed root causes. Your job is to
generate specific, prioritized action recommendations that the business can act on
within 24-48 hours.

ACTION QUALITY STANDARDS:
- SPECIFIC: Name the exact category, state, team, or metric to act on
- ACTIONABLE: Someone can start executing this today, not next quarter
- TIED TO EVIDENCE: Each action must reference the signal or root cause it addresses
- REALISTIC: Actions must be executable by a typical e-commerce ops/commercial team

URGENCY LEVELS:
- IMMEDIATE: Execute within 24 hours - for CRITICAL signals with high confidence
- THIS_WEEK: Execute within 7 days - for WARNING signals or lower-confidence CRITICAL
- MONITOR: No action needed yet, but track closely - for stabilizing or positive signals

OUTPUT RULES:
- Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown.
- Use exactly this schema:

{
  "recommendations": [
    {
      "id": "action_1",
      "title": "Short action title (max 8 words)",
      "description": "Specific action to take, who should do it, and expected outcome",
      "addresses_signal": "signal_id it addresses (e.g. signal_1)",
      "addresses_cause": "root cause category it addresses (e.g. logistics)",
      "urgency": "IMMEDIATE | THIS_WEEK | MONITOR",
      "expected_impact": "Specific expected outcome if action is taken",
      "owner": "ops_team | commercial_team | logistics_team | marketing_team | exec_team",
      "priority_score": 9
    }
  ],
  "executive_priority": "One sentence: the single most important thing to do right now",
  "total_revenue_at_risk": 0.0
}"""


def run(
    context: str,
    signals: dict[str, Any],
    root_causes: dict[str, Any],
) -> dict[str, Any]:
    """Run the Action Recommender agent on signals and root causes from Agents 1 & 2.

    Args:
        context: Formatted context string from context_builder for action_recommender.
        signals: Output dict from signal_detector.run().
        root_causes: Output dict from root_cause_analyzer.run().

    Returns:
        Parsed JSON dict with recommendations and executive priority.

    Raises:
        RuntimeError: If the LLM call fails or returns unparseable output.
    """
    logger.info(
        f"Agent 3 (Action Recommender) starting - "
        f"{len(signals.get('signals', []))} signals, "
        f"{len(root_causes.get('root_causes', []))} root causes"
    )

    enriched_context = _enrich_context(context, signals, root_causes)

    client = Groq(api_key=GROQ_API_KEY)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": enriched_context},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"Agent 3 LLM call failed: {e}") from e

    raw = response.choices[0].message.content.strip()
    logger.debug(f"Agent 3 raw response: {raw[:200]}...")

    result = _parse_response(raw)
    actions_count = len(result.get("recommendations", []))
    immediate = sum(1 for r in result.get("recommendations", []) if r.get("urgency") == "IMMEDIATE")
    logger.info(f"Agent 3 complete - {actions_count} recommendations | {immediate} IMMEDIATE")

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _enrich_context(
    context: str,
    signals: dict[str, Any],
    root_causes: dict[str, Any],
) -> str:
    """Append Agent 1 + Agent 2 outputs to the action recommender context."""
    return f"""{context}

SIGNALS FROM AGENT 1 (Signal Detector):
{json.dumps(signals, indent=2)}

ROOT CAUSES FROM AGENT 2 (Root Cause Analyzer):
{json.dumps(root_causes, indent=2)}

Based on the signals, root causes, and business context above, generate prioritized
action recommendations. For each critical signal with requires_immediate_action=true,
there must be at least one IMMEDIATE action.
"""


def _parse_response(raw: str) -> dict[str, Any]:
    """Parse and validate the LLM JSON response."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 3 failed to parse JSON response: {e}")
        logger.error(f"Raw response was: {raw[:500]}")
        return {
            "recommendations": [],
            "executive_priority": "Action recommendation failed - unable to parse LLM response.",
            "total_revenue_at_risk": 0.0,
            "error": str(e),
        }