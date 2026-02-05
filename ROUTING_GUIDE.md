# Routing Guide (System Perspective)

This document provides a deep, system-level explanation of how traffic flows through DataFoundry: from the user’s browser, through NGINX, into internal services, and back again. It covers URL routing, proxy behavior, headers, application configuration, Docker networking, request lifecycles, authentication layers, caching, logs/metrics visibility, and failure modes.

---

## 1) External Entry Point

### 1.1 Single host, multiple apps
All user traffic enters through a single public host:
- `http://<host>/` (dev)
- `https://<host>/` (production TLS)

NGINX is the only service that exposes a host port. All other containers are internal only.

### 1.2 Why this matters
- **One DNS name** simplifies user access
- **Single TLS termination** point simplifies certificates
- **Centralized auth controls** (IP allowlist, SSO gateway, or basic auth)
- **Consistent URLs** for all UIs

---

## 2) Path-Based Routing in NGINX

### 2.1 URL map
NGINX routes on URL path prefixes:
- `/superset/` → Superset UI + API
- `/airflow/` → Airflow UI + API
- `/grafana/` → Grafana UI
- `/` → minimal status response

### 2.2 NGINX config (conceptual)
NGINX matches location blocks by prefix:

```
location /superset/ { proxy_pass http://superset-web:8088/; }
location /airflow/  { proxy_pass http://airflow-webserver:8080/; }
location /grafana/  { proxy_pass http://grafana:3000/; }
location /          { return 200 "DataFoundry is running."; }
```

The trailing slash after `proxy_pass` ensures that path prefixes are handled consistently.

### 2.3 Proxy headers
Each upstream receives proxy headers so it can reconstruct the original client request context:
- `Host`: original host (e.g., `analytics.mycompany.com`)
- `X-Real-IP`: client IP
- `X-Forwarded-For`: client IP chain
- `X-Forwarded-Prefix`: `/superset`, `/airflow`, or `/grafana`

These headers allow the app to:
- Render correct URLs
- Generate accurate redirects
- Log actual client IPs

---

## 3) Application Awareness of Reverse Proxy

### 3.1 Superset
Superset must generate links under `/superset/` rather than `/`.
This is controlled by:
- `SUPERSET_BASE_URL=http://<host>/superset`
- `WEBSERVER_BASEURL` in `superset_config.py`
- `ENABLE_PROXY_FIX=True`

If this is missing:
- Assets may 404
- Redirects may send users to `/login` instead of `/superset/login`

### 3.2 Airflow
Airflow’s UI generates links based on `AIRFLOW__WEBSERVER__BASE_URL`.
Required settings:
- `AIRFLOW__WEBSERVER__BASE_URL=http://<host>/airflow`
- `AIRFLOW__WEBSERVER__ENABLE_PROXY_FIX=true`

If misconfigured:
- Links and static assets break
- Login redirects fail

### 3.3 Grafana
Grafana must render under `/grafana/`:
- `GF_SERVER_ROOT_URL=%(protocol)s://%(domain)s/grafana/`
- `GF_SERVER_SERVE_FROM_SUB_PATH=true`

If misconfigured:
- Grafana assets resolve to `/public/...` and 404

---

## 4) Docker Networking and Service Discovery

### 4.1 Docker network `df`
All services are on the same internal Docker network `df`.
No direct host ports are exposed except NGINX (80) and optionally Grafana if you choose.

### 4.2 Service discovery by name
Inside the network, containers resolve each other by service name:
- `superset-web`
- `airflow-webserver`
- `grafana`
- `postgres`
- `redis`
- `prometheus`

NGINX uses these names to proxy to upstreams.

### 4.3 Internal vs external view
- **External**: users only see `http(s)://<host>/...`
- **Internal**: services only see each other via `http://service:port`

---

## 5) Request Lifecycle: Superset Example (Detailed)

### 5.1 Browser initiates request
User visits:
```
https://analytics.mycompany.com/superset/
```

### 5.2 NGINX accepts TCP
- TLS terminates at NGINX (if enabled)
- NGINX selects `/superset/` location block
- NGINX sets proxy headers

### 5.3 NGINX forwards
NGINX sends the request to `superset-web:8088` over the Docker network.

### 5.4 Superset processes
Superset:
- Parses headers (`X-Forwarded-*`)
- Checks auth session
- Executes SQL against Postgres if needed
- Returns HTML and asset references

### 5.5 Browser asset loading
Browser requests:
```
/superset/static/...
/superset/api/v1/...
```

NGINX proxies each to Superset with the same headers.

---

## 6) Request Lifecycle: Airflow Example (Detailed)

### 6.1 UI request
User visits:
```
https://analytics.mycompany.com/airflow/
```

### 6.2 NGINX routing
NGINX proxies to `airflow-webserver:8080`.

### 6.3 Airflow webserver
Airflow webserver:
- Reads base URL from `AIRFLOW__WEBSERVER__BASE_URL`
- Generates absolute links and redirects
- Reads metadata from Postgres

### 6.4 DAG views
The UI calls back to `/airflow/api/v1/...` for DAG metadata.
NGINX proxies those as well.

---

## 7) Request Lifecycle: Grafana Example (Detailed)

### 7.1 UI request
User visits:
```
https://analytics.mycompany.com/grafana/
```

### 7.2 NGINX routing
NGINX proxies to `grafana:3000`.

### 7.3 Grafana rendering
Grafana uses its root URL and subpath settings to:
- Render correct asset URLs
- Fetch dashboards and queries via `/grafana/api/...`

---

## 8) Security Layers (Edge and App)

### 8.1 Edge security (NGINX)
NGINX can enforce:
- TLS termination
- IP allowlists
- Basic auth
- SSO gateway upstream

This is recommended because it applies uniformly to all apps.

### 8.2 Application auth
Each app has its own auth and RBAC:
- Superset: admin/analyst/viewer
- Airflow: admin/user/viewer
- Grafana: admin/editor/viewer

App auth is still necessary for auditability and fine-grained access.

---

## 9) Internal Data and Task Flow

This is not HTTP routing, but it impacts what routes are exercised.

### 9.1 Airflow → dlt
Airflow triggers the dlt pipeline, which loads data into Postgres.

### 9.2 Superset → Postgres
Superset queries Postgres for dashboards and charts.

### 9.3 Redis usage
- Superset caches query results
- Airflow uses Redis as Celery broker

---

## 10) Logs and Metrics Visibility

### 10.1 Logs
- Container logs → Promtail → Loki
- Grafana queries Loki for log panels

If routing fails, NGINX logs will show upstream errors.

### 10.2 Metrics
- Node Exporter → Prometheus → Grafana
- Airflow StatsD → StatsD Exporter → Prometheus → Grafana

---

## 11) Failure Modes and Diagnosis

### 11.1 404 on assets
**Likely cause**: wrong base URL or missing forwarded prefix.

**Fix**:
- Confirm `SUPERSET_BASE_URL`, `AIRFLOW__WEBSERVER__BASE_URL`, Grafana root URL
- Confirm NGINX sets `X-Forwarded-Prefix`

### 11.2 Redirect loops
**Likely cause**: app thinks it is hosted at `/` instead of `/superset/` or `/airflow/`.

### 11.3 502 Bad Gateway
**Likely cause**: upstream container down or wrong service name/port.

### 11.4 CORS errors
**Likely cause**: base URL mismatch or mixed http/https.

---

## 12) TLS Routing (Production)

### 12.1 HTTP → HTTPS redirect
NGINX handles this:
- Port 80 returns a redirect to HTTPS

### 12.2 Certificates
Certs are mounted into NGINX and referenced in the TLS config.

### 12.3 Base URLs
All base URLs must be updated to `https://<host>/...`.

---

## 13) Practical Debug Checklist

1. Check NGINX is up:
   - `curl http://<host>/`
2. Check NGINX routes:
   - `curl -I http://<host>/superset/`
   - `curl -I http://<host>/airflow/`
   - `curl -I http://<host>/grafana/`
3. Confirm base URLs in `.env`
4. Check upstream container health:
   - `docker compose ps`
5. Inspect NGINX logs:
   - `docker compose logs -f nginx`

---

## 14) Summary

- **NGINX is the system edge.**
- **Path-based routing** provides a single URL space for all apps.
- **Proxy headers + app base URLs** are critical for correct operation.
- **Docker networking** isolates internal services from external exposure.
- **Logs + metrics** make routing issues observable.
