"""Data loading and validation for the Olist e-commerce dataset."""

import logging
from pathlib import Path

import pandas as pd

from src.config import DATA_RAW, DATA_PROCESSED

logger = logging.getLogger(__name__)

# Columns required for the pipeline to function — missing any of these is a hard failure
REQUIRED_COLUMNS: dict[str, list[str]] = {
    "orders": ["order_id", "customer_id", "order_status", "order_purchase_timestamp"],
    "order_items": ["order_id", "product_id", "price", "freight_value"],
    "payments": ["order_id", "payment_value"],
    "products": ["product_id", "product_category_name"],
    "customers": ["customer_id", "customer_state"],
    "category": ["product_category_name", "product_category_name_english"],
}

FILE_MAP: dict[str, str] = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "products": "olist_products_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "category": "product_category_name_translation.csv",
}


def load_olist_tables(data_dir: Path = DATA_RAW) -> dict[str, pd.DataFrame]:
    """Load and validate all Olist CSV tables from the raw data directory.

    Args:
        data_dir: Path to the directory containing raw CSV files.

    Returns:
        Dictionary mapping table name to its DataFrame.

    Raises:
        FileNotFoundError: If a required CSV file is missing.
        ValueError: If a required column is absent from a loaded table.
    """
    tables: dict[str, pd.DataFrame] = {}

    for name, filename in FILE_MAP.items():
        path = data_dir / filename

        if not path.exists():
            if name in REQUIRED_COLUMNS:
                raise FileNotFoundError(
                    f"Required file not found: {path}. "
                    f"Download the Olist dataset from Kaggle and place CSVs in data/raw/."
                )
            logger.warning(f"Optional file missing, skipping: {filename}")
            continue

        try:
            tables[name] = pd.read_csv(path)
            logger.info(f"Loaded '{name}': {tables[name].shape[0]:,} rows × {tables[name].shape[1]} cols")
        except Exception as e:
            raise RuntimeError(f"Failed to read {filename}: {e}") from e

        _validate_columns(name, tables[name])

    return tables


def build_orders_master(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join core tables into a single analysis-ready master DataFrame.

    Filters to delivered orders only and enriches each order with:
    - Total revenue (aggregated from payments)
    - Product category (English name)
    - Customer state (geography)

    Args:
        tables: Output of load_olist_tables().

    Returns:
        Cleaned master DataFrame with one row per delivered order.
    """
    orders = tables["orders"].copy()
    items = tables["order_items"]
    payments = tables["payments"]
    customers = tables["customers"]
    products = tables["products"]
    category = tables["category"]

    # Aggregate to one row per order
    pay_agg = (
        payments.groupby("order_id")["payment_value"]
        .sum()
        .reset_index()
        .rename(columns={"payment_value": "revenue"})
    )

    items_agg = (
        items.groupby("order_id")
        .agg(item_count=("order_item_id", "count"), product_id=("product_id", "first"))
        .reset_index()
    )

    products_with_category = products.merge(category, on="product_category_name", how="left")

    df = (
        orders
        .merge(pay_agg, on="order_id", how="left")
        .merge(items_agg, on="order_id", how="left")
        .merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
        .merge(
            products_with_category[["product_id", "product_category_name_english"]],
            on="product_id",
            how="left",
        )
    )

    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    df["date"] = df["order_purchase_timestamp"].dt.date
    df["week"] = df["order_purchase_timestamp"].dt.to_period("W")
    df["month"] = df["order_purchase_timestamp"].dt.to_period("M")

    # Scope to delivered orders only
    before = len(df)
    df = df[df["order_status"] == "delivered"].copy()
    logger.info(f"Filtered to delivered orders: {len(df):,} / {before:,} retained")

    df = df.reset_index(drop=True)
    logger.info(f"Master orders DataFrame ready: {df.shape}")
    return df


def save_processed(df: pd.DataFrame, filename: str = "orders_master.parquet") -> Path:
    """Save the master DataFrame to data/processed/ as Parquet.

    Parquet is preferred over CSV for processed data: faster reads,
    smaller file size, and preserves dtypes (including Period columns as strings).

    Args:
        df: Master orders DataFrame.
        filename: Output filename.

    Returns:
        Path to the saved file.
    """
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # Parquet does not support Period dtype — convert to string before saving
    df_out = df.copy()
    for col in ["week", "month"]:
        if col in df_out.columns:
            df_out[col] = df_out[col].astype(str)

    out_path = DATA_PROCESSED / filename
    df_out.to_parquet(out_path, index=False)
    logger.info(f"Saved processed data to {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    return out_path


def load_processed(filename: str = "orders_master.parquet") -> pd.DataFrame:
    """Load the processed master DataFrame from data/processed/.

    Args:
        filename: Parquet filename to load.

    Returns:
        Master orders DataFrame.

    Raises:
        FileNotFoundError: If the processed file does not exist yet.
    """
    path = DATA_PROCESSED / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Processed file not found: {path}. Run the ingestion pipeline first."
        )
    df = pd.read_parquet(path)
    logger.info(f"Loaded processed data: {df.shape[0]:,} rows from {path}")
    return df


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_columns(table_name: str, df: pd.DataFrame) -> None:
    """Raise ValueError if any required column is missing from a DataFrame."""
    required = REQUIRED_COLUMNS.get(table_name, [])
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(
            f"Table '{table_name}' is missing required columns: {missing}"
        )
