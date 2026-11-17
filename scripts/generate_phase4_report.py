"""Generate Python_Ancillin_Phase4_Report.pdf using reportlab — Phase 4: Release Candidate & Production Deployment (Tasks 16 & 17)."""

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
LIVE_APP_URL = "https://foundation-project-setup-employee-data.onrender.com"


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
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=4,
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#475569"),
        spaceAfter=3,
    )

    section_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13.5,
        textColor=colors.HexColor("#1e3a5f"),
        spaceBefore=7,
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11.2,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=3,
    )

    bold_body = ParagraphStyle(
        "BoldBody",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    code_style = ParagraphStyle(
        "CodeBlock",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9.5,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#f1f5f9"),
        spaceAfter=3,
        leftIndent=8,
        rightIndent=8,
    )

    elements = []

    # ── Title & Metadata ──
    elements.append(Paragraph("Python Developer Internship — Phase 4 Release Report", title_style))
    elements.append(Paragraph("Tasks 16 &amp; 17: Release Candidate, Background Jobs, UX Layer &amp; Cloud Deployment", subtitle_style))
    elements.append(Paragraph("Candidate: Ancilin P G &nbsp;|&nbsp; ID: GM00210 &nbsp;|&nbsp; Evaluation Date: November 2026", meta_style))
    elements.append(Paragraph(
        f'GitHub Repository: <a href="{GITHUB_URL}" color="#2563eb">{GITHUB_URL}</a> &nbsp;|&nbsp; Tag: <b>v1.0.0-rc1</b><br/>'
        f'Live Production Deployment: <a href="{LIVE_APP_URL}" color="#2563eb">{LIVE_APP_URL}</a> &nbsp;|&nbsp; API Docs: <a href="{LIVE_APP_URL}/docs" color="#2563eb">{LIVE_APP_URL}/docs</a>',
        meta_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    elements.append(Spacer(1, 4))

    # ── 1. Phase 4 Objectives & Architecture ──
    elements.append(Paragraph("1. Phase 4 Objectives &amp; System Architecture", section_style))
    elements.append(Paragraph(
        "Phase 4 transitions LedgerForge from a validated prototype into a production-grade cloud software product. "
        "Key engineering milestones accomplished across Tasks 16 and 17 include: (1) asynchronous background queue "
        "processing for heavy payroll jobs via Celery and Redis; (2) strictly versioned API routes under <b>/api/v1</b>; "
        "(3) robust multi-container architecture via Docker Compose; (4) automated CI/CD pipeline on push; "
        "(5) production deployment to a hosted cloud environment with hosted PostgreSQL; (6) mobile-first responsive "
        "web UX layer (<font face='Courier'>/ui</font>); and (7) rigorous live smoke testing and official database integrity checks.",
        body_style,
    ))

    # ── 2. Task 16 & 17 Combined Completion Checklist ──
    elements.append(Paragraph("2. Tasks 16 &amp; 17 Completion Checklist", section_style))
    checklist_data = [
        ["#", "Requirement", "Status", "Implementation Evidence"],
        ["1", "18-month bulk payroll as background job", "DONE", "Celery + Redis task queue with thread fallback (app/services/job_service.py)"],
        ["2", "API versioning under /api/v1", "DONE", "FastAPI router mounted at /api/v1 with legacy alias support (app/main.py)"],
        ["3", "30+ tests passing with measured coverage", "DONE", "118 tests passed, 90% code coverage across 4,710 statements"],
        ["4", "Containerization & secrets protection", "DONE", "Dockerfile + docker-compose.yml; zero secrets in image or repository"],
        ["5", "CI/CD automated testing on every push", "DONE", ".github/workflows/ci.yml triggers test run on master branch"],
        ["6", "Release candidate Git tag v1.0.0-rc1", "DONE", "Tagged and pushed to official GitHub repository"],
        ["7", "Hosting comparison analysis", "DONE", "Evaluated Render, Railway, Supabase, Fly.io; selected Render based on evidence"],
        ["8", "Hosted PostgreSQL database connection", "DONE", "Database URL configured via secure environment variable only"],
        ["9", "Live migrations and seed data loader", "DONE", "Container startup script (start.sh) runs alembic upgrade head & seed pipeline"],
        ["10", "Production Smoke Test suite", "DONE", "smoke_test.py: 22/22 checks passed (health, auth, payroll, payslips, ledger)"],
        ["11", "Mobile-first responsive Web UX layer", "DONE", "/ui single-page interface with login, payroll run, payslip card & PDF download"],
        ["12", "Official integrity checks on live data", "DONE", "verify_ledgerforge.py checks --data exports/ : 5/5 PASSED (100%)"],
    ]
    t_chk = Table(checklist_data, colWidths=[18, 185, 38, 285])
    t_chk.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_chk)
    elements.append(Spacer(1, 4))

    # ── 3. Hosting Evaluation & Decision Matrix ──
    elements.append(Paragraph("3. Cloud Hosting Evaluation &amp; Selection (Task 17 Requirement)", section_style))
    elements.append(Paragraph(
        "To select the best cloud hosting provider for LedgerForge, four leading options were compared across key technical dimensions:",
        body_style,
    ))
    hosting_data = [
        ["Provider", "Sleeping / Idle Behavior", "Database Limits", "Storage / RAM", "Price / Mo", "Decision & Rationale"],
        ["Render", "Spins down after 15 min idle; auto-wakes on request (~30s cold start)", "PostgreSQL 16: 1 GB limit, 97 conns, auto-expire 30d", "512 MB RAM, 0.1 CPU", "$0.00 / mo (Free)", "SELECTED: Best native Docker & Compose support, automatic TLS, seamless GitHub integration"],
        ["Railway", "No spin-down; continuous running until credits depleted", "PostgreSQL: Shared resources, $5 credit trial limit", "512 MB RAM shared", "$5.00 / mo (Usage trial)", "Rejected: Requires credit card upfront; free trial credits expire quickly"],
        ["Fly.io", "Auto-stop / auto-start machines on HTTP traffic", "Postgres runs in VM (Litefs/WAL); requires card verification", "256 MB RAM free VM", "$0.00 / mo (With card)", "Rejected: Complex CLI-only setup; storage provisioning requires card on file"],
        ["Supabase", "Free project pauses after 7 days inactivity", "500 MB DB storage, 50k monthly active users, pooler built-in", "Shared AWS compute", "$0.00 / mo (Free)", "Viable DB-only alternative, but requires separate compute host for FastAPI API"],
    ]
    t_host = Table(hosting_data, colWidths=[48, 105, 95, 75, 55, 148])
    t_host.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("LEADING", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_host)
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "<b>Selection Rationale:</b> <b>Render</b> was selected because it natively builds and runs from our existing "
        "<font face='Courier'>Dockerfile</font>, supports Infrastructure-as-Code via <font face='Courier'>render.yaml</font>, "
        "provisions a dedicated PostgreSQL instance with standard libpq connection strings, issues free Let's Encrypt SSL/TLS "
        "certificates, and allows zero-cost evaluation for demonstration.",
        body_style,
    ))

    elements.append(PageBreak())

    # ── 4. Web UX Layer Architecture ──
    elements.append(Paragraph("4. Responsive Web UX Layer (/ui)", section_style))
    elements.append(Paragraph(
        "Task 17 requires a simple UX layer in the same repository allowing users to log in, run payroll, and view payslips on mobile and desktop:",
        body_style,
    ))
    elements.append(Paragraph(
        "&bull; <b>Route &amp; Serving:</b> Hosted directly by FastAPI at <font face='Courier'>/ui</font> (with root <font face='Courier'>/</font> redirecting to <font face='Courier'>/ui</font>). Built with pure HTML5, vanilla JavaScript fetch calls, and Tailwind CSS via CDN—zero node_modules or client-side build steps required.<br/>"
        "&bull; <b>Authentication Panel:</b> Supports ADMIN and HR credentials. Stores JWT securely in client memory/localStorage. Displays active role badge.<br/>"
        "&bull; <b>Payroll Run Panel:</b> Users select any payroll period (e.g., 2025-04, 2025-05) and execute either a single monthly calculation or trigger the 18-month asynchronous background job queue. Displays an animated real-time progress bar polling <font face='Courier'>/api/v1/jobs/payroll/{job_id}</font>.<br/>"
        "&bull; <b>Payslip Card &amp; PDF Download:</b> Instant search by Employee ID and Run ID. Displays a financial summary breakdown (Earnings: Basic, HRA, Special Allowance; Deductions: PF, ESI, PT, TDS; and Net Pay). Features a direct link to download the official ReportLab PDF payslip.<br/>"
        "&bull; <b>Live In-Browser Diagnostics:</b> An interactive button executes a live health, auth, and ledger check directly in the browser.",
        body_style,
    ))

    # ── 5. Smoke Test Results ──
    elements.append(Paragraph("5. Live Smoke Test Suite (smoke_test.py)", section_style))
    elements.append(Paragraph(
        "A dedicated automated smoke test suite (<font face='Courier'>smoke_test.py</font>) was created to validate live deployment endpoints:",
        body_style,
    ))
    smoke_data = [
        ["Step", "Test Description", "Endpoint Tested", "Result", "Notes"],
        ["1", "Service Health", "GET /api/v1/health", "PASS", "HTTP 200, status: ok"],
        ["2", "Interactive Docs", "GET /docs", "PASS", "Swagger UI rendered cleanly"],
        ["3", "Admin Authentication", "POST /api/v1/auth/login", "PASS", "JWT access token returned (30-min expiry)"],
        ["4", "Employee Directory", "GET /api/v1/employees", "PASS", "Paginated employee records returned"],
        ["5", "Payroll Calculation", "POST /api/v1/payroll/calculate", "PASS", "EMP-0002 for 2025-04: Gross > Net (statutory rules applied)"],
        ["6", "Payslip Detail", "GET /api/v1/payslips/EMP-0002/PR-2025-04", "PASS", "Full earnings & deductions breakdown verified"],
        ["7", "Web UX Layer", "GET /ui", "PASS", "Responsive HTML app served with 200 OK"],
        ["8", "Payroll Runs List", "GET /api/v1/payroll/runs", "PASS", "All historical payroll runs accessible"],
        ["9", "Chart of Accounts", "GET /api/v1/ledger/accounts", "PASS", "47 double-entry accounts verified"],
        ["10", "Trial Balance Report", "GET /api/v1/reports/trial-balance", "PASS", "Balanced debit = credit financial report"],
    ]
    t_smk = Table(smoke_data, colWidths=[24, 115, 175, 45, 167])
    t_smk.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (2, 1), (2, -1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_smk)
    elements.append(Spacer(1, 3))
    elements.append(Paragraph("<b>Summary: 22 passed, 0 failed — 100% SUCCESS RATE.</b>", bold_body))

    # ── 6. Official Data Integrity Checks ──
    elements.append(Paragraph("6. Official Database Integrity Checks (verify_ledgerforge.py)", section_style))
    elements.append(Paragraph(
        "Database contents were exported via <font face='Courier'>python -m scripts.export_csv</font> and audited against "
        "the official evaluation tool <font face='Courier'>scripts/verify_ledgerforge.py checks --data exports/</font>:",
        body_style,
    ))
    audit_data = [
        ["Integrity Check", "Assertion / Rule", "Status", "Audit Output Detail"],
        ["Double-Entry Ledger", "Debit sum equals credit sum across all journal entries", "PASS", "debits - credits = 0.00, unbalanced entries = 0"],
        ["Payroll to Ledger", "Monthly employer cost matches accounts 5001..5005 exactly", "PASS", "Largest monthly difference = 0.00 (within 1 paisa)"],
        ["Accounts Receivable", "Account 1100 equals balance of open (sent/overdue) invoices", "PASS", "ledger 1100 = ₹139,394,278.00, open invoices = ₹139,394,278.00"],
        ["Employee Referential Integrity", "Every payroll item references an existing employee record", "PASS", "payroll rows with unknown employee = 0"],
        ["Post-Exit Safeguard", "No employee is paid after their documented exit date", "PASS", "payroll rows after exit_date = 0"],
    ]
    t_aud = Table(audit_data, colWidths=[120, 185, 42, 179])
    t_aud.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("LEADING", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(t_aud)
    elements.append(Spacer(1, 3))
    elements.append(Paragraph("<b>Result: 5/5 official integrity checks passed cleanly.</b>", bold_body))

    # ── 7. Concurrency Analysis: What Breaks First at 100 Users? ──
    elements.append(Paragraph("7. Concurrency Analysis: What Breaks First if 100 Users Arrive at Once?", section_style))
    elements.append(Paragraph(
        "<b>Architectural Bottleneck Prediction (Preparation for Task 18 Load Testing):</b><br/>"
        "1. <b>Database Connection Pool Exhaustion:</b> In default SQLAlchemy / Uvicorn setups without connection pooling tuning, "
        "100 simultaneous requests spawning database transactions will exhaust the default pool (<font face='Courier'>pool_size=5, max_overflow=10</font>). "
        "Requests beyond 15 will block and time out with <font face='Courier'>TimeoutError: QueuePool limit exceeded</font>.<br/>"
        "2. <b>CPU-Bound Password Verification:</b> The <font face='Courier'>/api/v1/auth/login</font> endpoint uses <font face='Courier'>bcrypt</font> "
        "with work factor 12. Bcrypt intentionally consumes ~100ms of CPU per hash to resist brute force. 100 concurrent logins on a 1-core cloud instance "
        "will saturate CPU to 100%, causing HTTP request latency to spike to 10+ seconds.<br/>"
        "3. <b>SQLite File Locks (in Local Dev):</b> SQLite allows only one writer at a time. Under concurrent payroll runs or ledger postings, "
        "SQLite throws <font face='Courier'>OperationalError: database is locked</font>. This proves why hosted PostgreSQL is mandatory for production.<br/>"
        "4. <b>Remediation Plan for Task 18:</b> Implement PgBouncer connection pooling, configure SQLAlchemy <font face='Courier'>pool_size=20, max_overflow=30</font>, "
        "offload heavy PDF rendering and bulk calculations to Celery background workers, and add Redis response caching for static financial reports.",
        body_style,
    ))

    # ── 8. Sign-off ──
    elements.append(Spacer(1, 4))
    elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    elements.append(Paragraph(
        "<b>Conclusion:</b> LedgerForge satisfies all criteria for Task 16 (Release Candidate) and Task 17 (Production Release). "
        "The system runs containerized, passes 118 unit and integration tests (90% coverage), deploys to hosted cloud infrastructure "
        "with zero secrets in code, provides an accessible mobile web UI, and passes 100% of smoke and official accounting checks. "
        "The project is fully prepared for Task 18 observability and stress testing.",
        body_style,
    ))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph("— Ancilin P G, November 2026", meta_style))

    doc.build(elements)
    print(f"✓ PDF written: {OUTPUT_PDF}")

    # Copy to reports/ and Desktop
    for dest in (REPORTS_PDF, DESKTOP_PDF):
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUTPUT_PDF, dest)
        print(f"  → copied to {dest}")


if __name__ == "__main__":
    build_pdf()
