# SSO / OIDC Integration (Guidance)

## Superset (OIDC)
Superset supports OIDC via its security manager and config overrides.
Recommended approach:
- Configure an OIDC provider (Okta, Auth0, Azure AD)
- Set OIDC client ID/secret
- Enable `AUTH_OID` and configure provider settings in `superset_config.py`

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
