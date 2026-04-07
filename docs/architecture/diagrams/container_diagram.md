# Container Diagram

## Overview

This diagram shows the major application and platform containers that make up the Dis-Chem Omni-Channel Inventory Orchestrator.

```mermaid
graph TD

    users["Executives, Analysts, Operations Teams"]

    dashboard["Executive Dashboard<br/>Streamlit UI"]
    api["Application API<br/>FastAPI services"]
    agent["AI Inventory Agent<br/>LLM reasoning + recommendations"]
    ml["Forecasting Service<br/>Demand prediction models"]
    orchestrator["Batch & Streaming Orchestration<br/>Python pipelines"]
    metrics["Metrics & KPI Service<br/>Business logic layer"]

    bronze["Bronze Layer<br/>Raw data"]
    silver["Silver Layer<br/>Standardized data"]
    gold["Gold Layer<br/>Business-ready marts"]

    pos["POS Systems"]
    erp["ERP / SAP"]
    clinic["Clinic Systems"]
    events["Streaming Event Simulator"]

    users --> dashboard
    dashboard --> api
    api --> metrics
    api --> ml
    api --> agent

    orchestrator --> bronze
    orchestrator --> silver
    orchestrator --> gold

    pos --> orchestrator
    erp --> orchestrator
    clinic --> orchestrator
    events --> orchestrator

    metrics --> gold
    ml --> gold
    ml --> silver
    agent --> gold

    agent --> api
    ml --> api
    metrics --> api
