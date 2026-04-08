"""Slack delivery module - sends revenue intelligence reports via Incoming Webhook."""

import logging
from typing import Any

import requests

from src.config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)

# Slack block kit color bars for severity
SEVERITY_COLORS = {
    "CRITICAL": "#E24B4A",
    "WARNING":  "#EF9F27",
    "ROUTINE":  "#1D9E75",
}

SEVERITY_EMOJI = {
    "CRITICAL": ":red_circle:",
    "WARNING":  ":yellow_circle:",
    "ROUTINE":  ":green_circle:",
}


def send_report(report: dict[str, Any], anomalies: dict[str, Any]) -> bool:
    """Send a formatted revenue intelligence report to Slack.

    Uses Slack Block Kit for rich formatting — severity color bar,
    key metrics, top signals, and a direct link to the dashboard.

    Args:
        report: Output dict from report_generator.run().
        anomalies: Output dict from anomaly_detector.detect_anomalies().

    Returns:
        True if delivery succeeded, False otherwise.
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured — skipping Slack delivery")
        return False

    severity = report.get("severity", "ROUTINE")
    emoji = SEVERITY_EMOJI.get(severity, ":white_circle:")
    color = SEVERITY_COLORS.get(severity, "#888780")
    period = anomalies.get("period", "N/A")
    counts = anomalies.get("counts", {})

    # Build Block Kit payload
    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{emoji} Revenue Intelligence Report — {period}",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": report.get("slack_summary", "No summary available."),
                        },
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Severity*\n{severity}"},
                            {"type": "mrkdwn", "text": f"*Total Signals*\n{anomalies.get('total_anomalies', 0)}"},
                            {"type": "mrkdwn", "text": f"*Critical*\n{counts.get('CRITICAL', 0)}"},
                            {"type": "mrkdwn", "text": f"*Warning*\n{counts.get('WARNING', 0)}"},
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Investigate in Dashboard"
                                },
                                "url": "http://localhost:8501",
                                "style": "danger"
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"*One-liner:* {report.get('one_liner', '')}",
                            }
                        ],
                    },
                ],
            }
        ]
    }

    return _post(payload)


def send_error_alert(run_id: str, error_message: str) -> bool:
    """Send a pipeline failure alert to Slack.

    Called by the n8n Error Handler node when the Python pipeline crashes.

    Args:
        run_id: Pipeline run ID for traceability.
        error_message: Error description.

    Returns:
        True if delivery succeeded, False otherwise.
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured — skipping error alert")
        return False

    payload = {
        "attachments": [
            {
                "color": "#E24B4A",
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": ":rotating_light: Revenue Intelligence Agent — Pipeline Failed",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Run ID*\n{run_id}"},
                            {"type": "mrkdwn", "text": f"*Error*\n{error_message[:200]}"},
                        ],
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": "Check logs/ directory for full traceback."}
                        ],
                    },
                ],
            }
        ]
    }

    return _post(payload)


def send_test_message() -> bool:
    """Send a test message to verify the webhook is working.

    Returns:
        True if delivery succeeded, False otherwise.
    """
    payload = {
        "text": ":white_check_mark: Revenue Intelligence Agent — Slack connection verified!"
    }
    return _post(payload)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post(payload: dict[str, Any]) -> bool:
    """POST a payload to the Slack Incoming Webhook URL."""
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=10,
        )
        if response.status_code == 200 and response.text == "ok":
            logger.info("Slack message delivered successfully")
            return True
        else:
            logger.error(f"Slack delivery failed: {response.status_code} — {response.text}")
            return False
    except requests.exceptions.Timeout:
        logger.error("Slack delivery timed out")
        return False
    except Exception as e:
        logger.error(f"Slack delivery error: {e}")
        return False