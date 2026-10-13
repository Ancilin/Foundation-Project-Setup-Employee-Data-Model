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
  models/            # SQLAlchemy models: Department, Role, Employee (Task 2)
  schemas/           # Pydantic request/response models
  db/                # engine + session dependency
  core/config.py     # pydantic-settings: reads env vars / .env
migrations/          # Alembic migrations (versions/0001_create_employee_tables.py)
tests/               # pytest (health, constraints, hierarchy, migrations)
docs/                # ER diagram, draft API contract, sample data
scripts/             # helper scripts (sample-data generator)
Dockerfile, docker-compose.yml, alembic.ini, .env.example
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

- ER diagram: [`docs/er-diagram.md`](docs/er-diagram.md)

## Database & migrations (Task 2)

Tables: `departments`, `roles`, `employees` (full diagram, constraints and indexes in
[`docs/er-diagram.md`](docs/er-diagram.md)). Every table has `is_active` (soft delete),
`created_at`, `updated_at`. `employees.manager_id` points to another employee (the hierarchy).

**Apply the migration inside Docker** (stack must be up: `docker compose up -d --build`):

```bash
docker compose exec api alembic upgrade head      # build the schema from scratch
docker compose exec api alembic current           # which revision is applied
docker compose exec api alembic downgrade base    # roll back everything
docker compose exec db psql -U ledgerforge -d ledgerforge -c "\dt"   # list tables
```

Locally (needs `.env` and a reachable database): `alembic upgrade head`.
After changing a model, create a new migration: `alembic revision --autogenerate -m "describe change"`
and **review the generated file** before applying it.

### Design decision: one role per employee, not many

An employee has **one current role** (`employees.role_id`), not a many-to-many `employee_roles` table.

- **The data says so:** in the dataset every employee has exactly one `role_id` at a time. Changes
  (promotion, transfer) are *sequential* history, not simultaneous roles.
- **Payroll and reports need an unambiguous answer** to "what is this person's grade/salary band?".
  With many simultaneous roles every payroll, leave-approval and headcount query would need a rule
  to pick one, and double counting becomes easy.
- **Simpler schema:** a single foreign key, one join, one index.
- **History is still possible later:** if Task N needs promotion history, add an
  `employee_assignments` table (the dataset already has one: `effective_from`, `effective_to`,
  `role_id`, `manager_id`) *in addition to* the current role. That is an additive migration;
  switching from many-to-many back to one role would not be.

Trade-off accepted: someone who genuinely does two jobs at once must be modelled by their primary role.

### Other design choices

- **Natural string keys** (`EMP-0001`, `D01`, `R002`): the dataset uses the same codes in every sheet and
  workbook, so other teams can join on them directly.
- **Enums as `VARCHAR` + `CHECK`**, not PostgreSQL `ENUM`: adding a value is a simple constraint change
  instead of a hard-to-reverse type change.
- **No cascading deletes**: the database refuses to delete a department, role or manager that is still
  referenced. Use `is_active = false`.
- **Cycles in the hierarchy** longer than "own manager" are not blocked by the DB; Task 3's service layer must check.

## Next

Task 3 puts a CRUD API on top of these tables.
