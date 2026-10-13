# LedgerForge API

Foundation (Task 1) for the LedgerForge employee/payroll backend: a layered **FastAPI** app with
settings from environment variables, tests, and **Docker Compose** running the API with **PostgreSQL**.

## Project layout

```
app/
  main.py            # app factory / entry point (uvicorn app.main:app)
  api/               # HTTP layer: routers only (parse request -> call service -> return schema)
    router.py        #   collects all routers
    routes/health.py #   GET /health
  services/          # business logic (no HTTP, no SQL details leaking out)
  models/            # SQLAlchemy models (Task 2 adds employee tables)
  schemas/           # Pydantic request/response models
  db/                # engine + session dependency
  core/config.py     # pydantic-settings: reads env vars / .env
tests/               # pytest
docs/                # draft API contract + sample data
scripts/             # helper scripts (sample-data generator)
Dockerfile, docker-compose.yml, .env.example
```

Request flow: **route → service → model/DB**. Routes never contain business rules; services never
know about HTTP.

## Prerequisites

Python 3.12, Git, Docker (Docker Desktop must be **running**).

## Run with Docker (one command)

```bash
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
# edit .env: set a real POSTGRES_PASSWORD and SECRET_KEY
docker compose up --build
```

- API: <http://localhost:8000/health> → `{"status": "ok"}`
- Interactive docs: <http://localhost:8000/docs>
- Stop: `Ctrl+C`, then `docker compose down` (add `-v` to also delete the database volume).

> Inside Compose the API reaches Postgres at host **`db`** (the service name), not `localhost`.
> `docker-compose.yml` builds `DATABASE_URL` for the container from the `POSTGRES_*` values.

## Run tests (locally)

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Tests set fake `DATABASE_URL`/`SECRET_KEY` values themselves, so no `.env` or database is needed.

## Run the API without Docker

```bash
pip install -r requirements.txt
# .env must exist (see above); DATABASE_URL should point at localhost if you run Postgres yourself
uvicorn app.main:app --reload
```

## Configuration

All settings come from environment variables (or `.env`), see [`.env.example`](.env.example).

| Variable | Purpose |
|----------|---------|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credentials for the `db` container |
| `DATABASE_URL` | SQLAlchemy URL (Compose overrides the host to `db`) |
| `SECRET_KEY` | Signing key (min. 16 chars); generate a random one |
| `DEBUG` | `true`/`false` |

`.env` is git-ignored. Never commit real secrets.

## For other teams

- Draft API contract: [`docs/api-contract.md`](docs/api-contract.md)
- Sample fake data (10 employees): [`docs/sample_employees.json`](docs/sample_employees.json),
  [`docs/sample_employees.csv`](docs/sample_employees.csv)
- Regenerate the sample from the dataset:
  `python scripts/make_sample_data.py 01_LedgerForge_Python_Master_Dataset.xlsx`

## Next

Task 2 creates the employee tables in this database.
