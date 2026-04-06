"""Statistical anomaly detection on KPI outputs from kpi_engine.py."""

import logging
from typing import Any

import numpy as np
import pandas as pd

from src.config import ANOMALY_ZSCORE_THRESHOLD, CRITICAL_DROP_PCT, WARNING_DROP_PCT

logger = logging.getLogger(__name__)

# Severity levels used across the entire pipeline
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING = "WARNING"
SEVERITY_ROUTINE = "ROUTINE"


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def detect_anomalies(kpis: dict[str, Any]) -> dict[str, Any]:
    """Run all anomaly detection checks on the KPI package.

    This is the main function called by the orchestrator. It feeds
    the output of compute_all_kpis() and returns a structured anomaly
    report ready for consumption by Agent 1 (Signal Detector).

    Args:
        kpis: Output of kpi_engine.compute_all_kpis().

    Returns:
        Dict with anomalies list, max_severity, and summary counts.
    """
    logger.info("Starting anomaly detection")
    anomalies: list[dict[str, Any]] = []

    pop = kpis.get("period_over_period", {})
    trend = kpis.get("trend", [])

    if pop:
        anomalies += _check_overall_revenue(pop)
        anomalies += _check_dimensional_changes(pop.get("by_category", []), dimension="category")
        anomalies += _check_dimensional_changes(pop.get("by_state", []), dimension="state")

    if trend:
        anomalies += _check_zscore_anomalies(trend)

    # Sort by severity priority then magnitude
    severity_order = {SEVERITY_CRITICAL: 0, SEVERITY_WARNING: 1, SEVERITY_ROUTINE: 2}
    anomalies.sort(key=lambda x: (severity_order[x["severity"]], -abs(x["change_pct"])))

    max_severity = anomalies[0]["severity"] if anomalies else SEVERITY_ROUTINE

    counts = {s: sum(1 for a in anomalies if a["severity"] == s) for s in [SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_ROUTINE]}

    logger.info(
        f"Detection complete - {len(anomalies)} anomalies found | "
        f"CRITICAL: {counts[SEVERITY_CRITICAL]} | WARNING: {counts[SEVERITY_WARNING]}"
    )

    return {
        "max_severity": max_severity,
        "total_anomalies": len(anomalies),
        "counts": counts,
        "anomalies": anomalies,
        "period": pop.get("current_period", "unknown"),
        "previous_period": pop.get("previous_period", "unknown"),
    }


# ---------------------------------------------------------------------------
# Detection checks
# ---------------------------------------------------------------------------

def _check_overall_revenue(pop: dict[str, Any]) -> list[dict[str, Any]]:
    """Flag overall revenue and AOV changes that exceed thresholds."""
    anomalies = []

    for metric in ["revenue", "aov", "order_count"]:
        data = pop.get(metric, {})
        change_pct = data.get("change_pct", 0)

        severity = _classify_severity(change_pct)
        if severity == SEVERITY_ROUTINE:
            continue

        anomalies.append({
            "type": "overall",
            "metric": metric,
            "dimension": None,
            "value": data.get("current"),
            "previous_value": data.get("previous"),
            "change_pct": change_pct,
            "severity": severity,
            "description": (
                f"Overall {metric.upper()} changed {change_pct:+.1f}% "
                f"({_fmt(data.get('previous'))} -> {_fmt(data.get('current'))})"
            ),
        })
        logger.info(f"[{severity}] Overall {metric}: {change_pct:+.1f}%")

    return anomalies


def _check_dimensional_changes(
    dimensional_data: list[dict[str, Any]],
    dimension: str,
) -> list[dict[str, Any]]:
    """Flag individual category or state revenue changes that exceed thresholds."""
    anomalies = []
    dim_key = "product_category_name_english" if dimension == "category" else "customer_state"

    for row in dimensional_data:
        change_pct = row.get("change_pct", 0)
        severity = _classify_severity(change_pct)

        if severity == SEVERITY_ROUTINE:
            continue

        dim_value = row.get(dim_key, "unknown")
        anomalies.append({
            "type": f"dimensional_{dimension}",
            "metric": "revenue",
            "dimension": dim_value,
            "value": row.get("curr_revenue"),
            "previous_value": row.get("prev_revenue"),
            "change_pct": change_pct,
            "severity": severity,
            "description": (
                f"{dimension.capitalize()} '{dim_value}' revenue changed {change_pct:+.1f}% "
                f"(R${row.get('prev_revenue', 0):,.0f} -> R${row.get('curr_revenue', 0):,.0f})"
            ),
        })

    if anomalies:
        logger.info(f"Dimensional {dimension}: {len(anomalies)} anomalies detected")

    return anomalies


def _check_zscore_anomalies(trend: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect statistically unusual revenue periods using Z-score analysis.

    Z-score measures how many standard deviations a value is from the mean.
    A Z-score beyond the configured threshold (default: 2.5) indicates
    an unusually high or low period relative to historical norms.

    Args:
        trend: Output of kpi_engine.compute_trend().

    Returns:
        List of anomaly dicts for statistically extreme periods.
    """
    if len(trend) < 4:
        logger.warning("Not enough trend periods for Z-score analysis (need >= 4)")
        return []

    revenues = np.array([p["revenue"] for p in trend])
    mean = revenues.mean()
    std = revenues.std()

    if std == 0:
        return []

    anomalies = []
    for point in trend:
        z = (point["revenue"] - mean) / std
        if abs(z) < ANOMALY_ZSCORE_THRESHOLD:
            continue

        direction = "spike" if z > 0 else "drop"
        severity = SEVERITY_CRITICAL if abs(z) >= ANOMALY_ZSCORE_THRESHOLD + 1 else SEVERITY_WARNING

        anomalies.append({
            "type": "zscore",
            "metric": "revenue",
            "dimension": point["period"],
            "value": point["revenue"],
            "previous_value": round(float(mean), 2),
            "change_pct": round((point["revenue"] - mean) / mean * 100, 2),
            "z_score": round(float(z), 3),
            "severity": severity,
            "description": (
                f"Statistical {direction} detected in period {point['period']}: "
                f"R${point['revenue']:,.0f} (Z={z:.2f}, mean=R${mean:,.0f})"
            ),
        })
        logger.info(f"[{severity}] Z-score anomaly in {point['period']}: Z={z:.2f}")

    return anomalies


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_severity(change_pct: float) -> str:
    """Map a percentage change to a severity level.

    Uses thresholds from config:
    - CRITICAL: |change| > CRITICAL_DROP_PCT (default 15%)
    - WARNING:  |change| > WARNING_DROP_PCT  (default 5%)
    - ROUTINE:  everything else
    """
    abs_change = abs(change_pct)
    if abs_change >= CRITICAL_DROP_PCT:
        return SEVERITY_CRITICAL
    if abs_change >= WARNING_DROP_PCT:
        return SEVERITY_WARNING
    return SEVERITY_ROUTINE


def _fmt(value: Any) -> str:
    """Format a numeric value for display in descriptions."""
    if value is None:
        return "N/A"
    return f"R${float(value):,.0f}"