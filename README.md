# Revenue Intelligence Agent 🧠

> A multi-agent AI system that monitors e-commerce revenue data, detects anomalies, diagnoses root causes, generates prioritized action recommendations, and delivers them automatically to stakeholders — every morning at 8AM, without anyone lifting a finger.

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=flat-square)
![n8n](https://img.shields.io/badge/n8n-Orchestration-EA4B71?style=flat-square&logo=n8n&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)

**[Live Demo](https://revenue-agent.streamlit.app)** · **[Architecture](#architecture)** · **[Quick Start](#quick-start)**

</div>

---

## The Problem This Solves

Every e-commerce business has the same problem: revenue data is fragmented across categories, geographies, and time periods. When something goes wrong, leadership asks *"what happened and what should we do?"* — and it takes an analyst 2-3 days to compile the answer.

This system answers that question in under 60 seconds, automatically, every single day.

---

## What It Does

The system runs a full intelligence pipeline on your revenue data and delivers structured, actionable reports to Slack and Email before your team starts their morning.

When the pipeline runs, it:

1. Detects statistical anomalies across revenue, AOV, order volume, product categories, and geographic regions
2. Identifies the top 3-5 signals that actually matter — ranked by severity and confidence score
3. Diagnoses the root cause of each signal using dimensional analysis and historical context
4. Generates specific, prioritized action recommendations tied to each diagnosis
5. Formats everything into channel-appropriate reports and delivers them automatically

The result looks like this in Slack:

```
🔴 Revenue Intelligence Report — 2018-08

Revenue dropped 4.1% to R$985,414, with critical declines in BA (-47.7%)
and ES (-42.2%) states. Immediate actions: investigate BA and ES logistics.

Severity: CRITICAL    Total Signals: 14
Critical: 6           Warning: 8

[Investigate in Dashboard →]
```

And a full structured report lands in your inbox with root cause analysis and a prioritized action plan.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REVENUE INTELLIGENCE AGENT                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   DATA LAYER              PROCESSING LAYER                       │
│   ─────────               ───────────────                        │
│   Olist Dataset    ──►    KPI Engine                             │
│   (8 CSV tables)          Anomaly Detector                       │
│   Parquet cache           Context Builder                        │
│                                                                  │
│   AI INTELLIGENCE LAYER                                          │
│   ──────────────────────────────────────                         │
│   Agent 1: Signal Detector                                       │
│        "Revenue dropped 15% in Category X"                       │
│            │                                                     │
│            ▼                                                     │
│   Agent 2: Root Cause Analyzer                                   │
│        "Likely: seasonal pattern + stockout in top SKUs"         │
│            │                                                     │
│            ▼                                                     │
│   Agent 3: Action Recommender                                    │
│        "Priority 1: Restock SKU-X within 48h"                   │
│            │                                                     │
│            ▼                                                     │
│   Agent 4: Report Generator                                      │
│        Slack summary + Email brief + Dashboard data              │
│                                                                  │
│   ORCHESTRATION & DELIVERY                                       │
│   ──────────────────────────────────────                         │
│   n8n (cron trigger) ──► FastAPI ──► Python Pipeline            │
│                                           │                      │
│                              ┌────────────┼────────────┐         │
│                              ▼            ▼            ▼         │
│                           Slack        Email      Streamlit      │
│                          #alerts      Inbox      Dashboard       │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Data | Pandas, NumPy, Parquet | Ingestion, cleaning, KPI computation |
| AI | Groq API (LLaMA 3.3 70B) | 4-agent intelligence chain |
| Orchestration | n8n + FastAPI | Scheduled triggers, workflow automation |
| Anomaly Detection | SciPy (Z-score, IQR) | Statistical signal detection |
| Delivery | Slack Webhooks, Gmail SMTP | Multi-channel alert routing |
| Frontend | Streamlit | Interactive investigation dashboard |
| Containerization | Docker | n8n deployment |
| Dataset | Olist Brazilian E-Commerce | 100K+ real e-commerce transactions |

---

## How the 4-Agent Chain Works

The intelligence layer chains four specialized LLM agents, where each agent's output feeds the next:

**Agent 1 — Signal Detector** takes the raw KPI data and anomaly statistics, then identifies the 3-5 most significant signals. It assigns a confidence score to each signal and classifies them as `drop`, `spike`, or `trend_reversal`. This filters 14 raw anomalies down to 5 that actually need attention.

**Agent 2 — Root Cause Analyzer** receives the detected signals plus full dimensional breakdowns (by category and geography). It cross-references patterns — if two states drop while others grow, that points to a logistics issue rather than a demand problem. Each diagnosis includes supporting evidence and contributing factors.

**Agent 3 — Action Recommender** translates the root cause analysis into specific, executable actions. Every recommendation includes an owner (`logistics_team`, `commercial_team`), urgency (`IMMEDIATE`, `THIS_WEEK`, `MONITOR`), and an expected impact statement.

**Agent 4 — Report Generator** synthesizes all outputs into three delivery formats: a 2-line Slack summary, a structured email with full sections, and a one-liner for the dashboard headline.

Each agent receives only the context relevant to its task, keeping prompts focused and outputs consistent.

---

## Quick Start

### Prerequisites

- Python 3.10+
- Conda or virtualenv
- Docker Desktop (for n8n)
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Gmail account with App Password enabled

### 1. Clone and set up environment

```bash
git clone https://github.com/ilhamdenfatah/revenue-intelligence-agent.git
cd revenue-intelligence-agent

conda create -n ria-env python=3.10
conda activate ria-env
pip install -r requirements.txt
```

### 2. Download the dataset

Download the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) from Kaggle and extract all CSV files to `data/raw/`.

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
GROQ_API_KEY=your_groq_api_key

GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
ALERT_EMAIL_TO=your@gmail.com

SLACK_WEBHOOK_URL=your_slack_webhook_url
```

### 4. Run the data pipeline

```bash
# Ingest and process the raw dataset (first time only)
python -m src.orchestrator --rebuild

# Subsequent runs use the cached Parquet file
python -m src.orchestrator
```

### 5. Start the API and dashboard

Open two terminal windows:

```bash
# Terminal 1 — FastAPI
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Streamlit
streamlit run streamlit_app/app.py
```

### 6. Start n8n (optional — for scheduled automation)

```bash
docker start n8n
```

Open [localhost:5678](http://localhost:5678), import `n8n/workflows/daily_intelligence.json`, and activate the workflow. The pipeline will run automatically every day at 08:00 UTC.

---

## Project Structure

```
revenue-intelligence-agent/
├── src/
│   ├── config.py                  # Centralized configuration
│   ├── data_ingestion.py          # Data loading, validation, Parquet output
│   ├── kpi_engine.py              # Revenue, AOV, dimensional KPI computation
│   ├── anomaly_detector.py        # Z-score and threshold-based detection
│   ├── context_builder.py         # LLM context packaging per agent
│   ├── orchestrator.py            # 9-stage pipeline runner
│   ├── simulator.py               # Synthetic data generator (5 anomaly presets)
│   ├── api.py                     # FastAPI HTTP endpoints for n8n
│   ├── agents/
│   │   ├── signal_detector.py     # Agent 1
│   │   ├── root_cause_analyzer.py # Agent 2
│   │   ├── action_recommender.py  # Agent 3
│   │   └── report_generator.py    # Agent 4
│   └── delivery/
│       ├── slack_sender.py        # Slack Block Kit formatting + delivery
│       ├── email_sender.py        # HTML email via Gmail SMTP
│       └── whatsapp_sender.py     # WhatsApp via Twilio (planned)
├── streamlit_app/
│   ├── app.py                     # Entry point
│   ├── components/styles.py       # Global CSS and sidebar
│   └── pages/
│       ├── executive_overview.py  # Main dashboard with pipeline trigger
│       ├── nl_qa.py               # Conversational AI interface
│       ├── signal_history.py      # Timeline of all detected anomalies
│       └── deep_dive.py           # Per-signal root cause investigation
├── n8n/workflows/
│   └── daily_intelligence.json    # Importable n8n workflow
├── data/
│   ├── raw/                       # Olist CSVs (not tracked in git)
│   ├── processed/                 # Parquet cache (not tracked in git)
│   └── simulated/                 # Synthetic data output
└── logs/                          # Pipeline run logs (not tracked in git)
```

---

## Key Design Decisions

**Why four separate agents instead of one?** Specialization produces better outputs. A single agent asked to detect, diagnose, recommend, and report simultaneously produces mediocre results in all four areas. Separating them lets each agent receive only the context relevant to its task and develop focused, consistent outputs.

**Why n8n for orchestration?** n8n handles the scheduling, error handling, and delivery routing without requiring custom infrastructure. The Python pipeline stays clean and testable, while n8n manages the operational concerns — cron triggers, webhook endpoints, and severity-based routing to the right channels.

**Why Groq instead of OpenAI?** Groq's inference speed (LLaMA 3.3 70B at ~300 tokens/second) makes the 4-agent chain complete in under 15 seconds, compared to 45-60 seconds with GPT-4. For a system designed to run on a schedule and deliver time-sensitive alerts, latency matters.

**Why Parquet for processed data?** The Olist dataset is 120MB of raw CSV across 8 tables. After joining and filtering to delivered orders, the processed dataset is ~12MB in Parquet format — 10x compression, with faster reads and preserved column types.

---

## Roadmap

- [ ] WhatsApp delivery via Twilio API
- [ ] Full Docker Compose deployment (all services containerized)
- [ ] PostgreSQL backend for historical signal storage and trend analysis
- [ ] OpenClaw + Telegram conversational layer for on-demand queries
- [ ] Confidence-weighted severity routing to reduce alert fatigue
- [ ] Week-over-week and month-over-month comparison views in Streamlit

---

## Dataset

This project uses the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) — 100K+ real orders from 2016-2018, with 8 relational tables covering orders, payments, products, customers, sellers, and reviews.

The dataset is not included in this repository. Download it from Kaggle and place the CSV files in `data/raw/` before running the pipeline.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built by <a href="https://github.com/ilhamdenfatah">Ilham Den Fatah</a>
</div>