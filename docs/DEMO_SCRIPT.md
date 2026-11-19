# LedgerForge v1.0.0 — 5-Minute Live Demo Script

Use this script to record a crisp, confident 5-minute walkthrough (OBS Studio, Loom, or Windows Snipping Tool screen recording). Start the local stack before recording (`uvicorn app.main:app --reload` or `docker compose up`).

---

## Pre-Recording Setup (30 seconds before hitting Record)
1. Terminal 1 running `uvicorn app.main:app --reload` on `http://localhost:8000` (or live Render URL).
2. Browser tabs pre-opened:
   - Tab 1: `http://localhost:8000/ui` (Mobile-responsive Web Portal)
   - Tab 2: `http://localhost:8000/docs` (Swagger UI with 91/91 enriched examples)
   - Tab 3: GitHub Repository (`https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/releases/tag/v1.0.0`)
3. Terminal 2 ready at repo root (`C:\Users\ancillin\Desktop\Phase 3`) with clean screen (`cls`).

---

## Minute-by-Minute Walkthrough

### `0:00 – 0:45` | Introduction & Architecture Overview
- **Show:** GitHub repo README + Mermaid architecture diagram (`docs/architecture.md`).
- **Say:**
  > "Hi, I'm Ancilin. Over 20 days I built **LedgerForge v1.0.0**, a full-stack HR, Indian statutory payroll, and double-entry accounting backend using FastAPI, SQLAlchemy 2.0, PostgreSQL, Celery/Redis, and Docker. Every request flows cleanly through layered Routes → Services → ORM models across 29 normalized tables."

### `0:45 – 1:45` | Web Portal (`/ui`) & End-to-End Payroll Story
- **Show:** Browser Tab 1 (`http://localhost:8000/ui`).
- **Actions:**
  1. Log in as `admin` / `LedgerForge2025!` (show JWT authentication working).
  2. Run a live payroll calculation for `EMP-0002` (`2025-04`) showing gross pay, EPF, Professional Tax, New-Regime TDS, and net pay.
  3. View / download the generated PDF Payslip.
- **Say:**
  > "Users don't need curl to run payroll. Through `/ui`, an HR admin logs in via JWT, calculates gross-to-net pay with Indian statutory deductions, and downloads an official PDF payslip."

### `1:45 – 2:45` | Enriched Swagger Docs (`/docs`), Streaming Exports & Final Challenge
- **Show:** Browser Tab 2 (`http://localhost:8000/docs`).
- **Actions:**
  1. Click **Authorize** with the admin JWT.
  2. Expand `GET /api/v1/reports/department-payroll-cost` (Task 20 Final Challenge) → click **Try it out** → **Execute**. Highlight the 11 departments sorted by employer cost (Engineering 39.58%, Sales 14.70%, totaling ₹86.16 Cr across 18 months).
  3. Expand `GET /api/v1/exports/payroll` → highlight streaming CSV and `?format=xlsx` Excel export plus `/api/v1/exports/changes?since=...` incremental export.
- **Say:**
  > "All 91 API operations include real copy-paste examples in OpenAPI. For my Task 20 Final Challenge, I built an Executive Departmental Payroll Cost Breakdown report on its own feature branch using a single SQL `GROUP BY` query, plus streaming CSV and Excel exports with date and incremental filters."

### `2:45 – 3:45` | Performance, Observability & Disaster Recovery Proof
- **Show:** Terminal 2.
- **Run:**
  ```powershell
  curl.exe -s http://localhost:8000/health
  ```
  Show the JSON response (`database: connected`, `latency_ms`) and point out the structured JSON request log emitted in Terminal 1.
- **Say:**
  > "In Task 18 I profiled the slowest queries with `EXPLAIN`, added composite indexes cutting attendance and ledger query latency by 52–65%, added a TTL cache speeding Trial Balance up by 8,900x, added structured JSON logs, a live DB health probe returning 503 on outage, and a backup/restore script verified at 193,036 of 193,036 rows."

### `3:45 – 4:40` | Live Mathematical Audit (`verify_ledgerforge.py` & `pytest`)
- **Show:** Terminal 2.
- **Run:**
  ```powershell
  .\.venv\Scripts\python.exe scripts/verify_ledgerforge.py checks --data exports
  .\.venv\Scripts\python.exe scripts/verify_ledgerforge.py payroll exports/task19_payroll_export.csv --data exports
  .\.venv\Scripts\python.exe scripts/verify_ledgerforge.py trial-balance exports/trial_balance.csv --data exports
  ```
- **Say:**
  > "Here is the mathematical proof: 5 out of 5 official integrity checks pass with zero unbalanced journal entries and zero payroll-to-ledger variance; 7,340 out of 7,340 exported payroll rows match 100.00% within one paisa; 40 out of 40 Trial Balance accounts match with zero mismatches; and all 132 automated pytest tests pass."

### `4:40 – 5:00` | Honest Limits, Career Lesson & Handover
- **Show:** `RELEASE_NOTES.md` and GitHub `v1.0.0` tag.
- **Say:**
  > "In `RELEASE_NOTES.md` I documented honest limits—including single-process cache scaling to Redis and Render free-tier spin-down—and my biggest career lesson: standardize audit timestamp types and enum casing in `Base` on Day 1. Everything is tagged `v1.0.0` and ready for handover. Thank you!"
