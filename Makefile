.PHONY: up down logs restart dev-venv

up:
	./bootstrap.sh

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

dev-venv:
	./scripts/dev/setup_venv.sh
