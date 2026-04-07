# Application Architecture

## 1. Purpose of This Document

This document defines the application architecture for the **Dis-Chem Omni-Channel Inventory Orchestrator**. It describes the logical services, components, interaction patterns, and interfaces that operationalize the data platform and deliver business capabilities to end users.

The goal is to present a modular, service-oriented architecture that supports scalability, maintainability, and clear separation of concerns across ingestion, transformation, analytics, AI, and presentation layers.

---

## 2. Application Architecture Principles

- **Modularity**: Decompose the system into cohesive, loosely coupled services.
- **Separation of concerns**: Distinguish ingestion, transformation, metrics, ML, AI, and presentation.
- **API-first design**: Expose capabilities via well-defined interfaces for reuse and integration.
- **Event awareness**: Support both batch and event-driven (simulated streaming) interactions.
- **Observability**: Ensure logging, metrics, and tracing across services.
- **Governed AI**: Treat AI components as first-class services with policies, prompts, and audit trails.

---

## 3. High-Level Component Model

The application layer is composed of the following logical components:

1. **Ingestion Services**
2. **Transformation Services**
3. **Metrics & KPI Service**
4. **Forecasting Service (ML)**
5. **AI Inventory Agent (LLMOps)**
6. **API Layer**
7. **Executive Dashboard (UI)**
8. **Streaming Simulator & Alerts**
9. **Governance & Audit Service**

Each component is independently evolvable and can be deployed as a separate service if required.

---

## 4. Component Descriptions

### 4.1 Ingestion Services

**Purpose**: Acquire data from source systems and land it in the Bronze layer.

**Responsibilities**:
- Connect to POS, ERP/SAP, and clinic sources
- Validate basic schemas and formats
- Persist raw datasets to storage

**Interfaces**:
- File-based ingestion (CSV, JSON, Parquet)
- Scheduled batch jobs

---

### 4.2 Transformation Services

**Purpose**: Convert Bronze data into standardized Silver and business-ready Gold datasets.

**Responsibilities**:
- Data cleaning and normalization
- Schema conformance
- Business rule application
- Aggregation and mart construction

**Interfaces**:
- Orchestrated batch jobs
- SQL/Polars/DuckDB transformations

---

### 4.3 Metrics & KPI Service

**Purpose**: Centralize business metric definitions and calculations.

**Responsibilities**:
- Define KPI logic (e.g., inventory days, stock turn)
- Provide reusable metric computations
- Ensure consistency across dashboards and APIs

**Interfaces**:
- Internal library (Python)
- API endpoints for KPI retrieval

---

### 4.4 Forecasting Service (ML)

**Purpose**: Predict SKU-store demand and support replenishment decisions.

**Responsibilities**:
- Feature generation from Silver/Gold layers
- Model training and evaluation
- Forecast generation and storage

**Interfaces**:
- Batch training jobs
- API for forecast retrieval

---

### 4.5 AI Inventory Agent (LLMOps)

**Purpose**: Provide explainable, business-oriented reasoning for inventory exceptions and recommendations.

**Responsibilities**:
- Detect anomalies using rules + model signals
- Generate natural language explanations
- Recommend prioritized actions
- Log reasoning for auditability

**Interfaces**:
- Prompt templates and policies
- API endpoints for agent queries
- Integration with dashboard for narratives

---

### 4.6 API Layer

**Purpose**: Provide a unified interface for accessing data, metrics, forecasts, and AI outputs.

**Responsibilities**:
- Expose REST endpoints (FastAPI)
- Enforce access control and validation
- Serve as integration point for UI and external systems

**Example endpoints**:
- `/kpis`
- `/inventory/health`
- `/forecast`
- `/agent/explain`

---

### 4.7 Executive Dashboard (UI)

**Purpose**: Deliver executive-grade insights and interactive analytics.

**Responsibilities**:
- Present KPIs and trends
- Enable drill-down into inventory performance
- Display AI-generated explanations
- Support scenario exploration (future phase)

**Technology**:
- Streamlit (initial)

---

### 4.8 Streaming Simulator & Alerts

**Purpose**: Emulate real-time behavior and event-driven processing.

**Responsibilities**:
- Generate synthetic inventory events
- Trigger alerts based on thresholds
- Feed near-real-time signals into the system

**Value**:
- Demonstrates readiness for event-driven architectures

---

### 4.9 Governance & Audit Service

**Purpose**: Ensure traceability and compliance across the application layer.

**Responsibilities**:
- Log AI decisions and overrides
- Track KPI definitions and versions
- Maintain audit trails for sensitive operations

---

## 5. Interaction Patterns

### 5.1 Batch Flow

1. Ingestion services load data into Bronze
2. Transformation services produce Silver and Gold
3. Metrics service computes KPIs
4. Forecasting service generates predictions
5. Results exposed via API and dashboard

### 5.2 Event-Driven Flow (Simulated)

1. Streaming simulator emits inventory events
2. Alert logic detects anomalies
3. AI agent generates explanations
4. Dashboard displays alerts and narratives

---

## 6. API Design Considerations

- RESTful endpoints for simplicity
- Clear separation between data retrieval and AI reasoning endpoints
- Versioning for backward compatibility
- Input validation and error handling

---

## 7. Integration with Data Architecture

- Ingestion and transformation services write to medallion layers
- Metrics and forecasting services read from Gold/Silver
- API and dashboard consume Gold outputs
- AI agent uses curated context from Gold for reasoning

---

## 8. Integration with Technology Architecture

- Services run in containerized environments (Docker)
- CI/CD pipelines automate testing and deployment
- Logging and monitoring integrated across services

---

## 9. Non-Functional Requirements

### Scalability

- Services can scale independently
- Compute can be distributed as needed

### Reliability

- Retry mechanisms for ingestion and processing
- Idempotent transformations

### Performance

- Pre-aggregated Gold datasets
- Efficient query engines (DuckDB/Polars)

### Security

- API authentication and authorization
- Controlled access to sensitive endpoints

---

## 10. Application Architecture Summary

The application architecture transforms the data platform into an operational system. It provides modular services for ingestion, transformation, analytics, forecasting, and AI reasoning, all exposed through APIs and consumed via an executive dashboard.

This design ensures flexibility, scalability, and maintainability, while enabling future expansion into more advanced, real-time, and fully agentic workflows.
