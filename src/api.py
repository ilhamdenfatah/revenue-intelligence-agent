"""FastAPI HTTP endpoint - exposes the pipeline as an API for n8n to call.
"""

import logging
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.orchestrator import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Revenue Intelligence Agent API",
    description="HTTP interface for triggering the revenue intelligence pipeline",
    version="1.0.0",
)

# Allow n8n (Docker) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RunRequest(BaseModel):
    period: str = "month"
    rebuild_processed: bool = False


class PipelineStatus(BaseModel):
    status: str
    run_id: str
    timestamp: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint - use this to verify API is running.

    n8n can ping this before triggering the pipeline.
    """
    return {
        "status": "healthy",
        "service": "Revenue Intelligence Agent",
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/run")
def run_intelligence_pipeline(request: RunRequest = RunRequest()) -> dict[str, Any]:
    """Trigger the full revenue intelligence pipeline.

    This is the main endpoint called by n8n's HTTP Request node.
    Runs all 8 stages: data ingestion -> KPI -> anomaly detection ->
    context building -> 4 agents -> logging.

    Returns the full pipeline result including the report for all channels.
    n8n reads 'max_severity' from the response to route to the right channel.
    """
    logger.info(f"Pipeline triggered via API | period={request.period}")

    try:
        result = run_pipeline(
            period=request.period,
            rebuild_processed=request.rebuild_processed,
        )

        # Flatten key fields to top level for easy access in n8n
        return {
            "status": result.get("status"),
            "run_id": result.get("run_id"),
            "period": result.get("period"),
            "max_severity": result.get("report", {}).get("severity", "ROUTINE"),
            "total_anomalies": result.get("anomalies", {}).get("total_anomalies", 0),
            "critical_count": result.get("anomalies", {}).get("counts", {}).get("CRITICAL", 0),
            "warning_count": result.get("anomalies", {}).get("counts", {}).get("WARNING", 0),
            "slack_summary": result.get("report", {}).get("slack_summary", ""),
            "email_subject": result.get("report", {}).get("email_report", {}).get("subject", ""),
            "one_liner": result.get("report", {}).get("one_liner", ""),
            "full_result": result,
        }

    except Exception as e:
        logger.error(f"Pipeline failed via API: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "error": str(e),
                "message": "Pipeline execution failed. Check logs/ for details.",
            },
        )


@app.get("/status")
def get_last_status() -> dict[str, Any]:
    """Return a quick status summary without running the pipeline.

    Useful for n8n health monitoring workflows.
    """
    from pathlib import Path
    import json

    logs_dir = Path("logs")
    if not logs_dir.exists():
        return {"status": "no_runs_yet", "message": "No pipeline runs found"}

    log_files = sorted(logs_dir.glob("run_*.json"), reverse=True)
    if not log_files:
        return {"status": "no_runs_yet", "message": "No pipeline runs found"}

    latest = log_files[0]
    try:
        with open(latest, encoding="utf-8") as f:
            data = json.load(f)
        return {
            "status": data.get("status"),
            "run_id": data.get("run_id"),
            "period": data.get("period"),
            "last_run": latest.stem.replace("run_", ""),
            "max_severity": data.get("report", {}).get("severity", "unknown"),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
