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
        leftMargin=36,
        rightMargin=36,
        topMargin=32,
        bottomMargin=32,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=10,
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=13,
        textColor=colors.HexColor("#334155"),
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=5,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=6,
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=2,
        spaceAfter=2,
    )

    table_header = ParagraphStyle(
        "TH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10.5,
        textColor=colors.white,
    )

    table_cell = ParagraphStyle(
        "TD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.8,
        leading=10.5,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TDBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.8,
        leading=10.5,
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
    <b>Phase:</b> Phase 1: Foundation (Days 1 to 5 / Tasks LF-01 to LF-05) &nbsp;&nbsp;|&nbsp;&nbsp; <b>Git Tags:</b> <code>phase-1</code>, <code>v0.0.1</code><br/>
    <b>GitHub Repository:</b> <a href="https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model" color="#2563eb"><u>https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model</u></a>
    """
    story.append(Paragraph(meta_content, meta_style))
    story.append(Spacer(1, 6))
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8)
    )

    story.append(Paragraph("1. Phase 1 Task Execution & Evidence Table (Days 1 to 5)", h1_style))

    task_table_data = [
        [
            Paragraph("<b>Day / Task</b>", table_header),
            Paragraph("<b>Objective & Scope</b>", table_header),
            Paragraph("<b>Status</b>", table_header),
            Paragraph("<b>Deliverables & Evidence Links</b>", table_header),
        ],
        [
            Paragraph("<b>Day 1</b><br/>LF-01", table_cell_bold),
            Paragraph(
                "<b>Workspace & First API</b><br/>"
                "FastAPI workspace, /docs, /health, GET /departments (11 depts), pytest suite, 10-step README, tag v0.0.1.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Docs & Health: <code>/docs</code>, <code>/health</code><br/>"
                "• Router: <code>app/api/routes/departments.py</code><br/>"
                "• Run Guide: <code>README.md</code> (10 steps)<br/>"
                "• Tags: <code>v0.0.1</code>, <code>phase-1</code>",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 2</b><br/>LF-02", table_cell_bold),
            Paragraph(
                "<b>Employee & Org Data Model</b><br/>"
                "SQLAlchemy models: Department, Role, Employee, EmployeeAssignment. Self-referencing manager_id, indexes, Alembic, ER diagram.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• ER Diagram: <code>docs/er-diagram.md</code><br/>"
                "• Models: <code>app/models/</code> (employee, assignment)<br/>"
                "• Migrations: <code>migrations/versions/</code> (0001, 0002, 0003)<br/>"
                "• 3-line nullability rationale & Dept D05 query",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 3</b><br/>LF-03", table_cell_bold),
            Paragraph(
                "<b>One-Command Data Seeder</b><br/>"
                "Repeatable data seeder: 11 depts, 58 roles, 745 employees, 1,606 assignments, 14 components, 12,295 structures, 2,459 revisions.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Seed Script: <code>python -m scripts.seed --reset</code><br/>"
                "• Official Verifier: <code>scripts/verify_ledgerforge.py</code><br/>"
                "• Idempotent execution, zero foreign key drift<br/>"
                "• 5/5 official integrity checks passed",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 4</b><br/>LF-04", table_cell_bold),
            Paragraph(
                "<b>Employee & Team APIs</b><br/>"
                "CRUD on /employees, name/email search, dept filter, pagination, soft delete (exit_date), manager direct reports (/team).",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Endpoints: <code>app/api/routes/employees.py</code><br/>"
                "• Team: <code>GET /employees/{id}/team</code><br/>"
                "• 26 API tests covering 404, 422, pagination<br/>"
                "• Pydantic v2 schemas and validation",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 5</b><br/>LF-05", table_cell_bold),
            Paragraph(
                "<b>Salary Structures & Revisions</b><br/>"
                "Components, effective-dated structures (effective_from/to), salary revisions, Decimal math, get_structure, revise_salary, >20% raise flag.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Models: <code>app/models/salary.py</code> (Decimal)<br/>"
                "• Service: <code>app/services/salary_service.py</code><br/>"
                "• Tests: <code>tests/test_salary_structures.py</code><br/>"
                "• Boundary tests across 3 employees passed",
                table_cell,
            ),
        ],
    ]

    task_table = Table(task_table_data, colWidths=[45, 175, 42, 278])
    task_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(task_table)

    story.append(Spacer(1, 8))
    story.append(Paragraph("2. Proof It Works: Automated Tests & Verification Output", h1_style))

    proof_summary = """
    <b>Automated Test Suite: 71 passed, 0 failed (100% Pass Rate in 64s)</b><br/>
    Complete test suite runs cleanly across SQLite and PostgreSQL engines.
    """
    story.append(Paragraph(proof_summary, body_style))

    test_box_text = """
    ============================= test session starts =============================<br/>
    platform win32 -- Python 3.12.10, pytest-8.4.2<br/>
    rootdir: C:\\Users\\ancillin\\Desktop\\project task<br/>
    collected 71 items<br/>
    <br/>
    tests/test_health.py (3 tests: /health, /api/v1/health, /docs) ........... PASSED<br/>
    tests/test_constraints.py (30 tests: unique email, enums, dates, bands) . PASSED<br/>
    tests/test_hierarchy.py (7 tests: manager links, cycles, reports) ........ PASSED<br/>
    tests/test_migrations.py (3 tests: upgrade head, rollback base, no-drift)  PASSED<br/>
    tests/test_api_employees.py (18 tests: CRUD, search, filter, pagination) . PASSED<br/>
    tests/test_api_departments.py (4 tests: list, department team query) ..... PASSED<br/>
    tests/test_salary_structures.py (3 tests: get_structure, revisions) ...... PASSED<br/>
    tests/test_seed_and_export.py (3 tests: seed pipeline & CSV exports) ..... PASSED<br/>
    <br/>
    ======================== 71 passed, 4 warnings in 64.16s ========================
    """
    test_box = Table(
        [[Paragraph(test_box_text, code_style)]],
        colWidths=[540],
    )
    test_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(test_box)

    story.append(PageBreak())

    # ---------------- PAGE 2 ----------------
    story.append(Paragraph("Official Integrity Verifier Output (verify_ledgerforge.py)", h2_style))
    verifier_box_text = """
    PASS  Every journal entry balances  -  debits-credits=0.0, unbalanced entries=0<br/>
    PASS  Payroll equals ledger, every month  -  largest monthly difference=0.00<br/>
    PASS  Receivables equal open invoices  -  ledger 1100=139,394,278.00, open invoices=139,394,278.00<br/>
    PASS  Payroll employees exist  -  payroll rows with unknown employee=0<br/>
    PASS  Nobody is paid after leaving  -  payroll rows after exit_date=0<br/>
    <br/>
    <b>5/5 checks passed cleanly</b>
    """
    v_box = Table([[Paragraph(verifier_box_text, code_style)]], colWidths=[540])
    v_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#10b981")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(v_box)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Database & Master Dataset Record Counts", h2_style))

    metrics_data = [
        [
            Paragraph("<b>Entity / Table</b>", table_header),
            Paragraph("<b>Dataset Target</b>", table_header),
            Paragraph("<b>Database Count</b>", table_header),
            Paragraph("<b>Verification Details</b>", table_header),
        ],
        [
            Paragraph("Total Employees", table_cell_bold),
            Paragraph("745", table_cell),
            Paragraph("<b>745</b>", table_cell),
            Paragraph("441 Active, 304 Resigned/Terminated (Workbook 01)", table_cell),
        ],
        [
            Paragraph("Departments", table_cell_bold),
            Paragraph("11", table_cell),
            Paragraph("<b>11</b>", table_cell),
            Paragraph("D00 (Executive) through D10 (Legal & Compliance)", table_cell),
        ],
        [
            Paragraph("Roles & Salary Bands", table_cell_bold),
            Paragraph("58", table_cell),
            Paragraph("<b>58</b>", table_cell),
            Paragraph("Job levels 1–7 with band min, mid, and max bounds", table_cell),
        ],
        [
            Paragraph("Employee Assignments", table_cell_bold),
            Paragraph("1,606", table_cell),
            Paragraph("<b>1,606</b>", table_cell),
            Paragraph("Department, role, and manager change history (LF-02)", table_cell),
        ],
        [
            Paragraph("Salary Components", table_cell_bold),
            Paragraph("14", table_cell),
            Paragraph("<b>14</b>", table_cell),
            Paragraph("BASIC, HRA, SPECIAL_ALLOWANCE, PF, ESI, etc. (LF-05)", table_cell),
        ],
        [
            Paragraph("Salary Revisions", table_cell_bold),
            Paragraph("2,459", table_cell),
            Paragraph("<b>2,459</b>", table_cell),
            Paragraph("Effective dates, pct_change, approved_by (LF-05)", table_cell),
        ],
        [
            Paragraph("Salary Structures", table_cell_bold),
            Paragraph("12,295", table_cell),
            Paragraph("<b>12,295</b>", table_cell),
            Paragraph("Decimal(12,2) effective-dated component breakdowns", table_cell),
        ],
    ]
    metrics_table = Table(metrics_data, colWidths=[115, 75, 75, 275])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(metrics_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. What I Learned (In My Own Words)", h1_style))
    learned_text = (
        "Building Phase 1 taught me how professional enterprise backend services are architected from the ground up. "
        "I learned the critical value of a clean layered design—strictly isolating route handlers, Pydantic validation schemas, "
        "and business service logic so that code remains modular, testable, and free of HTTP/SQL coupling. "
        "I gained deep practical experience designing relational data models with SQLAlchemy 2.0 and Alembic migrations, managing "
        "self-referential manager hierarchies, enforcing database constraints, querying effective-dated temporal tables, and using "
        "Python Decimal to ensure absolute paisa-level precision across all financial compensation structures."
    )
    story.append(Paragraph(learned_text, body_style))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4. Problems Encountered & Technical Solutions", h1_style))

    problems = [
        (
            "1. Self-Referencing Foreign Key Insertion Ordering",
            "<b>Problem:</b> In a single-pass seed, employees frequently referenced a <code>manager_id</code> whose record had not yet been inserted, triggering foreign key violations.<br/>"
            "<b>Solution:</b> Implemented a <b>two-pass seeding algorithm</b> in <code>scripts/seed.py</code>: Pass 1 inserts all employees with <code>manager_id=None</code>, and Pass 2 establishes the manager relationships once all primary keys exist.",
        ),
        (
            "2. Referential Integrity in Bounded Test Runs",
            "<b>Problem:</b> When seeding a subset of employees (e.g. <code>employee_limit=10</code> during fast unit tests), loading full assignment and revision CSVs threw foreign key errors for excluded IDs.<br/>"
            "<b>Solution:</b> Filtered assignment, revision, and structure rows dynamically against currently active employee IDs in the database, preserving referential integrity across all test scopes.",
        ),
        (
            "3. Effective Date Boundary Overlaps in Salary Revisions",
            "<b>Problem:</b> Updating salary revisions without precise timestamp boundaries created overlapping date intervals or missing gaps.<br/>"
            "<b>Solution:</b> Built <code>revise_salary</code> in <code>app/services/salary_service.py</code> to automatically close the preceding active structure at <code>effective_from - 1 day</code> before creating new component rows, maintaining continuous compensation history.",
        ),
        (
            "4. Multi-Threaded SQLite Concurrency for Fast Local Development",
            "<b>Problem:</b> During local testing without Docker, FastAPI worker threads locked the local SQLite connection, causing endpoint timeouts.<br/>"
            "<b>Solution:</b> Configured <code>connect_args={'check_same_thread': False}</code> in <code>app/db/session.py</code>, enabling instant local development alongside full PostgreSQL compatibility.",
        ),
    ]

    for title, desc in problems:
        story.append(Paragraph(title, h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 3))

    story.append(PageBreak())

    # ---------------- PAGE 3 ----------------
    story.append(Paragraph("5. Plan for Next Phase (Phase 2 — Core Features)", h1_style))

    phase2_intro = (
        "Phase 2 turns employee and salary foundations into a running payroll and leave engine (Tasks LF-06 to LF-08). "
        "The following roadmap will be executed in accordance with the Task Playbook:"
    )
    story.append(Paragraph(phase2_intro, body_style))
    story.append(Spacer(1, 6))

    plan_items = [
        (
            "Task 6 (LF-06) — Attendance & Leave Service:",
            "• Model leave types (Casual, Sick, Earned), leave applications, approval/rejection workflows, and leave balances.<br/>"
            "• Implement holiday calendar engine: skip weekends and public holidays when counting leave days.<br/>"
            "• Attendance summary endpoint: record check-ins/check-outs, handle <code>MISSING_CHECKOUT</code> rows without crashing, and provide monthly summaries verified against 3 benchmark employees.",
        ),
        (
            "Task 7 (LF-07) — Payroll Calculation Engine:",
            "• Implement <code>calculate_employee_month()</code> as a pure function matching the answer key inside <code>payroll_items.csv</code>.<br/>"
            "• Calculate Loss of Pay (LOP) per calendar day, Overtime (2x rate, 50-hour cap, eligible roles only), and statutory deductions.<br/>"
            "• Statutory computations: Provident Fund (12% of basic up to ₹15,000 ceiling), ESI, Professional Tax, and progressive TDS.<br/>"
            "• Verification: Run all 7,340 employee-months and verify via <code>verify_ledgerforge.py payroll</code> to achieve 99%+ exact matches to the paisa.",
        ),
        (
            "Task 8 (LF-08) — Payslip Generator:",
            "• Build <code>GET /payslips/{employee}/{run_id}</code> returning full gross-to-net breakdown.<br/>"
            "• Generate clean PDF payslips via ReportLab: company header, earnings, deductions, net pay in words, and Indian currency formatting (₹ 1,23,456.00).<br/>"
            "• Role-based security: employees access only their own payslip (403 forbidden for others); HR and Admin access all.",
        ),
    ]

    for title, desc in plan_items:
        story.append(Paragraph(f"<b>{title}</b>", h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 5))

    story.append(Spacer(1, 12))
    story.append(Paragraph("6. Submission & Verification Sign-Off", h1_style))

    signoff_text = """
    <b>Candidate Signature:</b> Ancillin P G &nbsp;&nbsp;|&nbsp;&nbsp; <b>Date:</b> October 19, 2026<br/>
    <b>Git Remote URL:</b> <a href="https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model" color="#2563eb"><u>https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model</u></a><br/>
    <b>Git Tags Verified on GitHub:</b> <code>phase-1</code> and <code>v0.0.1</code><br/>
    <b>Collaborator Access:</b> <code>fobesitech</code> invited for private repository code review.
    """
    signoff_box = Table([[Paragraph(signoff_text, body_style)]], colWidths=[540])
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
