"""Agent 1: Signal Detector - identifies and ranks the most significant revenue signals."""

import json
import logging
from typing import Any

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a revenue signal detection specialist for an e-commerce business.

Your job is to analyze KPI data and statistical anomalies, then identify the top 3-5 most
significant signals that require business attention.

For each signal, you must assess:
- What exactly happened (specific metric, dimension, magnitude)
- Whether it is a positive or negative signal
- The severity (CRITICAL / WARNING / ROUTINE)
- A confidence score (0.0 - 1.0) based on the magnitude and consistency of the data

OUTPUT RULES:
- Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown.
- Use exactly this schema:

{
  "signals": [
    {
      "id": "signal_1",
      "title": "Short title of the signal (max 10 words)",
      "description": "What happened, with specific numbers",
      "metric": "revenue | aov | order_count",
      "dimension": "overall | category:<name> | state:<name>",
      "change_pct": -26.6,
      "severity": "CRITICAL | WARNING | ROUTINE",
      "confidence": 0.92,
      "signal_type": "drop | spike | trend_reversal | sustained_decline"
    }
  ],
  "overall_assessment": "One sentence summary of the overall revenue situation",
  "monitoring_priority": "CRITICAL | WARNING | ROUTINE"
}"""


def run(context: str) -> dict[str, Any]:
    """Run the Signal Detector agent on the prepared context.

    Args:
        context: Formatted context string from context_builder for signal_detector.

    Returns:
        Parsed JSON dict with signals, overall_assessment, and monitoring_priority.

    Raises:
        RuntimeError: If the LLM call fails or returns unparseable output.
    """
    logger.info("Agent 1 (Signal Detector) starting")

    client = Groq(api_key=GROQ_API_KEY)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=LLM_TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"Agent 1 LLM call failed: {e}") from e

    raw = response.choices[0].message.content.strip()
    logger.debug(f"Agent 1 raw response: {raw[:200]}...")

    result = _parse_response(raw)
    signals_found = len(result.get("signals", []))
    priority = result.get("monitoring_priority", "unknown")
    logger.info(f"Agent 1 complete - {signals_found} signals identified | Priority: {priority}")

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_response(raw: str) -> dict[str, Any]:
    """Parse and validate the LLM JSON response.

    Strips markdown fences if present, then parses JSON.
    Falls back to a structured error dict if parsing fails.
    """
    # Strip markdown code fences if the model added them
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Agent 1 failed to parse JSON response: {e}")
        logger.error(f"Raw response was: {raw[:500]}")
        return {
            "signals": [],
            "overall_assessment": "Signal detection failed - unable to parse LLM response.",
            "monitoring_priority": "ROUTINE",
            "error": str(e),
        }