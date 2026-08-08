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

### Local setup

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Configure environment:
   ```bash
   cp .env.example .env
   ```

3. Ensure PostgreSQL is running and matching `DATABASE_URL` in `.env`.

4. Run database migrations:
   ```bash
   uv run alembic upgrade head
   ```

5. Start the application:
   ```bash
   uv run uvicorn app.main:app --reload
   ```

The API will be available at `http://localhost:8000`, with a health check at `http://localhost:8000/health`.

### Docker Compose

Run PostgreSQL and the API (migrations will execute automatically before startup):

```bash
docker compose up --build
```

### Default Credentials

The initial migration creates these test accounts:

| Role | Email | Password |
| --- | --- | --- |
| User | `user@example.com` | `user-password` |
| Administrator | `admin@example.com` | `admin-password` |

### Testing & Code Quality

Run tests:
```bash
uv run pytest
```

Run linter:
```bash
uv run ruff check .
```

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
├── models/                # SQLAlchemy models
├── schemas/               # Pydantic schemas
├── services/              # Business logic
└── main.py                # FastAPI app entrypoint
```
