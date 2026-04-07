# Dis-Chem Omni-Channel Inventory Orchestrator

A production-style portfolio project that demonstrates how modern data engineering, analytics, MLOps, and LLMOps can be combined to solve a high-value retail healthcare problem: inventory optimization across an omni-channel pharmacy ecosystem.

## Why this project matters

Dis-Chem’s strategic shift from traditional retail pharmacy toward integrated primary healthcare creates a more complex supply chain environment. Inventory decisions now affect not only store availability and working capital, but also chronic medication continuity, compliance, patient experience, and margin protection.

This project simulates an executive-grade decision intelligence platform that helps leadership answer questions such as:
- Where is working capital trapped in excess stock?
- Which stores are at highest risk of stock-outs or expiry losses?
- Which SKUs need forecast-driven replenishment changes?
- How can an AI agent explain exceptions and recommend actions clearly?

## Business problem

Retail healthcare inventory is difficult because it combines:
- Regulated pharmaceutical products
- Front-shop retail goods
- Demand volatility across stores and channels
- High cost of stock-outs and expired items
- Executive pressure to improve stock turn and reduce inventory days

The project addresses this through a lakehouse-based architecture, KPI-first analytics, demand forecasting, and an AI inventory copilot.

## Solution overview

The platform includes:
- Batch ingestion for POS, ERP, and clinic data
- Simulated streaming events for inventory changes and alerts
- Medallion architecture (Bronze, Silver, Gold)
- Executive KPI layer for working capital, stock turn, compliance, and wastage
- Forecasting models for SKU-store demand
- LLM-powered agent for exception reasoning and decision support
- Streamlit dashboard for executive consumption

## Architecture summary

### Data sources
- Store POS transactions
- SAP / ERP inventory extracts
- Clinic prescription and dispensing data
- Synthetic streaming inventory events

### Core architecture
- **Storage:** Cloudflare R2 or local object store abstraction
- **Metadata / state:** Cloudflare D1 or lightweight SQL alternative
- **Compute:** DuckDB + Polars
- **Pipelines:** Python orchestration for batch and simulated streaming
- **ML layer:** Forecasting models with tracked experiments
- **LLM layer:** Agent workflows for exception analysis and action recommendations
- **Frontend:** Streamlit executive dashboard

## Medallion data model

### Bronze
Raw landed data with minimal transformation.
Examples:
- `pos_transactions_raw`
- `sap_inventory_levels_raw`
- `clinic_scripts_raw`

### Silver
Standardized and cleaned operational entities.
Examples:
- `dim_products_hc`
- `fct_inventory_snapshots`
- `fct_dispensing_log`

### Gold
Business-ready marts for reporting and AI.
Examples:
- `mart_inventory_health`
- `mart_financial_performance`
- `mart_customer_behavior`

## Executive KPIs

The dashboard focuses on measurable business value before advanced AI:
- Working capital unlocked
- Inventory days
- Stock turn rate
- Expiry and wastage exposure
- Schedule 6 dispensing auditability
- Basket penetration for chronic patients
- Reorder risk index
- Store-level service risk

## AI and advanced analytics

### Forecasting
The ML layer predicts demand at SKU-store level using historical sales, seasonality, and inventory context.

### AI inventory agent
The LLMOps layer explains anomalies such as:
- Overstock risk
- Stock-out risk
- Unusual dispensing patterns
- Margin leakage
- Reorder exceptions

The agent is designed to produce executive-friendly recommendations, not just technical output.

## Project goals

This repository is designed to showcase skills relevant to analytics, data engineering, platform thinking, and AI product delivery:
- Modern data architecture design
- Batch and streaming pipeline development
- KPI modeling for executive reporting
- MLOps practices for forecasting
- LLMOps practices for governed AI agents
- Dashboard development for business stakeholders
- Documentation quality suitable for enterprise environments

## Repository structure

```text
apps/           Frontend dashboard and API services
config/         Metrics, policies, settings, and data contracts
data/           Raw, bronze, silver, gold, and synthetic datasets
docs/           Business, architecture, runbooks, and operating documentation
infra/          Infrastructure-as-code, Docker, and cloud setup
models/         Model artifacts, prompt versions, and registry metadata
notebooks/      Exploration and model development notebooks
orchestration/  Batch and streaming workflows
sql/            SQL transformations and marts
src/            Core Python package for ingestion, transforms, ML, and agents
tests/          Unit, integration, data quality, and smoke tests
```

## Recommended tech stack

- Python
- DuckDB
- Polars
- Pandas
- Streamlit
- FastAPI
- Great Expectations or Soda for data quality
- MLflow for experiment tracking
- Evidently for model monitoring
- LiteLLM / OpenAI-compatible layer or Workers AI integration
- Docker
- GitHub Actions

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/dischem-omni-channel-inventory-orchestrator.git
cd dischem-omni-channel-inventory-orchestrator
```

### 2. Create environment

```bash
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
pip install -U pip
pip install -r apps/dashboard/requirements.txt
pip install -r apps/api/requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Populate values for storage, model endpoints, and dashboard settings.

### 4. Seed demo data

```bash
python scripts/seed_data.py
```

### 5. Run batch pipeline

```bash
python orchestration/batch/ingest_pos.py
python orchestration/batch/ingest_sap.py
python orchestration/batch/ingest_clinic.py
python orchestration/batch/build_gold.py
```

### 6. Run streaming simulator

```bash
python orchestration/streaming/simulator.py
```

### 7. Launch dashboard

```bash
streamlit run apps/dashboard/streamlit_app.py
```

## Example user stories

- As a CFO, I want to see trapped working capital by store so that I can prioritize inventory reduction.
- As a supply chain leader, I want to identify high-risk stock-out zones before service levels drop.
- As a pharmacy operations manager, I want auditable Schedule 6 movement reporting.
- As an executive, I want an AI assistant that explains why inventory exceptions matter and what action to take.

## MLOps scope

The project includes a lightweight but realistic MLOps lifecycle:

- Feature generation
- Baseline forecasting model
- Experiment tracking
- Model artifact storage
- Evaluation metrics
- Re-training hooks
- Monitoring placeholders

## LLMOps scope

The project also demonstrates practical LLMOps patterns:

- Prompt versioning
- Guardrails and policy config
- Retrieval-ready business context
- Reason logging for exceptions
- Human-readable summaries for executives
- Traceability of recommendations

## Testing and quality

The repository supports:

- Unit tests for transformations and metrics
- Integration tests for pipeline flow
- Data quality checks for schema and freshness
- Smoke tests for dashboard and API startup
- CI workflows for linting, tests, and docs validation

## Documentation strategy

This repository is intentionally documentation-heavy to mirror enterprise delivery standards. The `docs/` folder should contain:

- Architecture decisions
- KPI definitions
- Data contracts
- Security and POPIA notes
- Operating runbooks
- Demo walkthrough instructions
- Screenshots of dashboards

## Portfolio value

This is not just a coding project. It is a business-facing analytics product that demonstrates the ability to:

- Translate strategy into data products
- Build executive-grade reporting layers
- Design scalable pipelines
- Apply AI responsibly in a regulated industry
- Communicate clearly with both technical and non-technical stakeholders

## Roadmap

### Phase 1

- Build synthetic datasets
- Implement Bronze to Gold pipeline
- Deliver initial executive dashboard

### Phase 2

- Add demand forecasting and model tracking
- Add simulated streaming events and alerts
- Improve KPI drilldowns

### Phase 3

- Add AI inventory agent
- Add governance logs and exception audit trail
- Add scenario simulation features

### Phase 4

- Containerize services
- Add CI/CD and deployment automation
- Publish architecture diagrams and demo video

## Suggested screenshots for the repo

Add these visuals to improve recruiter and hiring manager impact:

- Executive dashboard landing page
- Inventory health deep-dive page
- Forecasting page
- AI agent explanation panel
- Architecture diagram
- Medallion data flow diagram

## Contribution guide

1. Create a feature branch
2. Commit logically and clearly
3. Add tests for all important logic
4. Update docs for any architecture or KPI changes
5. Open a pull request using the template

## License

Use MIT for portfolio simplicity unless you want to keep the repository private or more restricted.

## Author positioning statement

This project was developed as a portfolio-grade demonstration of executive analytics, healthcare retail inventory intelligence, and agentic AI system design using open-source tools and cloud-native patterns.

---

