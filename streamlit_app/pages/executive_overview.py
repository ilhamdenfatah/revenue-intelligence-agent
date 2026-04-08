"""Executive Overview page - main dashboard with live pipeline trigger."""

import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render():
    """Render the Executive Overview page."""

    # Page header
    st.markdown("""
    <div style='margin-bottom: 32px;'>
        <div style='font-family: Space Mono, monospace; font-size: 11px; 
                    letter-spacing: 0.12em; color: #55556A; 
                    text-transform: uppercase; margin-bottom: 8px;'>
            Executive Overview
        </div>
        <h1 style='font-size: 32px; font-weight: 600; color: #F0F0F5; 
                   margin: 0; line-height: 1.2;'>
            Revenue Intelligence
        </h1>
        <p style='color: #8888A0; margin: 8px 0 0 0; font-size: 15px;'>
            Real-time anomaly detection & prioritized alerts
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Run pipeline button
    col_btn, col_status = st.columns([1, 3])
    with col_btn:
        run_clicked = st.button("▶ Run Pipeline", use_container_width=True)

    if run_clicked:
        with st.spinner("Running 4-agent pipeline..."):
            result = _run_pipeline()
            if result:
                st.session_state["last_result"] = result
                st.success("Pipeline complete!")
            else:
                st.error("Pipeline failed. Check that uvicorn is running on port 8000.")

    # Load data
    result = st.session_state.get("last_result") or _load_latest_log()

    if not result:
        st.markdown("""
        <div style='text-align: center; padding: 80px 20px; 
                    background: #16161E; border-radius: 12px; 
                    border: 1px solid rgba(255,255,255,0.06);'>
            <div style='font-size: 48px; margin-bottom: 16px;'>🧠</div>
            <div style='font-size: 18px; font-weight: 500; 
                        color: #F0F0F5; margin-bottom: 8px;'>
                No data yet
            </div>
            <div style='color: #8888A0; font-size: 14px;'>
                Click "Run Pipeline" to generate your first intelligence report
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    _render_dashboard(result)


def _render_dashboard(result: dict):
    """Render the full dashboard with pipeline results."""
    report = result.get("report", {})
    anomalies = result.get("anomalies", {})
    kpis = result.get("kpis", {})
    signals = result.get("signals", {})
    severity = report.get("severity", "ROUTINE")
    period = result.get("period", "N/A")
    run_id = result.get("run_id", "N/A")

    counts = anomalies.get("counts", {})
    severity_color = {"CRITICAL": "#FF3B3B", "WARNING": "#FFB020", "ROUTINE": "#00D68F"}.get(severity, "#8888A0")
    severity_bg = {"CRITICAL": "rgba(255,59,59,0.1)", "WARNING": "rgba(255,176,32,0.1)", "ROUTINE": "rgba(0,214,143,0.1)"}.get(severity, "rgba(255,255,255,0.05)")

    # Status banner
    st.markdown(f"""
    <div style='background: {severity_bg}; border: 1px solid {severity_color}33; 
                border-radius: 12px; padding: 16px 24px; margin-bottom: 24px;
                display: flex; align-items: center; gap: 16px;'>
        <div style='font-family: Space Mono, monospace; font-size: 12px; 
                    font-weight: 700; color: {severity_color}; 
                    letter-spacing: 0.08em;'>{severity}</div>
        <div style='color: #8888A0; font-size: 13px;'>|</div>
        <div style='color: #F0F0F5; font-size: 14px;'>{report.get("one_liner", "")}</div>
        <div style='margin-left: auto; font-family: Space Mono, monospace; 
                    font-size: 10px; color: #55556A;'>
            {run_id[:15]} · {period}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPI Metrics row
    st.markdown('<div class="section-header">Key Metrics</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    pop = result.get("full_result", {}).get("period_over_period", {}) if "full_result" in result else {}

    with col1:
        rev = kpis.get("total_revenue", 0)
        rev_chg = result.get("full_result", {}).get("anomalies", {})
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Revenue</div>
            <div class="metric-value">R${rev:,.0f}</div>
            <div class="metric-delta" style="color: #8888A0;">Period: {period}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        orders = kpis.get("total_orders", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Orders</div>
            <div class="metric-value">{orders:,}</div>
            <div class="metric-delta" style="color: #8888A0;">Delivered only</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        aov = kpis.get("aov", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Avg Order Value</div>
            <div class="metric-value">R${aov:.2f}</div>
            <div class="metric-delta" style="color: #8888A0;">AOV</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        total_signals = anomalies.get("total_anomalies", 0)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Signals Detected</div>
            <div class="metric-value">{total_signals}</div>
            <div class="metric-delta">
                <span style="color: #FF3B3B;">{counts.get("CRITICAL", 0)} critical</span>
                <span style="color: #8888A0;"> · </span>
                <span style="color: #FFB020;">{counts.get("WARNING", 0)} warning</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Signals + Report columns
    col_signals, col_report = st.columns([1, 1], gap="large")

    with col_signals:
        st.markdown('<div class="section-header">Top Signals</div>', unsafe_allow_html=True)
        signal_list = signals.get("signals", [])
        if signal_list:
            for sig in signal_list[:5]:
                sev = sig.get("severity", "ROUTINE").lower()
                chg = sig.get("change_pct", 0)
                chg_color = "#FF3B3B" if chg < 0 else "#00D68F"
                chg_prefix = "+" if chg > 0 else ""
                st.markdown(f"""
                <div class="signal-card {sev}">
                    <div style="display: flex; justify-content: space-between; 
                                align-items: flex-start; margin-bottom: 6px;">
                        <span class="badge badge-{sev}">{sig.get("severity")}</span>
                        <span style="font-family: Space Mono, monospace; 
                                     font-size: 13px; color: {chg_color}; font-weight: 700;">
                            {chg_prefix}{chg:.1f}%
                        </span>
                    </div>
                    <div style="font-weight: 500; color: #F0F0F5; 
                                font-size: 14px; margin-bottom: 4px;">
                        {sig.get("title", "")}
                    </div>
                    <div style="font-size: 12px; color: #8888A0; line-height: 1.5;">
                        {sig.get("description", "")}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #55556A;">No signals available.</p>', unsafe_allow_html=True)

    with col_report:
        st.markdown('<div class="section-header">Executive Summary</div>', unsafe_allow_html=True)
        slack_summary = report.get("slack_summary", "")
        email_body = report.get("email_report", {}).get("body", "")

        st.markdown(f"""
        <div style="background: #16161E; border: 1px solid rgba(255,255,255,0.06); 
                    border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;">
            <div style="font-family: Space Mono, monospace; font-size: 10px; 
                        letter-spacing: 0.1em; color: #55556A; 
                        text-transform: uppercase; margin-bottom: 12px;">
                Slack Summary
            </div>
            <div style="font-size: 14px; color: #C0C0D0; line-height: 1.7;">
                {slack_summary}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Actions
        actions = result.get("actions", {})
        recommendations = actions.get("recommendations", [])
        if recommendations:
            st.markdown('<div class="section-header" style="margin-top: 8px;">Recommended Actions</div>', unsafe_allow_html=True)
            for rec in recommendations[:3]:
                urgency = rec.get("urgency", "MONITOR")
                urgency_color = {"IMMEDIATE": "#FF3B3B", "THIS_WEEK": "#FFB020", "MONITOR": "#00D68F"}.get(urgency, "#8888A0")
                st.markdown(f"""
                <div style="background: #16161E; border: 1px solid rgba(255,255,255,0.06); 
                            border-radius: 8px; padding: 12px 16px; margin-bottom: 8px;
                            display: flex; gap: 12px; align-items: flex-start;">
                    <span style="font-family: Space Mono, monospace; font-size: 9px; 
                                 font-weight: 700; color: {urgency_color}; 
                                 background: {urgency_color}22; padding: 2px 6px; 
                                 border-radius: 3px; white-space: nowrap; margin-top: 2px;">
                        {urgency}
                    </span>
                    <div>
                        <div style="font-size: 13px; font-weight: 500; 
                                    color: #F0F0F5; margin-bottom: 2px;">
                            {rec.get("title", "")}
                        </div>
                        <div style="font-size: 12px; color: #8888A0;">
                            Owner: {rec.get("owner", "").replace("_", " ").title()}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def _run_pipeline():
    """Call the FastAPI endpoint to run the pipeline."""
    try:
        import requests
        response = requests.post(
            "http://localhost:8000/run",
            json={"period": "month", "rebuild_processed": False},
            timeout=180,
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"API error: {e}")
    return None


def _load_latest_log():
    """Load the most recent pipeline run from logs/."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return None
    log_files = sorted(logs_dir.glob("run_*.json"), reverse=True)
    if not log_files:
        return None
    try:
        with open(log_files[0], encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
