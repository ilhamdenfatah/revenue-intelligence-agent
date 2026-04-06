"""Assembles structured context packages for LLM agent consumption.

The context builder is the bridge between the data/processing layer and the
AI intelligence layer. It takes KPI outputs and anomaly detection results,
then formats them into clean, information-dense prompts that the agents can
reason over effectively.
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def build_agent_context(
    kpis: dict[str, Any],
    anomalies: dict[str, Any],
) -> dict[str, str]:
    """Build the full context package for all four agents.

    Each agent receives a tailored context string - only the information
    relevant to its specific task. This keeps prompts focused and reduces
    token usage.

    Args:
        kpis: Output of kpi_engine.compute_all_kpis().
        anomalies: Output of anomaly_detector.detect_anomalies().

    Returns:
        Dict with keys: signal_detector, root_cause, action_recommender,
        report_generator - each containing a formatted context string.
    """
    logger.info("Building agent context packages")

    context = {
        "signal_detector": _build_signal_detector_context(kpis, anomalies),
        "root_cause": _build_root_cause_context(kpis, anomalies),
        "action_recommender": _build_action_recommender_context(kpis, anomalies),
        "report_generator": _build_report_generator_context(kpis, anomalies),
    }

    for agent, ctx in context.items():
        logger.info(f"Context built for '{agent}': {len(ctx)} chars")

    return context


# ---------------------------------------------------------------------------
# Per-agent context builders
# ---------------------------------------------------------------------------

def _build_signal_detector_context(
    kpis: dict[str, Any],
    anomalies: dict[str, Any],
) -> str:
    """Build context for Agent 1 - Signal Detector.

    Provides the statistical anomaly results and period-over-period summary.
    Agent 1 uses this to identify and rank the most significant signals.
    """
    pop = kpis.get("period_over_period", {})
    summary = kpis.get("summary", {})

    return f"""You are analyzing revenue performance for an e-commerce business.

ANALYSIS PERIOD: {anomalies.get('period', 'N/A')} vs {anomalies.get('previous_period', 'N/A')}

BUSINESS SUMMARY:
- Total Orders: {summary.get('total_orders', 0):,}
- Total Revenue: R${summary.get('total_revenue', 0):,.2f}
- Average Order Value (AOV): R${summary.get('aov', 0):.2f}

PERIOD-OVER-PERIOD CHANGES:
- Revenue: {pop.get('revenue', {}).get('change_pct', 0):+.1f}% \
(R${pop.get('revenue', {}).get('previous', 0):,.0f} -> R${pop.get('revenue', {}).get('current', 0):,.0f})
- Order Count: {pop.get('order_count', {}).get('change_pct', 0):+.1f}%
- AOV: {pop.get('aov', {}).get('change_pct', 0):+.1f}%

STATISTICAL ANOMALIES DETECTED ({anomalies.get('total_anomalies', 0)} total):
{_format_anomalies_for_context(anomalies.get('anomalies', []))}

MAX SEVERITY: {anomalies.get('max_severity', 'ROUTINE')}
"""


def _build_root_cause_context(
    kpis: dict[str, Any],
    anomalies: dict[str, Any],
) -> str:
    """Build context for Agent 2 - Root Cause Analyzer.

    Provides anomaly signals plus full dimensional breakdowns so the agent
    can correlate patterns across categories and geographies.
    """
    pop = kpis.get("period_over_period", {})

    category_breakdown = _format_dimensional_breakdown(
        pop.get("by_category", []),
        key="product_category_name_english",
        label="Category",
    )
    state_breakdown = _format_dimensional_breakdown(
        pop.get("by_state", []),
        key="customer_state",
        label="State",
    )

    critical = [a for a in anomalies.get("anomalies", []) if a["severity"] == "CRITICAL"]

    return f"""You are diagnosing root causes for revenue anomalies in an e-commerce business.

ANALYSIS PERIOD: {anomalies.get('period', 'N/A')} vs {anomalies.get('previous_period', 'N/A')}

CRITICAL SIGNALS TO DIAGNOSE:
{_format_anomalies_for_context(critical)}

FULL CATEGORY BREAKDOWN (current period vs previous):
{category_breakdown}

FULL STATE/GEOGRAPHY BREAKDOWN (current period vs previous):
{state_breakdown}

OVERALL METRICS:
- Revenue change: {pop.get('revenue', {}).get('change_pct', 0):+.1f}%
- Order count change: {pop.get('order_count', {}).get('change_pct', 0):+.1f}%
- AOV change: {pop.get('aov', {}).get('change_pct', 0):+.1f}%

NOTE: Order count increasing while revenue decreases indicates AOV compression,
not demand loss. Factor this into your root cause analysis.
"""


def _build_action_recommender_context(
    kpis: dict[str, Any],
    anomalies: dict[str, Any],
) -> str:
    """Build context for Agent 3 - Action Recommender.

    Provides signals and root causes together so the agent can generate
    specific, prioritized actions tied to each diagnosed problem.
    """
    pop = kpis.get("period_over_period", {})
    summary = kpis.get("summary", {})

    critical_anomalies = [a for a in anomalies.get("anomalies", []) if a["severity"] == "CRITICAL"]
    warning_anomalies = [a for a in anomalies.get("anomalies", []) if a["severity"] == "WARNING"]

    return f"""You are generating prioritized action recommendations for an e-commerce revenue team.

PERIOD: {anomalies.get('period', 'N/A')} vs {anomalies.get('previous_period', 'N/A')}

BUSINESS CONTEXT:
- Total Revenue: R${summary.get('total_revenue', 0):,.0f}
- AOV: R${summary.get('aov', 0):.2f}
- Overall revenue change: {pop.get('revenue', {}).get('change_pct', 0):+.1f}%

CRITICAL ISSUES REQUIRING IMMEDIATE ACTION ({len(critical_anomalies)}):
{_format_anomalies_for_context(critical_anomalies)}

WARNING ISSUES TO MONITOR ({len(warning_anomalies)}):
{_format_anomalies_for_context(warning_anomalies)}

Generate specific, actionable recommendations. Each action must be:
1. Tied to a specific signal above
2. Executable within 24-48 hours
3. Assigned an urgency: IMMEDIATE / THIS WEEK / MONITOR
"""


def _build_report_generator_context(
    kpis: dict[str, Any],
    anomalies: dict[str, Any],
) -> str:
    """Build context for Agent 4 - Report Generator.

    Provides the complete picture - summary, anomalies, and period context -
    for generating multi-format executive reports.
    """
    summary = kpis.get("summary", {})
    pop = kpis.get("period_over_period", {})

    top_anomalies = anomalies.get("anomalies", [])[:5]

    return f"""You are generating an executive revenue intelligence report.

REPORT PERIOD: {anomalies.get('period', 'N/A')}
COMPARISON: vs {anomalies.get('previous_period', 'N/A')}
OVERALL STATUS: {anomalies.get('max_severity', 'ROUTINE')}

KEY METRICS:
- Revenue: R${pop.get('revenue', {}).get('current', 0):,.0f} \
({pop.get('revenue', {}).get('change_pct', 0):+.1f}% MoM)
- Orders: {pop.get('order_count', {}).get('current', 0):,} \
({pop.get('order_count', {}).get('change_pct', 0):+.1f}% MoM)
- AOV: R${pop.get('aov', {}).get('current', 0):.2f} \
({pop.get('aov', {}).get('change_pct', 0):+.1f}% MoM)

TOP SIGNALS ({anomalies.get('total_anomalies', 0)} total - showing top 5):
{_format_anomalies_for_context(top_anomalies)}

SEVERITY BREAKDOWN:
- CRITICAL: {anomalies.get('counts', {}).get('CRITICAL', 0)}
- WARNING: {anomalies.get('counts', {}).get('WARNING', 0)}
- ROUTINE: {anomalies.get('counts', {}).get('ROUTINE', 0)}

Generate THREE output formats:
1. SLACK_SUMMARY: 2-3 sentences, emoji indicators, key numbers only
2. EMAIL_BRIEF: structured with sections (Overview, Key Signals, Recommended Actions)
3. WHATSAPP_ALERT: single paragraph, plain text, urgent tone if CRITICAL
"""


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _format_anomalies_for_context(anomalies: list[dict[str, Any]]) -> str:
    """Format anomaly list into a readable text block for LLM prompts."""
    if not anomalies:
        return "  No anomalies detected."

    lines = []
    for i, a in enumerate(anomalies, 1):
        dimension = f" [{a['dimension']}]" if a.get("dimension") else ""
        lines.append(
            f"  {i}. [{a['severity']}]{dimension} {a['description']}"
        )
    return "\n".join(lines)


def _format_dimensional_breakdown(
    data: list[dict[str, Any]],
    key: str,
    label: str,
) -> str:
    """Format a dimensional breakdown list into a readable table for LLM prompts."""
    if not data:
        return f"  No {label.lower()} breakdown available."

    lines = []
    for row in data:
        name = row.get(key, "unknown")
        curr = row.get("curr_revenue", 0)
        prev = row.get("prev_revenue", 0)
        change = row.get("change_pct", 0)
        direction = "+" if change >= 0 else ""
        lines.append(
            f"  {label} '{name}': R${curr:,.0f} ({direction}{change:.1f}% from R${prev:,.0f})"
        )
    return "\n".join(lines)