from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dischem_orchestrator.agent import AgentError, explain_inventory_exception
from dischem_orchestrator.api_data import DataServiceError, get_forecast, get_inventory_health, get_kpis_summary

DATA_GOLD_DIR = ROOT / "data" / "gold"
DEMO_DATA_DIR = ROOT / "apps" / "dashboard" / "demo_data"

def _pick_data_file(gold_name: str) -> Path:
    prod = DATA_GOLD_DIR / gold_name
    if prod.exists():
        return prod
    return DEMO_DATA_DIR / gold_name

KPI_PATH = _pick_data_file("kpi_summary.csv")
INVENTORY_HEALTH_PATH = _pick_data_file("mart_inventory_health.csv")
FORECAST_PATH = _pick_data_file("forecast_sku_store_daily.csv")
ALERTS_PATH = _pick_data_file("streaming_alerts.csv")
POLICY_PATH = ROOT / "config" / "policies" / "agent_policy.json"
PROMPT_PATH = ROOT / "config" / "prompts" / "inventory_agent_prompt.txt"
AUDIT_LOG_PATH = Path(tempfile.gettempdir()) / "agent_explanations_log.jsonl"

st.set_page_config(page_title="Dis-Chem Inventory Orchestrator", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
      .stApp { background: #f5f7fa; color: #0f172a; }
      h1, h2, h3 { color: #111827; letter-spacing: 0.1px; }
      .hero {
        background: linear-gradient(90deg, #b11226 0%, #ce2035 45%, #0f5c45 100%);
        color: #ffffff;
        border-radius: 0.75rem;
        padding: 1rem 1.1rem;
        margin-bottom: 0.8rem;
      }
      .hero-title { font-size: 1.25rem; font-weight: 700; margin: 0; }
      .hero-subtitle { font-size: 0.92rem; opacity: 0.95; margin: 0.25rem 0 0 0; }
      .panel {
        background: #ffffff;
        border: 1px solid #dce3ea;
        border-radius: 0.75rem;
        padding: 0.95rem 1rem;
      }
      .section-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.9px;
        color: #475569;
        margin-bottom: 0.35rem;
        font-weight: 700;
      }
      .insight {
        border-left: 4px solid #0f5c45;
        padding: 0.55rem 0.75rem;
        background: #f8fbfa;
        border-radius: 0.35rem;
        margin: 0.35rem 0;
      }
      .risk-high { color: #b91c1c; font-weight: 700; }
      .risk-medium { color: #b45309; font-weight: 700; }
      .risk-low { color: #166534; font-weight: 700; }
      .signal-chip {
        display: inline-block;
        background: #eef2f6;
        border: 1px solid #d4dbe3;
        border-radius: 999px;
        padding: 0.15rem 0.55rem;
        margin: 0.12rem 0.2rem 0.12rem 0;
        font-size: 0.82rem;
      }
      /* Make tabs unmistakably visible */
      .stTabs [data-baseweb="tab-list"] {
        gap: 0.6rem;
        background: #eef2f6;
        border: 1px solid #d4dbe3;
        padding: 0.4rem;
        border-radius: 0.7rem;
      }
      .stTabs [data-baseweb="tab"] {
        height: 2.2rem;
        border-radius: 0.55rem;
        padding: 0 0.9rem;
        font-weight: 650;
        color: #334155 !important;
        background: #ffffff !important;
        border: 1px solid #d4dbe3 !important;
      }
      .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background: linear-gradient(90deg, #b11226 0%, #ce2035 55%, #0f5c45 100%) !important;
        border: 1px solid #9f1239 !important;
      }
      .stTabs [data-baseweb="tab-highlight"] {
        background-color: transparent !important;
      }
      /* Force metric readability */
      [data-testid="stMetricLabel"] { color: #475569 !important; }
      [data-testid="stMetricValue"] { color: #111827 !important; }
      /* Ensure button text is always visible */
      .stButton > button {
        background: #0f5c45 !important;
        color: #ffffff !important;
        border: 1px solid #0f5c45 !important;
        font-weight: 600 !important;
      }
      .stButton > button:hover {
        background: #0c4a38 !important;
        border-color: #0c4a38 !important;
        color: #ffffff !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

using_demo_data = str(DEMO_DATA_DIR) in str(KPI_PATH)
if using_demo_data:
    st.info("Running with bundled demo data because `data/gold` artifacts are not present in this environment.")


def _store_options() -> list[str]:
    if not KPI_PATH.exists():
        return []
    stores = set()
    with KPI_PATH.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            stores.add(r["store_id"])
    return sorted(stores)


def _date_options() -> list[str]:
    if not KPI_PATH.exists():
        return []
    dates = set()
    with KPI_PATH.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("date"):
                dates.add(r["date"])
    return sorted(dates)


def _risk_tier(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _render_agent_response(resp: object) -> None:
    data = resp.as_dict()
    risk = data["risk_level"].lower()
    risk_class = f"risk-{risk if risk in {'high', 'medium', 'low'} else 'low'}"

    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown("<div class='section-label'>AI Narrative Brief</div>", unsafe_allow_html=True)
    st.markdown(f"### {data['summary']}")
    st.markdown(
        f"<span class='{risk_class}'>Risk: {data['risk_level'].upper()}</span> &nbsp;|&nbsp; "
        f"<strong>Confidence:</strong> {data['confidence']:.2f} &nbsp;|&nbsp; "
        f"<strong>Store:</strong> {data['store_id']} &nbsp;|&nbsp; <strong>Date:</strong> {data['date']}",
        unsafe_allow_html=True,
    )

    st.write("**Primary Drivers**")
    for d in data.get("key_drivers", []):
        st.markdown(f"- {d}")

    st.write("**Recommended Executive Actions**")
    for i, action in enumerate(data.get("recommended_actions", []), start=1):
        st.markdown(f"{i}. {action}")

    st.write("**Decision Signals**")
    chips = []
    for k, v in data.get("signals", {}).items():
        chips.append(f"<span class='signal-chip'>{k}: {v}</span>")
    st.markdown("".join(chips), unsafe_allow_html=True)

    st.caption(f"Run ID: {data['run_id']} | Policy: {data['policy_version']} | Prompt: {data['prompt_version']}")
    st.markdown("</div>", unsafe_allow_html=True)


stores = _store_options()
dates = _date_options()

st.markdown(
    """
    <div class="hero">
      <p class="hero-title">Dis-Chem Omni-Channel Inventory Orchestrator</p>
      <p class="hero-subtitle">Executive decision dashboard for working capital, service risk, and exception actioning.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

selected_store = st.sidebar.selectbox("Store", options=["ALL"] + stores, index=0)
selected_store_value = None if selected_store == "ALL" else selected_store

selected_date = st.sidebar.selectbox("Date", options=["LATEST"] + dates, index=0)
selected_date_value = None if selected_date == "LATEST" else selected_date

try:
    kpi = get_kpis_summary(KPI_PATH, date=selected_date_value, store_id=selected_store_value)
    inv = get_inventory_health(INVENTORY_HEALTH_PATH, date=selected_date_value, store_id=selected_store_value, limit=250)
except DataServiceError as exc:
    st.error(str(exc))
    st.stop()

metrics = kpi.get("metrics", {})
items = inv.get("items", [])
rows = inv.get("rows", 0)

tab_exec, tab_fc, tab_ai, tab_inv = st.tabs(
    ["Executive Highlights", "Forecasting", "AI Agent", "Inventory Health"]
)

with tab_exec:
    st.caption("Use the tabs to navigate: Executive Highlights | Forecasting | AI Agent | Inventory Health")
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Inventory Value", f"R {metrics.get('inventory_value_total', 0):,.0f}")
    k2.metric("Inventory Days", f"{metrics.get('inventory_days_avg', 0):.2f}")
    k3.metric("Stock Turn", f"{metrics.get('stock_turn_avg', 0):.2f}")
    k4.metric("Expiry Exposure", f"R {metrics.get('expiry_exposure_total', 0):,.0f}")
    k5.metric("Reorder Risk", f"{metrics.get('reorder_risk_avg', 0):.3f}")
    k6.metric("Service Risk", f"{metrics.get('service_risk_avg', 0):.3f}")

    st.markdown("### Executive Highlights")
    ins_left, ins_right = st.columns([1.2, 1.8])

    with ins_left:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("<div class='section-label'>Portfolio Posture</div>", unsafe_allow_html=True)
        overall_risk = _risk_tier(float(metrics.get("service_risk_avg", 0.0)))
        risk_cls = f"risk-{overall_risk}"
        st.markdown(
            f"<div class='insight'><strong>Overall service-risk posture:</strong> "
            f"<span class='{risk_cls}'>{overall_risk.upper()}</span></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='insight'><strong>Scope:</strong> {rows} store-day records in current filter.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with ins_right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown("<div class='section-label'>What Needs Attention</div>", unsafe_allow_html=True)
        top = items[:3]
        if not top:
            st.markdown("<div class='insight'>No inventory rows available for this filter.</div>", unsafe_allow_html=True)
        else:
            for r in top:
                st.markdown(
                    f"<div class='insight'><strong>{r.get('store_id')}</strong> | "
                    f"Reorder risk {float(r.get('reorder_risk_index', 0)):,.3f} | "
                    f"Service risk {float(r.get('store_service_risk', 0)):,.3f} | "
                    f"Stock cover {float(r.get('stock_cover_days', 0)):,.1f} days</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("</div>", unsafe_allow_html=True)

with tab_fc:
    st.subheader("Forecasting")
    forecast_store = st.selectbox("Forecast Store", options=["ALL"] + stores, index=0, key="fc_store")
    forecast_store_value = None if forecast_store == "ALL" else forecast_store
    forecast_rows = get_forecast(FORECAST_PATH, store_id=forecast_store_value, limit=300).get("items", [])
    st.dataframe(forecast_rows, use_container_width=True, height=460)

with tab_ai:
    st.subheader("AI Agent")
    default_agent_date = kpi.get("date") or (dates[-1] if dates else "2025-01-01")
    agent_date = st.selectbox(
        "Agent Date",
        options=dates if dates else [default_agent_date],
        index=(dates.index(default_agent_date) if default_agent_date in dates else 0),
    )
    agent_store = st.selectbox("Agent Store", options=stores if stores else ["ST001"], index=0, key="agent_store")
    agent_sku = st.text_input("SKU (optional)", value="")

    if st.button("Generate Executive Explanation"):
        try:
            response = explain_inventory_exception(
                day=agent_date,
                store_id=agent_store,
                sku_id=agent_sku.strip() or None,
                kpi_path=KPI_PATH,
                alerts_path=ALERTS_PATH,
                forecast_path=FORECAST_PATH,
                policy_path=POLICY_PATH,
                prompt_path=PROMPT_PATH,
                audit_log_path=AUDIT_LOG_PATH,
            )
            _render_agent_response(response)
        except AgentError as exc:
            st.error(str(exc))

with tab_inv:
    st.subheader("Inventory Health")
    st.dataframe(items, use_container_width=True, height=560)
