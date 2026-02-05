# DataFoundry

Local-first, self-hosted analytics stack with one-command install.

## What this is
- Single-node analytics appliance
- Docker Compose runtime
- Ansible-managed host setup
- Opinionated defaults, minimal config

## Quick start
1. Copy `.env.example` to `.env` and fill in values.
2. Run `./bootstrap.sh`.

The bootstrap script installs Docker (via Ansible), brings up services, and runs first-run initialization.

## Structure
- `bootstrap.sh` one-command installer
- `ansible/` host configuration and deploy
- `docker-compose.yml` runtime services
- `scripts/` init and bootstrap helpers

## Notes
- Host Python is used only for Ansible.
- All analytics tooling runs in containers.
