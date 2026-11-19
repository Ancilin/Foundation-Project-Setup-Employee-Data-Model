# LedgerForge v1.0.0 — Release Notes

**Release Tag:** `v1.0.0`
**Release Date:** November 19, 2026
**Author:** Ancilin P G (`GM00210`)
**Repository:** <https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model>

---

## 1. What Is Included in `v1.0.0`

LedgerForge `v1.0.0` is a complete, end-to-end HR, Indian Statutory Payroll, and Double-Entry Accounting backend built over 20 days across 4 engineering phases:

### Phase 1 — Foundation (Days 1–5)
- Layered FastAPI architecture (`Route → Service → SQLAlchemy 2.0 ORM → PostgreSQL/SQLite`) with Alembic schema migrations (`0001`–`0011`) and Docker Compose stack.
- Organization hierarchy (`departments`, `roles`, `employees`) with natural keys, `CHECK` constraints, soft deletion (`is_active`), and circular-manager cycle detection.
- One-command Excel master dataset seeder (`scripts/seed.py`) loading 29 tables and 193,036 records.
- Full Employee CRUD, search/pagination, team reporting lines, salary structures, and historical salary revisions.

### Phase 2 — Core Development (Days 6–10)
- Attendance ingestion (150,156 daily records) and leave balance/request workflows with holiday awareness.
- Indian Gross-to-Net Payroll Calculation Engine supporting LOP proration, overtime, variable pay, EPF (employee & employer), ESI (employee & employer), Professional Tax, and New-Regime TDS — matching **7,340 / 7,340 (100.00%)** official rows within 1 paisa.
- Automated PDF Payslip generator (`reportlab`).
- Double-Entry General Ledger (47-account Chart of Accounts, balanced debit=credit enforcement, reversal workflow).
- Client Invoicing, Accounts Receivable (Account `1100`), overdue tracking, and payment allocation.

### Phase 3 — Connected System (Days 11–15)
- Vendors, expense bills, duplicate bill detection, and monthly ledger reconciliation.
- End-to-end **Payroll-to-Books** automated double-entry posting across all 18 payroll runs with `0.00` monthly variance.
- JWT HS256 Authentication (`bcrypt` password hashing) and Role-Based Access Control (`ADMIN`, `HR`, `EMPLOYEE`).
- Database-driven Tax Slab & Statutory Rate configuration engine (no hardcoded rates).
- Financial Statements: **Trial Balance** (`40/40` accounts exact match), **Profit & Loss**, and **Balance Sheet** (`Assets = Liabilities + Equity + Current Profit`), with group accounts rolled up separately and never double-counted.

### Phase 4 — Production, Performance, Exports & Final Challenge (Days 16–20)
- **Background Jobs Queue**: Celery + Redis async worker with automatic local thread fallback (`POST /api/v1/jobs/payroll/bulk-run`).
- **API Versioning & CI/CD**: All routes under `/api/v1/*`; automated GitHub Actions test & coverage pipeline (`.github/workflows/ci.yml`).
- **Cloud Blueprint & Mobile Web UX (`/ui`)**: Dockerized Render blueprint (`render.yaml` + `start.sh`), zero secrets in Git, responsive portal for Login, Run Payroll, and Payslip PDF download, plus `scripts/smoke_test.py`.
- **Performance & Observability**: `EXPLAIN` query profiling + composite indexes (migration `0011`, up to 64.9% faster), pagination everywhere, TTL Trial Balance cache (`69.47 ms` → `0.01 ms`), structured JSON request logs (`app/core/logging.py`), and database-probing `/health` (`SELECT 1`, returns `503` on DB failure).
- **Disaster Recovery**: Tested backup and fresh-database restore (`scripts/backup_restore.py`) achieving **193,036 / 193,036 rows (100% parity)** across 29 tables.
- **Streaming Data Exports & 100% OpenAPI Docs**: Streaming CSV and Excel (`.xlsx`) downloads for Employees, Payroll, and Ledger with date filters; incremental delta export (`/api/v1/exports/changes?since=...`); **91/91 (100%)** OpenAPI operations enriched with real examples; stranger-ready `README.md`, `CHANGELOG.md`, and Mermaid architecture diagrams (`docs/architecture.md`).
- **Task 20 Final Challenge (`feat/department-payroll-cost-report`)**: New executive endpoint `GET /api/v1/reports/department-payroll-cost` built independently on its own feature branch and merged cleanly into `master`.

---

## 2. Final Audit Verification Evidence (`v1.0.0`)

Executed on November 19, 2026 against exported datasets and the full automated test suite:

| Audit Check | Command | Result |
| :--- | :--- | :--- |
| **Automated Test Suite** | `pytest -q` | **132 passed, 0 failed** |
| **Official Integrity Checks** | `python scripts/verify_ledgerforge.py checks --data exports` | **5/5 checks passed** (`debits-credits=0.0`, `largest monthly difference=0.00`, `ledger 1100 == open invoices = 139,394,278.00`, `unknown employee=0`, `paid after exit_date=0`) |
| **Official Payroll Export Audit** | `python scripts/verify_ledgerforge.py payroll exports/task19_payroll_export.csv --data exports` | **7,340 / 7,340 = 100.00%** exact match within 1 paisa |
| **Official Trial Balance Audit** | `python scripts/verify_ledgerforge.py trial-balance exports/trial_balance.csv --data exports` | **Accounts compared: 40, mismatched: 0** |
| **OpenAPI Example Coverage** | `tests/test_exports.py::test_openapi_schema_has_rich_examples` | **91 / 91 (100%)** operations have examples |
| **Backup & Fresh Restore** | `python scripts/backup_restore.py` | **193,036 / 193,036** rows matched across 29 tables |

---

## 3. What Is NOT Included (Explicit Scope Boundaries)

To keep `v1.0.0` focused, verifiable, and maintainable, the following enterprise integrations are intentionally excluded from this release and earmarked for `v1.1+`:
- **Direct Bank Payout / NEFT / IMPS Disbursal**: Payroll runs transition to `PAID` and post to ledger accounts, but no live bank payment rail or webhook reconciliation is wired.
- **Automated Statutory E-Filing**: Statutory summaries (EPF, ESI, PT, TDS) are computed and exportable, but direct submission to EPFO/ESIC/TRACES government portals is out of scope.
- **Multi-Currency FX Revaluation**: All accounting and payroll figures operate in single-currency INR (`Decimal` 2-place paisa precision).
- **Multi-Tenant Organization Isolation**: The schema models a single legal entity rather than row-level tenant isolation across multiple companies.
- **Self-Service Password Reset / Email SMTP Delivery**: User authentication uses seeded/admin-managed bcrypt accounts without outbound transactional email.

---

## 4. Known Limits & Honest Audit Notes

1. **Render Free-Tier Cloud Deployment & Cold Start**:
   - LedgerForge `v1.0.0` is live at **<https://ledgerforge-ijqw.onrender.com>** (`/docs`, `/ui`, `/health`) backed by hosted PostgreSQL via `render.yaml`.
   - On Render's free web tier, the container sleeps after 15 minutes of inactivity (~30–45s cold wake on the first request), and free Postgres databases expire after 30 days. Upgrading to Render Starter (~$14/mo total for always-on web + managed PostgreSQL) eliminates spin-down with zero code changes.
2. **In-Memory TTL Cache Is Single-Process**:
   - The 60-second Trial Balance TTL cache in `app/services/report_service.py` lives in Python process memory. Under a single Uvicorn worker it works cleanly (and invalidates automatically on ledger writes), but scaling horizontally to multiple web replicas requires migrating `_REPORT_CACHE` to Redis (`REDIS_URL`).
3. **SQLite Local Fallback Limitations**:
   - While SQLite enables zero-dependency local dev and fast in-memory pytest execution, concurrent bulk payroll writes should always run against PostgreSQL (via `docker-compose.yml` or hosted Postgres) for MVCC row-level locking.
4. **Excel (`.xlsx`) Export Buffering**:
   - CSV exports stream row chunks directly over HTTP (`StreamingResponse`) with constant memory, whereas `.xlsx` exports assemble the ZIP archive in memory via `openpyxl` write-only mode before returning `Response`—suitable for tens of thousands of rows, though multi-million-row workbooks should prefer CSV streaming or async background job export.

---

## 5. Final Challenge Notes (`feat/department-payroll-cost-report`)

- **What I built**: `GET /api/v1/reports/department-payroll-cost` — an Executive Departmental Payroll Cost & Statutory Breakdown report.
- **Why I chose it**: While `Trial Balance` reports by GL account and `P&L` reports company-level totals, CFOs and HR leads routinely ask: *"How much total employer cost (Gross + Employer PF + Employer ESI) did each department generate this month or fiscal year, and what percentage of company payroll does each department represent?"*
- **Design Decisions & Trade-Offs**:
  - **Single SQL `GROUP BY` Join**: Joined `payroll_items` directly to `departments` and aggregated in the database (`COUNT(DISTINCT employee_id)`, `SUM(gross_pay)`, `SUM(employer_cost)`, etc.) instead of fetching 7,340 ORM objects into Python—eliminating N+1 queries and executing across 18 months in milliseconds.
  - **Exact `Decimal` Arithmetic & Zero-Division Safety**: Used `Decimal` with `ROUND_HALF_UP` for all monetary sums, averages, and cost-share percentages, returning clean zero-filled payloads on empty date ranges.
  - **Strict RBAC**: Protected with `require_role("ADMIN", "HR")` so regular `EMPLOYEE` tokens receive `403 Forbidden`.
  - **Real 18-Month Output**: Verified across all **11 departments** and **7,340 payroll items** totaling **₹861,586,392.42** in employer cost (led by Engineering at `39.58%`, Sales at `14.70%`, and Data & AI at `12.85%`, summing cleanly to `100.00%`).

---

## 6. Career Lesson — What I Would Rebuild Differently

> **If I rebuilt LedgerForge from Day 1 with what I know now, I would unify every table's audit columns (`created_at`, `updated_at` as timezone-aware `TIMESTAMP WITH TIME ZONE` with database `server_default`) and strict enum/casing conventions inside a single shared `Base` contract before writing the first migration.**
>
> Across 20 days of iterative growth, small inconsistencies—such as `JournalEntry.created_at` being a nullable `VARCHAR(32)` while `Employee` and `PayrollItem` used `TimestampMixin`, or Title Case enum check constraints (`'Active'`, `'Permanent'`) in Phase 1 versus uppercase statuses (`'POSTED'`, `'PAID'`) in Phases 2–3—added friction later when building incremental delta exports, OpenAPI examples, and cross-table tests. Enforcing one strict schema convention upfront eliminates an entire class of downstream integration bugs.
