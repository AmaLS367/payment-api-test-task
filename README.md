# payment-api

FastAPI backend scaffold with async SQLAlchemy, PostgreSQL, and Alembic. Dependency and environment management is handled entirely by [uv](https://docs.astral.sh/uv/).

## Tech stack

- Python 3.12+
- FastAPI
- PostgreSQL + SQLAlchemy 2.x (async) + asyncpg
- Alembic (async migrations)
- Pydantic v2 / pydantic-settings
- pytest + pytest-asyncio
- Ruff
- Docker / Docker Compose

## Getting started

### Install dependencies

```bash
uv sync
```

### Configure environment

```bash
cp .env.example .env
```

### Run locally

Requires a running PostgreSQL instance matching `DATABASE_URL` in `.env`.

```bash
uv run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`, with a health check at `http://localhost:8000/health`.

### Run tests

```bash
uv run pytest
```

### Run Ruff

```bash
uv run ruff check .
```

### Run database migrations

```bash
uv run alembic upgrade head
```

To generate a new migration after adding/changing models:

```bash
uv run alembic revision --autogenerate -m "description"
```

### Run with Docker Compose

```bash
docker compose up --build
```

This starts PostgreSQL and the API, with the API waiting for the database healthcheck to pass.

## Project structure

```text
app/
├── api/
│   ├── deps.py          # Shared FastAPI dependencies
│   └── routes/          # Route modules (auth, users, admin, webhooks)
├── core/
│   ├── config.py        # Pydantic settings
│   └── security.py      # Password hashing / JWT helpers
├── db/
│   ├── base.py           # Declarative base
│   └── session.py        # Async engine + session factory
├── models/                # SQLAlchemy models (placeholders)
├── schemas/               # Pydantic schemas (placeholders)
├── services/              # Business logic (placeholders)
└── main.py                # FastAPI app entrypoint
```

## Next steps

- Implement the `User`, `Account`, and `Payment` SQLAlchemy models and generate the initial Alembic migration.
- Implement Pydantic schemas for those models.
- Implement JWT login/refresh flow in `app/api/routes/auth.py` using the helpers in `app/core/security.py`.
- Add `get_current_user` dependency in `app/api/deps.py` once auth is implemented.
- Implement user, admin, and payment webhook endpoint logic.
- Add CRUD/service-layer functions as real business logic is introduced.
