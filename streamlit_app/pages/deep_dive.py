"""Deep Dive page - detailed root cause analysis and actions for a selected signal."""

import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render():
    """Render the Deep Dive page."""

    from streamlit_app.components.styles import apply_global_styles
    apply_global_styles()
    
    st.markdown("""
    <div style='margin-bottom: 32px;'>
        <div style='font-family: Space Mono, monospace; font-size: 11px;
                    letter-spacing: 0.12em; color: #55556A;
                    text-transform: uppercase; margin-bottom: 8px;'>
            Investigation Mode
        </div>
        <h1 style='font-size: 32px; font-weight: 600; color: #F0F0F5;
                   margin: 0; line-height: 1.2;'>
            Deep Dive
        </h1>
        <p style='color: #8888A0; margin: 8px 0 0 0; font-size: 15px;'>
            Full root cause analysis and action plan for any signal
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Load latest result
    result = st.session_state.get("last_result") or _load_latest_log()

    if not result:
        st.markdown("""
        <div style='text-align: center; padding: 80px 20px;
                    background: #16161E; border-radius: 12px;
                    border: 1px solid rgba(255,255,255,0.06);'>
            <div style='font-size: 48px; margin-bottom: 16px;'>🔍</div>
            <div style='font-size: 18px; font-weight: 500;
                        color: #F0F0F5; margin-bottom: 8px;'>
                No data yet
            </div>
            <div style='color: #8888A0; font-size: 14px;'>
                Run the pipeline first to investigate signals
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    signals = result.get("signals", {}).get("signals", [])
    root_causes = result.get("root_causes", {}).get("root_causes", [])
    actions = result.get("actions", {}).get("recommendations", [])

    if not signals:
        st.warning("No signals found in the latest run.")
        return

    # Signal selector
    st.markdown('<div class="section-header">Select Signal to Investigate</div>', unsafe_allow_html=True)

    signal_options = {
        f"{s.get('severity')} — {s.get('title')} ({s.get('change_pct', 0):+.1f}%)": i
        for i, s in enumerate(signals)
    }

    selected_label = st.selectbox(
        "Signal",
        options=list(signal_options.keys()),
        label_visibility="collapsed",
    )
    selected_idx = signal_options[selected_label]
    signal = signals[selected_idx]

    st.markdown("<br>", unsafe_allow_html=True)

    # Signal detail header
    sev = signal.get("severity", "ROUTINE")
    chg = signal.get("change_pct", 0)
    sev_color = {"CRITICAL": "#FF3B3B", "WARNING": "#FFB020", "ROUTINE": "#00D68F"}.get(sev, "#8888A0")
    chg_color = "#FF3B3B" if chg < 0 else "#00D68F"
    chg_prefix = "+" if chg > 0 else ""

    st.markdown(f"""
    <div style='background: {sev_color}0D; border: 1px solid {sev_color}33;
                border-radius: 12px; padding: 24px 28px; margin-bottom: 24px;'>
        <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
            <div>
                <span class="badge badge-{sev.lower()}">{sev}</span>
                <h2 style='font-size: 22px; font-weight: 600; color: #F0F0F5;
                           margin: 10px 0 6px 0;'>{signal.get('title', '')}</h2>
                <p style='color: #8888A0; font-size: 14px; margin: 0; line-height: 1.6;'>
                    {signal.get('description', '')}
                </p>
            </div>
            <div style='text-align: right; flex-shrink: 0; margin-left: 24px;'>
                <div style='font-family: Space Mono, monospace; font-size: 32px;
                            font-weight: 700; color: {chg_color};'>
                    {chg_prefix}{chg:.1f}%
                </div>
                <div style='font-family: Space Mono, monospace; font-size: 11px;
                            color: #55556A; margin-top: 4px;'>
                    CONFIDENCE: {signal.get('confidence', 0):.0%}
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Two columns: Root Cause + Actions
    col_rc, col_act = st.columns([1, 1], gap="large")

    # Find matching root cause
    signal_id = signal.get("id", "")
    matching_rc = next(
        (rc for rc in root_causes if rc.get("signal_id") == signal_id),
        None
    )

    with col_rc:
        st.markdown('<div class="section-header">Root Cause Analysis</div>', unsafe_allow_html=True)

        if matching_rc:
            cause_category = matching_rc.get("cause_category", "unknown")
            confidence = matching_rc.get("confidence", 0)
            requires_action = matching_rc.get("requires_immediate_action", False)

            st.markdown(f"""
            <div style='background: #16161E; border: 1px solid rgba(255,255,255,0.06);
                        border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;'>
                <div style='display: flex; justify-content: space-between;
                            align-items: center; margin-bottom: 12px;'>
                    <span style='font-family: Space Mono, monospace; font-size: 10px;
                                 color: #4D9FFF; background: rgba(77,159,255,0.1);
                                 padding: 3px 8px; border-radius: 4px;
                                 text-transform: uppercase; letter-spacing: 0.08em;'>
                        {cause_category}
                    </span>
                    <span style='font-family: Space Mono, monospace; font-size: 10px;
                                 color: #55556A;'>
                        {confidence:.0%} confidence
                    </span>
                </div>
                <div style='font-size: 14px; color: #F0F0F5; font-weight: 500;
                            margin-bottom: 12px; line-height: 1.6;'>
                    {matching_rc.get('primary_cause', '')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Supporting evidence
            evidence = matching_rc.get("supporting_evidence", [])
            if evidence:
                st.markdown("""
                <div style='font-family: Space Mono, monospace; font-size: 10px;
                            letter-spacing: 0.1em; color: #55556A;
                            text-transform: uppercase; margin-bottom: 10px;'>
                    Supporting Evidence
                </div>
                """, unsafe_allow_html=True)
                for e in evidence:
                    st.markdown(f"""
                    <div style='display: flex; gap: 10px; margin-bottom: 8px;
                                align-items: flex-start;'>
                        <span style='color: #4D9FFF; font-size: 12px; margin-top: 2px;'>▸</span>
                        <span style='font-size: 13px; color: #8888A0; line-height: 1.6;'>{e}</span>
                    </div>
                    """, unsafe_allow_html=True)

            # Contributing factors
            factors = matching_rc.get("contributing_factors", [])
            if factors:
                st.markdown("""
                <div style='font-family: Space Mono, monospace; font-size: 10px;
                            letter-spacing: 0.1em; color: #55556A;
                            text-transform: uppercase; margin: 16px 0 10px;'>
                    Contributing Factors
                </div>
                """, unsafe_allow_html=True)
                for f in factors:
                    st.markdown(f"""
                    <div style='display: flex; gap: 10px; margin-bottom: 6px;'>
                        <span style='color: #FFB020; font-size: 12px;'>◆</span>
                        <span style='font-size: 13px; color: #8888A0;'>{f}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color: #55556A;">No root cause analysis available for this signal.</p>', unsafe_allow_html=True)

    with col_act:
        st.markdown('<div class="section-header">Recommended Actions</div>', unsafe_allow_html=True)

        # Filter actions relevant to this signal
        relevant_actions = [
            a for a in actions
            if a.get("addresses_signal") == signal_id
        ]

        if not relevant_actions:
            relevant_actions = actions[:2]

        for action in relevant_actions:
            urgency = action.get("urgency", "MONITOR")
            urgency_color = {
                "IMMEDIATE": "#FF3B3B",
                "THIS_WEEK": "#FFB020",
                "MONITOR": "#00D68F"
            }.get(urgency, "#8888A0")
            priority = action.get("priority_score", 0)

            st.markdown(f"""
            <div style='background: #16161E; border: 1px solid rgba(255,255,255,0.06);
                        border-radius: 12px; padding: 18px 22px; margin-bottom: 12px;
                        border-left: 3px solid {urgency_color};'>
                <div style='display: flex; justify-content: space-between;
                            align-items: center; margin-bottom: 10px;'>
                    <span style='font-family: Space Mono, monospace; font-size: 10px;
                                 font-weight: 700; color: {urgency_color};
                                 background: {urgency_color}22; padding: 3px 8px;
                                 border-radius: 4px; letter-spacing: 0.08em;'>
                        {urgency}
                    </span>
                    <span style='font-family: Space Mono, monospace; font-size: 10px;
                                 color: #55556A;'>
                        PRIORITY {priority}/10
                    </span>
                </div>
                <div style='font-size: 14px; font-weight: 500; color: #F0F0F5;
                            margin-bottom: 8px;'>
                    {action.get('title', '')}
                </div>
                <div style='font-size: 13px; color: #8888A0; line-height: 1.6;
                            margin-bottom: 10px;'>
                    {action.get('description', '')}
                </div>
                <div style='display: flex; justify-content: space-between;
                            font-size: 11px; color: #55556A;'>
                    <span>Owner: {action.get('owner', '').replace('_', ' ').title()}</span>
                    <span style='color: #00D68F;'>{action.get('expected_impact', '')[:60]}...</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Data Quality Notes
    if matching_rc and matching_rc.get("data_quality_notes"):
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style='background: rgba(77,159,255,0.05); border: 1px solid rgba(77,159,255,0.2);
                    border-radius: 8px; padding: 12px 16px;'>
            <span style='font-family: Space Mono, monospace; font-size: 10px;
                         color: #4D9FFF; text-transform: uppercase;
                         letter-spacing: 0.08em;'>Data Quality Note</span>
            <p style='font-size: 13px; color: #8888A0; margin: 6px 0 0 0; line-height: 1.6;'>
                {matching_rc.get('data_quality_notes', '')}
            </p>
        </div>
        """, unsafe_allow_html=True)


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


if __name__ == "__main__" or True:
    render()