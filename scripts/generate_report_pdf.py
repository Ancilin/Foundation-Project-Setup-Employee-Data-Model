"""Generate Python_Ancillin_Phase1_Report.pdf using reportlab."""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PDF = ROOT / "Python_Ancillin_Phase1_Report.pdf"
DESKTOP_PDF = Path(r"C:\Users\ancillin\Desktop\Python_Ancillin_Phase1_Report.pdf")


def build_pdf():
    doc = SimpleDocTemplate(
        str(OUTPUT_PDF),
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=12,
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=14,
        textColor=colors.HexColor("#334155"),
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=3,
        spaceAfter=3,
    )

    table_header = ParagraphStyle(
        "TH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    table_cell = ParagraphStyle(
        "TD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TDBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )

    story = []

    # ---------------- PAGE 1 ----------------
    story.append(Paragraph("LedgerForge — Phase 1 Report", title_style))
    story.append(
        Paragraph("WorkforceOS: Core Payroll, Accounting & Employee Data Engine", subtitle_style)
    )

    meta_content = """
    <b>Candidate Name:</b> Ancillin P G &nbsp;&nbsp;|&nbsp;&nbsp; <b>Track:</b> Python Developer<br/>
    <b>Phase:</b> Phase 1 (Foundation) &nbsp;&nbsp;|&nbsp;&nbsp; <b>Git Tags:</b> <code>phase-1</code>, <code>handoff-day2</code><br/>
    <b>GitHub Repository:</b> <a href="https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model" color="#2563eb"><u>https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model</u></a>
    """
    story.append(Paragraph(meta_content, meta_style))
    story.append(Spacer(1, 8))
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=10)
    )

    story.append(Paragraph("1. Phase 1 Task Execution & Evidence Table", h1_style))

    task_table_data = [
        [
            Paragraph("<b>#</b>", table_header),
            Paragraph("<b>Task Name</b>", table_header),
            Paragraph("<b>Status</b>", table_header),
            Paragraph("<b>Deliverables & Evidence Links</b>", table_header),
        ],
        [
            Paragraph("1", table_cell_bold),
            Paragraph(
                "<b>Project Skeleton & Early Handoff Package</b>",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• <code>GET /health</code> & <code>GET /api/v1/health</code><br/>"
                "• Draft Contract: <code>docs/api-contract.md</code><br/>"
                "• Sample Data: <code>scripts/sample_employees.json</code><br/>"
                "• Tagged: <code>handoff-day2</code>",
                table_cell,
            ),
        ],
        [
            Paragraph("2", table_cell_bold),
            Paragraph(
                "<b>Employee, Department & Role Data Model</b>",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• ER Diagram: <code>docs/er-diagram.md</code><br/>"
                "• Alembic Migration: <code>0001_create_employee_tables.py</code><br/>"
                "• 1-to-many & self-reference hierarchy (<code>manager_id</code>)<br/>"
                "• Decision: <i>One current role per person</i> in README",
                table_cell,
            ),
        ],
        [
            Paragraph("3", table_cell_bold),
            Paragraph("<b>Employee & Team APIs</b>", table_cell),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Interactive Docs: <code>/docs</code> (Swagger UI)<br/>"
                "• Full CRUD: POST/GET/PATCH/DELETE <code>/employees</code><br/>"
                "• Team & Dept: <code>/employees/{id}/team</code>, <code>/departments</code><br/>"
                "• Pydantic schemas, validation, pagination, unified error codes",
                table_cell,
            ),
        ],
        [
            Paragraph("4", table_cell_bold),
            Paragraph(
                "<b>Master Dataset, Seed Pipeline & Early Exports</b>",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Seed Script: <code>python -m scripts.seed --reset</code><br/>"
                "• Faker enrichment (seed 42), linked salaries & attendance<br/>"
                "• 745 employees, 11 depts, 58 roles, 9,000 attendance logs<br/>"
                "• Exports: <code>exports/</code> (employees, salaries, attendance CSVs)",
                table_cell,
            ),
        ],
        [
            Paragraph("5", table_cell_bold),
            Paragraph(
                "<b>Developer Guide & Handoff Integration</b>",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Aligned with <i>LedgerForge — Python Developer Guide</i><br/>"
                "• Base path <code>/api/v1</code> mounted with health component checks<br/>"
                "• Two-pass foreign key hierarchy resolution; clean working tree",
                table_cell,
            ),
        ],
    ]

    task_table = Table(task_table_data, colWidths=[20, 150, 48, 314])
    task_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(task_table)

    story.append(Spacer(1, 10))
    story.append(Paragraph("2. Proof It Works: Automated Tests & Metrics", h1_style))

    proof_summary = """
    <b>Automated Test Suite: 67 passed, 0 failed (100% Pass Rate in 8.04s)</b><br/>
    The entire application was validated using <code>pytest</code> against SQLite and PostgreSQL engines.
    """
    story.append(Paragraph(proof_summary, body_style))

    test_box_text = """
    ============================= test session starts =============================<br/>
    platform win32 -- Python 3.12.10, pytest-8.4.2<br/>
    rootdir: C:\\Users\\ancillin\\Desktop\\project task<br/>
    collected 67 items<br/>
    <br/>
    tests/test_health.py (3 tests: /health, /api/v1/health, /docs) ........... PASSED [  4%]<br/>
    tests/test_constraints.py (30 tests: unique email, enums, dates, bands) . PASSED [ 49%]<br/>
    tests/test_hierarchy.py (7 tests: manager links, cycles, reports) ........ PASSED [ 60%]<br/>
    tests/test_migrations.py (3 tests: upgrade head, rollback base, no-drift)  PASSED [ 64%]<br/>
    tests/test_api_employees.py (18 tests: CRUD, search, filter, pagination) . PASSED [ 91%]<br/>
    tests/test_api_departments.py (4 tests: list, department team query) ..... PASSED [ 97%]<br/>
    tests/test_seed_and_export.py (2 tests: seed pipeline & CSV exports) ..... PASSED [100%]<br/>
    <br/>
    ======================== 67 passed, 4 warnings in 8.04s ========================
    """
    test_box = Table(
        [[Paragraph(test_box_text, code_style)]],
        colWidths=[532],
    )
    test_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(test_box)

    story.append(PageBreak())

    # ---------------- PAGE 2 ----------------
    story.append(Paragraph("Database & Master Dataset Verification Metrics", h2_style))

    metrics_data = [
        [
            Paragraph("<b>Metric</b>", table_header),
            Paragraph("<b>Expected (Workbook 01)</b>", table_header),
            Paragraph("<b>Actual Seeded</b>", table_header),
            Paragraph("<b>Verification Details</b>", table_header),
        ],
        [
            Paragraph("Total Employees", table_cell_bold),
            Paragraph("745", table_cell),
            Paragraph("<b>745</b>", table_cell),
            Paragraph("441 Active, 304 Resigned/Terminated", table_cell),
        ],
        [
            Paragraph("Departments", table_cell_bold),
            Paragraph("11", table_cell),
            Paragraph("<b>11</b>", table_cell),
            Paragraph("D00 (Exec) through D10 (Legal & Compliance)", table_cell),
        ],
        [
            Paragraph("Roles & Salary Bands", table_cell_bold),
            Paragraph("58", table_cell),
            Paragraph("<b>58</b>", table_cell),
            Paragraph("Levels 1-7 with min, mid, and max annual bands", table_cell),
        ],
        [
            Paragraph("Salaries (Linked)", table_cell_bold),
            Paragraph("745", table_cell),
            Paragraph("<b>745</b>", table_cell),
            Paragraph("Basic (40%), HRA (50%), Special allowance within CTC", table_cell),
        ],
        [
            Paragraph("Attendance History", table_cell_bold),
            Paragraph("Multi-month logs", table_cell),
            Paragraph("<b>9,000 rows</b>", table_cell),
            Paragraph("Present (~85%), Leave, HalfDay, Late, Overtime", table_cell),
        ],
        [
            Paragraph("CSV Exports", table_cell_bold),
            Paragraph("5 tables", table_cell),
            Paragraph("<b>5 files</b>", table_cell),
            Paragraph("Cleanly exported to <code>exports/</code> directory", table_cell),
        ],
    ]
    metrics_table = Table(metrics_data, colWidths=[110, 100, 75, 247])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(metrics_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("3. What I Learned (In My Own Words)", h1_style))
    learned_text = (
        "Building Phase 1 taught me how professional enterprise backend services are architected from the ground up. "
        "I learned the critical value of a clean layered design—strictly isolating route handlers, Pydantic validation schemas, "
        "and business service logic so that code remains modular, testable, and free of HTTP/SQL coupling. "
        "I gained deep practical experience designing relational data models with SQLAlchemy 2.0 and Alembic migrations, managing "
        "self-referential manager hierarchies, enforcing database constraints, and generating deterministic synthetic datasets "
        "using Faker with fixed random seeds for reproducible team testing and cross-domain handoffs."
    )
    story.append(Paragraph(learned_text, body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("4. Problems Encountered & Technical Solutions", h1_style))

    problems = [
        (
            "1. Self-Referencing Foreign Key Insertion Ordering",
            "<b>Problem:</b> When seeding employees in a single pass, employees frequently referenced a <code>manager_id</code> whose record had not yet been inserted, triggering foreign key constraint violations.<br/>"
            "<b>Solution:</b> Implemented a <b>two-pass seeding algorithm</b> in <code>scripts/seed.py</code>: Pass 1 inserts all employees with <code>manager_id=None</code>, and Pass 2 establishes the manager relationships once all primary keys exist.",
        ),
        (
            "2. Attendance ID String Truncation on PostgreSQL",
            "<b>Problem:</b> Attendance identifiers formatted as <code>ATT-EMP-XXXX-YYYYMMDD</code> (21 chars) exceeded the initial <code>VARCHAR(20)</code> column length, raising <code>StringDataRightTruncation</code>.<br/>"
            "<b>Solution:</b> Upgraded the column definition to <code>VARCHAR(32)</code> in both SQLAlchemy models and Alembic migration <code>0002</code>.",
        ),
        (
            "3. Multi-Threaded SQLite Concurrency for Fast Local Development",
            "<b>Problem:</b> During local testing without Docker, FastAPI worker threads locked the local SQLite connection, causing endpoint timeouts.<br/>"
            "<b>Solution:</b> Configured <code>connect_args={'check_same_thread': False}</code> in <code>app/db/session.py</code>, enabling instant local development alongside full PostgreSQL compatibility.",
        ),
        (
            "4. Docker WSL2 Port Proxy Conflict",
            "<b>Problem:</b> A zombie background Windows socket forwarder held port 8000 when Docker Desktop was stopped.<br/>"
            "<b>Solution:</b> Mounted development on port 8001 and pre-configured <code>.vscode/launch.json</code> for seamless 1-click debugging.",
        ),
    ]

    for title, desc in problems:
        story.append(Paragraph(title, h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ---------------- PAGE 3 ----------------
    story.append(Paragraph("5. Plan for Next Phase (Phase 2)", h1_style))

    phase2_intro = (
        "Phase 2 focuses on <b>Access Control, Payroll Calculation Engine, and Payslips</b>. "
        "The following roadmap will be executed in accordance with the official developer guide:"
    )
    story.append(Paragraph(phase2_intro, body_style))
    story.append(Spacer(1, 6))

    plan_items = [
        (
            "Task 5 — Authentication & Role-Based Access Control (RBAC):",
            "• Endpoints: <code>POST /api/v1/auth/login</code>, <code>POST /api/v1/auth/refresh</code>, <code>GET /api/v1/auth/me</code>.<br/>"
            "• Password security: Bcrypt hashing with default format <code>Zenith#&lt;employee_id&gt;</code>.<br/>"
            "• Token architecture: Signed JWT tokens (HS256) containing claims (<code>sub</code>, <code>employee_id</code>, <code>role</code>, <code>type</code>).<br/>"
            "• Role dependency: Implement <code>require_role(ADMIN, HR, EMPLOYEE)</code> protecting all resource endpoints.",
        ),
        (
            "Tasks 6 & 7 — Salary Structure & Attendance/Leave Engine:",
            "• Track salary revision history effective on the 1st of each month with 409 conflict checks for overlapping periods.<br/>"
            "• Standardized monthly gross component split: BASIC (40%), HRA (50% of basic), CONV (1,600/800), MED (1,250/0), SPECIAL (balance).<br/>"
            "• Leave balance engine: Accrual rules for CL (12), SL (12), and EL (1.25/month up to 30 carryover) with Loss of Pay (LOP) calculations.",
        ),
        (
            "Tasks 8 & 9 — Payroll Engine & Automated Payslips:",
            "• Mathematical calculation engine strictly matching answer keys in <code>tests/fixtures/payroll_runs.xlsx</code>.<br/>"
            "• Prorated payable days calculation: <code>max(0, days_employed - lop_days)</code>.<br/>"
            "• Statutory deductions: Provident Fund (12% of basic up to 15,000 ceiling), ESI, and progressive TDS tax slabs.<br/>"
            "• Payslip generation: JSON endpoint, printable PDF generation, and batch ZIP export.",
        ),
    ]

    for title, desc in plan_items:
        story.append(Paragraph(f"<b>{title}</b>", h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 10))
    story.append(Paragraph("6. Submission & Verification Sign-Off", h1_style))

    signoff_text = """
    <b>Candidate Signature:</b> Ancillin P G &nbsp;&nbsp;|&nbsp;&nbsp; <b>Date:</b> October 19, 2026<br/>
    <b>Git Remote URL:</b> <a href="https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model" color="#2563eb"><u>https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model</u></a><br/>
    <b>Git Tags Verified on GitHub:</b> <code>phase-1</code> and <code>handoff-day2</code><br/>
    <b>Collaborator Access:</b> <code>fobesitech</code> invited for private repository code review.
    """
    signoff_box = Table([[Paragraph(signoff_text, body_style)]], colWidths=[532])
    signoff_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#2563eb")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(signoff_box)

    doc.build(story)
    print(f"Generated PDF at {OUTPUT_PDF}")

    # Copy to Desktop for easy access
    try:
        import shutil

        shutil.copyfile(OUTPUT_PDF, DESKTOP_PDF)
        print(f"Copied PDF to Desktop: {DESKTOP_PDF}")
    except Exception as e:
        print(f"Could not copy to Desktop: {e}")


if __name__ == "__main__":
    build_pdf()
