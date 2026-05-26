# 🔍 Payments Fraud Detection Pipeline

> End-to-end fraud detection system built on GCP — real-time scoring, explainable AI, and a natural language investigation agent powered by Gemini 2.0 Flash.

**[Dashboard →](https://datastudio.google.com/s/hgFPpy13Vy0)**

---

## Overview

A production-grade fraud detection pipeline processing **590,000 real payment transactions** from the IEEE-CIS Fraud Detection dataset. Built to mirror the stack used by payments companies and fintechs — BigQuery, DBT Core, XGBoost, and a GenAI investigation agent deployed on GCP.

| Metric | Value |
|---|---|
| Dataset | IEEE-CIS Fraud Detection (Kaggle) |
| Transactions | 590,540 |
| Fraud rate | 3.50% (20,663 fraud) |
| Model AUROC | 0.8926 |
| Model AUPRC | 0.5253 |
| Stack | GCP · BigQuery · DBT Core · XGBoost · LangGraph · Gemini 2.0 Flash |
| Cost | $0 (GCP free tier) |

---

## Key Findings

**Statistical Analysis (scipy)**
- `card_txn_count_1h` — p-value `9.66e-106` — velocity is the strongest fraud signal
- `c1`, `c2`, `c11` — p-value `0.00` — Vesta transaction aggregates dominate
- `transaction_amt` alone is NOT significant (p=0.22) — context matters more than raw amount
- 10/12 features significantly different between fraud and legit populations

**SHAP Feature Importance (Top 5)**
1. `c13` — Vesta transaction count aggregate
2. `c1` — high values strongly push toward fraud
3. `c14` — Vesta aggregate
4. `email_domains_match` — engineered in DBT — #4 most important feature
5. `c6` — Vesta aggregate

**Business Insights**
- Discover cards: 7.73% fraud rate vs overall 3.50%
- Product C: 11.69% fraud rate — highest of all product categories
- Night transactions (12am–6am): 1.1x more likely to be fraud
- Free email domains: 3.85% fraud rate vs 2.70% for corporate emails

---

## Project Structure

```
fraud_pipeline/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── data/                      # gitignored — put CSVs here
├── ingestion/
│   └── ingest.py
├── Credit_Risk/               # DBT project
│   └── models/
│       ├── staging/
│       ├── intermediate/
│       └── mart/
├── models/
│   ├── statistical_analysis.py
│   └── train_model.py
├── agent/
│   └── app.py
└── deploy/
    ├── Dockerfile
    ├── deploy_cloud_run.py
    └── setup_scheduler.py
```

---

## Setup

```bash
git clone https://github.com/your-username/fraud-detection-pipeline
cd fraud-detection-pipeline
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in GCP_PROJECT_ID and GOOGLE_AI_API_KEY
```

Download IEEE-CIS dataset from https://www.kaggle.com/competitions/ieee-fraud-detection/data
and place CSVs in `data/`

```bash
# Phase 1 — Ingest
python ingestion/ingest.py --data-dir ./data

# Phase 2 — DBT
cd Credit_Risk && dbt run && dbt test && cd ..

# Phase 3 — ML
python models/statistical_analysis.py
python models/train_model.py

# Phase 4 — Agent
streamlit run agent/app.py

# Phase 5 — Deploy
python deploy/deploy_cloud_run.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Cloud | GCP (BigQuery, Cloud Run, Cloud Functions, Cloud Scheduler) |
| Transformation | DBT Core 1.8 |
| ML | XGBoost, scikit-learn, SHAP, scipy |
| GenAI | Gemini 2.0 Flash, LangGraph, LangChain |
| App | Streamlit |
| Language | Python 3.12 |
| Cost | $0 (free tier) |

---

## Resume Bullet Points

- Built end-to-end payments fraud detection pipeline on GCP processing 590k transactions (BigQuery, DBT Core, Cloud Run, Cloud Scheduler)
- Engineered velocity and behavioral features in DBT Core — `email_domains_match` ranked #4 most important feature by SHAP
- Trained XGBoost fraud classifier achieving AUROC 0.89 and AUPRC 0.53 on heavily imbalanced dataset (3.5% fraud rate)
- Deployed LangGraph GenAI investigation agent (Gemini 2.0 Flash) enabling natural language queries over fraud data
- Implemented SHAP explainability to surface per-transaction fraud drivers for analyst review
- Automated daily pipeline refresh using Cloud Scheduler + Cloud Functions

---

*Built as a finance data + AI portfolio project targeting payments risk and fraud management roles.*
