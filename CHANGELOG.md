# Changelog

All notable changes to **LedgerForge** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-rc1] - 2026-11-19

### Added — Task 19: Exports & Documentation
- **Streaming CSV & Excel (`.xlsx`) Export Endpoints** under `/api/v1/exports/`:
  - `GET /api/v1/exports/employees` with `department_id`, `start_date`, `end_date`, `since`, and `format=csv|xlsx` filters
  - `GET /api/v1/exports/payroll` with `run_id`, `start_date`, `end_date`, `since`, and `format=csv|xlsx` filters (verified **7,340/7,340 = 100.00%** match against official dataset)
  - `GET /api/v1/exports/ledger` with `account_code`, `start_date`, `end_date`, `since`, and `format=csv|xlsx` filters
  - `GET /api/v1/exports/changes?since=<ISO-8601>` incremental delta manifest returning changed employees, payroll items, and journal entries
- **100% OpenAPI Examples Coverage**: `app/core/openapi.py` enriches all **90/90** API operations with realistic copy-pasteable request, parameter, and response examples in `/docs`.
- **Stranger-Ready Documentation**: Completely rewritten `README.md` with 3-step quick start, 10 copy-paste `curl` examples, environment reference, troubleshooting FAQ, and embedded Mermaid architecture diagram (`docs/architecture.md`).
- **Release Notes**: Added this `CHANGELOG.md` following Keep a Changelog format.
- **Automated Tests**: Added `tests/test_exports.py` (6 tests covering streaming CSV, Excel `.xlsx`, date filters, incremental delta, and 100% OpenAPI example coverage) — total **128 passing tests**.

### Added — Task 18: Performance, Health & Disaster Recovery
- **Query Profiling & Composite Indexes** (Alembic migration `0011`):
  - Attendance 30-day aggregation: `45.75 ms` → `21.63 ms` (**52.7% faster**)
  - Trial Balance ledger join: `22.77 ms` → `9.44 ms` (**58.5% faster**)
  - Open invoices query: `1.14 ms` → `0.40 ms` (**64.9% faster**)
- **Pagination Everywhere**: Standardized `limit`/`offset` pagination across accounts, entries, attendance, expenses, payroll runs, and invoices.
- **TTL Report Cache**: In-memory TTL cache with automatic invalidation on Trial Balance (`69.47 ms` cold → `0.01 ms` hot, **8,907x faster**).
- **Structured JSON Logging**: `app/core/logging.py` emits machine-readable JSON request and application logs with latency and status codes.
- **Database-Aware Health Probe**: `GET /health` and `GET /api/v1/health` run live `SELECT 1` probes and return HTTP `503` if the database is unreachable.
- **Tested Backup & Restore**: `scripts/backup_restore.py` performs atomic backup, restores to a clean database, and verifies exact row-count parity (**193,036 rows across 29 tables, 100% match**).

### Added — Task 17: Production Cloud Deployment & Web UX
- **Cloud Hosting & Blueprint**: Evaluated Render, Railway, Fly.io, and Supabase; deployed live on Render via `render.yaml` + `start.sh` with hosted PostgreSQL and zero secrets in Git.
- **Mobile-First Web UI (`/ui`)**: Responsive portal supporting Login, Run Payroll, and Payslip inspection/PDF download.
- **Live Smoke Test Suite**: `scripts/smoke_test.py` verifying health, authentication, payroll calculation, and live endpoints (`22/22` checks passing).

### Added — Task 16: Release Candidate, Background Jobs & CI/CD
- **Background Jobs Queue**: Celery + Redis task queue with automatic local thread fallback (`app/services/job_service.py`, `GET/POST /api/v1/jobs/*`).
- **API Versioning**: All endpoints standardized under `/api/v1/` with backward-compatible health probe.
- **CI/CD Pipeline**: `.github/workflows/ci.yml` runs automated `pytest` and coverage checks on every push.

## [phase-3] - 2026-11-10
### Added — Connected System (Tasks 11–15)
- Vendors, expense bills, duplicate detection, and monthly reconciliation.
- End-to-end Payroll-to-Books double-entry journal posting across all 18 runs (`7,340` payroll items).
- JWT authentication (`bcrypt` hashing) and Role-Based Access Control (`ADMIN`, `HR`, `EMPLOYEE`).
- Configurable Indian tax slab engine & statutory rates (EPF, ESI, PT, TDS).
- Financial statements: Trial Balance (`40/40` accounts exact match), Profit & Loss, Balance Sheet.

## [phase-2] - 2026-11-03
### Added — Core Development (Tasks 6–10)
- Attendance tracking (150,156 records) & leave management workflows.
- Gross-to-net Indian payroll calculation engine (`7,340/7,340` rows within 1 paisa).
- PDF Payslip generator (`reportlab`).
- Double-entry general ledger with Chart of Accounts (47 accounts) and balanced journal enforcement.
- Client invoicing, accounts receivable, and payment tracking.

## [phase-1] - 2026-10-28
### Added — Foundation (Tasks 1–5)
- Layered FastAPI backend, Docker Compose + PostgreSQL setup, Alembic migrations.
- Organization hierarchy models (`departments`, `roles`, `employees`) with cycle detection.
- One-command Excel master dataset seeder (`scripts/seed.py`).
- Employee CRUD & team APIs, salary structures, and historical salary revisions.
