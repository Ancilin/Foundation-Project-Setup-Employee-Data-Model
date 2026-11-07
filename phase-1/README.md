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

## Handoff package

Shared deliverables and Day-2 handoff package for other teams:

- **Draft API contract**: [`docs/api-contract.md`](docs/api-contract.md)
- **Sample employee data (10 records)**: [`scripts/sample_employees.json`](scripts/sample_employees.json) (and [`docs/sample_employees.json`](docs/sample_employees.json), [`docs/sample_employees.csv`](docs/sample_employees.csv))
- **ER diagram**: [`docs/er-diagram.md`](docs/er-diagram.md)
- **Master dataset (Workbook 01)**: [`data/seed/01_LedgerForge_Python_Master_Dataset.xlsx`](data/seed/01_LedgerForge_Python_Master_Dataset.xlsx)
- **One-command seed script**: [`scripts/seed.py`](scripts/seed.py) (`python -m scripts.seed --reset`)
- **CSV exports (early exports)**: [`exports/`](exports/) (`employees.csv`, `salaries.csv`, `attendance.csv`, `departments.csv`, `roles.csv`)
- **Handoff Git Tag**: `handoff-day2`

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
- **Cycles in the hierarchy** longer than "own manager" are checked and prevented by `employee_service.py`.

## Employee & Team APIs (Task 3)

Layered CRUD and query endpoints with validation, pagination, filtering, search, and soft deletion.

### Endpoints

| Method | Path | Summary | Notes |
|---|---|---|---|
| `POST` | `/employees` | Create employee | Auto-assigns next `EMP-XXXX` if omitted; checks unique email, valid dates |
| `GET` | `/employees` | List employees | Query params: `page=1`, `size=20`, `department=D01`, `status=Active`, `q=name/email`, `include_inactive=false` |
| `GET` | `/employees/{id}` | Get employee | 200 with details or 404 |
| `PATCH` | `/employees/{id}` | Update employee | Partial update; checks email uniqueness & prevents hierarchy cycles |
| `DELETE` | `/employees/{id}` | Soft delete | Sets `is_active = false` (never erases historical records) |
| `GET` | `/employees/{id}/team` | Direct reports | Returns all employees reporting directly to this manager |
| `GET` | `/departments` | List departments | All 11 active departments |
| `GET` | `/departments/{id}/employees`| Department employees | All employees in a department |

### Error Format

All errors return a consistent JSON response:
```json
{
  "detail": "Description of the error",
  "error_code": "NOT_FOUND | CONFLICT | VALIDATION_ERROR | BAD_REQUEST"
}
```

### Quick Commands

```powershell
# Run all automated tests
.venv\Scripts\python -m pytest -v

# Seed or re-seed the full 745 employees from Excel
.venv\Scripts\python scripts\seed_from_dataset.py
```

## Master Dataset, Seed Pipeline & Early Exports (Task 4)

LedgerForge uses a realistic synthetic master dataset pipeline bridging foundational company structures with Faker-enriched employees, salaries, and attendance records.

### Dataset Source & Licensing

- **Base Dataset**: Derived from benchmark HR Analytics / Employee Attrition datasets (IBM HR Analytics benchmark dataset on Kaggle).
- **License**: Released under **Apache 2.0 / CC-BY 4.0** (Open Data Commons / Public Domain Dedication). Safe for enterprise research, educational benchmarking, and multi-domain model training.
- **Master Excel Source**: [`01_LedgerForge_Python_Master_Dataset.xlsx`](01_LedgerForge_Python_Master_Dataset.xlsx).

### Data Pipeline Architecture

1. **Faker Enrichment with Fixed Seed (`42`)**:
   - Ensures 100% deterministic, reproducible datasets across all machines, environments, and team runs.
   - Replaces placeholder identifiers with realistic human names, unique corporate emails (`first.last@ledgerforge.com`), valid dates, and phone numbers.
   - Eliminates "test123" dummy data.

2. **Linked Salary Structure**:
   - Every employee has a corresponding row in the `salaries` table.
   - Salary calculations (`monthly_gross`, `basic`, `hra`, `special_allowance`, `annual_ctc`) are mathematically anchored within their respective role's salary band (`band_min_annual` to `band_max_annual`).

3. **Linked Attendance History**:
   - Generates attendance logs spanning multiple calendar months.
   - Realistic distributions: ~85% `Present` (with check-in/check-out and overtime), ~5% `Leave`, ~4% `HalfDay`, ~3% `Late`, and ~3% `Absent`.
   - Every attendance record references a valid, existing `employee_id`.

4. **Idempotency & Two-Pass Hierarchy**:
   - Re-running the pipeline at any point is completely safe and causes no duplicate key conflicts.
   - Two-pass employee insertion ensures manager hierarchy self-referential foreign keys are resolved without constraint failures.

### Running the Seed Pipeline

One-command seed on the active PostgreSQL database:

```bash
# Seed all 5 tables (departments, roles, employees, salaries, attendance) and generate CSV exports
python -m scripts.seed
```

### CSV Exports

Export clean, linked CSV files for cross-domain usage (Data, AI/ML, Reporting):

```bash
python -m scripts.export_csv
```

Exported files are saved to the [`exports/`](exports/) directory:
- [`exports/employees.csv`](exports/employees.csv) (745 records)
- [`exports/salaries.csv`](exports/salaries.csv) (745 records)
- [`exports/attendance.csv`](exports/attendance.csv) (9,000+ records)
- [`exports/departments.csv`](exports/departments.csv) (11 departments)
- [`exports/roles.csv`](exports/roles.csv) (58 roles)

## Next

With realistic employees, salary grades, and attendance in place, **Task 5** protects APIs with authentication, role-based access control (RBAC), and permissions.

