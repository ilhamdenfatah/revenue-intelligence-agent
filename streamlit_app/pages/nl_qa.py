"""NL Q&A page - Ask the Agent anything about revenue data."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def render():
    """Render the NL Q&A page."""

    from streamlit_app.components.styles import apply_global_styles
    apply_global_styles()
    
    st.markdown("""
    <div style='margin-bottom: 32px;'>
        <div style='font-family: Space Mono, monospace; font-size: 11px;
                    letter-spacing: 0.12em; color: #55556A;
                    text-transform: uppercase; margin-bottom: 8px;'>
            Natural Language Interface
        </div>
        <h1 style='font-size: 32px; font-weight: 600; color: #F0F0F5;
                   margin: 0; line-height: 1.2;'>
            Ask the Agent
        </h1>
        <p style='color: #8888A0; margin: 8px 0 0 0; font-size: 15px;'>
            Ask anything about revenue, anomalies, or business performance
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Hello! I'm your Revenue Intelligence Agent. Ask me anything about your revenue data — anomalies, root causes, trends, or recommended actions. What would you like to know?"
        })

    # Suggested questions
    if len(st.session_state.messages) <= 1:
        st.markdown('<div class="section-header">Suggested Questions</div>', unsafe_allow_html=True)
        suggestions = [
            "Why did revenue drop in August 2018?",
            "What are the top 3 signals I should act on today?",
            "Which product category needs immediate attention?",
            "What caused the BA state revenue decline?",
            "Give me a summary of this month's performance",
        ]
        cols = st.columns(3)
        for i, suggestion in enumerate(suggestions[:3]):
            with cols[i]:
                if st.button(suggestion, key=f"suggestion_{i}", use_container_width=True):
                    st.session_state.pending_question = suggestion
                    st.rerun()

        cols2 = st.columns(2)
        for i, suggestion in enumerate(suggestions[3:]):
            with cols2[i]:
                if st.button(suggestion, key=f"suggestion_{i+3}", use_container_width=True):
                    st.session_state.pending_question = suggestion
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

    # Chat history
    st.markdown('<div class="section-header">Conversation</div>', unsafe_allow_html=True)

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            _render_message(msg["role"], msg["content"])

    # Handle pending question from suggestion buttons
    if "pending_question" in st.session_state:
        question = st.session_state.pop("pending_question")
        _handle_question(question)
        st.rerun()

    # Chat input
    question = st.chat_input("Ask about revenue, anomalies, trends...")
    if question:
        _handle_question(question)
        st.rerun()


def _render_message(role: str, content: str):
    """Render a single chat message."""
    if role == "user":
        st.markdown(f"""
        <div style='display: flex; justify-content: flex-end; margin-bottom: 16px;'>
            <div style='background: #7C5CFC; color: white; padding: 12px 18px;
                        border-radius: 16px 16px 4px 16px; max-width: 70%;
                        font-size: 14px; line-height: 1.6;'>
                {content}
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='display: flex; justify-content: flex-start; margin-bottom: 16px; gap: 12px;'>
            <div style='width: 32px; height: 32px; background: #16161E;
                        border: 1px solid rgba(124,92,252,0.4);
                        border-radius: 50%; display: flex; align-items: center;
                        justify-content: center; flex-shrink: 0; font-size: 14px;
                        padding-top: 4px;'>
                🧠
            </div>
            <div style='background: #16161E; border: 1px solid rgba(255,255,255,0.06);
                        color: #C0C0D0; padding: 12px 18px;
                        border-radius: 4px 16px 16px 16px; max-width: 75%;
                        font-size: 14px; line-height: 1.7;'>
                {content}
            </div>
        </div>
        """, unsafe_allow_html=True)


def _handle_question(question: str):
    """Process a user question through the agent."""
    # Add user message
    st.session_state.messages.append({"role": "user", "content": question})

    # Get answer from LLM
    with st.spinner("Thinking..."):
        answer = _ask_agent(question)

    st.session_state.messages.append({"role": "assistant", "content": answer})


def _ask_agent(question: str) -> str:
    """Send question to Groq LLM with revenue context."""
    try:
        from groq import Groq
        from src.config import GROQ_API_KEY, GROQ_MODEL, LLM_TEMPERATURE

        # Load latest pipeline context
        context = _load_context()

        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=LLM_TEMPERATURE,
            messages=[
                {
                    "role": "system",
                    "content": f"""You are a Revenue Intelligence Agent assistant for an e-commerce business.
You have access to the latest revenue analysis results below.
Answer the user's question clearly and concisely based on this data.
Use specific numbers when available. Keep responses under 200 words.
Format your response in plain text — no markdown headers, no bullet points.

LATEST REVENUE CONTEXT:
{context}"""
                },
                *[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ]
            ],
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"I encountered an error while processing your question: {str(e)}. Please make sure the pipeline has been run at least once."


def _load_context() -> str:
    """Load the latest pipeline results as context for the LLM."""
    import json
    from pathlib import Path

    # Try session state first
    result = st.session_state.get("last_result")

    # Fall back to latest log
    if not result:
        logs_dir = Path("logs")
        if logs_dir.exists():
            log_files = sorted(logs_dir.glob("run_*.json"), reverse=True)
            if log_files:
                try:
                    with open(log_files[0], encoding="utf-8") as f:
                        result = json.load(f)
                except Exception:
                    pass

    if not result:
        return "No pipeline data available yet. Ask the user to run the pipeline first."

    # Build concise context string
    report = result.get("report", {})
    anomalies = result.get("anomalies", {})
    kpis = result.get("kpis", {})
    signals = result.get("signals", {})
    root_causes = result.get("root_causes", {})
    actions = result.get("actions", {})

    return f"""
Period: {result.get('period', 'N/A')}
Status: {report.get('severity', 'N/A')}
Total Revenue: R${kpis.get('total_revenue', 0):,.2f}
Total Orders: {kpis.get('total_orders', 0):,}
AOV: R${kpis.get('aov', 0):.2f}
Total Anomalies: {anomalies.get('total_anomalies', 0)} ({anomalies.get('counts', {}).get('CRITICAL', 0)} critical, {anomalies.get('counts', {}).get('WARNING', 0)} warning)

Overall Assessment: {signals.get('overall_assessment', 'N/A')}

Top Signals:
{_format_signals(signals.get('signals', []))}

Root Causes Summary: {root_causes.get('cross_signal_patterns', 'N/A')}

Executive Priority: {actions.get('executive_priority', 'N/A')}

One-liner: {report.get('one_liner', 'N/A')}
"""


def _format_signals(signals: list) -> str:
    """Format signals list as readable text."""
    if not signals:
        return "No signals available"
    lines = []
    for s in signals[:5]:
        lines.append(
            f"- [{s.get('severity')}] {s.get('title')}: {s.get('change_pct', 0):+.1f}% "
            f"(confidence: {s.get('confidence', 0):.0%})"
        )
    return "\n".join(lines)


# Allow direct page access
if __name__ == "__main__" or True:
    import streamlit as st
    if "section-header" not in st.session_state:
        pass
    render()