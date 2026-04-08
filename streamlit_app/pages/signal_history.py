"""Signal History page - timeline of all detected anomalies across pipeline runs."""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render():
    """Render the Signal History page."""

    from streamlit_app.components.styles import apply_global_styles
    apply_global_styles()
    
    st.markdown("""
    <div style='margin-bottom: 32px;'>
        <div style='font-family: Space Mono, monospace; font-size: 11px;
                    letter-spacing: 0.12em; color: #55556A;
                    text-transform: uppercase; margin-bottom: 8px;'>
            Historical View
        </div>
        <h1 style='font-size: 32px; font-weight: 600; color: #F0F0F5;
                   margin: 0; line-height: 1.2;'>
            Signal History
        </h1>
        <p style='color: #8888A0; margin: 8px 0 0 0; font-size: 15px;'>
            All anomalies detected across pipeline runs
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Load all run logs
    all_runs = _load_all_runs()

    if not all_runs:
        st.markdown("""
        <div style='text-align: center; padding: 80px 20px;
                    background: #16161E; border-radius: 12px;
                    border: 1px solid rgba(255,255,255,0.06);'>
            <div style='font-size: 48px; margin-bottom: 16px;'>📊</div>
            <div style='font-size: 18px; font-weight: 500;
                        color: #F0F0F5; margin-bottom: 8px;'>
                No history yet
            </div>
            <div style='color: #8888A0; font-size: 14px;'>
                Run the pipeline at least once to see signal history
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Summary stats across all runs
    total_runs = len(all_runs)
    total_signals = sum(len(r.get("signals", {}).get("signals", [])) for r in all_runs)
    total_critical = sum(r.get("anomalies", {}).get("counts", {}).get("CRITICAL", 0) for r in all_runs)
    critical_runs = sum(1 for r in all_runs if r.get("report", {}).get("severity") == "CRITICAL")

    # Stats row
    st.markdown('<div class="section-header">Summary</div>', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Runs</div>
            <div class="metric-value">{total_runs}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Signals</div>
            <div class="metric-value">{total_signals}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Critical Signals</div>
            <div class="metric-value" style="color: #FF3B3B;">{total_critical}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Critical Runs</div>
            <div class="metric-value" style="color: #FF3B3B;">{critical_runs}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter controls
    st.markdown('<div class="section-header">Filter</div>', unsafe_allow_html=True)
    col_f1, col_f2 = st.columns([1, 3])
    with col_f1:
        severity_filter = st.selectbox(
            "Severity",
            ["All", "CRITICAL", "WARNING", "ROUTINE"],
            label_visibility="collapsed",
        )

    # Timeline
    st.markdown('<div class="section-header">Timeline</div>', unsafe_allow_html=True)

    for run in all_runs:
        run_id = run.get("run_id", "unknown")
        period = run.get("period", "N/A")
        status = run.get("status", "unknown")
        report = run.get("report", {})
        anomalies = run.get("anomalies", {})
        signals_data = run.get("signals", {})
        severity = report.get("severity", "ROUTINE")
        counts = anomalies.get("counts", {})

        # Apply filter
        if severity_filter != "All" and severity != severity_filter:
            continue

        severity_color = {
            "CRITICAL": "#FF3B3B",
            "WARNING": "#FFB020",
            "ROUTINE": "#00D68F"
        }.get(severity, "#8888A0")

        # Run header
        with st.expander(
            f"🗓️ Run {run_id[:15]}  |  {severity}  |  "
            f"{counts.get('CRITICAL', 0)}C · {counts.get('WARNING', 0)}W signals",
            expanded=(severity == "CRITICAL")
        ):
            # One-liner
            one_liner = report.get("one_liner", "")
            if one_liner:
                st.markdown(f"""
                <div style='background: {severity_color}11; border-left: 3px solid {severity_color};
                            padding: 10px 16px; border-radius: 0 8px 8px 0;
                            margin-bottom: 16px; font-size: 13px; color: #C0C0D0;'>
                    {one_liner}
                </div>
                """, unsafe_allow_html=True)

            # Signals in this run
            signal_list = signals_data.get("signals", [])
            if signal_list:
                cols = st.columns(2)
                for i, sig in enumerate(signal_list):
                    sev = sig.get("severity", "ROUTINE").lower()
                    chg = sig.get("change_pct", 0)
                    chg_color = "#FF3B3B" if chg < 0 else "#00D68F"
                    chg_prefix = "+" if chg > 0 else ""
                    with cols[i % 2]:
                        st.markdown(f"""
                        <div class="signal-card {sev}" style="margin-bottom: 8px;">
                            <div style="display: flex; justify-content: space-between;
                                        align-items: center; margin-bottom: 4px;">
                                <span class="badge badge-{sev}">{sig.get('severity')}</span>
                                <span style="font-family: Space Mono, monospace;
                                             font-size: 12px; color: {chg_color}; font-weight: 700;">
                                    {chg_prefix}{chg:.1f}%
                                </span>
                            </div>
                            <div style="font-size: 13px; font-weight: 500;
                                        color: #F0F0F5; margin-bottom: 2px;">
                                {sig.get('title', '')}
                            </div>
                            <div style="font-size: 11px; color: #8888A0;">
                                Confidence: {sig.get('confidence', 0):.0%}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown('<p style="color: #55556A; font-size: 13px;">No signals in this run.</p>', unsafe_allow_html=True)


def _load_all_runs() -> list:
    """Load all pipeline run logs from logs/ directory."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return []

    runs = []
    for log_file in sorted(logs_dir.glob("run_*.json"), reverse=True):
        try:
            with open(log_file, encoding="utf-8") as f:
                data = json.load(f)
                if data.get("status") == "success":
                    runs.append(data)
        except Exception:
            continue

    return runs


if __name__ == "__main__" or True:
    render()