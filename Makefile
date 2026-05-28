COMPOSE ?= docker compose

.PHONY: help build up down logs ps test migrate revision shell psql redis-cli clean

help:
	@echo "Available targets:"
	@echo "  build     - Build the app image"
	@echo "  up        - Start app, postgres, and redis"
	@echo "  down      - Stop and remove containers"
	@echo "  logs      - Tail logs from all services"
	@echo "  ps        - Show service status"
	@echo "  migrate   - Run alembic upgrade head inside the app container"
	@echo "  revision  - Generate a new alembic revision (use M=\"msg\")"
	@echo "  test      - Run pytest inside the app container"
	@echo "  shell     - Open a shell in the app container"
	@echo "  psql      - Open a psql session against the postgres service"
	@echo "  redis-cli - Open redis-cli against the redis service"
	@echo "  clean     - Stop containers and remove volumes"

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

migrate:
	$(COMPOSE) run --rm app alembic upgrade head

revision:
	$(COMPOSE) run --rm app alembic revision --autogenerate -m "$(M)"

test:
	$(COMPOSE) run --rm -e DATABASE_URL=sqlite:///./test.db -e CACHE_ENABLED=false app pytest -q

shell:
	$(COMPOSE) exec app sh

psql:
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-task_api} -d $${POSTGRES_DB:-task_api}

redis-cli:
	$(COMPOSE) exec redis redis-cli

clean:
	$(COMPOSE) down -v
