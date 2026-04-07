# Architecture Diagrams

This folder contains the core architecture visuals for the **Dis-Chem Omni-Channel Inventory Orchestrator**.

## Diagram Index

### 1. System Context Diagram
**File:** `system_context.md`  
Shows the high-level relationship between the platform, its users, and external source systems.

### 2. Container Diagram
**File:** `container_diagram.md`  
Shows the major platform components, including the dashboard, API, AI agent, forecasting service, orchestration layer, and medallion data layers.

### 3. Data Flow & Medallion Architecture
**File:** `data_flow.md`  
Shows how data moves from source systems through Bronze, Silver, and Gold layers into dashboards, ML models, and AI services.

### 4. AI Agent Flow Diagram
**File:** `ai_agent_flow.md`  
Shows how the AI Inventory Agent uses governed business context, policies, prompts, analytical signals, and audit logging to generate explainable recommendations.

## Why These Diagrams Matter

Together, these diagrams show that the solution has been designed across multiple architectural layers:

- **System context** for enterprise positioning
- **Application containers** for modular platform design
- **Data flow architecture** for lakehouse and analytics design
- **AI flow architecture** for governed LLMOps and explainable recommendations

## Suggested Reading Order

1. `system_context.md`
2. `container_diagram.md`
3. `data_flow.md`
4. `ai_agent_flow.md`

## Portfolio Positioning

These diagrams are intended to demonstrate enterprise architecture thinking across business, data, application, and AI-enabled platform layers. They support the written architecture documents in the parent `docs/architecture/` folder.
