# DataSpec: local analytics without the cloud tax

Most analytics stacks assume the cloud. That is the default. It is also the trap.

Cloud is a tax on latency, privacy, and attention. It is great for scale. It is bad for calm.

DataSpec is the opposite. It is a full analytics stack you run on one box. It is local‑first by design. It does not need Kubernetes. It does not need a SaaS control plane. It does not need a credit card.

This post explains what DataSpec is, why it exists, and how every piece connects. It uses simple language. It is long on purpose. If you want to run this stack, you should understand it.

## What “local‑first analytics” means

Local‑first is not just “self‑hosted.” It is a bias. It is a design decision that shows up everywhere.

It means:

- Data stays on your machine by default.
- The system works without a network beyond your LAN.
- Every service runs in containers you can see and control.
- The stack is debuggable with basic tools.
- There is one place to back up.

This is not about ideology. It is about control. If the stack is local, it is yours. If it is yours, you can fix it when it breaks.

## The problem DataSpec solves

Most teams want the same things:

- Ingest data.
- Store data.
- Schedule jobs.
- Query data.
- Make dashboards.
- Keep logs.

You can get this from a cloud vendor. You can also get it by wiring open‑source tools together. The second path is painful because the defaults are not aligned. DataSpec is that alignment.

## The architecture in one sentence

Postgres is the warehouse. Airflow runs dlt to load data. Superset queries Postgres. pgAdmin is the DB UI. Loki + Promtail + Grafana capture and visualize logs.

That is it. No more moving parts.

## Component by component

### 1) Postgres: the warehouse

Postgres is the core. Everything writes to it. Everything reads from it.

Why Postgres?

- It is stable.
- It is fast enough for most teams.
- It is easy to back up.
- It has a huge ecosystem.

In DataSpec, Postgres is both the **analytics store** and the **metadata store**. Superset and Airflow each keep their internal metadata in Postgres. That keeps the stack simple. You manage one database.

If Postgres is down, the stack is down. That is a feature, not a bug. One failure mode is easier than five.

### 2) dlt: ingestion engine

dlt is the ingestion engine. It fetches data, normalizes it, and loads it into Postgres.

Why dlt instead of a big ETL tool?

- It is minimal.
- It is Python.
- It has a clean mental model.

dlt lets you write a resource that yields rows. It manages the table structure and load state. You don’t have to think about loading mechanics.

In DataSpec, dlt loads NYC Taxi data on first run. That is the default dataset. It is big enough to test the stack. It is simple enough to understand.

### 3) Airflow: orchestration

Airflow runs the ingestion jobs. It also runs any other Python workflows you add later.

What Airflow does here:

- Schedules jobs.
- Runs the dlt pipeline.
- Tracks runs, retries, and logs.

Airflow is heavy if you run it wrong. DataSpec runs it in **LocalExecutor** mode on a single node. That is the right choice for this system. You get parallelism without the overhead.

Airflow is the control plane. It decides what runs and when. It does not store data. It just moves it.

### 4) Superset: BI and dashboards

Superset is the BI layer. It sits on top of Postgres. It gives you charts, dashboards, SQL Lab, and permissions.

Why Superset?

- It is mature.
- It supports Postgres well.
- It has RBAC.
- It is open source.

Superset has its own metadata database. DataSpec stores that in Postgres too. That is simple and consistent. Superset uses the `superset` database by default.

When you open Superset, you add a database connection to your warehouse. The connection string points to `postgres` (the service name). That matters. `localhost` would point to the Superset container itself, not Postgres.

### 5) pgAdmin: raw DB UI

pgAdmin is for people who want to see tables, not dashboards.

It connects directly to Postgres and lets you browse schemas, run SQL, and inspect data.

Why include it?

- It makes debugging faster.
- It helps during ingestion issues.
- It is a simple way to validate the system.

pgAdmin is not fancy. It is effective.

### 6) Logging stack: Loki + Promtail + Grafana

Logs matter. If you can’t see logs, you can’t fix things.

The logging stack is:

- **Promtail** tails Docker container logs.
- **Loki** stores them.
- **Grafana** shows them.

This works because all services write logs to stdout. Docker captures that. Promtail reads those files. Loki stores them. Grafana queries Loki.

Grafana is exposed on a separate port. It does not block core services. It is optional. But when things go wrong, it is the fastest way to see what happened.

## How the components interact

Here is the real data flow:

1. Airflow schedules a DAG.
2. The DAG calls the dlt pipeline.
3. dlt pulls raw data and normalizes it.
4. dlt writes data into Postgres.
5. Superset queries Postgres.
6. pgAdmin shows Postgres tables.
7. Promtail reads logs from Airflow, Superset, pgAdmin, Postgres.
8. Loki stores those logs.
9. Grafana shows logs via Loki.

You can see why it works. It is linear. It is boring. That is the goal.

## Boot sequence (what happens when you run it)

When you run `docker compose up -d`, a few things happen in order:

1. The setup container creates directories under `./data` and applies permissions.
2. Postgres starts and runs init scripts.
3. Airflow starts and initializes its metadata tables.
4. Superset starts and initializes its metadata tables.
5. pgAdmin starts and registers the Postgres server.
6. Airflow triggers the first NYC Taxi load.
7. Logging stack starts and begins tailing logs.

The setup container is a small thing, but it is important. It makes sure folders exist and permissions are correct. That prevents the classic “permission denied” errors.

## What is local‑first actually buying you?

### 1) Debuggability

Local logs and local data are easy to inspect. You do not need to learn a cloud console. You do not need to dig through a managed service UI.

You can use `docker compose logs`, pgAdmin, and Grafana. That is enough.

### 2) Privacy

Data never leaves your machine by default. That matters for regulated data. It also matters for internal datasets that you do not want to leak.

### 3) Predictable cost

There is no per‑query pricing. There is no “surprise bill.” Your cost is hardware and power. That is it.

### 4) Stable interfaces

Cloud vendors change things. Managed services go down. Local stacks do not do this. Your stack does not change unless you change it.

### 5) Low latency

Network hops are expensive. Local stack = low latency. That is especially useful when analysts run lots of ad‑hoc queries.

## What you give up

Local‑first is not free. You trade convenience for control.

- You have to manage updates.
- You have to monitor disk usage.
- You have to back up `./data`.

This is the cost. For small teams, the cost is reasonable. 

## How to add a new data source

Adding a new source is a DAG problem, not a platform problem.

1. Create a new DAG file under `airflow/dags/`.
2. Use dlt to pull your data in Python.
3. Point the destination to Postgres using the same credentials.
4. Trigger the DAG.

That is it. You do not need to touch Superset or pgAdmin to ingest. They just see new tables once they land.

## How to connect Superset to the warehouse

Superset has two databases:

- **Metadata DB** (already configured by the container)
- **Warehouse DB** (you connect manually)

To add the warehouse, use this connection string:

```
postgresql+psycopg2://datafoundry:<POSTGRES_PASSWORD>@postgres:5432/datafoundry
```

Replace `<POSTGRES_PASSWORD>` with the value in `data/credentials.txt`.

The host is `postgres`, not `localhost`. This is inside Docker networking, not your laptop.

## How logging works in detail

Docker writes every container’s stdout/stderr to disk.

Promtail reads those files at `/var/lib/docker/containers/*/*.log`. It tags them by container name. It pushes them to Loki.

Loki stores logs in a simple filesystem layout. Grafana queries Loki over HTTP.

If logs look missing, check these:

- Is Promtail healthy?
- Is Loki healthy?
- Is Grafana pointing to Loki?

You can do all of this with the Docker logs and Grafana itself.

## Failure modes and how to recover

### Postgres failure

If Postgres goes down, everything else will fail. That is expected.

Fix Postgres first. Then restart the other services if needed.

### Airflow failure

Airflow failure means your jobs do not run. It does not destroy data. Restart Airflow. Your data is still in Postgres.

### Superset failure

Superset failure means dashboards go down. Data is still fine. Restart Superset.

### Logging failure

If Grafana is down, the stack still works. You just lose log visibility. This is acceptable for a local‑first stack.

## Backup strategy

You only need to back up `./data`.

- `./data/postgres` contains all warehouse data.
- `./data/superset` contains Superset metadata.
- `./data/airflow` contains Airflow metadata and logs.
- `./data/logging` contains Loki and Grafana data.

If you back those up, you can restore the system.

## Security basics

- Change all passwords in `.env`.
- Use strong values for Superset secret key and Airflow fernet key.
- Do not expose these ports to the public internet.

Local‑first does not mean “no security.” It means the threat model is smaller. Still take it seriously.

## Why not use a managed cloud stack?

You can. It will work. It will also lock you in.

DataSpec gives you ownership. You can run it anywhere. You can move it. You can understand it.

That is the trade‑off. That is why it exists.

## What this is not

- It is not a cloud service.
- It is not Kubernetes.
- It is not a generic PaaS.

It is a small, hard‑working stack for teams that want control.

## The point

DataSpec is not trying to be everything. It is trying to be reliable.

If you can run it on a box and it does the job, that is a win.

That is why it exists.

## Performance and sizing

This stack is built for small teams. That still means you should size it correctly.

Here are sane starting points:

- 4 vCPU / 16 GB RAM for light usage
- 8 vCPU / 32 GB RAM for heavier queries and bigger data
- SSD storage is not optional

Postgres is the hot path. Give it the best disk you have. If you are slow, you will feel it there first.

Airflow and Superset are CPU‑bound. They need enough CPU to serve pages and run tasks. They do not need huge RAM unless you throw huge datasets at them.

If you want more speed:

- Add indexes on high‑use columns.
- Use materialized views for common dashboards.
- Keep data types clean.

## Data quality and idempotency

dlt tracks pipeline state. That gives you idempotent loads if you design them that way.

The default NYC Taxi flow is a full refresh. It is simple and safe. It does not prove incremental logic.

If you add incremental sources, you should:

- Pick a clear cursor field.
- Store that cursor in dlt state.
- Avoid manual edits to the target tables.

Airflow retries failures. dlt can recover if the state is consistent. The failure you saw earlier is what happens when state files are missing. That is why we pin `DLT_HOME` to a mounted path.

## Configuration and secrets

The stack reads configuration from `.env`. That is standard Docker Compose behavior.

If you do nothing, it uses defaults. If you do something, you override.

The credentials file is there to make life easy. It reflects the current effective values. It is not used by the containers. It is for you.

Treat it like a secret. Do not publish it.

## What to change first

If you are adapting DataSpec to a real environment, here is the sane order:

1. Change passwords in `.env`.
2. Add your data source to Airflow.
3. Add the database in Superset.
4. Build one dashboard.
5. Add backup automation for `./data`.

Do not skip the backup step. It is the only part you will regret later.

## What is inside the Docker images

Airflow is built from the official base image. Superset is the official image. pgAdmin is official.

That is on purpose. You do not want a custom image for everything if you can avoid it.

We only build what we have to. That keeps upgrades simple.

## Upgrades

Upgrades are manual. 

A safe upgrade path looks like this:

1. Stop the stack.
2. Backup `./data`.
3. Pull new images.
4. Start the stack.
5. Verify Airflow and Superset migrations.

If you do this in a test environment first, you are doing it right.

## If you outgrow one node

At some point, you will outgrow a single machine. That is fine.

The model still helps you:

- Postgres can move to a dedicated box.
- Airflow can move to a separate node.
- Superset can scale horizontally if needed.

DataSpec is not a cage. It is a starting point.

## Local‑first is a discipline

The hardest part of local‑first is not technology. It is discipline.

You will be tempted to add cloud services. You will be tempted to add a vendor for “just one thing.”

If you do that, the stack stops being local‑first. That might be okay. Just be honest about it.

## A note on correctness vs. convenience

Small stacks are easy to change. That is power and risk.

If you edit tables by hand, you can break downstream dashboards. If you run ad‑hoc SQL on production tables, you can create subtle bugs.

The right answer is to treat Postgres as the system of record and push changes through Airflow or dlt when you can.

## Final word

DataSpec is not trying to impress you. It is trying to run.

If you want a stack you can understand end to end, this is it.

