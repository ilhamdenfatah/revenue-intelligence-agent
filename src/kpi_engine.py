"""KPI computation engine - transforms the master orders DataFrame into structured metrics."""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def compute_all_kpis(df: pd.DataFrame, period: str = "month") -> dict[str, Any]:
    """Compute the full KPI package from the master orders DataFrame.

    This is the main function called by the orchestrator and AI agents.
    It returns a single structured dict containing every metric the
    Signal Detector agent needs to identify anomalies.

    Args:
        df: Master orders DataFrame from data_ingestion.build_orders_master().
        period: Aggregation period - 'day', 'week', or 'month'.

    Returns:
        Dict with keys: summary, trend, by_category, by_state, period_over_period.
    """
    logger.info(f"Computing KPIs for {len(df):,} orders at '{period}' granularity")

    kpis = {
        "period": period,
        "summary": compute_summary(df),
        "trend": compute_trend(df, period),
        "by_category": compute_by_dimension(df, "product_category_name_english", top_n=15),
        "by_state": compute_by_dimension(df, "customer_state", top_n=10),
        "period_over_period": compute_period_over_period(df, period),
    }

    logger.info("KPI computation complete")
    return kpis


# ---------------------------------------------------------------------------
# Individual KPI functions
# ---------------------------------------------------------------------------

def compute_summary(df: pd.DataFrame) -> dict[str, float]:
    """Compute overall business summary metrics.

    Args:
        df: Master orders DataFrame.

    Returns:
        Dict with total_orders, total_revenue, aov, median_order_value,
        avg_items_per_order.
    """
    total_orders = len(df)
    total_revenue = df["revenue"].sum()
    aov = df["revenue"].mean()
    median_order_value = df["revenue"].median()
    avg_items = df["item_count"].mean() if "item_count" in df.columns else None

    summary = {
        "total_orders": int(total_orders),
        "total_revenue": round(float(total_revenue), 2),
        "aov": round(float(aov), 2),
        "median_order_value": round(float(median_order_value), 2),
        "avg_items_per_order": round(float(avg_items), 2) if avg_items is not None else None,
    }

    logger.info(
        f"Summary - Orders: {total_orders:,} | Revenue: R${total_revenue:,.0f} | AOV: R${aov:.2f}"
    )
    return summary


def compute_trend(df: pd.DataFrame, period: str = "month") -> list[dict[str, Any]]:
    """Compute revenue and order volume trend over time.

    Args:
        df: Master orders DataFrame.
        period: 'day', 'week', or 'month'.

    Returns:
        List of dicts, each representing one time period with revenue,
        order_count, and aov.
    """
    period_col = _get_period_col(df, period)

    trend = (
        df.groupby(period_col)
        .agg(
            revenue=("revenue", "sum"),
            order_count=("order_id", "count"),
        )
        .reset_index()
    )
    trend["aov"] = trend["revenue"] / trend["order_count"]
    trend[period_col] = trend[period_col].astype(str)
    trend = trend.rename(columns={period_col: "period"})

    # Round floats for clean JSON serialization
    trend["revenue"] = trend["revenue"].round(2)
    trend["aov"] = trend["aov"].round(2)

    logger.info(f"Trend computed: {len(trend)} {period} periods")
    return trend.to_dict(orient="records")


def compute_by_dimension(
    df: pd.DataFrame,
    dimension: str,
    top_n: int = 15,
) -> list[dict[str, Any]]:
    """Compute revenue breakdown by a categorical dimension.

    Args:
        df: Master orders DataFrame.
        dimension: Column name to group by (e.g. 'product_category_name_english').
        top_n: Number of top values to return.

    Returns:
        List of dicts sorted by revenue descending, each with the dimension
        value, revenue, order_count, aov, and revenue_share_pct.
    """
    if dimension not in df.columns:
        logger.warning(f"Dimension '{dimension}' not found in DataFrame, skipping")
        return []

    total_revenue = df["revenue"].sum()

    breakdown = (
        df.groupby(dimension)
        .agg(
            revenue=("revenue", "sum"),
            order_count=("order_id", "count"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
        .head(top_n)
    )
    breakdown["aov"] = (breakdown["revenue"] / breakdown["order_count"]).round(2)
    breakdown["revenue_share_pct"] = (breakdown["revenue"] / total_revenue * 100).round(2)
    breakdown["revenue"] = breakdown["revenue"].round(2)

    logger.info(f"Breakdown by '{dimension}': top {len(breakdown)} returned")
    return breakdown.to_dict(orient="records")


def compute_period_over_period(
    df: pd.DataFrame,
    period: str = "month",
    n_periods: int = 3,
) -> dict[str, Any]:
    """Compute period-over-period revenue change for the most recent periods.

    Compares the latest period against the previous one, and provides
    percentage changes for the top categories and states as well.
    This output is the primary input for the Signal Detector agent.

    Args:
        df: Master orders DataFrame.
        period: 'day', 'week', or 'month'.
        n_periods: Number of recent periods to include in the comparison window.

    Returns:
        Dict with current_period, previous_period, revenue_change_pct,
        order_count_change_pct, aov_change_pct, and dimensional breakdowns.
    """
    period_col = _get_period_col(df, period)

    trend = (
        df.groupby(period_col)
        .agg(revenue=("revenue", "sum"), order_count=("order_id", "count"))
        .reset_index()
        .sort_values(period_col)
    )
    trend["aov"] = trend["revenue"] / trend["order_count"]

    if len(trend) < 2:
        logger.warning("Not enough periods to compute period-over-period comparison")
        return {}

    current = trend.iloc[-1]
    previous = trend.iloc[-2]

    def pct_change(curr: float, prev: float) -> float:
        if prev == 0:
            return 0.0
        return round((curr - prev) / prev * 100, 2)

    pop = {
        "current_period": str(current[period_col]),
        "previous_period": str(previous[period_col]),
        "revenue": {
            "current": round(float(current["revenue"]), 2),
            "previous": round(float(previous["revenue"]), 2),
            "change_pct": pct_change(current["revenue"], previous["revenue"]),
        },
        "order_count": {
            "current": int(current["order_count"]),
            "previous": int(previous["order_count"]),
            "change_pct": pct_change(current["order_count"], previous["order_count"]),
        },
        "aov": {
            "current": round(float(current["aov"]), 2),
            "previous": round(float(previous["aov"]), 2),
            "change_pct": pct_change(current["aov"], previous["aov"]),
        },
        "by_category": _dimensional_pop(df, period_col, "product_category_name_english", current, previous),
        "by_state": _dimensional_pop(df, period_col, "customer_state", current, previous),
    }

    logger.info(
        f"Period-over-period: {pop['previous_period']} -> {pop['current_period']} | "
        f"Revenue change: {pop['revenue']['change_pct']:+.1f}%"
    )
    return pop


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_period_col(df: pd.DataFrame, period: str) -> str:
    """Map period string to the correct DataFrame column name."""
    mapping = {"day": "date", "week": "week", "month": "month"}
    if period not in mapping:
        raise ValueError(f"Invalid period '{period}'. Choose from: {list(mapping.keys())}")
    col = mapping[period]
    if col not in df.columns:
        raise ValueError(f"Column '{col}' not found. Ensure build_orders_master() was called.")
    return col


def _dimensional_pop(
    df: pd.DataFrame,
    period_col: str,
    dimension: str,
    current: pd.Series,
    previous: pd.Series,
    top_n: int = 10,
) -> list[dict[str, Any]]:
    """Compute period-over-period revenue change per dimension value.

    Used internally by compute_period_over_period() to show which categories
    or states drove the overall change.
    """
    if dimension not in df.columns:
        return []

    def agg_for_period(period_val: Any) -> pd.DataFrame:
        mask = df[period_col].astype(str) == str(period_val)
        return (
            df[mask]
            .groupby(dimension)["revenue"]
            .sum()
            .reset_index()
            .rename(columns={"revenue": "revenue"})
        )

    curr_df = agg_for_period(current[period_col]).rename(columns={"revenue": "curr_revenue"})
    prev_df = agg_for_period(previous[period_col]).rename(columns={"revenue": "prev_revenue"})

    merged = curr_df.merge(prev_df, on=dimension, how="outer").fillna(0)
    merged["change_pct"] = merged.apply(
        lambda r: round((r["curr_revenue"] - r["prev_revenue"]) / r["prev_revenue"] * 100, 2)
        if r["prev_revenue"] != 0 else 0.0,
        axis=1,
    )
    merged = merged.sort_values("curr_revenue", ascending=False).head(top_n)
    merged["curr_revenue"] = merged["curr_revenue"].round(2)
    merged["prev_revenue"] = merged["prev_revenue"].round(2)

    return merged.to_dict(orient="records")