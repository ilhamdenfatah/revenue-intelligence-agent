"""Synthetic data simulator - generates realistic 'today's data' for demo and testing.

Simulates daily e-commerce transactions based on Olist historical statistics,
with controllable anomaly injection to demonstrate the detection pipeline.
Run this script to generate a fresh batch of simulated data for any date.
"""

import argparse
import logging
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from src.config import DATA_RAW, DATA_SIMULATED
from src.data_ingestion import load_processed

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Historical baseline stats derived from Olist dataset
# (computed from actual data - these are real distribution parameters)
# ---------------------------------------------------------------------------

BASELINE = {
    "daily_orders_mean": 320,
    "daily_orders_std": 45,
    "revenue_per_order_mean": 159.86,
    "revenue_per_order_std": 120.0,
    "revenue_per_order_min": 10.0,
    "top_categories": [
        "health_beauty", "watches_gifts", "bed_bath_table", "housewares",
        "sports_leisure", "furniture_decor", "auto", "computers_accessories",
        "telephony", "pet_shop", "toys", "cool_stuff", "garden_tools",
        "perfumery", "baby",
    ],
    "category_weights": [
        0.12, 0.10, 0.09, 0.08, 0.08, 0.07, 0.07, 0.06,
        0.05, 0.05, 0.04, 0.04, 0.04, 0.03, 0.03,
    ],
    "top_states": ["SP", "RJ", "MG", "RS", "PR", "SC", "BA", "DF", "GO", "ES"],
    "state_weights": [0.42, 0.13, 0.11, 0.06, 0.06, 0.05, 0.04, 0.03, 0.03, 0.02],
}

# Anomaly presets — use these for demo to guarantee interesting signals
ANOMALY_PRESETS = {
    "revenue_crash": {
        "description": "Overall revenue drops 25% — simulates a bad day",
        "order_multiplier": 0.75,
        "revenue_multiplier": 0.75,
    },
    "category_drop": {
        "description": "watches_gifts drops 40% — simulates stockout or pricing issue",
        "category_override": {"watches_gifts": 0.60},
    },
    "state_drop": {
        "description": "BA and ES drop 50% — simulates regional logistics issue",
        "state_override": {"BA": 0.50, "ES": 0.50},
    },
    "aov_compression": {
        "description": "Order count up 20%, but AOV down 20% — mix shift",
        "order_multiplier": 1.20,
        "revenue_multiplier": 0.80,
    },
    "healthy": {
        "description": "Normal day with slight growth — no anomalies",
        "order_multiplier": 1.05,
        "revenue_multiplier": 1.05,
    },
}


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def generate_daily_data(
    target_date: Optional[date] = None,
    anomaly_preset: Optional[str] = None,
    n_orders: Optional[int] = None,
    save: bool = True,
) -> pd.DataFrame:
    """Generate a synthetic daily orders batch.

    Args:
        target_date: Date to simulate. Defaults to today.
        anomaly_preset: Name of anomaly preset to inject (see ANOMALY_PRESETS).
        n_orders: Override number of orders. Defaults to baseline distribution.
        save: If True, save to data/simulated/ as CSV.

    Returns:
        DataFrame with simulated orders in the same schema as orders_master.
    """
    if target_date is None:
        target_date = date.today()

    preset = ANOMALY_PRESETS.get(anomaly_preset, {}) if anomaly_preset else {}
    logger.info(f"Generating synthetic data for {target_date} | preset={anomaly_preset or 'none'}")

    # Determine order count
    order_multiplier = preset.get("order_multiplier", 1.0)
    if n_orders is None:
        n_orders = max(10, int(
            np.random.normal(BASELINE["daily_orders_mean"], BASELINE["daily_orders_std"])
            * order_multiplier
        ))

    logger.info(f"Generating {n_orders} orders")

    orders = []
    for i in range(n_orders):
        category = _sample_category(preset.get("category_override", {}))
        state = _sample_state(preset.get("state_override", {}))
        revenue = _sample_revenue(category, preset.get("revenue_multiplier", 1.0))
        timestamp = _sample_timestamp(target_date)

        orders.append({
            "order_id": f"sim_{target_date.strftime('%Y%m%d')}_{i:04d}",
            "customer_id": f"cust_{random.randint(10000, 99999)}",
            "order_status": "delivered",
            "order_purchase_timestamp": timestamp,
            "revenue": round(revenue, 2),
            "item_count": random.choices([1, 2, 3, 4], weights=[0.60, 0.25, 0.10, 0.05])[0],
            "product_id": f"prod_{random.randint(10000, 99999)}",
            "customer_state": state,
            "product_category_name_english": category,
            "date": target_date,
            "week": str(pd.Period(target_date, freq="W")),
            "month": str(pd.Period(target_date, freq="M")),
            "is_simulated": True,
        })

    df = pd.DataFrame(orders)
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])

    if save:
        _save_simulated(df, target_date)

    total_revenue = df["revenue"].sum()
    aov = df["revenue"].mean()
    logger.info(
        f"Simulation complete | orders={n_orders} | "
        f"revenue=R${total_revenue:,.0f} | AOV=R${aov:.2f}"
    )

    if anomaly_preset:
        logger.info(f"Anomaly injected: {preset.get('description', anomaly_preset)}")

    return df


def generate_date_range(
    start_date: date,
    end_date: date,
    anomaly_schedule: Optional[dict[str, str]] = None,
) -> pd.DataFrame:
    """Generate synthetic data for a range of dates.

    Useful for populating a demo dataset that simulates recent weeks/months.

    Args:
        start_date: First date to generate.
        end_date: Last date to generate (inclusive).
        anomaly_schedule: Dict mapping date strings ('2024-01-15') to preset names.

    Returns:
        Combined DataFrame for all dates in range.
    """
    anomaly_schedule = anomaly_schedule or {}
    all_dfs = []
    current = start_date

    while current <= end_date:
        preset = anomaly_schedule.get(current.strftime("%Y-%m-%d"))
        df = generate_daily_data(target_date=current, anomaly_preset=preset, save=False)
        all_dfs.append(df)
        current += timedelta(days=1)

    combined = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Generated {len(combined):,} orders across {(end_date - start_date).days + 1} days")
    return combined


def append_to_master(simulated_df: pd.DataFrame) -> pd.DataFrame:
    """Append simulated data to the processed master DataFrame.

    This is how we make the pipeline treat simulated data as if it's
    real incoming data — by merging it into the existing master dataset
    before running KPI computation.

    Args:
        simulated_df: Output of generate_daily_data().

    Returns:
        Combined DataFrame with historical + simulated data.
    """
    historical = load_processed()
    combined = pd.concat([historical, simulated_df], ignore_index=True)
    logger.info(
        f"Appended {len(simulated_df):,} simulated rows to "
        f"{len(historical):,} historical rows = {len(combined):,} total"
    )
    return combined


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sample_category(category_override: dict[str, float]) -> str:
    """Sample a product category, applying any override multipliers."""
    categories = BASELINE["top_categories"]
    weights = list(BASELINE["category_weights"])

    for cat, multiplier in category_override.items():
        if cat in categories:
            idx = categories.index(cat)
            weights[idx] *= multiplier

    total = sum(weights)
    normalized = [w / total for w in weights]
    return random.choices(categories, weights=normalized)[0]


def _sample_state(state_override: dict[str, float]) -> str:
    """Sample a customer state, applying any override multipliers."""
    states = BASELINE["top_states"]
    weights = list(BASELINE["state_weights"])

    for state, multiplier in state_override.items():
        if state in states:
            idx = states.index(state)
            weights[idx] *= multiplier

    total = sum(weights)
    normalized = [w / total for w in weights]
    return random.choices(states, weights=normalized)[0]


def _sample_revenue(category: str, revenue_multiplier: float) -> float:
    """Sample a revenue value using a log-normal distribution.

    Log-normal is used because e-commerce order values are right-skewed:
    most orders are small, but occasional high-value orders exist.
    """
    # Category-specific AOV adjustments based on Olist data
    category_aov_multipliers = {
        "watches_gifts": 1.8,
        "computers_accessories": 1.6,
        "auto": 1.4,
        "furniture_decor": 1.3,
        "health_beauty": 0.9,
        "pet_shop": 0.8,
        "baby": 0.8,
        "toys": 0.7,
    }
    cat_multiplier = category_aov_multipliers.get(category, 1.0)
    mean = BASELINE["revenue_per_order_mean"] * cat_multiplier * revenue_multiplier
    std = BASELINE["revenue_per_order_std"]

    # Log-normal sampling
    sigma = np.sqrt(np.log(1 + (std / mean) ** 2))
    mu = np.log(mean) - sigma ** 2 / 2
    value = np.random.lognormal(mu, sigma)

    return max(BASELINE["revenue_per_order_min"], value)


def _sample_timestamp(target_date: date) -> datetime:
    """Sample a realistic order timestamp within business hours."""
    # Orders peak between 9am-9pm
    hour = random.choices(
        range(24),
        weights=[1,1,1,1,1,2,3,5,8,10,10,10,9,9,9,9,8,8,7,6,5,4,2,1]
    )[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime(target_date.year, target_date.month, target_date.day, hour, minute, second)


def _save_simulated(df: pd.DataFrame, target_date: date) -> Path:
    """Save simulated data to data/simulated/ as CSV."""
    DATA_SIMULATED.mkdir(parents=True, exist_ok=True)
    filename = f"simulated_{target_date.strftime('%Y%m%d')}.csv"
    path = DATA_SIMULATED / filename
    df.to_csv(path, index=False)
    logger.info(f"Saved simulated data to {path}")
    return path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="Generate synthetic revenue data for demo")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD (default: today)")
    parser.add_argument("--preset", type=str, default=None, choices=list(ANOMALY_PRESETS.keys()), help="Anomaly preset to inject")
    parser.add_argument("--orders", type=int, default=None, help="Override number of orders")
    parser.add_argument("--list-presets", action="store_true", help="List available anomaly presets")
    args = parser.parse_args()

    if args.list_presets:
        print("\nAvailable anomaly presets:")
        for name, preset in ANOMALY_PRESETS.items():
            print(f"  {name:20s} - {preset['description']}")
        print()
    else:
        target = date.fromisoformat(args.date) if args.date else date.today()
        df = generate_daily_data(
            target_date=target,
            anomaly_preset=args.preset,
            n_orders=args.orders,
        )
        print(f"\nGenerated {len(df)} orders for {target}")
        print(f"Total revenue: R${df['revenue'].sum():,.2f}")
        print(f"AOV: R${df['revenue'].mean():.2f}")
        print(f"\nCategory breakdown:")
        print(df.groupby("product_category_name_english")["revenue"].sum().sort_values(ascending=False).head(5).to_string())
        print(f"\nState breakdown:")
        print(df.groupby("customer_state")["revenue"].sum().sort_values(ascending=False).head(5).to_string())