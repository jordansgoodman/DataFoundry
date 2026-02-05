.PHONY: up down logs restart init

up:
	./bootstrap-dev.sh

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200

init:
	docker compose run --rm superset-web /app/scripts/init.sh
