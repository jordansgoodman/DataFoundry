# Governance And Access

## DataFoundry BI
- Current: Admin-only login (RBAC roadmap)
- Plan: Admin/Analyst/Viewer roles and dataset-level permissions

## Airflow
- Use built-in RBAC (Admin, User, Viewer)
- Restrict DAG editing to Admins
- Use environment variables for credentials

## Audit Notes
- Review access logs in NGINX and Grafana
- Keep backups for compliance as required
