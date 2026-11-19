"""Generate Python_Ancillin_Final_Consolidated_Report.pdf — Complete Days 1–20 Consolidated Handover Report (v1.0.0)."""

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
OUTPUT_PDF = ROOT / "Python_Ancillin_Final_Consolidated_Report.pdf"
REPORTS_PDF = ROOT / "reports" / "Python_Ancillin_Final_Consolidated_Report.pdf"
DESKTOP_PDF = Path(r"C:\Users\ancillin\Desktop\Python_Ancillin_Final_Consolidated_Report.pdf")

GITHUB_URL = "https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model"
TAG_URL = f"{GITHUB_URL}/releases/tag/v1.0.0"
CHALLENGE_BRANCH_URL = f"{GITHUB_URL}/tree/feat/department-payroll-cost-report"


def _styled_table(data: list[list[str]], col_widths: list[int], header_hex: str = "#1e3a5f", center_cols: tuple[int, ...] = ()) -> Table:
    tbl = Table(data, colWidths=col_widths)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_hex)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.7),
        ("LEADING", (0, 0), (-1, -1), 8.8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    for col in center_cols:
        style_cmds.append(("ALIGN", (col, 0), (col, -1), "CENTER"))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


def build_pdf() -> None:
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=15.5, leading=19, textColor=colors.HexColor("#0f172a"), spaceAfter=2,
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=9.2, leading=12, textColor=colors.HexColor("#2563eb"), spaceAfter=3,
    )
    meta_style = ParagraphStyle(
        "MetaText", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7.8, leading=10.4, textColor=colors.HexColor("#475569"), spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "SectionHead", parent=styles["Normal"], fontName="Helvetica-Bold",
        fontSize=10.2, leading=13, textColor=colors.HexColor("#1e3a5f"), spaceBefore=7, spaceAfter=2.5,
    )
    body_style = ParagraphStyle(
        "BodyText2", parent=styles["Normal"], fontName="Helvetica",
        fontSize=7.9, leading=10.8, textColor=colors.HexColor("#1e293b"), spaceAfter=3,
    )
    code_style = ParagraphStyle(
        "CodeBlock", parent=styles["Normal"], fontName="Courier",
        fontSize=6.8, leading=9.0, textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"), spaceAfter=3, leftIndent=6, rightIndent=6,
    )

    elements = []

    # ── Header ──
    elements.append(Paragraph("LedgerForge v1.0.0 — Final Consolidated Engineering &amp; Handover Report", title_style))
    elements.append(Paragraph("Complete 20-Day Delivery (Phases 1–4): HR, Indian Statutory Payroll &amp; Double-Entry Accounting Engine", subtitle_style))
    elements.append(Paragraph("Candidate: Ancilin P G &nbsp;|&nbsp; ID: GM00210 &nbsp;|&nbsp; Track: Python Developer &nbsp;|&nbsp; Release Date: November 19, 2026", meta_style))
    elements.append(Paragraph(
        f'GitHub Repository: <a href="{GITHUB_URL}" color="#2563eb">{GITHUB_URL}</a><br/>'
        f'Release Tag v1.0.0: <a href="{TAG_URL}" color="#2563eb">{TAG_URL}</a> &nbsp;|&nbsp; '
        f'Final Challenge Branch: <a href="{CHALLENGE_BRANCH_URL}" color="#2563eb">feat/department-payroll-cost-report</a>',
        meta_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1")))
    elements.append(Spacer(1, 3))

    # ── 1. Executive Summary ──
    elements.append(Paragraph("1. Executive Summary", section_style))
    elements.append(Paragraph(
        "From an empty workspace on Day 1 to a tagged <b>v1.0.0</b> production release on Day 20, LedgerForge delivers a complete, "
        "mathematically verified HR, Indian statutory payroll, and double-entry accounting platform built with <b>FastAPI</b>, "
        "<b>SQLAlchemy 2.0</b>, <b>PostgreSQL 16</b>, <b>Alembic</b>, <b>Celery + Redis</b>, and <b>Docker Compose</b>. "
        "Across 29 normalized database tables and 91 documented API operations, the system processes 18 months of historical operations "
        "(745 employees, 150,156 attendance rows, 7,340 payroll items, 2,524 journal entries, 743 invoices, and 501 vendor expense bills) "
        "with zero accounting variance.",
        body_style,
    ))

    # ── 2. Consolidated Phase 1–4 Delivery Matrix ──
    elements.append(Paragraph("2. Complete 20-Day Milestone Delivery Matrix (Phases 1–4)", section_style))
    phase_rows = [
        ["Phase", "Days / Tasks", "Core Capabilities Shipped", "Git Tag", "Verification Proof"],
        ["Phase 1:\nFoundation", "Days 1–5\n(LF-01 to LF-05)", "Layered FastAPI app, Docker + Postgres, Alembic (0001–0003), Departments/Roles/Employees + cycle checks, Excel master seeder, Salary structures & revisions", "phase-1\nv0.0.1", "71 passed\n5/5 checks"],
        ["Phase 2:\nCore Engine", "Days 6–10\n(LF-06 to LF-10)", "Attendance (150k rows) & Leave workflows, Indian Gross-to-Net Payroll Engine (EPF/ESI/PT/TDS), PDF Payslips, Double-Entry Ledger (47 COA), Invoices & AR", "phase-2", "96 passed\n7,340/7,340 payroll"],
        ["Phase 3:\nConnected System", "Days 11–15\n(LF-11 to LF-15)", "Vendors & Expense Bills + duplicate detection, 18-Run Payroll-to-Books posting, JWT + bcrypt RBAC, DB-driven Tax Engine, Trial Balance / P&L / Balance Sheet", "phase-3", "113 passed\n40/40 Trial Balance"],
        ["Phase 4:\nProduction & Handover", "Days 16–20\n(LF-16 to LF-20)", "Celery/Redis jobs, /api/v1, CI/CD, Render Blueprint + /ui portal, EXPLAIN indexing (52–65% faster), TTL cache (8,900x), JSON logs, DB /health, Backup/Restore, Streaming CSV/Excel exports, 91/91 OpenAPI examples, Final Challenge & v1.0.0 audit", "v1.0.0", "132 passed\n5/5 checks\n193,036/193,036 restore"],
    ]
    elements.append(_styled_table(phase_rows, [68, 66, 240, 48, 108], center_cols=(3,)))

    # ── 3. Final Official Audit Evidence ──
    elements.append(Paragraph("3. Final Release Audit Evidence (Executed November 19, 2026)", section_style))
    audit_rows = [
        ["Audit Gate", "Verification Command", "Exact Outcome", "Status"],
        ["Official Integrity Checks", "python scripts/verify_ledgerforge.py checks --data exports", "5/5 checks passed (debits-credits=0.0, payroll-ledger diff=0.00, AR 1100=139,394,278.00, unknown emp=0, post-exit=0)", "PASS"],
        ["Official Payroll Export", "python scripts/verify_ledgerforge.py payroll exports/task19_payroll_export.csv --data exports", "Rows expected 7340, found 7340 — Exact matches (within 1 paisa): 7340/7340 = 100.00%", "PASS"],
        ["Official Trial Balance", "python scripts/verify_ledgerforge.py trial-balance exports/trial_balance.csv --data exports", "Accounts compared: 40, mismatched: 0", "PASS"],
        ["Automated Test Suite", "pytest -q", "132 passed, 0 failed (~90% statement coverage across all modules)", "PASS"],
        ["OpenAPI Examples Audit", "tests/test_exports.py::test_openapi_schema_has_rich_examples", "91 / 91 (100.0%) API operations enriched with realistic examples", "PASS"],
        ["Disaster Recovery Restore", "python scripts/backup_restore.py", "193,036 / 193,036 rows restored across 29 tables (100% parity)", "PASS"],
    ]
    elements.append(_styled_table(audit_rows, [94, 178, 224, 34], header_hex="#0f766e", center_cols=(3,)))

    elements.append(Spacer(1, 3))
    elements.append(Paragraph(
        "<b>Verbatim Official Verifier Output:</b>",
        body_style,
    ))
    elements.append(Paragraph(
        "PASS  Every journal entry balances - debits-credits=0.0, unbalanced entries=0<br/>"
        "PASS  Payroll equals ledger, every month - largest monthly difference=0.00<br/>"
        "PASS  Receivables equal open invoices - ledger 1100=139,394,278.00, open invoices=139,394,278.00<br/>"
        "PASS  Payroll employees exist - payroll rows with unknown employee=0<br/>"
        "PASS  Nobody is paid after leaving - payroll rows after exit_date=0<br/>"
        "5/5 checks passed | Payroll: 7340/7340 = 100.00% | Trial Balance: 40 compared, 0 mismatched",
        code_style,
    ))

    elements.append(PageBreak())

    # ── 4. Task 20 Final Challenge ──
    elements.append(Paragraph("4. Final Challenge — Built Independently on Feature Branch", section_style))
    elements.append(Paragraph(
        "<b>Feature Selected:</b> Executive Departmental Payroll Cost &amp; Statutory Breakdown Report "
        "(<font face='Courier'>GET /api/v1/reports/department-payroll-cost</font>) developed independently on Git branch "
        "<font face='Courier'>feat/department-payroll-cost-report</font> and merged cleanly (<font face='Courier'>--no-ff</font>) into <font face='Courier'>master</font>.<br/>"
        "<b>Why Chosen:</b> Trial Balance reports by GL account and P&amp;L summarizes company-level totals, leaving a real CFO/HR analytics gap: "
        "understanding total employer cost (Gross + Employer PF + Employer ESI) and percentage budget share per department.<br/>"
        "<b>Key Engineering Decisions:</b> (1) Single SQL <font face='Courier'>GROUP BY</font> query joining <font face='Courier'>payroll_items</font> and "
        "<font face='Courier'>departments</font> to eliminate N+1 ORM queries; (2) Exact <font face='Courier'>Decimal</font> arithmetic with <font face='Courier'>ROUND_HALF_UP</font> "
        "and safe zero-division guards for empty date ranges; (3) Strict <font face='Courier'>ADMIN/HR</font> RBAC (blocking <font face='Courier'>EMPLOYEE</font> with HTTP 403); "
        "(4) Full OpenAPI example + 4 unit/integration tests (<font face='Courier'>tests/test_department_cost_report.py</font>).",
        body_style,
    ))

    dept_rows = [
        ["Dept ID", "Department Name", "Unique Emp", "Payroll Items", "Total Employer Cost (INR)", "Cost Share"],
        ["D01", "Engineering", "201", "2,763", "341,011,491.13", "39.58%"],
        ["D04", "Sales", "56", "770", "126,678,542.69", "14.70%"],
        ["D03", "Data & AI", "61", "911", "110,724,768.20", "12.85%"],
        ["D02", "Product & Design", "32", "457", "70,628,351.82", "8.20%"],
        ["D06", "Customer Support", "70", "930", "48,046,050.62", "5.58%"],
        ["D08–D00", "Remaining 6 Departments (Finance, Ops, HR, Mktg, Legal, Exec)", "110", "1,509", "164,497,187.96", "19.09%"],
        ["TOTAL", "All 11 Departments (18 Months)", "530", "7,340", "861,586,392.42", "100.00%"],
    ]
    elements.append(_styled_table(dept_rows, [48, 198, 56, 62, 110, 56], header_hex="#334155", center_cols=(0, 2, 3, 5)))

    # ── 5. Honest Limits & Next Steps ──
    elements.append(Paragraph("5. Honest Scope Boundaries, Known Limits &amp; Next Steps", section_style))
    elements.append(Paragraph(
        "&bull; <b>Render Free-Tier Live URL Audit Note:</b> On final probe (Nov 19, 2026), the previously deployed Render free-tier URL "
        "returned <font face='Courier'>HTTP 404 (x-render-routing: no-server)</font> due to Render's free-tier inactivity spin-down / 30-day Postgres expiry. "
        "Redeploying tag <font face='Courier'>v1.0.0</font> via <font face='Courier'>render.yaml</font> (or upgrading to Render Starter ~$14/mo total) "
        "restores permanent 24/7 uptime with zero code changes.<br/>"
        "&bull; <b>Single-Process TTL Cache:</b> The 60s Trial Balance cache runs in-process; multi-replica production scaling should move cache keys to Redis (<font face='Courier'>REDIS_URL</font>).<br/>"
        "&bull; <b>Out of Scope for v1.0.0 (Roadmap v1.1+):</b> Direct bank NEFT/IMPS disbursement rails, automated EPFO/TRACES e-filing uploads, multi-currency FX revaluation, multi-tenant isolation, and SMTP transactional email.",
        body_style,
    ))

    # ── 6. Career Reflection ──
    elements.append(Paragraph("6. Career Lesson — What I Would Rebuild Differently", section_style))
    elements.append(Paragraph(
        "<i>\"If I rebuilt LedgerForge from Day 1 with what I know now, I would enforce a single shared SQLAlchemy <font face='Courier'>Base</font> contract "
        "with timezone-aware <font face='Courier'>TIMESTAMP WITH TIME ZONE</font> audit columns (<font face='Courier'>created_at</font>, <font face='Courier'>updated_at</font>) "
        "and uniform uppercase enum values across every table before writing Migration 0001.\"</i><br/>"
        "Small early schema inconsistencies (e.g., nullable <font face='Courier'>VARCHAR(32)</font> timestamps on <font face='Courier'>journal_entries</font> vs. "
        "<font face='Courier'>TimestampMixin</font> elsewhere, and Title Case vs. UPPERCASE check constraints) surfaced weeks later during incremental delta exports "
        "and OpenAPI enrichment. Standardizing foundational schema conventions on Day 1 prevents compounding integration friction.",
        body_style,
    ))

    # ── 7. Handover Checklist & Demo Guide ──
    elements.append(Paragraph("7. Final Go-Live Review &amp; Handover Artifacts", section_style))
    elements.append(Paragraph(
        "&bull; <b>Repository &amp; Release Tag:</b> <font face='Courier'>v1.0.0</font> pushed to GitHub with clean history and zero committed secrets.<br/>"
        "&bull; <b>Handover Documentation:</b> <font face='Courier'>README.md</font> (10 copy-paste examples), <font face='Courier'>RELEASE_NOTES.md</font>, "
        "<font face='Courier'>CHANGELOG.md</font>, and Mermaid architecture (<font face='Courier'>docs/architecture.md</font>).<br/>"
        "&bull; <b>5-Minute Demo Walkthrough Script:</b> Prepared in <font face='Courier'>docs/DEMO_SCRIPT.md</font> covering architecture, <font face='Courier'>/ui</font> payroll run &amp; payslip PDF, "
        "<font face='Courier'>/docs</font> Final Challenge &amp; streaming exports, <font face='Courier'>/health</font> + JSON logs, and live <font face='Courier'>verify_ledgerforge.py</font> proof.",
        body_style,
    ))

    elements.append(Spacer(1, 5))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#cbd5e1")))
    elements.append(Paragraph(
        "<b>Final Sign-Off:</b> I built, verified, documented, released, and audited a complete HR, Indian statutory payroll, and double-entry accounting backend (LedgerForge v1.0.0).",
        body_style,
    ))
    elements.append(Paragraph("— Ancilin P G (GM00210), November 19, 2026", meta_style))

    doc.build(elements)
    print(f"✓ Final Consolidated PDF written: {OUTPUT_PDF}")
    for dest in (REPORTS_PDF, DESKTOP_PDF):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_PDF, dest)
        print(f"  → copied to {dest}")


if __name__ == "__main__":
    build_pdf()
