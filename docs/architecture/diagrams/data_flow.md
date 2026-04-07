# Data Flow & Medallion Architecture

## Overview

This diagram shows how data flows through the system using a medallion architecture (Bronze, Silver, Gold), supporting batch and streaming ingestion.

```mermaid
graph LR

    pos["POS Systems"]
    erp["ERP / SAP"]
    clinic["Clinic Systems"]
    events["Streaming Events"]

    bronze["Bronze Layer<br/>Raw Data"]
    silver["Silver Layer<br/>Cleaned & Standardized"]
    gold["Gold Layer<br/>Business-Ready Data"]

    dashboard["Dashboard"]
    ml["ML Models"]
    agent["AI Agent"]

    pos --> bronze
    erp --> bronze
    clinic --> bronze
    events --> bronze

    bronze --> silver
    silver --> gold

    gold --> dashboard
    gold --> ml
    gold --> agent

    silver --> ml
