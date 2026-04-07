"""Main pipeline orchestrator - runs the full Revenue Intelligence Agent in sequence.

This is the single entry point for executing the complete pipeline locally.
In production, this is triggered by n8n workflows (scheduled, webhook, or event-driven).
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.anomaly_detector import detect_anomalies
from src.context_builder import build_agent_context
from src.data_ingestion import build_orders_master, load_olist_tables, load_processed, save_processed
from src.kpi_engine import compute_all_kpis
from src.agents import action_recommender, report_generator, root_cause_analyzer, signal_detector
from src.delivery.slack_sender import send_report as slack_send
from src.delivery.email_sender import send_report as email_send

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

LOGS_DIR = Path("logs")


def run_pipeline(
    period: str = "month",
    rebuild_processed: bool = False,
) -> dict[str, Any]:
    """Run the full Revenue Intelligence Agent pipeline.

    Executes all stages in sequence:
    1. Data ingestion (or load from cache)
    2. KPI computation
    3. Anomaly detection
    4. Context building
    5. Agent 1 - Signal Detector
    6. Agent 2 - Root Cause Analyzer
    7. Agent 3 - Action Recommender
    8. Agent 4 - Report Generator
    9. Save run log

    Args:
        period: Aggregation period for KPIs - 'day', 'week', or 'month'.
        rebuild_processed: If True, re-ingest raw data even if processed file exists.

    Returns:
        Dict containing all pipeline outputs keyed by stage name.
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(f"Pipeline starting | run_id={run_id} | period={period}")

    result: dict[str, Any] = {"run_id": run_id, "period": period, "status": "running"}

    try:
        # -----------------------------------------------------------------
        # Stage 1: Data
        # -----------------------------------------------------------------
        logger.info("Stage 1/8: Data ingestion")
        if rebuild_processed:
            tables = load_olist_tables()
            df = build_orders_master(tables)
            save_processed(df)
        else:
            df = load_processed()

        result["data"] = {"rows": len(df), "columns": list(df.columns)}

        # -----------------------------------------------------------------
        # Stage 2: KPI Computation
        # -----------------------------------------------------------------
        logger.info("Stage 2/8: KPI computation")
        kpis = compute_all_kpis(df, period=period)
        result["kpis"] = {
            "total_orders": kpis["summary"]["total_orders"],
            "total_revenue": kpis["summary"]["total_revenue"],
            "aov": kpis["summary"]["aov"],
        }

        # -----------------------------------------------------------------
        # Stage 3: Anomaly Detection
        # -----------------------------------------------------------------
        logger.info("Stage 3/8: Anomaly detection")
        anomalies = detect_anomalies(kpis)
        result["anomalies"] = {
            "total": anomalies["total_anomalies"],
            "max_severity": anomalies["max_severity"],
            "counts": anomalies["counts"],
        }

        # -----------------------------------------------------------------
        # Stage 4: Context Building
        # -----------------------------------------------------------------
        logger.info("Stage 4/8: Building agent context")
        context = build_agent_context(kpis, anomalies)

        # -----------------------------------------------------------------
        # Stage 5: Agent 1 - Signal Detector
        # -----------------------------------------------------------------
        logger.info("Stage 5/8: Agent 1 - Signal Detector")
        signals = signal_detector.run(context["signal_detector"])
        result["signals"] = signals

        # -----------------------------------------------------------------
        # Stage 6: Agent 2 - Root Cause Analyzer
        # -----------------------------------------------------------------
        logger.info("Stage 6/8: Agent 2 - Root Cause Analyzer")
        root_causes = root_cause_analyzer.run(context["root_cause"], signals)
        result["root_causes"] = root_causes

        # -----------------------------------------------------------------
        # Stage 7: Agent 3 - Action Recommender
        # -----------------------------------------------------------------
        logger.info("Stage 7/8: Agent 3 - Action Recommender")
        actions = action_recommender.run(context["action_recommender"], signals, root_causes)
        result["actions"] = actions

        # -----------------------------------------------------------------
        # Stage 8: Agent 4 - Report Generator
        # -----------------------------------------------------------------
        logger.info("Stage 8/8: Agent 4 - Report Generator")
        report = report_generator.run(
            context["report_generator"], signals, root_causes, actions
        )
        result["report"] = report

        result["status"] = "success"
        logger.info(
            f"Pipeline complete | run_id={run_id} | "
            f"severity={report.get('severity')} | "
            f"signals={len(signals.get('signals', []))} | "
            f"actions={len(actions.get('recommendations', []))}"
        )

        # -----------------------------------------------------------------
        # Stage 9: Delivery
        # -----------------------------------------------------------------
        logger.info("Stage 9/9: Delivering reports")
        severity = report.get("severity", "ROUTINE")

        if severity in ["CRITICAL", "WARNING"]:
            slack_send(report, anomalies)

        email_send(report, anomalies)

        result["delivery"] = {
            "slack": severity in ["CRITICAL", "WARNING"],
            "email": True,
        }

    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"Pipeline failed at run_id={run_id}: {e}", exc_info=True)
        raise

    finally:
        _save_run_log(run_id, result)

    return result


def print_summary(result: dict[str, Any]) -> None:
    """Print a clean summary of the pipeline run to stdout."""
    report = result.get("report", {})
    anomaly_counts = result.get("anomalies", {}).get("counts", {})

    print("\n" + "=" * 60)
    print(f"PIPELINE RUN: {result['run_id']}")
    print(f"STATUS: {result['status'].upper()}")
    print("=" * 60)

    if result["status"] == "success":
        print(f"\nDATA: {result['data']['rows']:,} orders processed")
        print(f"REVENUE: R${result['kpis']['total_revenue']:,.2f}")
        print(f"ANOMALIES: {result['anomalies']['total']} detected "
              f"(CRITICAL: {anomaly_counts.get('CRITICAL', 0)}, "
              f"WARNING: {anomaly_counts.get('WARNING', 0)})")
        print(f"\n{report_generator.format_for_display(report)}")
    else:
        print(f"\nERROR: {result.get('error', 'Unknown error')}")

    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_run_log(run_id: str, result: dict[str, Any]) -> None:
    """Persist the full pipeline result to a JSON log file in logs/."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_path = LOGS_DIR / f"run_{run_id}.json"

    # Make result JSON-serializable (remove non-serializable objects)
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str, ensure_ascii=False)
        logger.info(f"Run log saved to {log_path}")
    except Exception as e:
        logger.warning(f"Failed to save run log: {e}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    period = sys.argv[1] if len(sys.argv) > 1 else "month"
    rebuild = "--rebuild" in sys.argv

    result = run_pipeline(period=period, rebuild_processed=rebuild)
    print_summary(result)