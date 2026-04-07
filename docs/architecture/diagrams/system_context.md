```mermaid
graph TD

    exec["Executive Leadership"]
    ops["Operations Teams"]
    analyst["Data Analyst"]

    system["Inventory Intelligence Platform"]

    pos["POS Systems"]
    erp["ERP / SAP"]
    clinic["Clinic Systems"]

    exec -->|Views dashboards & insights| system
    ops -->|Receives alerts & recommendations| system
    analyst -->|Queries data & KPIs| system

    pos -->|Sales data| system
    erp -->|Inventory data| system
    clinic -->|Dispensing data| system
