# AI Agent Flow Diagram

## Overview

This diagram shows how the AI Inventory Agent uses governed business context, analytical signals, and policy controls to generate explainable recommendations.

```mermaid
graph TD

    user["Executive / Analyst / Operations User"]
    dashboard["Executive Dashboard / API"]
    agent["AI Inventory Agent"]

    gold["Gold Layer<br/>Business-ready marts"]
    forecasts["Forecast Outputs"]
    rules["Business Rules & Thresholds"]
    policies["Agent Policies & Guardrails"]
    prompts["Prompt Templates"]
    audit["Audit Log / Decision Trace"]

    explanation["Explainable Recommendation"]
    action["Suggested Action / Escalation"]

    user --> dashboard
    dashboard --> agent

    gold --> agent
    forecasts --> agent
    rules --> agent
    policies --> agent
    prompts --> agent

    agent --> explanation
    agent --> action

    explanation --> dashboard
    action --> dashboard

    agent --> audit
