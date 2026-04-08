"""Global styles and sidebar navigation - imported by every page."""

import streamlit as st


def apply_global_styles():
    """Inject global CSS and render sidebar. Call at top of every page's render()."""

    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg-primary: #0A0A0F;
    --bg-secondary: #111118;
    --bg-card: #16161E;
    --bg-card-hover: #1C1C26;
    --accent-red: #FF3B3B;
    --accent-amber: #FFB020;
    --accent-green: #00D68F;
    --accent-blue: #4D9FFF;
    --accent-purple: #7C5CFC;
    --text-primary: #F0F0F5;
    --text-secondary: #8888A0;
    --text-muted: #55556A;
    --border: rgba(255,255,255,0.06);
    --border-hover: rgba(255,255,255,0.12);
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-primary);
}

[data-testid="stSidebarNav"] { display: none !important; }

[data-testid="stSidebar"] {
    background-color: var(--bg-secondary) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] * { color: var(--text-primary) !important; }

#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }

.metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    transition: all 0.2s ease;
}
.metric-card:hover {
    border-color: var(--border-hover);
    background: var(--bg-card-hover);
}
.metric-label {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.1em;
    color: var(--text-secondary);
    text-transform: uppercase;
    margin-bottom: 8px;
}
.metric-value {
    font-size: 28px;
    font-weight: 600;
    color: var(--text-primary);
    line-height: 1;
}
.metric-delta { font-size: 13px; margin-top: 6px; font-weight: 500; }
.delta-up { color: var(--accent-green); }
.delta-down { color: var(--accent-red); }

.signal-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    border-left: 3px solid transparent;
    transition: all 0.2s ease;
}
.signal-card:hover { border-color: var(--border-hover); }
.signal-card.critical { border-left-color: var(--accent-red); }
.signal-card.warning  { border-left-color: var(--accent-amber); }
.signal-card.routine  { border-left-color: var(--accent-green); }

.badge {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 3px 8px;
    border-radius: 4px;
    text-transform: uppercase;
}
.badge-critical { background: rgba(255,59,59,0.15);  color: var(--accent-red); }
.badge-warning  { background: rgba(255,176,32,0.15); color: var(--accent-amber); }
.badge-routine  { background: rgba(0,214,143,0.15);  color: var(--accent-green); }

.section-header {
    font-family: 'Space Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.12em;
    color: var(--text-muted);
    text-transform: uppercase;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.stButton > button {
    background: var(--accent-purple) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    padding: 8px 20px !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #9070FF !important;
    transform: translateY(-1px);
}
</style>
""", unsafe_allow_html=True)

    # Sidebar navigation — rendered on every page
    with st.sidebar:
        st.markdown("""
        <div style='padding: 8px 0 24px 0;'>
            <div style='font-family: Space Mono, monospace; font-size: 13px;
                        color: #7C5CFC; letter-spacing: 0.08em; margin-bottom: 4px;'>
                REVENUE INTELLIGENCE
            </div>
            <div style='font-size: 20px; font-weight: 600; color: #F0F0F5;'>
                Agent Dashboard
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.page_link("app.py", label="🏠 Executive Overview")
        st.page_link("pages/nl_qa.py", label="💬 Ask the Agent")
        st.page_link("pages/signal_history.py", label="📊 Signal History")
        st.page_link("pages/deep_dive.py", label="🔍 Deep Dive")

        st.markdown("---")
        st.markdown("""
        <div style='font-family: Space Mono, monospace; font-size: 10px;
                    color: #55556A; letter-spacing: 0.08em;'>
            POWERED BY GROQ + LLAMA 3.3
        </div>
        """, unsafe_allow_html=True)