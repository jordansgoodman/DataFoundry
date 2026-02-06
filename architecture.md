# Architecture

## Components (Concise)
- **NGINX**: Single entrypoint and reverse proxy. Routes `/bi/`, `/airflow/`, `/grafana/`.
- **PostgreSQL**: Primary analytics warehouse and metadata store.
- **Redis**: Cache and async coordination (Airflow Celery broker).
- **DataFoundry BI (Streamlit)**: BI UI and API.
- **Airflow Webserver**: Orchestration UI and API.
- **Airflow Scheduler**: Schedules DAGs and task instances.
- **Airflow Worker**: Executes tasks with Celery.
- **dlt**: Ingestion pipelines that load data into Postgres.
- **Promtail**: Docker log shipper that tails container logs.
- **Loki**: Log storage backend.
- **Grafana**: Logs + metrics dashboards.
- **Prometheus**: Metrics scraper and time‑series store.
- **Node Exporter**: Host metrics (CPU, memory, disk, network).
- **StatsD Exporter**: Bridges Airflow StatsD metrics into Prometheus.

## Data + Control Flow
- Users access **NGINX** which routes to BI, Airflow, and Grafana.
- **Airflow** schedules ingestion using **dlt**, loading data into **Postgres**.
- **DataFoundry BI** queries **Postgres** for dashboards and charts.
- **Redis** backs Airflow Celery execution.
- **Promtail** ships container logs into **Loki**.
- **Grafana** reads logs from Loki and metrics from **Prometheus**.
- **Prometheus** scrapes **Node Exporter** and **StatsD Exporter**.

## ASCII Diagram
```
                         +----------------------+
                         |       Users          |
                         +----------+-----------+
                                    |
                                    v
                             +------+------+
                             |    NGINX    |
                             +---+---+-----+
                                 |   |
          +----------------------+   +----------------------+
          |                                              |
          v                                              v
+---------------------+                        +---------------------+
|   DataFoundry BI    |                        |      Airflow        |
|    (Streamlit)      |                        | Web/Scheduler/Worker|
+----------+----------+                        +----------+----------+
           |                                              |
           |                                              | triggers
           v                                              v
     +-----+-----+                               +--------+--------+
     | Postgres  |<--------- dlt loads ----------|      dlt         |
     +-----+-----+                               +-----------------+
           ^
           |
      +----+----+
      | Redis   |
      +----+----+
           |
           | Celery + cache
           v
+---------------------+
|     Airflow         |
|   async tasks       |
+---------------------+

  Logs + Metrics:

  Docker logs -> Promtail -> Loki -> Grafana
  Node Exporter -> Prometheus -> Grafana
  Airflow StatsD -> StatsD Exporter -> Prometheus -> Grafana
```

## Mermaid Diagram
```mermaid
flowchart TD
  U["Users"] --> N["NGINX"]
  N --> S["DataFoundry BI (Streamlit)"]
  N --> A["Airflow (Web/Scheduler/Worker)"]
  N --> G["Grafana"]

  A -->|triggers| D["dlt"]
  D --> P["Postgres"]
  S --> P
  R["Redis"] --> A
  R --> A

  subgraph Logs
    L1["Docker logs"] --> PR["Promtail"] --> LK["Loki"] --> G
  end

  subgraph Metrics
    NE["Node Exporter"] --> PM["Prometheus"] --> G
    SD["Airflow StatsD"] --> SE["StatsD Exporter"] --> PM
  end
```
