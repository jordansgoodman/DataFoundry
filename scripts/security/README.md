# Security Hardening Notes

## Required Before Production
- Change all default credentials in `.env`.
- Set strong `SUPERSET_SECRET_KEY` and `AIRFLOW__CORE__FERNET_KEY`.
- Enable TLS on NGINX and provide valid certificates.
- Restrict access to `/airflow/`, `/grafana/`, and `/superset/` (IP allowlist or SSO).

## TLS Setup (Recommended)
1. Create or obtain TLS certs:
   - `scripts/security/tls/fullchain.pem`
   - `scripts/security/tls/privkey.pem`
2. Replace `scripts/nginx/nginx.conf` with `scripts/security/nginx.tls.conf`.
3. Restart NGINX.

## Optional Basic Auth
For a simple shield, add basic auth at NGINX level by using `auth_basic` and an htpasswd file.

## Optional IP Allowlist
To restrict access by IP:
1. Use `scripts/security/nginx.allowlist.conf` as a template.
2. Add `include /etc/nginx/allowlist.conf;` inside the TLS server block.
3. Mount the allowlist file into the NGINX container.

## Docker Socket Exposure
Promtail needs access to the Docker socket to read container labels and logs.
If you want to avoid mounting the socket, switch to file-based log scraping and drop container discovery.
