.PHONY: help up down restart build logs migrate seed seed-synthetic clean test lint backend-shell db-shell

help:
	@echo "India Trade Analytics — make targets"
	@echo ""
	@echo "  make up              Start everything (Postgres, backend, frontend)"
	@echo "  make down            Stop everything"
	@echo "  make restart         Restart all services"
	@echo "  make build           Rebuild containers"
	@echo "  make logs            Tail logs"
	@echo "  make migrate         Run DB migrations inside backend"
	@echo "  make seed            Run idempotent dim/admin seed inside backend"
	@echo "  make seed-synthetic  Insert synthetic trade data (so dashboards have data)"
	@echo "  make clean           Stop and DELETE the database volume"
	@echo "  make test            Run backend tests"
	@echo "  make backend-shell   Bash inside backend container"
	@echo "  make db-shell        psql inside Postgres container"

up:
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose restart

build:
	docker compose build

logs:
	docker compose logs -f --tail=200

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m app.seeds.run

seed-synthetic:
	docker compose exec backend python -m app.seeds.synthetic_trade

clean:
	docker compose down -v

test:
	docker compose exec backend pytest

lint:
	docker compose exec backend ruff check .
	docker compose exec frontend npm run lint || true

backend-shell:
	docker compose exec backend bash

db-shell:
	docker compose exec postgres psql -U trade -d india_trade
