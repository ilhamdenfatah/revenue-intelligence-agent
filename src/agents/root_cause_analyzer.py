"""Agent 2: Root Cause Analyzer - diagnoses why detected signals occurred."""

import json
import logging
from typing import Any

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a revenue diagnostics analyst for an e-commerce business.

You receive detected revenue signals from a Signal Detector agent, along with full
dimensional breakdowns (by category and by geography). Your job is to diagnose the
most likely root causes for each signal by looking for corroborating patterns in the data.

DIAGNOSTIC FRAMEWORK:
- If a state drops AND a category in that state also drops, they are likely correlated
- If order count is up but AOV is down, the cause is pricing/mix shift, not demand loss
- If only one state drops while others are stable, suspect logistics or local competition
- If a category drops across multiple states, suspect supply, pricing, or seasonal factors
- Spikes can also be anomalies - investigate if they are sustainable or one-time events

OUTPUT RULES:
- Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown.
- Use exactly this schema:

{
  "root_causes": [
    {
      "signal_id": "signal_1",
      "signal_title": "Title of the signal being diagnosed",
      "primary_cause": "Most likely root cause in one sentence",
      "supporting_evidence": ["evidence point 1 from the data", "evidence point 2"],
      "contributing_factors": ["secondary factor 1", "secondary factor 2"],
      "cause_category": "logistics | pricing | demand | seasonal | supply | competition | data_anomaly",
      "confidence": 0.85,
      "requires_immediate_action": true
    }
  ],
  "cross_signal_patterns": "Any patterns observed across multiple signals",
  "data_quality_notes": "Any concerns about data reliability that affect diagnosis"
}"""


def run(context: str, signals: dict[str, Any]) -> dict[str, Any]:
    """Run the Root Cause Analyzer agent on signals from Agent 1.

    Args:
        context: Formatted context string from context_builder for root_cause.
        signals: Output dict from signal_detector.run().

    Returns:
        Parsed JSON dict with root_causes and cross-signal patterns.

    Raises:
        RuntimeError: If the LLM call fails or returns unparseable output.
    """
    logger.info(f"Agent 2 (Root Cause Analyzer) starting - analyzing {len(signals.get('signals', []))} signals")

    # Enrich context with Agent 1 output so Agent 2 has full picture
    enriched_context = _enrich_context(context, signals)

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
        raise RuntimeError(f"Agent 2 LLM call failed: {e}") from e

    raw = response.choices[0].message.content.strip()
    logger.debug(f"Agent 2 raw response: {raw[:200]}...")

    result = _parse_response(raw)
    causes_found = len(result.get("root_causes", []))
    logger.info(f"Agent 2 complete - {causes_found} root causes diagnosed")

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _enrich_context(context: str, signals: dict[str, Any]) -> str:
    """Append Agent 1 signal output to the root cause context string.

    Agent 2 needs both the raw dimensional data (from context_builder)
    AND the prioritized signals (from Agent 1) to do accurate diagnosis.
    """
    signals_text = json.dumps(signals, indent=2)
    return f"""{context}

SIGNALS IDENTIFIED BY SIGNAL DETECTOR (Agent 1 output):
{signals_text}

Using the dimensional breakdowns above AND the signals identified by Agent 1,
diagnose the root cause for each signal. Reference specific data points as evidence.
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
        logger.error(f"Agent 2 failed to parse JSON response: {e}")
        logger.error(f"Raw response was: {raw[:500]}")
        return {
            "root_causes": [],
            "cross_signal_patterns": "Root cause analysis failed - unable to parse LLM response.",
            "data_quality_notes": str(e),
            "error": str(e),
        }