"""Data loading and validation for Olist dataset."""
import logging
import pandas as pd
from pathlib import Path
from src.config import DATA_RAW, DATA_PROCESSED

logger = logging.getLogger(__name__)


def load_olist_tables() -> dict[str, pd.DataFrame]:
    """Load all Olist CSV tables from data/raw/."""
    tables = {
        "orders": "olist_orders_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "order_payments": "olist_order_payments_dataset.csv",
        "products": "olist_products_dataset.csv",
        "customers": "olist_customers_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "reviews": "olist_order_reviews_dataset.csv",
        "geolocation": "olist_geolocation_dataset.csv",
        "product_category": "product_category_name_translation.csv",
    }
    loaded = {}
    for key, filename in tables.items():
        path = DATA_RAW / filename
        if not path.exists():
            logger.warning(f"Missing file: {filename}")
            continue
        loaded[key] = pd.read_csv(path)
        logger.info(f"Loaded {key}: {loaded[key].shape}")
    return loaded


def build_orders_master(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Join core tables into a single analysis-ready orders dataframe."""
    orders = tables["orders"].copy()
    items = tables["order_items"]
    payments = tables["order_payments"]
    customers = tables["customers"]
    products = tables["products"]
    category = tables["product_category"]

    # Aggregate payments per order
    pay_agg = payments.groupby("order_id")["payment_value"].sum().reset_index()
    pay_agg.columns = ["order_id", "revenue"]

    # Aggregate items per order
    items_agg = items.groupby("order_id").agg(
        item_count=("order_item_id", "count"),
        product_id=("product_id", "first"),
    ).reset_index()

    df = (
        orders
        .merge(pay_agg, on="order_id", how="left")
        .merge(items_agg, on="order_id", how="left")
        .merge(customers[["customer_id", "customer_state"]], on="customer_id", how="left")
        .merge(products[["product_id", "product_category_name"]], on="product_id", how="left")
        .merge(category, on="product_category_name", how="left")
    )

    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"])
    df["date"] = df["order_purchase_timestamp"].dt.date
    df = df[df["order_status"] == "delivered"].copy()

    logger.info(f"Master orders built: {df.shape}")
    return df
