import logging
logging.basicConfig(level=logging.INFO)

from src.data_ingestion import load_processed
from src.kpi_engine import compute_all_kpis
from src.anomaly_detector import detect_anomalies
from src.context_builder import build_agent_context
from src.agents import signal_detector, root_cause_analyzer
import json

df = load_processed()
kpis = compute_all_kpis(df, period="month")
anomalies = detect_anomalies(kpis)
context = build_agent_context(kpis, anomalies)

signals = signal_detector.run(context["signal_detector"])
root_causes = root_cause_analyzer.run(context["root_cause"], signals)

print(json.dumps(root_causes, indent=2))