.PHONY: env creds up down logs restart dev-venv

env:
	python3 ./scripts/setup/generate_env.py

creds: env

up: env
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

dev-venv:
	./scripts/dev/setup_venv.sh
