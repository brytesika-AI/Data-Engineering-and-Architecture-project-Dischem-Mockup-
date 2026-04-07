# Data Architecture

## 1. Purpose of This Document

This document defines the data architecture for the **Dis-Chem Omni-Channel Inventory Orchestrator**. It describes how data is sourced, structured, transformed, governed, and delivered to support executive decision-making, operational analytics, and AI-driven capabilities.

The objective is to establish a scalable, governed, and reusable data foundation that supports both traditional business intelligence and advanced analytics use cases.

---

## 2. Data Architecture Principles

The design of the data architecture is guided by the following principles:

- **Business-aligned data modeling**: Data structures reflect business entities such as products, stores, inventory positions, and dispensing events.
- **Separation of concerns**: Raw ingestion, standardized transformation, and business-ready outputs are clearly separated.
- **Single source of truth**: Gold-layer datasets serve as the authoritative source for KPIs and reporting.
- **Reusability**: Data products are designed to be reused across dashboards, forecasting models, and AI agents.
- **Traceability**: Every metric and insight can be traced back to source data.
- **Governance by design**: Data quality, contracts, and masking are embedded into pipelines.

---

## 3. Source Data Domains

The architecture integrates multiple operational domains.

### 3.1 Point-of-Sale (POS)

- Transaction-level sales data
- SKU-level demand signals
- Store-level performance indicators

### 3.2 ERP / SAP

- Inventory levels
- Procurement and replenishment data
- Cost and financial attributes

### 3.3 Clinic and Dispensing Systems

- Prescription data
- Dispensing events
- Controlled drug tracking

### 3.4 Synthetic Streaming Layer

- Simulated inventory changes
- Event-driven stock alerts
- Near-real-time anomaly signals

---

## 4. Medallion Architecture

The platform uses a **Bronze → Silver → Gold** medallion architecture to organize data transformation and consumption.

### 4.1 Bronze Layer (Raw Data)

The Bronze layer stores raw ingested data with minimal transformation.

#### Characteristics

- Immutable append-only storage
- Schema preserved as received
- Minimal validation

#### Example tables

- `pos_transactions_raw`
- `sap_inventory_levels_raw`
- `clinic_scripts_raw`

---

### 4.2 Silver Layer (Standardized Data)

The Silver layer contains cleaned, conformed, and standardized datasets.

#### Key transformations

- Data cleaning and normalization
- Schema alignment across sources
- Deduplication
- Enrichment with reference data

#### Example tables

- `dim_products_hc`
- `fct_inventory_snapshots`
- `fct_dispensing_log`

#### Business role

The Silver layer provides a trusted operational view of the business that can be reused across multiple downstream use cases.

---

### 4.3 Gold Layer (Business Data Products)

The Gold layer contains curated datasets optimized for analytics, KPIs, and AI consumption.

#### Example marts

- `mart_inventory_health`
- `mart_financial_performance`
- `mart_customer_behavior`

#### Characteristics

- Pre-aggregated metrics
- Business-friendly schemas
- Consistent definitions across dashboards

#### Business role

The Gold layer serves as the single source of truth for executive reporting and advanced analytics.

---

## 5. Data Modeling Approach

The architecture uses a hybrid modeling approach:

- **Dimensional modeling** for analytical marts
- **Fact tables** for transactions and events
- **Dimension tables** for products, stores, and customers

This approach supports both performance and interpretability.

---

## 6. Data Pipelines

### 6.1 Batch Processing

Batch pipelines handle periodic ingestion and transformation:

- POS ingestion
- ERP ingestion
- Clinic ingestion
- Bronze → Silver → Gold transformations

### 6.2 Streaming Simulation

A simulated streaming layer is used to model real-time behavior:

- inventory updates
- anomaly detection triggers
- alert generation

This demonstrates readiness for real-time architectures without requiring live infrastructure.

---

## 7. Data Quality and Validation

Data quality is embedded into the architecture.

### Key checks

- schema validation
- completeness checks
- freshness checks
- anomaly detection

### Tools (proposed)

- Great Expectations or Soda

---

## 8. Data Governance

### 8.1 Data Contracts

Data contracts define expectations between layers:

- schema definitions
- field-level constraints
- update frequency

### 8.2 Data Lineage

All transformations are traceable from Gold back to source systems.

### 8.3 Sensitive Data Handling

- PII masking at the Silver layer
- restricted access to sensitive fields

---

## 9. Data Access Patterns

Different consumers access data in different ways:

- dashboards query Gold tables
- forecasting models consume Gold + Silver features
- AI agents use curated context from Gold

---

## 10. Integration with ML and AI

The data architecture supports:

- feature generation for forecasting
- training datasets for ML models
- contextual inputs for LLM agents
- traceable outputs for AI explanations

---

## 11. Scalability Considerations

The architecture is designed to scale through:

- separation of storage and compute
- modular pipeline design
- incremental data processing

---

## 12. Data Architecture Summary

The data architecture establishes a governed, scalable, and reusable foundation for the Dis-Chem Omni-Channel Inventory Orchestrator. It enables consistent reporting, supports advanced analytics, and ensures that all insights are traceable, reliable, and aligned with business needs.
