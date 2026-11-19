# LedgerForge v1.0.0 — 5-Minute Demo Recording Guide

> **Rule:** Speak naturally in your own words — use these bullet cues as a visual checklist, **do NOT read verbatim**.

---

## Pre-Recording Checklist
1. **Confirm your live URL is awake and visible in the browser address bar** (do NOT record `localhost`!):
   - If Render's free service spun down, trigger a redeploy of tag `v1.0.0` via `render.yaml` in the Render dashboard and open `https://<your-live-url>/health` until it returns `{"status":"ok","database":"connected"}`.
2. Pre-open 3 clean browser tabs (hide messy bookmarks):
   - Tab 1: `https://<your-live-url>/ui` (Web Portal)
   - Tab 2: `https://<your-live-url>/docs` (Swagger UI — 91/91 examples)
   - Tab 3: `https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/releases/tag/v1.0.0`
3. Terminal window ready at repo root (`C:\Users\ancillin\Desktop\Phase 3`) for the final `verify_ledgerforge.py` proof.

---

## Part 1 — `0:00 to 1:00` | Your Face on Camera (No Screen Yet)
Keep it warm, concise, and conversational (3 bullet cues):
- **Who you are:** "Hi, I'm Ancilin P G, Python Developer track."
- **The problem LedgerForge solves:** Growing companies juggle HR, attendance, Indian payroll taxes (EPF, ESI, PT, TDS), and accounting books in disconnected spreadsheets—causing paisa rounding errors, accidental payments after exit, and books that don't balance.
- **What you built:** Over 20 days I built **LedgerForge v1.0.0**—a complete FastAPI + PostgreSQL + Celery/Redis backend with 29 tables, 91 documented APIs, role-based security, double-entry accounting, streaming exports, and a mobile web UI.

---

## Part 2 — `1:00 to 5:00` | Screen Recording (Live Link Visible in Address Bar!)

### `1:00 – 2:15` | Live Story Step 1 & 2: Run Payroll → View Payslip (`/ui`)
- Point out the **live HTTPS URL** in the browser address bar.
- Log into `/ui` as `admin` / `LedgerForge2025!` (mention HR & Employee roles exist too).
- Calculate payroll for `EMP-0002` (`2025-04`) → highlight Gross (`₹179,130.40`), EPF, PT, TDS, Net Pay (`₹158,504.61`).
- Open/download the **PDF Payslip**.

### `2:15 – 3:30` | Live Story Step 3 & 4: See the Books → See Financial & Challenge Reports (`/docs`)
- Switch to `/docs` (live URL in address bar), click **Authorize** with your Bearer JWT.
- Call `GET /api/v1/reports/trial-balance` or `GET /api/v1/reports/balance-sheet` → point out `is_balanced: true`, `difference: 0.00` (Assets `₹463.76M` == Liabilities + Equity + Current Profit).
- Call your **Final Challenge** endpoint `GET /api/v1/reports/department-payroll-cost` (built independently on branch `feat/department-payroll-cost-report`) → highlight all 11 departments totaling `₹861.59M` (`100.00%` share, matching P&L `5001–5005` to the paisa).
- Briefly show `/api/v1/exports/payroll?format=xlsx` (streaming CSV / Excel exports).

### `3:30 – 4:40` | Live Proof That It Works (Terminal Verifier + Tests)
- Switch to Terminal and run:
  ```powershell
  .\.venv\Scripts\python.exe scripts/verify_ledgerforge.py checks --data exports
  .\.venv\Scripts\python.exe scripts/verify_ledgerforge.py payroll exports/task19_payroll_export.csv --data exports
  .\.venv\Scripts\python.exe scripts/verify_ledgerforge.py trial-balance exports/trial_balance.csv --data exports
  ```
- Highlight the exact passing output: **5/5 checks passed**, **7,340/7,340 (100.00%)** payroll exact match, **40/40** Trial Balance exact match, plus **132/132** passing `pytest` tests and **193,036/193,036** backup/restore parity.

### `4:40 – 5:00` | Wrap-Up & Handover
- Show the GitHub `v1.0.0` / `phase-4` tag page (`RELEASE_NOTES.md`), mention one honest limit (moving the TTL cache to Redis for multi-replica scale), and thank the viewer.

---

## Upload & Link Verification Checklist
- [ ] Export video (`.mp4`, 1080p, clear audio, ≤ 5:00).
- [ ] Upload to YouTube (**Unlisted**) or Google Drive (**Anyone with the link can view**).
- [ ] **Open the link in a Private / Incognito browser window** to confirm anyone can play it without signing in.
- [ ] Paste the tested video link, live URL, and `Python_Ancillin_Final_Consolidated_Report.pdf` into the **Google Form** (and upload `Python_Ancillin_Phase4_Report.pdf` ONLY on the programme site form!).
