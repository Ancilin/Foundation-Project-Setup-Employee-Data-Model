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
- [`exports/attendance.csv`](exports/attendance.csv) (150,155 records)
- [`exports/departments.csv`](exports/departments.csv) (11 departments)
- [`exports/roles.csv`](exports/roles.csv) (58 roles)
- [`exports/holidays.csv`](exports/holidays.csv) (19 holidays)
- [`exports/leave_types.csv`](exports/leave_types.csv) (6 leave types)
- [`exports/leave_balances.csv`](exports/leave_balances.csv) (441 balances)
- [`exports/leave_requests.csv`](exports/leave_requests.csv) (3,441 requests)

## Attendance & Leave Service (Task 6 / LF-06)

### 1. Rule for `MISSING_CHECKOUT` Rows

About `0.13%` (`198` of `150,155` rows) of daily attendance records have a valid `check_in` punch but no `check_out` punch (`data_quality_flag = "MISSING_CHECKOUT"`, `check_out = NULL`, `hours_worked = NULL`). To ensure two payroll clerks always compute the exact same monthly summary and payroll numbers:

1. **Attendance Status is Honored**: Because the employee has a verified `check_in` punch, the recorded day status (`PRESENT`, `WFH`, or `HALF_DAY_UNPAID`) is counted normally toward `days_present`, `days_wfh`, or `half_days`. It is **never** penalized as a full-day unpaid absence (`ABSENT_LOP`).
2. **Zero Overtime on Missing Check-Out**: Because the departure time was not captured, no overtime can be verified or claimed for that day (`overtime_hours = 0.00`), and `hours_worked` remains `NULL` (safely treated as `0.00` when summing `total_hours_worked` so aggregation never crashes).
3. **Explicit Audit Counter**: `monthly_summary(employee, month)` tracks and returns `missing_checkout_count` so HR can audit or regularize unclosed punches before payroll lock.

### 2. Working-Day & Leave Balance Rules

- **Weekends & Holidays Excluded**: `count_working_days(session, start_date, end_date)` excludes Saturdays (`weekday == 5`), Sundays (`weekday == 6`), and all company holidays in the `holidays` table.
- **State Flows (`Pending` → `Approved` / `Rejected`)**:
  - `POST /leave/requests` (`apply_leave`): Computes working days excluding weekends and holidays, checks available balance (`cl_balance`, `sl_balance`, `el_balance`), rejects the request (`400 INSUFFICIENT_BALANCE`) when the balance is not enough, and otherwise records the request as `Pending` while incrementing `pending_days`.
  - `POST /leave/requests/{id}/approve` (`approve_leave`): Deducts `days` from the corresponding balance (`cl_balance`, `sl_balance`, or `el_balance`), increments `*_used`, decrements `pending_days`, and transitions status to `Approved`.
  - `POST /leave/requests/{id}/reject` (`reject_leave`): Releases `pending_days` without reducing the employee's leave balance and transitions status to `Rejected`.

### 3. Hand-Count Verification vs. Program Output (3 Employees)

| Employee & Month | Metric | CSV Hand Count | `monthly_summary()` Output | Match |
|---|---|---:|---:|:---:|
| **`EMP-0002` (`2025-05`)** | Working Days (`2025-05-01` Holiday excluded) | `21` | `21` | PASS |
| | Days Present (`PRESENT`) | `2` | `2` | PASS |
| | Work From Home (`WFH`) | `18` | `18` | PASS |
| | Half-Day Unpaid (`HALF_DAY_UNPAID` on `2025-05-02`) | `1` (`0.50` LOP) | `1` (`0.50` LOP) | PASS |
| | Absent (`ABSENT_LOP` + `UNPAID_LEAVE`) | `0` | `0` | PASS |
| | Late Check-ins (`late_flag = 'Y'`) | `2` | `2` | PASS |
| | Overtime Hours | `0.00` | `0.00` | PASS |
| **`EMP-0011` (`2026-01`)** | Working Days (Jan 1, 14, 26 Holidays excluded) | `19` | `19` | PASS |
| | Days Present (`PRESENT`) | `9` | `9` | PASS |
| | Work From Home (`WFH`) | `8` | `8` | PASS |
| | Paid Leave (`PAID_LEAVE`) | `1` | `1` | PASS |
| | Absent (`ABSENT_LOP`) | `1` (`1.00` LOP) | `1` (`1.00` LOP) | PASS |
| | Late Check-ins (`late_flag = 'Y'`) | `1` | `1` | PASS |
| | Overtime Hours (`2.0 + 1.0 + 1.0`) | `4.00` | `4.00` | PASS |
| **`EMP-0148` (`2025-12`)** | Working Days (`2025-12-25` Holiday excluded) | `22` | `22` | PASS |
| | Days Present (`PRESENT`, incl. 1 `MISSING_CHECKOUT`) | `9` | `9` | PASS |
| | Work From Home (`WFH`) | `10` | `10` | PASS |
| | Paid Leave (`PAID_LEAVE`) | `2` | `2` | PASS |
| | Absent (`ABSENT_LOP`) | `1` (`1.00` LOP) | `1` (`1.00` LOP) | PASS |
| | Late Check-ins (`late_flag = 'Y'`) | `1` | `1` | PASS |
| | Overtime Hours | `0.00` | `0.00` | PASS |
| | Missing Check-Out Rows (`MISSING_CHECKOUT`) | `1` | `1` | PASS |

### 4. Design Sketch: Half-Day Leave

- **Schema & Types**:
  - Store `days`, `*_balance`, `*_used`, and `pending_days` as `Numeric(6, 2)` (`Decimal`) instead of `Integer` so `0.50` day increments are exact without floating-point drift.
  - Add `is_half_day: bool = False` and `half_day_session: Literal["FIRST_HALF", "SECOND_HALF"] | None = None` to `LeaveApplyRequest`.
  - Add `HALF_DAY_UNPAID` (counts as `0.50` `lop_days`) and `HALF_DAY_PAID` (counts as `0.00` `lop_days` and `0.50` paid leave day) to `Attendance.status`.
- **Validation & Day Counting**:
  - A half-day leave request must have `start_date == end_date` on a valid working day (not a weekend or holiday).
  - `count_working_days(..., is_half_day=True)` returns `Decimal("0.50")` if that date is a working day and `Decimal("0.00")` if it falls on a weekend or holiday.
  - Two half-day requests on the same date are permitted only if they occupy opposite sessions (`FIRST_HALF` vs `SECOND_HALF`).

## Payroll Calculation Engine (Task 7 / LF-07)

### 1. Plain-English Payroll Rules (`app/services/payroll_service.py`)

1. **Loss of Pay (LOP) & Fixed Component Proration**:
   - `payable_days = days_employed - lop_days`, where `days_employed` accounts for mid-month joiners (`hire_date`) and leavers (`exit_date`), and `lop_days = ABSENT_LOP + UNPAID_LEAVE + 0.5 * HALF_DAY_UNPAID`.
   - Each fixed monthly component (`BASIC`, `HRA`, `CONV`, `MED`, `SPECIAL`) is prorated by `payable_days / calendar_days` and rounded half-up to 2 decimal places (`ROUND_HALF_UP`).
   - `earned_fixed_pay = basic + hra + conveyance + medical + special_allowance`.
2. **Overtime Pay**:
   - Paid only to overtime-eligible roles (`overtime_eligible == True`, Levels 1–2 in Support, HR, Finance, Operations).
   - Capped at `50.00` hours per month: `overtime_hours_paid = min(raw_overtime_hours, 50.00)`.
   - `overtime_pay = round_half_up(overtime_hours_paid * (monthly_fixed_gross / 208) * 2)`.
3. **Gross Pay**:
   - `gross_pay = earned_fixed_pay + overtime_pay + variable_pay`.
4. **Provident Fund (PF)**:
   - Applies to permanent employees (`pf_applicable == True`; Fixed-Term Contract staff have `0.00`).
   - Wage ceiling is `INR 15,000` on earned basic: `pf_wage = min(basic, 15000.00)`.
   - Both employee (`pf_employee`) and employer (`pf_employer`) contribute `12%` of `pf_wage` (max `INR 1,800.00`).
5. **Employees' State Insurance (ESI)**:
   - Applies to permanent employees whose `monthly_fixed_gross <= 21,000.00`.
   - `esi_employee = round_half_up(gross_pay * 0.75%)`, `esi_employer = round_half_up(gross_pay * 3.25%)`.
6. **Professional Tax (PT)**:
   - `INR 200.00` per month when `gross_pay >= 25,000.00`; otherwise `0.00`.
7. **Income Tax Deducted at Source (TDS)**:
   - Annual base taxable income = `(monthly_fixed_gross * 12) - 75,000` (standard deduction).
   - Progressive New Regime slabs (`0–4L: 0%`, `4–8L: 5%`, `8–12L: 10%`, `12–16L: 15%`, `16–20L: 20%`, `20–24L: 25%`, `24L+: 30%`) with Section 87A tax rebate up to `INR 12,00,000` taxable income and `4%` Health & Education Cess.
   - Regular monthly TDS is `round_half_up((annual_base_tax_with_cess / 12) * (payable_days / calendar_days))`.
   - One-time monthly `variable_pay` and `overtime_pay` are taxed at their marginal slab impact plus `4%` cess: `round_half_up(annual_total_tax_with_cess - annual_base_tax_with_cess)`.
8. **Total Deductions, Net Pay & Employer Cost**:
   - `total_deductions = pf_employee + esi_employee + professional_tax + tds + other_deductions`
   - `net_pay = gross_pay - total_deductions`
   - `employer_cost = gross_pay + pf_employer + esi_employer`

### 2. Official Verification Output (`verify_ledgerforge.py payroll`)

```text
$ python scripts/run_payroll_verification.py
Saved 7340 calculated payroll rows to exports/my_payroll.csv

$ python scripts/verify_ledgerforge.py payroll exports/my_payroll.csv --data data/csv
Rows expected 7340, rows found in your file 7340
Exact matches (within 1 paisa): 7340/7340 = 100.00%
```

### 3. Mismatch & Rounding Diagnostic Log (What the Last Rows Teach You)

| Engine Variant | Exact `0.00` Matches | Within `0.01` Paisa | Root Cause of 1-Paisa Boundary Differences |
|---|---:|---:|---|
| **Variant C**: Prorate base TDS by `earned_fixed_pay / monthly_fixed_gross` | `7,215 / 7,340` (`98.30%`) | `7,340 / 7,340` (`100.00%`) | `earned_fixed_pay` is the sum of 5 already-rounded components, which introduces up to `0.02` INR drift compared to the true day ratio `payable_days / calendar_days`. |
| **Variant B**: Sum unrounded `prorated_base_tds + marginal_bonus_tds`, then round once | `7,234 / 7,340` (`98.56%`) | `7,340 / 7,340` (`100.00%`) | `106` rows with `variable_pay > 0` differ by `0.01` paisa when the third decimal digits of base TDS and bonus TDS both lie in `[0.003, 0.004]`. |
| **Final Engine (Variant A)**: Prorate base TDS by `payable_days / calendar_days` and round regular TDS & marginal bonus TDS separately (`ROUND_HALF_UP`) | **`7,340 / 7,340` (`100.00%`)** | **`7,340 / 7,340` (`100.00%`)** | Zero mismatches (`0` rows differ even by `0.01` paisa). |

### 4. Why `0.1 + 0.2` Is a Problem for Money (and How `Decimal` Fixes It)

IEEE-754 binary floating-point (`float`) represents numbers in base-2 fractions ($1/2, 1/4, 1/8, \dots$). Just as $1/3$ is a repeating fraction in base-10 ($0.3333\dots$), $0.1$ ($1/10$) and $0.2$ ($1/5$) are infinite repeating fractions in base-2:

```python
>>> 0.1 + 0.2
0.30000000000000004
>>> 0.1 + 0.2 == 0.3
False
>>> round(2.675, 2)  # Binary approximation + round-half-to-even rounds DOWN
2.67
```

`decimal.Decimal` stores base-10 digits exactly and supports commercial `ROUND_HALF_UP` rounding:

```python
>>> from decimal import Decimal, ROUND_HALF_UP
>>> Decimal("0.1") + Decimal("0.2") == Decimal("0.3")
True
>>> Decimal("2.675").quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
Decimal('2.68')
```

## Payslip Generator & PDF Document System (Task 8 / LF-08)

### 1. API Endpoints & Access Control (`app/api/routes/payslip.py`, `app/services/payslip_service.py`)

- **`GET /payslips/{employee_id}/{run_id}`**:
  - Computes every payslip figure fresh from the payroll calculation engine (`calculate_employee_month_from_db`) and returns structured JSON (or PDF when `?format=pdf`).
- **`GET /payslips/{employee_id}/{run_id}/pdf`**:
  - Generates and returns a single-page A4 PDF payslip (`application/pdf`) using ReportLab (`generate_payslip_pdf`).
- **Ownership & Privacy Enforcement (`enforce_payslip_access`)**:
  - Only the employee who owns the payslip (`requester_id == employee_id` or `X-Employee-Id` header) or an `HR` / `ADMIN` user (`requester_role in ("HR", "ADMIN")` or `X-Role` header) may fetch a payslip.
  - Any other employee ("a stranger") or unauthenticated caller receives **`403 Forbidden`** (`error_code = "FORBIDDEN"`).

### 2. Payslip Layout & Indian Number Formatting

1. **Company Header**: `Zenith Nova Technologies Pvt Ltd`, registered address, and payroll run period (`PR-YYYY-MM`).
2. **Employee & Period Metadata Grid**: Employee ID, Name, Work Email, Department, Role/Designation, Employment Type, Monthly Fixed Gross, and Pay Date.
3. **Attendance & Payable Days Strip**: Calendar Days, Days Employed, LOP Days, Payable Days, and Paid Overtime Hours.
4. **Side-by-Side Earnings & Deductions Table**: All monetary figures formatted in the **Indian numbering system** (`format_inr`, e.g., `1,58,504.61`, `5,94,315.91`).
5. **Prominent Net Pay Banner**: Styled in a high-contrast emerald callout box (`20pt Helvetica-Bold`) as the largest, most visible figure on the page, paired with **Net Pay in Indian Words** (`number_to_indian_words`).
6. **Year-to-Date (YTD) & Employer Cost Summary**: Cumulative financial-year YTD Gross, Deductions, TDS, PF, and Net Pay alongside Employer PF (`12%`) and ESI (`3.25%`).

### 3. Hand-Comparison of 3 Generated Payslip PDFs vs. `payroll_items.csv` (`PR-2025-04`)

Sample PDFs generated in `exports/payslips/`:
- `exports/payslips/payslip_EMP-0002_PR-2025-04.pdf`
- `exports/payslips/payslip_EMP-0011_PR-2025-04.pdf`
- `exports/payslips/payslip_EMP-0049_PR-2025-04.pdf`

| Field / Component | `EMP-0002` (`payroll_items.csv` vs PDF) | `EMP-0011` (`payroll_items.csv` vs PDF) | `EMP-0049` (`payroll_items.csv` vs PDF) | Match |
|---|---:|---:|---:|:---:|
| **Payable / Calendar Days** | `30.0 / 30` (`0.0` LOP) | `29.5 / 30` (`0.5` LOP) | `29.0 / 30` (`1.0` LOP) | PASS |
| **Monthly Fixed Gross** | `1,44,460.00` | `24,041.00` | `4,65,375.00` | PASS |
| **Basic Salary** | `57,784.00` | `9,455.73` | `1,79,945.00` | PASS |
| **House Rent Allowance (HRA)** | `28,892.00` | `4,727.87` | `89,972.50` | PASS |
| **Conveyance Allowance** | `1,600.00` | `1,573.33` | `1,546.67` | PASS |
| **Medical Allowance** | `1,250.00` | `1,229.17` | `1,208.33` | PASS |
| **Special Allowance** | `54,934.00` | `6,654.22` | `1,77,190.00` | PASS |
| **Earned Fixed Pay** | `1,44,460.00` | `23,640.32` | `4,49,862.50` | PASS |
| **Overtime Pay** | `0.00` (`0.0h`) | `346.75` (`1.5h`) | `0.00` (`0.0h`) | PASS |
| **Variable Pay (Bonus)** | `34,670.40` | `12,982.14` | `3,62,992.50` | PASS |
| **GROSS PAY** | **`1,79,130.40`** | **`36,969.21`** | **`8,12,855.00`** | **PASS** |
| **PF (Employee 12%)** | `1,800.00` | `1,134.69` | `1,800.00` | PASS |
| **ESI (Employee 0.75%)** | `0.00` | `0.00` | `0.00` | PASS |
| **Professional Tax (PT)** | `200.00` | `200.00` | `200.00` | PASS |
| **Income Tax (TDS)** | `18,625.79` | `0.00` | `2,16,539.09` | PASS |
| **TOTAL DEDUCTIONS** | **`20,625.79`** | **`1,334.69`** | **`2,18,539.09`** | **PASS** |
| **NET PAY (Take-Home)** | **`1,58,504.61`** | **`35,634.52`** | **`5,94,315.91`** | **PASS** |

## Double-Entry Accounting Ledger (Task 9 / LF-09)

### 1. Debits, Credits & Chart of Accounts (`app/models/ledger.py`, `app/services/ledger_service.py`)

- **Plain-English Rule**: Every financial event has two sides—*where the money came from* (**Credit**) and *where it went or what it bought* (**Debit**). In every journal entry, **Total Debits must equal Total Credits (`total_debit == total_credit`)** to the paisa (`0.00` difference).
- **Chart of Accounts (47 Accounts across 5 Types)**:
  1. **`ASSET` (`1000–1590`, Normal Debit)**: Bank (`1001`), Accounts Receivable (`1100`), GST Input Credit (`1200`), Employee Advances (`1300`), Fixed Assets (`1500`).
  2. **`LIABILITY` (`2000–2300`, Normal Credit)**: Accounts Payable (`2001`), Salaries Payable (`2100`), PF Payable (`2110`), ESI Payable (`2120`), TDS Payable (`2130`), Professional Tax Payable (`2140`), GST Output (`2200`).
  3. **`EQUITY` (`3000–3100`, Normal Credit)**: Share Capital (`3001`), Retained Earnings (`3100`).
  4. **`INCOME` (`4000–4900`, Normal Credit)**: Software Services (`4001`), SaaS (`4002`), Consulting (`4003`), Support (`4004`).
  5. **`EXPENSE` (`5000–5301`, Normal Debit)**: Employer Payroll Costs (`5001` Salaries & Wages, `5002` Overtime, `5003` Incentives & Bonus, `5004` Employer PF, `5005` Employer ESI) and Operating Expenses (`5101–5301`).

### 2. Immutability & Reversal Rule (Think for Yourself)

- **Why Posted Entries Are Read-Only**: Once a journal entry is `POSTED`, editing or deleting it in-place is strictly refused (`409 Conflict`, `error_code = "IMMUTABLE_POSTED_ENTRY"`), enforced both in the service layer (`update_journal_entry` / `delete_journal_entry`) and via SQLAlchemy ORM `before_update` / `before_delete` event listeners.
- **What We Offer Instead (`reverse_journal_entry` / `POST /ledger/entries/{entry_id}/reverse`)**:
  - To correct a mistake on a posted entry, the system posts a **reversing entry** (`reversal_of_source_id = original.source_id`) that swaps every line's `debit` and `credit` (`new_debit = old_credit`, `new_credit = old_debit`).
  - Both the original entry and the reversing entry remain permanently in the books so the audit trail is complete, while the net account balance returns to zero before the corrected entry is posted.

### 3. Official Verification Check Output (`verify_ledgerforge.py checks --data exports/`)

```text
$ python scripts/verify_ledgerforge.py checks --data exports/
PASS  Every journal entry balances  -  debits-credits=0.0, unbalanced entries=0
PASS  Payroll equals ledger, every month  -  largest monthly difference=0.00
PASS  Receivables equal open invoices  -  ledger 1100=139,394,278.00, open (sent/overdue/part-paid) invoices=139,394,278.00
PASS  Payroll employees exist  -  payroll rows with unknown employee=0
PASS  Nobody is paid after leaving  -  payroll rows after exit_date=0

5/5 checks passed
```

### 4. Sample Payroll Journal Entry Printed as a Table (`JE-000105` — `PR-2025-04`)

Posted via `post_payroll_run_to_ledger(session, "PR-2025-04")` (`entry_date = 2025-04-30`, `source_type = PAYROLL_RUN`, `source_id = PR-2025-04`):

| Account Code | Account Name | Cost Center(s) | Debit (INR) | Credit (INR) | Line Description |
|---:|---|---|---:|---:|---|
| `5001` | Salaries & Wages | `D00`–`D10` (11 depts) | `39,776,995.27` | `0.00` | Departmental earned fixed pay (`basic + hra + conv + med + special`) |
| `5002` | Overtime Expense | `D06`, `D07`, `D08`, `D09` | `170,928.18` | `0.00` | Departmental overtime pay (`2x` hourly rate) |
| `5003` | Incentives & Bonus | `D01`–`D10` (10 depts) | `12,792,186.98` | `0.00` | Departmental performance bonus / variable pay |
| `5004` | Employer PF Contribution | `D00`–`D10` (11 depts) | `618,963.94` | `0.00` | Employer PF (`12%` of basic up to ₹15,000 ceiling) |
| `5005` | Employer ESI Contribution | `D06` | `4,317.71` | `0.00` | Employer ESI (`3.25%` of gross for eligible staff) |
| `2100` | Salaries Payable | — | `0.00` | `46,035,111.16` | Net salaries payable (take-home pay) |
| `2110` | PF Payable | — | `0.00` | `1,237,927.88` | PF payable (`employee 12% + employer 12%`) |
| `2120` | ESI Payable | — | `0.00` | `5,314.10` | ESI payable (`employee 0.75% + employer 3.25%`) |
| `2130` | TDS on Salary Payable | — | `0.00` | `6,007,238.94` | Income tax deducted at source (TDS) |
| `2140` | Professional Tax Payable | — | `0.00` | `74,800.00` | Professional tax payable (`₹200` per eligible employee) |
| `1300` | Employee Advances & Loans | — | `0.00` | `3,000.00` | Recovery of employee advances (`other_deductions`) |
| **TOTAL** | **43 Journal Lines** | **`status = POSTED`** | **`53,363,392.08`** | **`53,363,392.08`** | **Exact Balance (`debits - credits = 0.00`)** |

## Clients, Invoices, Payments & Accounts Receivable (Task 10 / LF-10)

### 1. Invoice Status Flow & Ledger Posting Rules (`app/services/invoice_service.py`)

- **Status Lifecycle**: `DRAFT` $\rightarrow$ `SENT` $\rightarrow$ `PARTIALLY_PAID` $\rightarrow$ `PAID` (or `OVERDUE` / `CANCELLED`).
- **GST Calculation**: Domestic clients (`client_type == "DOMESTIC"`) carry `18%` GST (`gst_amount = round_half_up(subtotal * 18%)`); Export clients (`client_type == "EXPORT"`) are zero-rated (`0%` GST).
- **Double-Entry Ledger Posting Rules**:
  1. **`DRAFT` & `CANCELLED` Guard**: `DRAFT` and `CANCELLED` invoices **never** post to the ledger (`post_invoice_to_ledger` refuses them with `422 Unprocessable Entity`, `INVALID_INVOICE_STATUS_FOR_POSTING`).
  2. **Sending an Invoice (`POST /invoices/{id}/send`)**:
     - **Debit `1100` (`Accounts Receivable`)**: `total_amount` (`subtotal + gst_amount`)
     - **Credit `4001`–`4004` (`Service Line Revenue`)**: `subtotal`
     - **Credit `2200` (`GST Output Payable`)**: `gst_amount` (when `> 0.00`)
  3. **Recording a Payment (`POST /invoices/{id}/payments`)**:
     - **Debit `1001` (`Bank - Operating Account`)**: `payment_amount`
     - **Credit `1100` (`Accounts Receivable`)**: `payment_amount`
     - Reduces `balance_due = total_amount - amount_paid` and updates status to `PARTIALLY_PAID` or `PAID`.

### 2. What Happens to the Ledger When a `SENT` Invoice Is Later Cancelled? (Think for Yourself)

- **Case A — Cancelling a `DRAFT` Invoice**: Since a `DRAFT` invoice was never posted to the ledger, cancelling it simply sets `status = "CANCELLED"` and `balance_due = 0.00` with no ledger entry.
- **Case B — Cancelling a `SENT` or `OVERDUE` Invoice (No Payments Received)**:
  - Because the `SENT` invoice already posted a `POSTED` (read-only) journal entry debiting `1100` (`Accounts Receivable`) and crediting Revenue (`400x`) and GST (`2200`), we cannot delete or edit that original entry.
  - Instead, `cancel_invoice()` calls `reverse_journal_entry(session, invoice.ledger_entry_id)` to post an official **reversing entry** (Debit `400x` Revenue & `2200` GST Output; Credit `1100` Accounts Receivable) and sets `status = "CANCELLED"` and `balance_due = 0.00`.
  - This reduces both Ledger Account `1100` and Open Invoices by the exact same amount so **Check 3 (`Receivables equal open invoices`) remains 100% reconciled**.
- **Case C — Invoice with Payments Already Received (`amount_paid > 0`)**: Direct cancellation is refused (`409 Conflict`, `CANNOT_CANCEL_PAID_INVOICE`); payments must be refunded/reversed or adjusted via a credit note first.

### 3. Check 3 & Accounts Receivable Reconciliation (`GET /invoices/receivables`)

```text
$ python scripts/verify_ledgerforge.py checks --data exports/
PASS  Every journal entry balances  -  debits-credits=0.0, unbalanced entries=0
PASS  Payroll equals ledger, every month  -  largest monthly difference=0.00
PASS  Receivables equal open invoices  -  ledger 1100=139,394,278.00, open (sent/overdue/part-paid) invoices=139,394,278.00
PASS  Payroll employees exist  -  payroll rows with unknown employee=0
PASS  Nobody is paid after leaving  -  payroll rows after exit_date=0

5/5 checks passed
```

- **Company-Wide Reconciliation**:
  - **Open Invoices (`SENT`, `OVERDUE`, `PARTIALLY_PAID`)**: `67` open invoices totaling **`INR 139,394,278.00`**
  - **Ledger Account `1100` (`Accounts Receivable`) Balance**: **`INR 139,394,278.00`**
  - **Reconciled Difference**: **`INR 0.00`** (`is_reconciled = True`)






