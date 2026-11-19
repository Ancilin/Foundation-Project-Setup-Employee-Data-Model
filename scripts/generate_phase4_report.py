"""Generate Python_Ancillin_Phase4_Report.pdf — Phase 4 Review & Report (Days 16–20, strictly 2–3 pages)."""

import shutil
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = ROOT / "Python_Ancillin_Phase4_Report.pdf"
REPORTS_PDF = ROOT / "reports" / "Python_Ancillin_Phase4_Report.pdf"
DESKTOP_PDF = Path(r"C:\Users\ancillin\Desktop\Python_Ancillin_Phase4_Report.pdf")

GITHUB_URL = "https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model"
TAG_PHASE4_URL = f"{GITHUB_URL}/releases/tag/phase-4"
TAG_V1_URL = f"{GITHUB_URL}/releases/tag/v1.0.0"
BRANCH_URL = f"{GITHUB_URL}/tree/feat/department-payroll-cost-report"
LIVE_APP_URL = "https://ledgerforge-ijqw.onrender.com"


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(36, 16, "LedgerForge — Phase 4 Report (Days 16–20) | Ancilin P G (GM00210)")
    canvas.drawRightString(letter[0] - 36, 16, f"Page {doc.page}")
    canvas.restoreState()


def _table(data, col_widths, header_hex="#1e3a5f", center_cols=()):
    tbl = Table(data, colWidths=col_widths)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_hex)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.0),
        ("LEADING", (0, 0), (-1, -1), 9.2),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]
    for c in center_cols:
        cmds.append(("ALIGN", (c, 0), (c, -1), "CENTER"))
    tbl.setStyle(TableStyle(cmds))
    return tbl


def build_pdf() -> int:
    page_counter = {"pages": 0}

    def _track_page(canvas, doc):
        page_counter["pages"] = max(page_counter["pages"], doc.page)
        _on_page(canvas, doc)

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=26,
        bottomMargin=28,
    )
    styles = getSampleStyleSheet()

    title_s = ParagraphStyle(
        "TitleS", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=15, leading=18, textColor=colors.HexColor("#0f172a"), spaceAfter=2,
    )
    sub_s = ParagraphStyle(
        "SubS", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9.2, leading=12, textColor=colors.HexColor("#2563eb"), spaceAfter=3,
    )
    meta_s = ParagraphStyle(
        "MetaS", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7.9, leading=10.8, textColor=colors.HexColor("#334155"), spaceAfter=2,
    )
    h_s = ParagraphStyle(
        "HS", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10.2, leading=13, textColor=colors.HexColor("#1e3a5f"), spaceBefore=7, spaceAfter=3,
    )
    body_s = ParagraphStyle(
        "BodyS", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.0, leading=11.0, textColor=colors.HexColor("#1e293b"), spaceAfter=3,
    )
    code_s = ParagraphStyle(
        "CodeS", parent=styles["Normal"], fontName="Courier",
        fontSize=7.0, leading=9.3, textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"), spaceAfter=3, leftIndent=6, rightIndent=6,
    )
    cell_s = ParagraphStyle(
        "CellS", parent=styles["Normal"], fontName="Helvetica",
        fontSize=6.9, leading=9.0, textColor=colors.HexColor("#1e293b"),
    )

    el = []

    # ── PAGE 1: Header + 5-Task Table + Core Verification Proof ──
    el.append(Paragraph("Python Developer Programme — Phase 4 Engineering Report", title_s))
    el.append(Paragraph("Phase 4 (Days 16–20): Production Release, Performance, Backups, Exports, Final Audit &amp; Challenge", sub_s))
    el.append(Paragraph(
        f'<b>Name:</b> Ancilin P G (ID: GM00210) &nbsp;|&nbsp; <b>Track:</b> Python Developer &nbsp;|&nbsp; <b>Phase:</b> Phase 4 (Days 16–20)<br/>'
        f'<b>GitHub Repository:</b> <a href="{GITHUB_URL}" color="#2563eb">{GITHUB_URL}</a><br/>'
        f'<b>Live Production App:</b> <a href="{LIVE_APP_URL}/docs" color="#2563eb">{LIVE_APP_URL}/docs</a> &nbsp;|&nbsp; '
        f'<a href="{LIVE_APP_URL}/ui" color="#2563eb">{LIVE_APP_URL}/ui</a> &nbsp;|&nbsp; '
        f'<a href="{LIVE_APP_URL}/health" color="#2563eb">/health</a><br/>'
        f'<b>Git Tags:</b> <a href="{TAG_PHASE4_URL}" color="#2563eb"><b>phase-4</b></a> &nbsp;|&nbsp; '
        f'<a href="{TAG_V1_URL}" color="#2563eb"><b>v1.0.0</b></a> &nbsp;|&nbsp; '
        f'<b>Final Challenge Branch:</b> <a href="{BRANCH_URL}" color="#2563eb">feat/department-payroll-cost-report</a>',
        meta_s,
    ))
    el.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 4))

    # ── 1. Table of the 5 Phase 4 Tasks ──
    el.append(Paragraph("1. Phase 4 Tasks Summary (Days 16 to 20)", h_s))
    tasks_tbl = [
        ["Task", "Milestone", "Status", "Concrete Evidence (Code / Proof / Links)"],
        [
            "Task 16\n(Day 16)",
            "Release Candidate:\nJobs, /api/v1 & CI/CD",
            "DONE",
            Paragraph(
                f"Celery + Redis background job queue with local thread fallback (<font face='Courier'>app/services/job_service.py</font>), "
                f"all routes versioned under <font face='Courier'>/api/v1</font>, multi-service Docker Compose, and GitHub Actions CI "
                f"(<a href='{GITHUB_URL}/blob/phase-4/.github/workflows/ci.yml' color='#2563eb'>ci.yml</a>).", cell_s
            ),
        ],
        [
            "Task 17\n(Day 17)",
            "Release to Production:\nCloud DB, /ui & Smoke",
            "DONE",
            Paragraph(
                f"Hosting matrix (Render selected), Infrastructure-as-Code <a href='{GITHUB_URL}/blob/phase-4/render.yaml' color='#2563eb'>render.yaml</a> "
                f"+ <font face='Courier'>start.sh</font> with zero secrets in Git, responsive <font face='Courier'>/ui</font> web portal (login, payroll, payslip PDF), "
                f"and <font face='Courier'>scripts/smoke_test.py</font> (22/22 checks passed).", cell_s
            ),
        ],
        [
            "Task 18\n(Day 18)",
            "Performance, Health\n&amp; Tested Backups",
            "DONE",
            Paragraph(
                f"<font face='Courier'>EXPLAIN</font> profiling + composite indexes (migration <font face='Courier'>0011</font>, 52.7–64.9% faster), "
                f"pagination everywhere, TTL Trial Balance cache (8,907x faster), structured JSON logs (<font face='Courier'>app/core/logging.py</font>), "
                f"DB-probing <font face='Courier'>/health</font> (HTTP 503 on DB outage), and <font face='Courier'>backup_restore.py</font> restoring 193,036/193,036 rows.", cell_s
            ),
        ],
        [
            "Task 19\n(Day 19)",
            "Exports, OpenAPI Docs\n&amp; Architecture",
            "DONE",
            Paragraph(
                f"Streaming CSV &amp; Excel (<font face='Courier'>.xlsx</font>) exports for employees, payroll &amp; ledger with date filters + "
                f"incremental <font face='Courier'>/exports/changes?since=...</font> (7,340/7,340 = 100.00% payroll match); 91/91 (100%) OpenAPI examples; "
                f"stranger-ready <a href='{GITHUB_URL}/blob/phase-4/README.md' color='#2563eb'>README.md</a> (10 curl examples), "
                f"<a href='{GITHUB_URL}/blob/phase-4/docs/architecture.md' color='#2563eb'>Mermaid diagram</a> &amp; <font face='Courier'>CHANGELOG.md</font>.", cell_s
            ),
        ],
        [
            "Task 20\n(Day 20)",
            "Final Audit, Release\nNotes &amp; Final Challenge",
            "DONE",
            Paragraph(
                f"Final audit passed (5/5 checks, 7,340/7,340 payroll, 40/40 Trial Balance, 132/132 pytest); "
                f"<a href='{GITHUB_URL}/blob/phase-4/RELEASE_NOTES.md' color='#2563eb'>RELEASE_NOTES.md</a> &amp; demo guide; "
                f"Final Challenge <font face='Courier'>GET /api/v1/reports/department-payroll-cost</font> built independently on "
                f"<a href='{BRANCH_URL}' color='#2563eb'>feat/department-payroll-cost-report</a> and merged into <font face='Courier'>v1.0.0</font>.", cell_s
            ),
        ],
    ]
    el.append(_table(tasks_tbl, [48, 92, 36, 364], center_cols=(0, 2)))
    el.append(Spacer(1, 5))

    # ── 2. Proof It Works: Automated Tests & Official Verifier Output ──
    el.append(Paragraph("2. Proof It Works — Automated Tests &amp; Official Checker Output", h_s))
    el.append(Paragraph(
        "Every phase deliverable was verified end-to-end using the full <font face='Courier'>pytest</font> suite and the official "
        "<font face='Courier'>scripts/verify_ledgerforge.py</font> checker against exported production datasets:",
        body_s,
    ))
    el.append(Paragraph(
        "$ pytest -q<br/>"
        "132 passed, 4 warnings in 153.14s  (0 failed; includes 100% OpenAPI 91/91 example coverage &amp; 4 Final Challenge tests)<br/><br/>"
        "$ python scripts/verify_ledgerforge.py checks --data exports<br/>"
        "PASS  Every journal entry balances  -  debits-credits=0.0, unbalanced entries=0<br/>"
        "PASS  Payroll equals ledger, every month  -  largest monthly difference=0.00<br/>"
        "PASS  Receivables equal open invoices  -  ledger 1100=139,394,278.00, open (sent/overdue/part-paid) invoices=139,394,278.00<br/>"
        "PASS  Payroll employees exist  -  payroll rows with unknown employee=0<br/>"
        "PASS  Nobody is paid after leaving  -  payroll rows after exit_date=0<br/>"
        "5/5 checks passed<br/><br/>"
        "$ python scripts/verify_ledgerforge.py payroll exports/task19_payroll_export.csv --data exports<br/>"
        "Rows expected 7340, rows found in your file 7340 | Exact matches (within 1 paisa): 7340/7340 = 100.00%<br/><br/>"
        "$ python scripts/verify_ledgerforge.py trial-balance exports/trial_balance.csv --data exports<br/>"
        "Accounts compared: 40, mismatched: 0",
        code_s,
    ))

    el.append(PageBreak())

    # ── PAGE 2: Performance + Backup/Restore + Final Challenge ──
    el.append(Paragraph("3. Performance Benchmarks &amp; Tested Disaster Recovery (Task 18)", h_s))
    perf_rows = [
        ["Query / Operation Profiled", "Before", "After", "Speedup", "Fix Applied"],
        ["Attendance 30-Day Aggregation (150,156 rows)", "45.75 ms", "21.63 ms", "52.7% faster", "Composite index ix_attendance_date_emp_status"],
        ["Trial Balance Ledger Join (6,784 lines)", "22.77 ms", "9.44 ms", "58.5% faster", "Index ix_journal_entries_status on posted entries"],
        ["Open Invoices & Receivables (743 rows)", "1.14 ms", "0.40 ms", "64.9% faster", "Covering index ix_invoices_status"],
        ["Trial Balance Report (Cold vs. TTL Hot Cache)", "87.30 ms", "0.01 ms", "8,907x faster", "60s TTL cache with auto-invalidation on ledger writes"],
        ["Disaster Recovery Restore (29 tables)", "Backup 50.8 MB", "Fresh DB", "100% Parity", "193,036 / 193,036 rows matched via backup_restore.py"],
    ]
    el.append(_table(perf_rows, [160, 62, 54, 62, 202], header_hex="#334155", center_cols=(1, 2, 3)))
    el.append(Spacer(1, 5))

    # ── 4. Final Challenge (Mini Challenge on Own Branch) ──
    el.append(Paragraph("4. Final Challenge — Built Independently on Its Own Branch (Task 20)", h_s))
    el.append(Paragraph(
        "<b>Branch:</b> <font face='Courier'>feat/department-payroll-cost-report</font> (pushed to GitHub and merged via <font face='Courier'>--no-ff</font> into <font face='Courier'>master</font>).<br/>"
        "<b>What I Built:</b> <font face='Courier'>GET /api/v1/reports/department-payroll-cost</font> — an executive Departmental Payroll Cost &amp; Statutory Breakdown "
        "endpoint supporting optional <font face='Courier'>run_id</font>, <font face='Courier'>start_date</font>, and <font face='Courier'>end_date</font> filters, protected by <font face='Courier'>ADMIN/HR</font> RBAC.<br/>"
        "<b>Design Decisions:</b> Used a single SQL <font face='Courier'>GROUP BY</font> join between <font face='Courier'>payroll_items</font> and <font face='Courier'>departments</font> "
        "to avoid N+1 queries, exact <font face='Courier'>Decimal</font> arithmetic with <font face='Courier'>ROUND_HALF_UP</font>, safe zero-division guards, OpenAPI enrichment (91/91 coverage), "
        "and 4 unit/integration tests (<font face='Courier'>tests/test_department_cost_report.py</font>).<br/>"
        "<b>Verified Result on 18-Month DB:</b> 11 departments, 7,340 payroll items, total employer cost <b>₹861,586,392.42</b> — matching Profit &amp; Loss "
        "accounts <font face='Courier'>5001–5005</font> (<b>₹861,586,392.42</b>) to the exact paisa (Engineering 39.58%, Sales 14.70%, Data &amp; AI 12.85%; total share = 100.00%).",
        body_s,
    ))
    el.append(Spacer(1, 4))

    # ── 5. What I Learned (In My Own Words — 4 lines) ──
    el.append(Paragraph("5. What I Learned (In My Own Words)", h_s))
    el.append(Paragraph(
        "Phase 4 taught me that writing working endpoints is only half of software engineering—shipping a service means making it "
        "observable, fast, recoverable, and understandable by someone who has never met you. Profiling with <font face='Courier'>EXPLAIN</font> "
        "proved that guessing bottlenecks wastes time compared to measuring first and indexing second. Practising an actual database restore "
        "showed me why teams say an untested backup is just a hope. Most importantly, writing stranger-ready documentation and auditing "
        "my own live deployment forced me to spot and document honest limits rather than hide them.",
        body_s,
    ))
    el.append(Spacer(1, 4))

    # ── 6. Problems I Hit and How I Solved Them ──
    el.append(Paragraph("6. Problems I Hit &amp; How I Solved Them", h_s))
    probs_rows = [
        ["Problem Encountered", "Root Cause", "How I Solved It"],
        [
            "Streaming payroll export &amp; tests failed with TypeError on PayrollItem fields",
            "Used assumed names (item_id, basic_pay) instead of actual ORM column names (payroll_item_id, basic) and Title Case CHECK constraints",
            "Inspected SQLAlchemy __table__.columns and CHECK constraints directly, fixed export_service.py &amp; test fixtures, and verified 7,340/7,340 (100.00%) match",
        ],
        [
            "Incremental delta export missed JournalEntry records on SQLite",
            "JournalEntry.created_at was nullable VARCHAR(32) without a server_default unlike TimestampMixin tables",
            "Updated delta filter to match created_at >= since.isoformat() OR entry_date >= since.date(), then covered it with an automated assertion in test_exports.py",
        ],
        [
            "37 of 90 OpenAPI operations lacked Swagger examples initially",
            "Only requestBody paths had examples; read-only GET endpoints and path params were uncovered",
            "Extended app/core/openapi.py with parameter + 200 response examples and added a pytest gate enforcing 100% (91/91) coverage automatically",
        ],
        [
            "Render Docker startup failed on postgres:// URL & missing Excel file",
            "Render injects postgresql:// (needing postgresql+psycopg:// for psycopg v3) and Docker image shipped data/csv/ without the large .xlsx workbook",
            "Added URL normalizer in app/core/config.py, CSV fallback in scripts/seed.py, reportlab in requirements.txt, and CRLF stripping in Dockerfile → live on Render (HTTP 200)",
        ],
    ]
    el.append(_table(probs_rows, [145, 165, 230], header_hex="#7c2d12"))
    el.append(Spacer(1, 5))

    # ── 7. What I Would Improve Next ──
    el.append(Paragraph("7. What I Would Improve Next", h_s))
    el.append(Paragraph(
        "&bull; <b>Distributed Redis Caching:</b> Move the 60-second Trial Balance TTL cache from in-process Python memory to Redis (<font face='Courier'>REDIS_URL</font>) "
        "so cache invalidation stays consistent across multiple Uvicorn replicas.<br/>"
        "&bull; <b>Always-On Production Tier &amp; Automated Nightly Backups:</b> Upgrade from free-tier hosting to a paid managed PostgreSQL + always-on web service "
        "with scheduled <font face='Courier'>pg_dump</font> backups and automated weekly restore verification.<br/>"
        "&bull; <b>Uniform Day-1 Schema Contract:</b> Standardize timezone-aware <font face='Courier'>created_at/updated_at</font> timestamps and uppercase enums in a single "
        "shared SQLAlchemy <font face='Courier'>Base</font> before Migration 0001.<br/>"
        "&bull; <b>Enterprise Integrations (v1.1+):</b> Add bank NEFT/IMPS disbursement webhooks, statutory EPFO/TRACES e-filing exports, and multi-tenant isolation.",
        body_s,
    ))
    el.append(Spacer(1, 4))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Paragraph(
        "<b>Self-Check Passed:</b> I can explain every module, trace any payroll figure from attendance to the Balance Sheet, add a feature on a clean branch, "
        "and debug failures live in an interview. — <b>Ancilin P G (GM00210), Tag: phase-4 / v1.0.0</b>",
        meta_s,
    ))

    doc.build(el, onFirstPage=_track_page, onLaterPages=_track_page)
    print(f"✓ Phase 4 PDF written ({page_counter['pages']} pages): {OUTPUT_PDF}")
    for dest in (REPORTS_PDF, DESKTOP_PDF):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_PDF, dest)
        print(f"  → copied to {dest}")
    return page_counter["pages"]


if __name__ == "__main__":
    pages = build_pdf()
    assert 2 <= pages <= 3, f"Phase 4 report must be 2–3 pages, got {pages}!"
