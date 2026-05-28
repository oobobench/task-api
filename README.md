# task-api

FastAPI task management API with JWT auth, PostgreSQL, and an optional Redis cache.

## Quick start (Docker)

Prerequisites: Docker with the Compose plugin.

```sh
cp .env.example .env
docker compose up --build
```

The app entrypoint runs `alembic upgrade head` before starting, so the schema is
ready by the time the API serves traffic. Once the stack is healthy:

- API: http://localhost:8000
- Health check: http://localhost:8000/health
- OpenAPI docs: http://localhost:8000/docs

Stop with `docker compose down`, or `docker compose down -v` to also drop the
postgres and redis volumes.

## Configuration

All configuration is read from environment variables. See
[`.env.example`](.env.example) for the full list. Key variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy URL used by the app and Alembic. |
| `REDIS_URL` | Redis URL used by the optional task cache. |
| `CACHE_ENABLED` | `true` to enable the Redis-backed cache. |
| `TASK_API_SECRET_KEY` | JWT signing key — **change in production**. |
| `APP_PORT` / `POSTGRES_PORT` / `REDIS_PORT` | Host port bindings. |

## Makefile

Common workflows are wrapped in `make` targets:

```sh
make build      # build the app image
make up         # start app + postgres + redis
make down       # stop the stack
make logs       # tail logs
make migrate    # alembic upgrade head
make revision M="add foo"  # generate a new revision
make test       # run pytest inside the app container
make psql       # open a psql session
make clean      # down + remove volumes
```

Run `make help` to see all targets.

## Local development (without Docker)

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=sqlite:///./tasks.db
alembic upgrade head
uvicorn main:app --reload
```

Tests use an ephemeral SQLite database and do not require Postgres or Redis:

```sh
pytest -q
```
