# Governance And Access

## Superset
- Default roles: Admin, Analyst, Viewer
- Use dataset-level permissions for `analytics` schema
- Keep SQL Lab access limited to analysts

## Airflow
- Use built-in RBAC (Admin, User, Viewer)
- Restrict DAG editing to Admins
- Use environment variables for credentials

## Audit Notes
- Review access logs in NGINX and Grafana
- Keep backups for compliance as required
