"""Agent 4: Report Generator - synthesizes all agent outputs into delivery-ready reports."""

import json
import logging
from typing import Any

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an executive communication specialist for an e-commerce business.

You receive the complete revenue intelligence package - signals, root causes, and action
recommendations - and synthesize them into delivery-ready reports for different channels.

WRITING STANDARDS:
- Lead with the most important finding, not background context
- Use specific numbers, not vague language ("revenue dropped R$42K" not "revenue declined")
- Confident, direct tone - no hedging language like "it seems" or "possibly"
- No jargon - write as if explaining to a smart non-technical executive
- Slack/WhatsApp: punchy and scannable. Email: structured and complete.

SEVERITY INDICATORS:
- CRITICAL status: use 🔴 in Slack, urgent tone in WhatsApp, "ACTION REQUIRED" in email subject
- WARNING status: use 🟡 in Slack, measured tone in WhatsApp, "ATTENTION NEEDED" in email subject
- ROUTINE status: use 🟢 in Slack, neutral tone everywhere

OUTPUT RULES:
- Respond ONLY with a valid JSON object. No preamble, no explanation, no markdown.
- All string values must be single-line. Use \\n for line breaks inside strings, never actual newlines.
- The email body must be a single string with \\n for paragraph breaks, not a multi-line value.
- Use exactly this schema:

{
  "slack_summary": "2-3 sentences with emoji indicators and key numbers",
  "whatsapp_alert": "Single paragraph, plain text, urgent if CRITICAL, max 100 words",
  "email_report": {
    "subject": "Email subject line",
    "body": "Full email body with clear sections: Overview, Key Signals, Root Causes, Recommended Actions"
  },
  "one_liner": "Single sentence suitable for a dashboard headline or push notification",
  "severity": "CRITICAL | WARNING | ROUTINE"
}"""


def run(
    context: str,
    signals: dict[str, Any],
    root_causes: dict[str, Any],
    actions: dict[str, Any],
) -> dict[str, Any]:
    """Run the Report Generator agent on the full intelligence package.

    Args:
        context: Formatted context string from context_builder for report_generator.
        signals: Output dict from signal_detector.run().
        root_causes: Output dict from root_cause_analyzer.run().
        actions: Output dict from action_recommender.run().

    Returns:
        Parsed JSON dict with slack_summary, whatsapp_alert, email_report, and one_liner.

    Raises:
        RuntimeError: If the LLM call fails or returns unparseable output.
    """
    logger.info("Agent 4 (Report Generator) starting - synthesizing full intelligence package")

    enriched_context = _enrich_context(context, signals, root_causes, actions)

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
        raise RuntimeError(f"Agent 4 LLM call failed: {e}") from e

    raw = response.choices[0].message.content.strip()
    logger.debug(f"Agent 4 raw response: {raw[:200]}...")

    result = _parse_response(raw)
    logger.info(f"Agent 4 complete - reports generated | Severity: {result.get('severity', 'unknown')}")

    return result


def format_for_display(report: dict[str, Any]) -> str:
    """Format the report dict into a human-readable console output.

    Useful for debugging and local testing without a delivery channel.

    Args:
        report: Output dict from run().

    Returns:
        Formatted string with all report formats clearly separated.
    """
    lines = [
        "=" * 60,
        "REVENUE INTELLIGENCE REPORT",
        "=" * 60,
        "",
        f"ONE-LINER: {report.get('one_liner', 'N/A')}",
        f"SEVERITY:  {report.get('severity', 'N/A')}",
        "",
        "--- SLACK ---",
        report.get("slack_summary", "N/A"),
        "",
        "--- WHATSAPP ---",
        report.get("whatsapp_alert", "N/A"),
        "",
        "--- EMAIL ---",
        f"Subject: {report.get('email_report', {}).get('subject', 'N/A')}",
        "",
        report.get("email_report", {}).get("body", "N/A"),
        "",
        "=" * 60,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _enrich_context(
    context: str,
    signals: dict[str, Any],
    root_causes: dict[str, Any],
    actions: dict[str, Any],
) -> str:
    """Append all three prior agent outputs to the report generator context."""
    return f"""{context}

SIGNALS (Agent 1 output):
{json.dumps(signals, indent=2)}

ROOT CAUSES (Agent 2 output):
{json.dumps(root_causes, indent=2)}

RECOMMENDED ACTIONS (Agent 3 output):
{json.dumps(actions, indent=2)}

Synthesize the above into the three delivery formats. The email body should be
comprehensive. The Slack and WhatsApp versions should be concise but include
the most critical numbers and the top 1-2 immediate actions.
"""


def _parse_response(raw: str) -> dict[str, Any]:
    """Parse and validate the LLM JSON response.

    Handles two common LLM JSON issues:
    1. Markdown code fences (```json ... ```)
    2. Literal newlines inside JSON string values (invalid per JSON spec)
    """
    cleaned = raw.strip()

    # Strip markdown fences
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    # Replace literal newlines inside JSON strings with \n escape sequence
    # This fixes "Invalid control character" errors from multi-line LLM outputs
    import re
    cleaned = re.sub(r'(?<=": ")(.*?)(?="(?:\s*[,}\]]))', 
                     lambda m: m.group(0).replace('\n', '\\n').replace('\r', ''),
                     cleaned, flags=re.DOTALL)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Final fallback: replace all literal newlines globally
        try:
            cleaned = cleaned.replace('\n', '\\n').replace('\r', '')
            # Restore actual structural newlines (between JSON keys)
            cleaned = cleaned.replace('\\n  ', '\n  ').replace('\\n}', '\n}')
            return json.loads(cleaned)
        except json.JSONDecodeError as e2:
            logger.error(f"Agent 4 failed to parse JSON response: {e2}")
            logger.error(f"Raw response was: {raw[:500]}")
            return {
                "slack_summary": "Report generation failed.",
                "whatsapp_alert": "Report generation failed.",
                "email_report": {"subject": "Report generation failed", "body": str(e2)},
                "one_liner": "Report generation failed.",
                "severity": "ROUTINE",
                "error": str(e2),
            }