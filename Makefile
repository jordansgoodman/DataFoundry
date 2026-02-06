.PHONY: up down logs restart

up:
	./bootstrap.sh

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=200
