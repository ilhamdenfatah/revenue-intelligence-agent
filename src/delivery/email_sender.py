"""Email delivery module - sends revenue intelligence reports via Gmail SMTP."""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.config import ALERT_EMAIL_TO, GMAIL_APP_PASSWORD, GMAIL_USER

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_report(report: dict[str, Any], anomalies: dict[str, Any]) -> bool:
    """Send a formatted revenue intelligence report via email.

    Sends an HTML email with full structured report — overview, key signals,
    root causes, and recommended actions.

    Args:
        report: Output dict from report_generator.run().
        anomalies: Output dict from anomaly_detector.detect_anomalies().

    Returns:
        True if delivery succeeded, False otherwise.
    """
    if not _is_configured():
        return False

    severity = report.get("severity", "ROUTINE")
    period = anomalies.get("period", "N/A")
    email_report = report.get("email_report", {})
    subject = email_report.get("subject", f"Revenue Intelligence Report — {period}")
    body_text = email_report.get("body", "No report body available.")

    html_body = _build_html(severity, period, body_text, anomalies)

    return _send(
        to=ALERT_EMAIL_TO,
        subject=subject,
        html_body=html_body,
        plain_body=body_text,
    )


def send_error_alert(run_id: str, error_message: str) -> bool:
    """Send a pipeline failure alert via email.

    Args:
        run_id: Pipeline run ID for traceability.
        error_message: Error description.

    Returns:
        True if delivery succeeded, False otherwise.
    """
    if not _is_configured():
        return False

    subject = "ACTION REQUIRED: Revenue Intelligence Agent Pipeline Failed"
    plain_body = f"Pipeline run {run_id} failed.\n\nError: {error_message}"
    html_body = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
      <div style="background:#FEE2E2;border-left:4px solid #E24B4A;padding:16px;border-radius:4px">
        <h2 style="margin:0 0 8px;color:#991B1B">Pipeline Failed</h2>
        <p style="margin:0;color:#7F1D1D">Run ID: <code>{run_id}</code></p>
      </div>
      <div style="margin-top:16px;background:#F9FAFB;padding:16px;border-radius:4px">
        <p style="margin:0;color:#374151"><strong>Error:</strong> {error_message}</p>
        <p style="margin:8px 0 0;color:#6B7280;font-size:13px">Check logs/ directory for full traceback.</p>
      </div>
    </div>
    """

    return _send(
        to=ALERT_EMAIL_TO,
        subject=subject,
        html_body=html_body,
        plain_body=plain_body,
    )


def send_test_email() -> bool:
    """Send a test email to verify SMTP configuration.

    Returns:
        True if delivery succeeded, False otherwise.
    """
    if not _is_configured():
        return False

    return _send(
        to=ALERT_EMAIL_TO,
        subject="Revenue Intelligence Agent — Email connection verified!",
        html_body="""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;padding:24px">
          <div style="background:#D1FAE5;border-left:4px solid #1D9E75;padding:16px;border-radius:4px">
            <h2 style="margin:0;color:#065F46">Email connection verified!</h2>
            <p style="margin:8px 0 0;color:#047857">Revenue Intelligence Agent is ready to deliver reports.</p>
          </div>
        </div>
        """,
        plain_body="Revenue Intelligence Agent - Email connection verified!",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_html(
    severity: str,
    period: str,
    body_text: str,
    anomalies: dict[str, Any],
) -> str:
    """Build a clean HTML email body from the report text."""
    severity_colors = {
        "CRITICAL": {"bg": "#FEE2E2", "border": "#E24B4A", "text": "#991B1B", "badge": "#E24B4A"},
        "WARNING":  {"bg": "#FEF3C7", "border": "#EF9F27", "text": "#92400E", "badge": "#EF9F27"},
        "ROUTINE":  {"bg": "#D1FAE5", "border": "#1D9E75", "text": "#065F46", "badge": "#1D9E75"},
    }
    colors = severity_colors.get(severity, severity_colors["ROUTINE"])
    counts = anomalies.get("counts", {})

    # Convert plain text body to HTML paragraphs
    paragraphs = "".join(
        f"<p style='margin:0 0 12px;color:#374151;line-height:1.6'>{line}</p>"
        for line in body_text.replace("\\n", "\n").split("\n")
        if line.strip()
    )

    return f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
  <div style="max-width:640px;margin:32px auto;background:#FFFFFF;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.1)">

    <!-- Header -->
    <div style="background:{colors['border']};padding:24px 32px">
      <h1 style="margin:0;color:#FFFFFF;font-size:20px;font-weight:600">
        Revenue Intelligence Report
      </h1>
      <p style="margin:4px 0 0;color:rgba(255,255,255,0.85);font-size:14px">
        Period: {period}
      </p>
    </div>

    <!-- Severity banner -->
    <div style="background:{colors['bg']};border-left:4px solid {colors['border']};padding:12px 32px">
      <span style="background:{colors['badge']};color:#FFFFFF;font-size:12px;font-weight:600;
                   padding:2px 10px;border-radius:12px;letter-spacing:0.5px">{severity}</span>
      <span style="margin-left:12px;color:{colors['text']};font-size:13px">
        {anomalies.get('total_anomalies', 0)} signals detected —
        {counts.get('CRITICAL', 0)} critical, {counts.get('WARNING', 0)} warning
      </span>
    </div>

    <!-- Body -->
    <div style="padding:24px 32px">
      {paragraphs}
    </div>

    <!-- Footer -->
    <div style="padding:16px 32px;background:#F9FAFB;border-top:1px solid #E5E7EB">
      <p style="margin:0;color:#9CA3AF;font-size:12px">
        Sent by Revenue Intelligence Agent &nbsp;·&nbsp;
        Automated report — do not reply
      </p>
    </div>

  </div>
</body>
</html>
"""


def _send(to: str, subject: str, html_body: str, plain_body: str) -> bool:
    """Send an email via Gmail SMTP with both plain text and HTML parts."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"Revenue Intelligence Agent <{GMAIL_USER}>"
    msg["To"] = to

    msg.attach(MIMEText(plain_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, to, msg.as_string())
        logger.info(f"Email delivered to {to}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("Email auth failed — check GMAIL_USER and GMAIL_APP_PASSWORD in .env")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        return False
    except Exception as e:
        logger.error(f"Email delivery error: {e}")
        return False


def _is_configured() -> bool:
    """Check that all required email config variables are set."""
    missing = [v for v, val in [
        ("GMAIL_USER", GMAIL_USER),
        ("GMAIL_APP_PASSWORD", GMAIL_APP_PASSWORD),
        ("ALERT_EMAIL_TO", ALERT_EMAIL_TO),
    ] if not val]

    if missing:
        logger.warning(f"Email not configured — missing: {missing}")
        return False
    return True