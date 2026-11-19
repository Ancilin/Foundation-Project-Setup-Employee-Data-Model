"""Generate Python_Ancillin_Final_Consolidated_Report.pdf — Complete 10-Page Consolidated Project Report (8–12 pages, Google Form Submission)."""

import shutil
from pathlib import Path
from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
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
OUTPUT_PDF = ROOT / "Python_Ancillin_Final_Consolidated_Report.pdf"
REPORTS_PDF = ROOT / "reports" / "Python_Ancillin_Final_Consolidated_Report.pdf"
DESKTOP_PDF = Path(r"C:\Users\ancillin\Desktop\Python_Ancillin_Final_Consolidated_Report.pdf")

GITHUB_URL = "https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model"
TAG_V1_URL = f"{GITHUB_URL}/releases/tag/v1.0.0"
TAG_P4_URL = f"{GITHUB_URL}/releases/tag/phase-4"
BRANCH_URL = f"{GITHUB_URL}/tree/feat/department-payroll-cost-report"
LIVE_URL = "https://ledgerforge-ijqw.onrender.com"


def _styled_table(data, col_widths, header_hex="#1e3a5f", center_cols=(), font_size=7.4):
    tbl = Table(data, colWidths=col_widths)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_hex)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("LEADING", (0, 0), (-1, -1), font_size + 2.4),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
    ]
    for c in center_cols:
        cmds.append(("ALIGN", (c, 0), (c, -1), "CENTER"))
    tbl.setStyle(TableStyle(cmds))
    return tbl


def _draw_box(d: Drawing, x: float, y: float, w: float, h: float, title: str, sub: str, fill_hex: str, border_hex: str, title_hex: str = "#0f172a"):
    d.add(Rect(x, y, w, h, rx=5, ry=5, fillColor=colors.HexColor(fill_hex), strokeColor=colors.HexColor(border_hex), strokeWidth=1.1))
    d.add(String(x + w / 2, y + h - 15, title, textAnchor="middle", fontName="Helvetica-Bold", fontSize=8.0, fillColor=colors.HexColor(title_hex)))
    if sub:
        d.add(String(x + w / 2, y + 7, sub, textAnchor="middle", fontName="Helvetica", fontSize=6.6, fillColor=colors.HexColor("#334155")))


def _draw_arrow_down(d: Drawing, x: float, y_top: float, y_bot: float):
    d.add(Line(x, y_top, x, y_bot + 4, strokeColor=colors.HexColor("#475569"), strokeWidth=1.1))
    d.add(Polygon([x - 3.5, y_bot + 5, x + 3.5, y_bot + 5, x, y_bot], fillColor=colors.HexColor("#475569"), strokeWidth=0))


def _draw_arrow_right(d: Drawing, x_left: float, x_right: float, y: float):
    d.add(Line(x_left, y, x_right - 4, y, strokeColor=colors.HexColor("#475569"), strokeWidth=1.1))
    d.add(Polygon([x_right - 5, y + 3.2, x_right - 5, y - 3.2, x_right, y], fillColor=colors.HexColor("#475569"), strokeWidth=0))


def _build_architecture_drawing() -> Drawing:
    """Native vector system architecture diagram for Page 3."""
    d = Drawing(530, 265)
    # Background container for Cloud / Docker Stack
    d.add(Rect(8, 8, 514, 186, rx=8, ry=8, fillColor=colors.HexColor("#f8fafc"), strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=1.0, strokeDashArray=[4, 2]))
    d.add(String(18, 182, "Docker Compose / Render Cloud Stack", fontName="Helvetica-Bold", fontSize=7.5, fillColor=colors.HexColor("#475569")))

    # Tier 1: Clients
    _draw_box(d, 20, 218, 148, 36, "Mobile Web UI (/ui)", "Login · Run Payroll · Payslip PDF", "#eff6ff", "#2563eb", "#1d4ed8")
    _draw_box(d, 191, 218, 148, 36, "Swagger / OpenAPI (/docs)", "91 / 91 Operations w/ Examples", "#eff6ff", "#2563eb", "#1d4ed8")
    _draw_box(d, 362, 218, 148, 36, "BI & Export Consumers", "Streaming CSV · Excel (.xlsx)", "#eff6ff", "#2563eb", "#1d4ed8")

    _draw_arrow_down(d, 94, 218, 168)
    _draw_arrow_down(d, 265, 218, 168)
    _draw_arrow_down(d, 436, 218, 168)

    # Tier 2: FastAPI Middleware & Routers
    _draw_box(d, 20, 134, 490, 34, "FastAPI Application Layer (/api/v1/* + /health)", "Structured JSON Logging Middleware  |  JWT HS256 + bcrypt RBAC (ADMIN / HR / EMPLOYEE)  |  Pydantic v2 Validation", "#eef2ff", "#4f46e5", "#3730a3")

    _draw_arrow_down(d, 175, 134, 114)
    _draw_arrow_down(d, 420, 134, 114)

    # Tier 3: Services + Cache & Async Queue
    _draw_box(d, 20, 76, 305, 38, "Domain Service Layer + In-Memory TTL Cache", "Employees · Attendance · Payroll Engine · Ledger · Tax · Reports · Exports", "#ecfdf5", "#059669", "#065f46")
    _draw_box(d, 345, 76, 165, 38, "Redis Broker + Celery Worker", "Async Bulk Payroll (Thread Fallback)", "#fff7ed", "#ea580c", "#9a3412")
    _draw_arrow_right(d, 325, 345, 95)

    _draw_arrow_down(d, 175, 76, 54)
    _draw_arrow_down(d, 427, 76, 54)

    # Tier 4: ORM & Database
    _draw_box(d, 20, 16, 490, 38, "SQLAlchemy 2.0 ORM  →  PostgreSQL 16 (Hosted / Docker Volume)  |  SQLite Local Fallback", "29 Normalized Tables · CHECK Constraints · Alembic Migrations (0001–0011) · Composite Indexes · Verified Backup/Restore", "#f1f5f9", "#334155", "#0f172a")
    return d


def _build_payroll_flow_drawing() -> Drawing:
    """Native vector end-to-end flow diagram from Attendance to Balance Sheet (Page 7)."""
    d = Drawing(530, 112)
    stages = [
        (8, "1. Attendance", "30 / 30 Payable", "#eff6ff", "#2563eb"),
        (114, "2. Payroll Engine", "Gross→Net + CTC", "#ecfdf5", "#059669"),
        (220, "3. Payslip PDF", "EMP-0002 Slip", "#fefce8", "#ca8a04"),
        (326, "4. Journal Entry", "JE-000105 (43 L)", "#fff7ed", "#ea580c"),
        (432, "5. Statements", "TB · P&L · BS", "#f3e8ff", "#7c3aed"),
    ]
    for i, (x, title, sub, fill, stroke) in enumerate(stages):
        _draw_box(d, x, 54, 92, 42, title, sub, fill, stroke, "#0f172a")
        if i < len(stages) - 1:
            _draw_arrow_right(d, x + 92, x + 106, 75)

    # Bottom verification bar
    _draw_box(d, 8, 8, 516, 32, "Mathematical Reconciliation Invariant Across Every Stage: Variance = ₹0.00", "SUM(payroll_items.employer_cost) = ₹861,586,392.42  ==  P&L Accts 5001–5005  |  Balance Sheet: Assets (₹463.76M) == Liab + Equity + Profit", "#ecfdf5", "#047857", "#065f46")
    _draw_arrow_down(d, 265, 54, 40)
    return d


def build_pdf() -> int:
    page_counter = {"pages": 0}

    def _on_later(canvas, doc):
        page_counter["pages"] = max(page_counter["pages"], doc.page)
        canvas.saveState()
        canvas.setFont("Helvetica", 7.3)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(36, 18, "LedgerForge v1.0.0 — Final Consolidated Report | Ancilin P G (GM00210)")
        canvas.drawRightString(letter[0] - 36, 18, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.setLineWidth(0.5)
        canvas.line(36, 28, letter[0] - 36, 28)
        canvas.restoreState()

    def _on_first(canvas, doc):
        page_counter["pages"] = max(page_counter["pages"], doc.page)
        canvas.saveState()
        # Top accent banner on Cover page
        canvas.setFillColor(colors.HexColor("#0f172a"))
        canvas.rect(0, letter[1] - 115, letter[0], 115, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#2563eb"))
        canvas.rect(0, letter[1] - 120, letter[0], 5, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 21)
        canvas.setFillColor(colors.white)
        canvas.drawString(42, letter[1] - 54, "LEDGERFORGE v1.0.0")
        canvas.setFont("Helvetica", 11)
        canvas.setFillColor(colors.HexColor("#cbd5e1"))
        canvas.drawString(42, letter[1] - 74, "Final Consolidated Project Report — HR, Indian Statutory Payroll & Double-Entry Accounting Engine")
        canvas.setFont("Helvetica-Bold", 8.5)
        canvas.setFillColor(colors.HexColor("#93c5fd"))
        canvas.drawString(42, letter[1] - 96, "PYTHON DEVELOPER PROGRAMME  |  DAYS 1 TO 20 (PHASES 1–4)  |  FINAL HANDOVER SUBMISSION")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=38,
        rightMargin=38,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()

    h1 = ParagraphStyle(
        "H1", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=13.5, leading=17, textColor=colors.HexColor("#0f172a"), spaceBefore=2, spaceAfter=5,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10.2, leading=13.2, textColor=colors.HexColor("#1e3a5f"), spaceBefore=8, spaceAfter=3,
    )
    body = ParagraphStyle(
        "Body", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.6, leading=12.4, textColor=colors.HexColor("#1e293b"), spaceAfter=4.5,
    )
    small = ParagraphStyle(
        "Small", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7.8, leading=11.0, textColor=colors.HexColor("#334155"), spaceAfter=3,
    )
    code_s = ParagraphStyle(
        "CodeS", parent=styles["Normal"], fontName="Courier",
        fontSize=7.2, leading=9.8, textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"), spaceAfter=4, leftIndent=6, rightIndent=6,
    )
    callout = ParagraphStyle(
        "Callout", parent=styles["Normal"], fontName="Helvetica",
        fontSize=8.3, leading=11.8, textColor=colors.HexColor("#1e3a5f"),
        backColor=colors.HexColor("#eff6ff"), leftIndent=8, rightIndent=8, spaceAfter=5,
    )

    el = []

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER PAGE
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Spacer(1, 108))
    el.append(Paragraph("Project &amp; Candidate Information", h2))
    cover_meta = [
        ["Field", "Details & Clickable Verification Links"],
        ["Candidate Name & ID", "Ancilin P G  (ID: GM00210)"],
        ["Programme Track", "Python Developer Track — Complete 20-Day Capstone (Phases 1 to 4)"],
        ["Project Name", "LedgerForge — Unified HR, Indian Statutory Payroll & Double-Entry Accounting Backend"],
        ["GitHub Repository", Paragraph(f'<a href="{GITHUB_URL}" color="#2563eb">{GITHUB_URL}</a>', small)],
        ["Release Tags", Paragraph(f'<a href="{TAG_V1_URL}" color="#2563eb"><b>v1.0.0</b></a> &nbsp;|&nbsp; <a href="{TAG_P4_URL}" color="#2563eb"><b>phase-4</b></a> &nbsp;|&nbsp; phase-3, phase-2, phase-1, v0.0.1', small)],
        ["Final Challenge Branch", Paragraph(f'<a href="{BRANCH_URL}" color="#2563eb">feat/department-payroll-cost-report</a> (merged into master)', small)],
        ["Live Deployment Link", Paragraph(f'<a href="{LIVE_URL}/docs" color="#2563eb"><b>{LIVE_URL}/docs</b></a> &nbsp;|&nbsp; <a href="{LIVE_URL}/ui" color="#2563eb">/ui</a> &nbsp;|&nbsp; <a href="{LIVE_URL}/health" color="#2563eb">/health</a>', small)],
        ["5-Minute Demo Video", "Unlisted Demo Link: [Paste tested unlisted YouTube / Google Drive link in Google Form] (Script in docs/DEMO_SCRIPT.md)"],
        ["Submission Date", "November 19, 2026"],
    ]
    el.append(_styled_table(cover_meta, [132, 404], header_hex="#1e3a5f", font_size=8.0))
    el.append(Spacer(1, 14))

    el.append(Paragraph("Verified Release Highlights (v1.0.0 Final Audit)", h2))
    kpi_rows = [
        ["132 / 132 Passed", "7,340 / 7,340 (100%)", "5 / 5 Checks Passed"],
        ["Automated pytest suite\n(0 failures, ~90% coverage)", "Official payroll match\n(within 1 paisa tolerance)", "Zero unbalanced entries,\n0.00 ledger variance"],
        ["40 / 40 Exact Match", "193,036 / 193,036 Rows", "91 / 91 (100%)"],
        ["Trial Balance accounts\n(0 mismatched)", "Backup restored cleanly\nacross 29 tables", "OpenAPI endpoints with\nreal copy-paste examples"],
    ]
    t_kpi = Table(kpi_rows, colWidths=[178, 178, 180])
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#0f766e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("FONTSIZE", (0, 2), (-1, 2), 11),
        ("FONTSIZE", (0, 1), (-1, 1), 8.0),
        ("FONTSIZE", (0, 3), (-1, 3), 8.0),
        ("LEADING", (0, 1), (-1, 1), 10.5),
        ("LEADING", (0, 3), (-1, 3), 10.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
        ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#f8fafc")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    el.append(t_kpi)
    el.append(Spacer(1, 16))
    el.append(Paragraph(
        "<b>Table of Contents:</b> Page 1: Cover &amp; KPIs · Page 2: The Project in One Page · Page 3: System Architecture Diagram · "
        "Pages 4–6: Deep-Dive into All 5 Modules (What It Does, Proof, Lesson) · Page 7: End-to-End Trace (Attendance to Balance Sheet) · "
        "Page 8: Live Link, Demo Logins &amp; How to Test · Page 9: Challenges, Honest Limits &amp; Next Steps · "
        "Page 10: Task 20 Final Challenge, Interview Self-Check &amp; Sign-Off.",
        small,
    ))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 2: THE PROJECT IN ONE PAGE
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("1. The Project in One Page", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 4))

    el.append(Paragraph("The Business Problem", h2))
    el.append(Paragraph(
        "Growing Indian technology companies frequently manage workforce records, attendance sheets, monthly payroll calculations, "
        "vendor bills, client invoices, and accounting books in disconnected spreadsheets. This fragmentation creates five expensive failure modes: "
        "(1) manual LOP and Indian statutory tax miscalculations (EPF ceilings, ESI wage thresholds, Professional Tax, New-Regime TDS); "
        "(2) paying exited employees accidentally because HR exits do not sync with payroll; "
        "(3) double-entry accounting drift where payroll expenses do not equal Trial Balance accounts; "
        "(4) unmonitored Accounts Receivable where open customer invoices diverge from Ledger Account 1100; and "
        "(5) zero audit trail, backup discipline, or role-based access control over sensitive salary data.",
        body,
    ))

    el.append(Paragraph("The Users (3 Distinct Role Personas)", h2))
    users_tbl = [
        ["Role", "Who They Are", "Key Workflows Supported in LedgerForge"],
        ["ADMIN", "Finance Controller / Engineering Lead / CFO", "Full system control: manage user accounts, configure tax slabs & statutory rates, post/reverse ledger entries, run bulk payroll jobs, view Trial Balance / P&L / Balance Sheet / Departmental Cost reports, stream full exports."],
        ["HR", "HR Manager / Payroll Operations", "Onboard/update employees, manage salary revisions, approve leave requests, execute monthly payroll runs, generate payslip PDFs, review departmental payroll cost analytics, and download CSV/Excel exports."],
        ["EMPLOYEE", "Individual Contributor / Staff Member", "Self-service access strictly scoped to their own identity: view profile, submit leave requests, inspect attendance records, and download their own payslips while blocked (HTTP 403) from other employees' salaries or company books."],
    ]
    el.append(_styled_table(users_tbl, [68, 128, 340], header_hex="#1e3a5f", center_cols=(0,), font_size=7.8))
    el.append(Spacer(1, 5))

    el.append(Paragraph("What I Built (End-to-End Scope)", h2))
    el.append(Paragraph(
        "Over 20 days across 4 structured phases, I designed, built, tested, optimized, documented, and audited <b>LedgerForge v1.0.0</b>—a "
        "single, unified backend service and responsive web portal where HR events automatically drive mathematically exact financial statements:",
        body,
    ))
    built_bullets = [
        "&bull; <b>29 Normalized Relational Tables &amp; 11 Alembic Migrations:</b> Modelling departments, roles, employees, reporting trees, salary structures/revisions, 150,156 daily attendance logs, leave balances, 18 payroll runs (7,340 items), 47-account Chart of Accounts, 2,524 balanced journal entries, 743 client invoices, 501 vendor expense bills, tax slabs, and background jobs.",
        "&bull; <b>91 Documented API v1 Endpoints + Mobile Web Portal (/ui):</b> Strictly layered FastAPI routes (`Route → Service → ORM`), JWT HS256 + bcrypt RBAC, interactive Swagger UI with 100% example coverage, and a responsive `/ui` portal for login, payroll execution, and payslip PDF downloads.",
        "&bull; <b>Exact Indian Statutory &amp; Double-Entry Accounting Engine:</b> Database-driven tax rules computing Gross-to-Net pay to the exact paisa (`7,340/7,340 = 100.00%` match) and auto-posting balanced journal entries so `Debits == Credits` (`₹5,298,104,813.57`) and `Assets == Liabilities + Equity + Current Profit` (`₹463,762,958.65`, variance `₹0.00`).",
        "&bull; <b>Production Engineering Discipline:</b> Docker Compose multi-container stack (API, PostgreSQL, Redis, Celery worker), GitHub Actions CI, `EXPLAIN`-guided composite indexes (52–65% faster), 8,900x faster TTL report caching, structured JSON logs, DB-probing `/health`, tested 193,036-row disaster recovery, streaming CSV/Excel exports, and an independent Final Challenge analytics report.",
    ]
    for b in built_bullets:
        el.append(Paragraph(b, body))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 3: ARCHITECTURE DIAGRAM
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("2. System Architecture Diagram", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 4))
    el.append(Paragraph(
        "LedgerForge enforces a strict unidirectional layered architecture (<b>Client → Middleware → Route → Domain Service → ORM → Database</b>). "
        "HTTP routers never contain accounting or tax formulas; domain services never import FastAPI HTTP primitives. "
        "The same architecture diagram is maintained as Mermaid source in <font face='Courier'>docs/architecture.md</font> and <font face='Courier'>README.md</font>.",
        body,
    ))
    el.append(Spacer(1, 4))
    el.append(_build_architecture_drawing())
    el.append(Spacer(1, 8))

    el.append(Paragraph("Codebase Layer Breakdown &amp; Responsibilities", h2))
    arch_tbl = [
        ["Layer / Folder", "Key Files", "Engineering Responsibility & Design Rule"],
        ["HTTP Routes\napp/api/routes/", "15 route modules (employees, salaries, attendance, leave, payroll, ledger, invoices, expenses, tax, reports, jobs, exports, auth, health, ui)", "Request parsing, Pydantic v2 validation, JWT RBAC dependency injection (`require_role`), pagination, and `StreamingResponse` delivery."],
        ["Domain Services\napp/services/", "employee_service, payroll_service, ledger_service, invoice_service, expense_service, tax_service, report_service, export_service, job_service, auth_service", "Pure business logic: cycle detection, gross-to-net Indian payroll math, balanced double-entry posting, TTL report caching, chunked CSV/Excel generators."],
        ["Core Infrastructure\napp/core/", "config.py, security.py, logging.py, openapi.py, celery_app.py", "Environment-only Pydantic settings (zero secrets in code), HS256 JWT + bcrypt, structured JSON logs, 91/91 OpenAPI enrichment, Celery broker config."],
        ["Data Models &amp; DB\napp/models/ &amp; migrations/", "29 SQLAlchemy 2.0 ORM models + Alembic revisions 0001–0011", "Natural business keys (`EMP-0001`, `PR-2025-04`), CHECK constraints, soft deletes (`is_active`), composite performance indexes."],
        ["Ops, Seeding &amp; QA\nscripts/ &amp; tests/", "seed.py, verify_ledgerforge.py, smoke_test.py, backup_restore.py, 132 pytest tests", "One-command Excel workbook seeding, mathematical dataset verification, live smoke probes, atomic backup/restore proof, automated GitHub CI."],
    ]
    el.append(_styled_table(arch_tbl, [98, 174, 264], header_hex="#1e3a5f", font_size=7.4))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 4: MODULES 1 & 2
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("3. Deep-Dive Into the 5 Core Modules (Modules 1 &amp; 2)", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 3))

    # Module 1
    el.append(Paragraph("Module 1: Organization Hierarchy, Employees &amp; Compensation (Days 1–5)", h2))
    el.append(Paragraph(
        "<b>What It Does:</b> Models the complete company structure—11 departments (`D00`–`D10`), 58 graded roles with salary bands, "
        "745 employees with manager reporting hierarchies, 12,295 effective-dated salary structures, and 2,459 historical salary revisions. "
        "Provides paginated CRUD, search (`?q=`), department rosters, direct-report team trees (`/employees/{id}/team`), soft deletion "
        "(`is_active=false` so historical payroll never breaks), and effective-date salary lookups for any payroll month.",
        body,
    ))
    m1_tbl = [
        ["Dimension", "Evidence / Details"],
        ["One Concrete Proof", "Master seeder loads 745 employees, 11 departments, 58 roles, 12,295 salary structures & 2,459 revisions cleanly; Phase 1 test suite passed 71/71 tests (including DB CHECK constraints, email uniqueness, and multi-hop manager cycle rejection)."],
        ["One Key Lesson", "Modelling one current role per employee (`employees.role_id`) plus a separate `employee_assignments` history table avoided ambiguous salary-band joins while preserving full promotion history—and preventing hard deletes protects historical accounting integrity."],
    ]
    el.append(_styled_table(m1_tbl, [110, 426], header_hex="#1e3a5f", font_size=7.8))
    el.append(Spacer(1, 10))

    # Module 2
    el.append(Paragraph("Module 2: Attendance, Leave &amp; Indian Statutory Payroll Engine (Days 6–8)", h2))
    el.append(Paragraph(
        "<b>What It Does:</b> Processes 150,156 daily attendance logs, 3,442 leave requests, leave balances, and public holiday calendars to compute "
        "exact `calendar_days`, `days_employed`, `lop_days`, and `payable_days` per employee per month. Feeds payable days and active salary components "
        "(Basic, HRA, Conveyance, Medical, Special Allowance, Overtime, Variable Pay) into the Indian statutory engine computing Employee/Employer EPF, "
        "Employee/Employer ESI, state Professional Tax, and New-Regime TDS, then renders official downloadable PDF Payslips via ReportLab.",
        body,
    ))
    m2_tbl = [
        ["Dimension", "Evidence / Details"],
        ["One Concrete Proof", "Across all 18 historical payroll runs, `verify_ledgerforge.py payroll` verified 7,340 / 7,340 exported rows = 100.00% exact match within 1 paisa, with 0 unknown employees and 0 payments issued after an employee's exit_date."],
        ["One Key Lesson", "Never use binary floating-point (`float`) for payroll or tax calculations—strict `Decimal` arithmetic with explicit `ROUND_HALF_UP` at each statutory step (EPF wage cap, ESI threshold, monthly TDS projection) is what unlocked 100.00% exact paisa parity."],
    ]
    el.append(_styled_table(m2_tbl, [110, 426], header_hex="#0f766e", font_size=7.8))
    el.append(Spacer(1, 8))
    el.append(Paragraph(
        "<b>Statutory Guardrails Enforced in Code:</b> (a) Exited employees are excluded automatically past `exit_date` (verified: 0 post-exit rows); "
        "(b) Mid-month joiners/leavers are prorated by `payable_days / calendar_days`; (c) Payroll runs follow an explicit state machine (`DRAFT → APPROVED → PAID`) "
        "preventing accidental duplicate runs for the same period.",
        callout,
    ))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 5: MODULES 3 & 4
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("3. Deep-Dive Into the 5 Core Modules (Modules 3 &amp; 4)", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 3))

    # Module 3
    el.append(Paragraph("Module 3: Double-Entry General Ledger, Invoicing &amp; Vendor Expenses (Days 9–12)", h2))
    el.append(Paragraph(
        "<b>What It Does:</b> Implements a full double-entry accounting engine backed by a 47-account Chart of Accounts (`1000` Assets, `2000` Liabilities, "
        "`3000` Equity, `4000` Income, `5000` Expenses). Every posted journal entry enforces `SUM(debit) == SUM(credit)` atomically and supports non-destructive "
        "reversals. Integrates three operational sub-ledgers directly into the books: (1) all 18 monthly payroll runs auto-post cost-center expense debits and statutory "
        "payable credits; (2) 743 client invoices and 709 invoice payments drive Accounts Receivable (`1100`); and (3) 501 vendor expense bills include duplicate-bill detection "
        "and monthly expense-to-ledger reconciliation.",
        body,
    ))
    m3_tbl = [
        ["Dimension", "Evidence / Details"],
        ["One Concrete Proof", "Across 2,524 posted journal entries and 6,784 journal lines: 0 unbalanced entries (debits - credits = 0.00), largest monthly payroll-to-ledger difference = 0.00 across all 18 months, and Ledger Account 1100 (₹139,394,278.00) equals open invoices (₹139,394,278.00) to the paisa."],
        ["One Key Lesson", "Accounting records must be immutable once posted—supporting corrective reversal entries instead of `DELETE`/`UPDATE` mutations preserves full auditability and guarantees that sub-ledger totals never silently drift from the general ledger."],
    ]
    el.append(_styled_table(m3_tbl, [110, 426], header_hex="#1e3a5f", font_size=7.8))
    el.append(Spacer(1, 10))

    # Module 4
    el.append(Paragraph("Module 4: Security (JWT RBAC), Configurable Tax Engine &amp; Financial Statements (Days 13–15)", h2))
    el.append(Paragraph(
        "<b>What It Does:</b> Secures every business endpoint with `bcrypt` password hashing, signed HS256 JWT tokens, and declarative FastAPI role dependencies "
        "(`ADMIN`, `HR`, `EMPLOYEE`). Replaces hardcoded statutory constants with database-backed `tax_slabs`, `tax_parameters`, and `statutory_rates` tables "
        "(editable via API with rerun simulation). Builds the three canonical financial statements—<b>Trial Balance</b>, <b>Profit &amp; Loss</b>, and <b>Balance Sheet</b>—"
        "separating parent group headers (`is_group='Y'`) from leaf accounts (`is_group='N'`) so parent totals are rolled up cleanly without ever double-counting.",
        body,
    ))
    m4_tbl = [
        ["Dimension", "Evidence / Details"],
        ["One Concrete Proof", "`verify_ledgerforge.py trial-balance` matched 40 / 40 accounts (0 mismatched); Trial Balance balances at ₹5,298,104,813.57 (diff ₹0.00); Balance Sheet verifies Assets (₹463,762,958.65) == Liabilities (₹77,499,607.07) + Equity (₹161,579,764.00) + Current Profit (₹224,683,587.58) with ₹0.00 difference."],
        ["One Key Lesson", "Explicitly filtering `is_group == 'N'` in every financial aggregation prevented subtle 2x double-counting bugs on parent accounts (1000/2000/3000/4000/5000), and moving tax slabs into database tables turns annual budget changes into data updates instead of risky code deployments."],
    ]
    el.append(_styled_table(m4_tbl, [110, 426], header_hex="#0f766e", font_size=7.8))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 6: MODULE 5
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("3. Deep-Dive Into the 5 Core Modules (Module 5)", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 3))

    el.append(Paragraph("Module 5: Production Readiness, Performance, Backups &amp; Data Exports (Days 16–19)", h2))
    el.append(Paragraph(
        "<b>What It Does:</b> Elevates LedgerForge from a local prototype into an operable production service: (1) Celery + Redis asynchronous job queue with "
        "graceful local thread fallback for bulk multi-month payroll runs; (2) versioned `/api/v1` routing, Docker Compose orchestration, Render Infrastructure-as-Code "
        "(`render.yaml`), GitHub Actions CI, and a mobile-friendly `/ui` web portal; (3) `EXPLAIN`-driven composite database indexes (migration `0011`), uniform "
        "pagination, 60-second TTL caching on Trial Balance, structured JSON request logging, and a DB-probing `/health` endpoint returning HTTP `503` on database failure; "
        "(4) automated backup and fresh-database restore proof (`scripts/backup_restore.py`); and (5) streaming CSV &amp; Excel (`.xlsx`) export endpoints for employees, "
        "payroll, and ledger with date filters, an incremental `/exports/changes?since=...` delta feed, and 91/91 OpenAPI examples.",
        body,
    ))

    el.append(Paragraph("Before-and-After Performance &amp; Disaster Recovery Proof", h2))
    perf_rows = [
        ["Measured Workload", "Before Optimization", "After Index / Cache", "Gain", "Engineering Change"],
        ["Attendance 30-Day Query (150,156 rows)", "45.75 ms (Temp B-Tree)", "21.63 ms", "52.7% faster", "Composite index ix_attendance_date_emp_status"],
        ["Trial Balance Ledger Join (6,784 lines)", "22.77 ms (Full scan)", "9.44 ms", "58.5% faster", "Index ix_journal_entries_status"],
        ["Open Invoices AR Query (743 rows)", "1.14 ms (Status scan)", "0.40 ms", "64.9% faster", "Covering index ix_invoices_status"],
        ["Trial Balance Report (Cold → TTL Hot)", "87.30 ms", "0.01 ms", "8,907x faster", "60s TTL cache w/ ledger write invalidation"],
        ["Payroll Run Read Throughput", "2.14 ms / run", "0.67 ms / run", "68.7% faster", "Index ix_payroll_runs_status"],
        ["Backup → Fresh DB Restore (29 tables)", "50.8 MB backup", "193,036 / 193,036", "100% parity", "Automated verification in backup_restore.py"],
    ]
    el.append(_styled_table(perf_rows, [145, 92, 76, 56, 167], header_hex="#334155", center_cols=(2, 3), font_size=7.2))
    el.append(Spacer(1, 8))

    m5_tbl = [
        ["Dimension", "Evidence / Details"],
        ["One Concrete Proof", "Streaming CSV export `/api/v1/exports/payroll` produced 7,340 rows matching official payroll 100.00% within 1 paisa; `backup_restore.py` restored all 193,036 rows across 29 tables with 0 mismatches; `test_exports.py` enforces 91/91 (100%) OpenAPI examples automatically."],
        ["One Key Lesson", "Measure first with `EXPLAIN`, fix second, and never trust an untested backup—practising a real restore into a blank database and writing stranger-ready documentation exposed subtle edge cases (like nullable `JournalEntry.created_at` strings) that unit tests alone would have missed."],
    ]
    el.append(_styled_table(m5_tbl, [110, 426], header_hex="#1e3a5f", font_size=7.8))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 7: HOW THE MODULES CONNECT (ATTENDANCE -> BALANCE SHEET)
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("4. How the Modules Connect — Attendance to Balance Sheet", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 3))
    el.append(Paragraph(
        "To demonstrate how all five modules behave as one cohesive financial machine, below is the exact, database-verified lifecycle of "
        "<b>Payroll Run <font face='Courier'>PR-2025-04</font> (April 2025, 386 active employees)</b> and individual employee "
        "<b><font face='Courier'>EMP-0002</font> (Jatin Jayaraman)</b> from daily attendance all the way into the final Balance Sheet.",
        body,
    ))
    el.append(_build_payroll_flow_drawing())
    el.append(Spacer(1, 6))

    trace_rows = [
        ["Stage", "Module / Table", "Exact Real Data Recorded for April 2025 (PR-2025-04)"],
        [
            "1. Attendance\n&amp; Leave",
            "Module 2\nattendance, leave_requests",
            "EMP-0002 has 30 calendar days in April 2025, 30 days employed, 0.00 LOP days → 30.00 payable days (100% proration factor). Exited employees past exit_date are excluded (0 violations across 386 employees).",
        ],
        [
            "2. Salary &\nTax Rules",
            "Modules 1 &amp; 4\nsalary_structures, tax_slabs",
            "Effective April 2025 salary structure loaded for EMP-0002: Fixed Monthly Gross ₹179,130.40. Active FY2025-26 New-Regime TDS slabs and statutory rates (EPF cap ₹1,800, PT ₹200) fetched from database tables.",
        ],
        [
            "3. Payroll\nCalculation",
            "Module 2\npayroll_runs, payroll_items",
            "EMP-0002 result: Gross ₹179,130.40 − Deductions ₹20,625.79 (EPF ₹1,800.00 + PT ₹200.00 + TDS ₹18,625.79) = Net Pay ₹158,504.61; Employer Cost = ₹180,930.40 (+₹1,800 Employer PF). Full PR-2025-04 total (386 items): Gross ₹52,740,110.43 | Net ₹46,035,111.16 | Employer Cost ₹53,363,392.08.",
        ],
        [
            "4. Payslip\n&amp; Export",
            "Modules 2 &amp; 5\nPDF &amp; /exports/payroll",
            "PDF Payslip rendered via ReportLab (`/api/v1/payroll/runs/PR-2025-04/payslips/EMP-0002/pdf`) and row streamed via `/api/v1/exports/payroll?run_id=PR-2025-04` (CSV or Excel .xlsx).",
        ],
        [
            "5. Double-Entry\nLedger Posting",
            "Module 3\njournal_entries, journal_lines",
            "Auto-posted Journal Entry JE-000105 (2025-04-30, POSTED, 43 lines): DEBIT cost-center Payroll Expenses (Accts 5001–5005) = ₹53,363,392.08; CREDIT Salaries Payable 2100 (₹46,035,111.16), EPF Payable 2110 (₹1,237,927.88), ESI Payable 2120 (₹5,314.10), TDS Payable 2130 (₹6,007,238.94), PT Payable 2140 (₹74,800.00), Advances 1300 (₹3,000.00) = ₹53,363,392.08. Variance = ₹0.00.",
        ],
        [
            "6. Financial\nStatements",
            "Module 4\nTB, P&amp;L, Balance Sheet",
            "18 posted payroll entries sum to ₹861,586,392.42 in P&L Accts 5001–5005 (matching Departmental Payroll Cost Report to the paisa). Trial Balance balances at ₹5,298,104,813.57; Net Profit ₹224,683,587.58 flows into Balance Sheet Equity so Assets == Liabilities + Equity + Profit = ₹463,762,958.65 (diff ₹0.00).",
        ],
    ]
    el.append(_styled_table(trace_rows, [68, 92, 376], header_hex="#1e3a5f", font_size=7.3))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 8: LIVE LINK, DEMO LOGINS & HOW TO TEST
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("5. Live Deployment Link, Demo Logins &amp; How to Test", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 4))

    el.append(Paragraph("Deployment URLs &amp; Instant Local Startup", h2))
    el.append(Paragraph(
        f"&bull; <b>Live Cloud Production URL (Render + Hosted PostgreSQL):</b> <a href='{LIVE_URL}/docs' color='#2563eb'><b>{LIVE_URL}/docs</b></a><br/>"
        f"&bull; <b>Mobile Web UI:</b> <a href='{LIVE_URL}/ui' color='#2563eb'>{LIVE_URL}/ui</a> &nbsp;|&nbsp; "
        f"<b>Health Probe:</b> <a href='{LIVE_URL}/health' color='#2563eb'>{LIVE_URL}/health</a> (HTTP 200, database: healthy)<br/>"
        f"&bull; <b>One-Command Local Docker Stack:</b> <font face='Courier'>cp .env.example .env &amp;&amp; docker compose up --build</font> "
        f"(launches PostgreSQL 16, Redis, FastAPI on <font face='Courier'>http://localhost:8000</font>, and Celery Worker).<br/>"
        f"&bull; <b>Note on Free-Tier Cold Start:</b> Render's free web tier sleeps after 15 minutes of inactivity; the first request takes ~30–45s to wake, after which responses are sub-second.",
        body,
    ))

    el.append(Paragraph("Demo Accounts (All 3 Roles — Verified Seeded Credentials)", h2))
    login_tbl = [
        ["Role", "Username / Login", "Password", "User / Emp ID", "What You Can Test With This Account"],
        ["ADMIN", "admin  (alias for\nsanjay.kumar@znova-demo.example)", "LedgerForge2025!", "U-0099 /\nEMP-0099", "Full access: /ui payroll runs, Trial Balance / P&L / Balance Sheet, Departmental Cost report, CSV/Excel exports, tax slab edits, user management."],
        ["HR", "hemant.mathew@znova-demo.example", "LedgerForge2025!", "U-0011 /\nEMP-0011", "HR & Payroll ops: Employee CRUD, salary revisions, leave approvals, monthly payroll runs, payslip PDFs, departmental cost analytics & exports."],
        ["EMPLOYEE", "jatin.jayaraman@znova-demo.example", "LedgerForge2025!", "U-0002 /\nEMP-0002", "Self-service only: view own profile/payslip (`EMP-0002`), submit leave request. Calling admin/HR reports returns HTTP 403 Forbidden (proves RBAC)."],
    ]
    el.append(_styled_table(login_tbl, [54, 146, 78, 56, 202], header_hex="#0f766e", center_cols=(0, 3), font_size=7.2))
    el.append(Spacer(1, 6))

    el.append(Paragraph("Step-by-Step Testing Guide (Web UI, Swagger &amp; CLI)", h2))
    el.append(Paragraph(
        "<b>A. Web Portal Walkthrough (<font face='Courier'>/ui</font>):</b> Open <font face='Courier'>/ui</font> on desktop or phone → log in as "
        "<font face='Courier'>admin</font> / <font face='Courier'>LedgerForge2025!</font> → calculate payroll for <font face='Courier'>EMP-0002</font> (<font face='Courier'>2025-04</font>) → "
        "inspect Gross/PF/PT/TDS/Net breakdown → download official PDF payslip.<br/>"
        "<b>B. Interactive API Testing (<font face='Courier'>/docs</font>):</b> Open <font face='Courier'>/docs</font> → execute <font face='Courier'>POST /api/v1/auth/login</font> "
        "(pre-filled example!) → copy <font face='Courier'>access_token</font> → click <b>Authorize</b> → test any of the 91 enriched endpoints including "
        "<font face='Courier'>GET /api/v1/reports/department-payroll-cost</font> and <font face='Courier'>GET /api/v1/exports/payroll?format=xlsx</font>.<br/>"
        "<b>C. Automated CLI Verification:</b>",
        body,
    ))
    el.append(Paragraph(
        "# 1. Run full 132-test automated suite (in-memory SQLite, zero external setup needed)<br/>"
        "pytest -q<br/><br/>"
        "# 2. Run all 3 official verifier audits against exported data<br/>"
        "python scripts/verify_ledgerforge.py checks --data exports<br/>"
        "python scripts/verify_ledgerforge.py payroll exports/task19_payroll_export.csv --data exports<br/>"
        "python scripts/verify_ledgerforge.py trial-balance exports/trial_balance.csv --data exports<br/><br/>"
        "# 3. Run live smoke test &amp; disaster recovery backup/restore proof<br/>"
        "python scripts/smoke_test.py --url http://localhost:8000<br/>"
        "python scripts/backup_restore.py",
        code_s,
    ))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 9: CHALLENGES, MISTAKES, HONEST LIMITS & IMPROVEMENTS
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("6. Challenges, Mistakes &amp; What I Learned", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 3))

    chal_tbl = [
        ["Challenge / Mistake", "What Went Wrong", "How I Fixed It &amp; What I Learned"],
        [
            "Paisa rounding drift in early payroll runs",
            "Intermediate float rounding caused 1–2 paisa mismatches on TDS & EPF across 7,340 rows",
            "Switched every salary/tax calculation to `Decimal` with `ROUND_HALF_UP` at statutory boundaries → achieved 7,340/7,340 (100.00%) exact match.",
        ],
        [
            "Group account double-counting risk in statements",
            "Summing all ChartOfAccount rows counted both parent groups (e.g. 5000) and leaf children (5001–5005)",
            "Separated `is_group='N'` leaves from `is_group='Y'` rollups across Trial Balance, P&L, and Balance Sheet → 40/40 accounts exact match.",
        ],
        [
            "ORM column &amp; CHECK constraint mismatches in Task 19",
            "Export fixtures assumed `item_id`/`basic_pay` and uppercase `'MALE'` instead of `payroll_item_id`/`basic` and Title Case `'Male'`",
            "Audited actual SQLAlchemy table metadata and constraints; aligned `export_service.py`, OpenAPI examples, and fixtures cleanly.",
        ],
        [
            "Incremental delta export missed JournalEntries on SQLite",
            "`JournalEntry.created_at` was nullable `VARCHAR(32)` without a DB `server_default` unlike `TimestampMixin` tables",
            "Updated delta query to check `created_at >= since.isoformat() OR entry_date >= since.date()` and locked behavior with pytest.",
        ],
        [
            "OpenAPI docs initially covered only 53/90 endpoints",
            "Only `requestBody` routes received examples; GET list/report routes had none",
            "Added parameter and 200 response examples in `app/core/openapi.py` plus an automated pytest assertion guaranteeing 100% (91/91) coverage.",
        ],
    ]
    el.append(_styled_table(chal_tbl, [118, 174, 244], header_hex="#7c2d12", font_size=7.3))
    el.append(Spacer(1, 8))

    el.append(Paragraph("7. Honest Limits &amp; What I Would Improve Next", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 3))

    limits_tbl = [
        ["Area", "Honest Current Limit in v1.0.0", "Planned Next-Step Improvement (v1.1+)"],
        ["Cloud Hosting Tier", "Live on Render Free Tier (ledgerforge-ijqw.onrender.com), which sleeps after 15 min idle (~30–45s cold wake) and expires free Postgres after 30 days.", "Upgrade to Render Starter (~$14/mo for always-on web + managed Postgres) with automated nightly `pg_dump` to S3/R2."],
        ["Report Caching", "60-second Trial Balance TTL cache lives in process memory—safe for 1 worker, but not shared across multiple horizontal replicas.", "Move `_REPORT_CACHE` keys and invalidation pub/sub into Redis (`REDIS_URL`), which is already part of `docker-compose.yml`."],
        ["Large Excel Exports", "CSV streams chunk-by-chunk with constant RAM, whereas `.xlsx` buffers the ZIP workbook in memory via `openpyxl` write-only mode.", "Offload >50k-row Excel exports to a Celery background job that writes to object storage and returns a signed download URL."],
        ["Banking &amp; E-Filing", "Payroll marks runs `PAID` and posts balanced ledger entries, but does not call bank NEFT/IMPS APIs or EPFO/TRACES filing portals.", "Add pluggable payout adapters (RazorpayX / bank H2H SFTP) and statutory ECR / Form 24Q export generators."],
        ["Multi-Tenancy &amp; Auth", "Single-company schema with admin-managed bcrypt accounts (no self-service SMTP password reset or tenant isolation).", "Introduce `organization_id` row-level security, refresh-token rotation, and transactional SMTP/SES notifications."],
    ]
    el.append(_styled_table(limits_tbl, [92, 220, 224], header_hex="#334155", font_size=7.3))

    el.append(PageBreak())

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 10: FINAL CHALLENGE, CAREER LESSON & SIGN-OFF
    # ═══════════════════════════════════════════════════════════════════════
    el.append(Paragraph("8. Task 20 Final Challenge — Built Independently on Its Own Branch", h1))
    el.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    el.append(Spacer(1, 3))

    el.append(Paragraph(
        f"<b>Branch:</b> <a href='{BRANCH_URL}' color='#2563eb'><font face='Courier'>feat/department-payroll-cost-report</font></a> "
        f"(developed without a step-by-step guide, tested, pushed, and merged via <font face='Courier'>--no-ff</font> into <font face='Courier'>master</font>).<br/>"
        "<b>What I Decided to Build &amp; Why:</b> LedgerForge already had GL-account Trial Balance and company-level P&amp;L statements, "
        "but lacked an executive department-level cost breakdown. I designed and shipped <b><font face='Courier'>GET /api/v1/reports/department-payroll-cost</font></b> "
        "(supporting <font face='Courier'>run_id</font>, <font face='Courier'>start_date</font>, and <font face='Courier'>end_date</font> filters) so CFOs and HR leads can instantly "
        "see headcount, gross pay, deductions, net pay, employer PF/ESI burden, average pay, and percentage share of company payroll per department.<br/>"
        "<b>Architecture &amp; Quality Decisions:</b> Single SQL <font face='Courier'>GROUP BY</font> join on <font face='Courier'>payroll_items</font> + <font face='Courier'>departments</font> "
        "(zero N+1 queries), exact <font face='Courier'>Decimal</font> math with safe empty-range guards, strict <font face='Courier'>ADMIN/HR</font> RBAC (blocking <font face='Courier'>EMPLOYEE</font> "
        "with HTTP 403), OpenAPI example keeping 91/91 (100%) coverage, and 4 automated tests in <font face='Courier'>tests/test_department_cost_report.py</font>.",
        body,
    ))

    el.append(Paragraph("Live 18-Month Output (Reconciles to P&amp;L Accounts 5001–5005 to the Exact Paisa)", h2))
    dept_rows = [
        ["Dept ID", "Department Name", "Unique Emp", "Items", "Total Employer Cost (INR)", "Share %"],
        ["D01", "Engineering", "201", "2,763", "341,011,491.13", "39.58%"],
        ["D04", "Sales", "56", "770", "126,678,542.69", "14.70%"],
        ["D03", "Data & AI", "61", "911", "110,724,768.20", "12.85%"],
        ["D02", "Product & Design", "32", "457", "70,628,351.82", "8.20%"],
        ["D06", "Customer Support", "70", "930", "48,046,050.62", "5.58%"],
        ["D08", "Finance & Accounts", "21", "297", "42,190,095.48", "4.90%"],
        ["D09", "Operations & IT", "39", "502", "40,470,326.11", "4.70%"],
        ["D07", "Human Resources", "23", "298", "25,341,182.07", "2.94%"],
        ["D05", "Marketing", "14", "224", "24,058,878.44", "2.79%"],
        ["D10", "Legal & Compliance", "12", "170", "23,630,719.45", "2.74%"],
        ["D00", "Executive Office", "1", "18", "8,805,986.41", "1.02%"],
        ["TOTAL", "All 11 Departments (Matches P&L 5001–5005 = ₹861,586,392.42)", "530", "7,340", "861,586,392.42", "100.00%"],
    ]
    el.append(_styled_table(dept_rows, [48, 224, 52, 42, 114, 56], header_hex="#1e3a5f", center_cols=(0, 2, 3, 5), font_size=7.0))
    el.append(Spacer(1, 8))

    el.append(Paragraph("9. Career Lesson &amp; Final Interview Self-Check", h2))
    el.append(Paragraph(
        "<b>What I Would Rebuild Differently (Career Lesson):</b> <i>\"With what I know now, I would define one shared SQLAlchemy "
        "<font face='Courier'>Base</font> contract on Day 1 enforcing timezone-aware <font face='Courier'>TIMESTAMP WITH TIME ZONE</font> "
        "audit columns (<font face='Courier'>created_at</font>, <font face='Courier'>updated_at</font>) and uniform uppercase enum values across every "
        "single table before writing Migration 0001—eliminating weeks of downstream friction in incremental exports, OpenAPI schemas, and cross-table tests.\"</i><br/><br/>"
        "<b>Interview Self-Check:</b> Yes—I can walk an interviewer through every layer of LedgerForge, trace any employee's payslip into the Trial Balance "
        "and Balance Sheet, profile and index a slow SQL query live, add a tested feature on a clean Git branch, and defend every architectural trade-off honestly.",
        callout,
    ))
    el.append(Spacer(1, 4))
    el.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1")))
    el.append(Paragraph(
        "<b>Final Handover Sign-Off:</b> I built, tested, audited, documented, and released a complete HR, Indian statutory payroll, and double-entry "
        "accounting backend from an empty folder to <b>LedgerForge v1.0.0</b>. — <b>Ancilin P G (GM00210), November 19, 2026</b>",
        small,
    ))

    doc.build(el, onFirstPage=_on_first, onLaterPages=_on_later)
    print(f"✓ Final Consolidated PDF written ({page_counter['pages']} pages): {OUTPUT_PDF}")
    for dest in (REPORTS_PDF, DESKTOP_PDF):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_PDF, dest)
        print(f"  → copied to {dest}")
    return page_counter["pages"]


if __name__ == "__main__":
    pages = build_pdf()
    assert 8 <= pages <= 12, f"Consolidated report must be 8–12 pages, got {pages}!"
