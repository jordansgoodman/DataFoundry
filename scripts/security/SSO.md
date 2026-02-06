# SSO / OIDC Integration (Guidance)

## DataFoundry BI (Streamlit)
Streamlit does not ship with built-in OIDC. Recommended approach:
- Place an SSO gateway in front of NGINX (OIDC/OAuth proxy)
- Or integrate OIDC in the BI app if you want native auth

## Grafana (OAuth)
Grafana supports OAuth for most identity providers.
Recommended approach:
- Set `GF_AUTH_GENERIC_OAUTH_*` environment variables
- Disable basic auth and anonymous access

## NGINX (SSO Gateway)
Optional: Put an SSO gateway in front of NGINX if you want a single auth layer.

## Notes
- Keep local admin users for break‑glass access.
- Test login flows on a staging node before production.
