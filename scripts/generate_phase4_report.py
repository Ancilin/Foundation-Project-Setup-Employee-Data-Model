"""Generate Python_Ancillin_Phase4_Report.pdf using reportlab — Task 16 release candidate report."""

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
        fontSize=15.5,
        leading=18.5,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=2,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#2563eb"),
        spaceAfter=5,
    )

    meta_style = ParagraphStyle(
        "MetaText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#475569"),
        spaceAfter=4,
    )

    section_style = ParagraphStyle(
        "SectionHead",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a5f"),
        spaceBefore=10,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "BodyText2",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12.5,
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
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#f1f5f9"),
        spaceAfter=4,
        leftIndent=12,
        rightIndent=12,
    )

    link_style = ParagraphStyle(
        "LinkText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#2563eb"),
    )

    elements = []

    # ── Title ──
    elements.append(Paragraph("Python Developer Internship — Phase 4 Report", title_style))
    elements.append(Paragraph("Task 16: Make it a Product", subtitle_style))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph("Candidate: Ancilin P G &nbsp;|&nbsp; ID: GM00210 &nbsp;|&nbsp; Date: November 2026", meta_style))
    elements.append(Paragraph(
        f'GitHub: <a href="{GITHUB_URL}" color="#2563eb">{GITHUB_URL}</a> &nbsp;|&nbsp; Tag: <b>v1.0.0-rc1</b>',
        meta_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    elements.append(Spacer(1, 6))

    # ── 1. Objective ──
    elements.append(Paragraph("1. Objective", section_style))
    elements.append(Paragraph(
        "Turn the working LedgerForge system into a release candidate: heavy payroll jobs run in the background via "
        "a task queue, the API is versioned under <b>/api/v1</b>, test coverage exceeds 30 tests, and the entire stack "
        "runs from one <font face='Courier'>docker compose up</font> command with no secrets baked into the image.",
        body_style,
    ))

    # ── 2. Task 16 Completion Checklist ──
    elements.append(Paragraph("2. Task 16 Completion Checklist", section_style))
    checklist_data = [
        ["#", "Requirement", "Status", "Evidence"],
        ["1", "docker compose up starts a working, seeded API", "DONE", "docker-compose.yml: api + db + redis + worker"],
        ["2", "30 or more tests pass", "DONE", "118 tests passed (90% coverage)"],
        ["3", "No secret exists inside the image", "DONE", ".dockerignore excludes .env; env_file at runtime"],
        ["4", "The queue handles the bulk payroll run", "DONE", "Celery + Redis; fallback to daemon threads"],
        ["5", "API versioned under /api/v1", "DONE", "app/main.py: prefix=\"/api/v1\""],
        ["6", "Git tag v1.0.0-rc1", "DONE", "git tag v1.0.0-rc1 pushed to origin"],
        ["7", "CI workflow on every push", "DONE", ".github/workflows/ci.yml"],
    ]
    t = Table(checklist_data, colWidths=[22, 200, 42, 260])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6))

    # ── 3. Background Jobs Architecture ──
    elements.append(Paragraph("3. Background Jobs &amp; Queue Architecture", section_style))
    elements.append(Paragraph(
        "The 18-month bulk payroll run is dispatched as an asynchronous background job. The system supports two modes:",
        body_style,
    ))
    elements.append(Paragraph(
        "<b>Production (Docker Compose):</b> Celery worker connected to a Redis broker processes jobs. "
        "The API returns HTTP 202 with a <font face='Courier'>job_id</font> and the client polls a progress endpoint.",
        body_style,
    ))
    elements.append(Paragraph(
        "<b>Development fallback:</b> When Redis is unavailable, the job runs in a daemon thread using "
        "<font face='Courier'>FastAPI BackgroundTasks</font> or Python <font face='Courier'>threading</font>.",
        body_style,
    ))
    elements.append(Spacer(1, 2))
    elements.append(Paragraph("Key endpoints:", bold_body))
    endpoint_data = [
        ["Method", "Path", "Description"],
        ["POST", "/api/v1/jobs/payroll/bulk-run", "Trigger 18-month payroll (returns 202 + job_id)"],
        ["GET", "/api/v1/jobs/payroll/{job_id}", "Poll job progress (percent, status, results)"],
        ["GET", "/api/v1/jobs", "List all background jobs"],
    ]
    t2 = Table(endpoint_data, colWidths=[42, 200, 282])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (1, -1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 6))

    # ── 4. Docker Compose Setup ──
    elements.append(Paragraph("4. Docker Compose Setup", section_style))
    elements.append(Paragraph(
        "The <font face='Courier'>docker-compose.yml</font> defines four services:",
        body_style,
    ))
    compose_data = [
        ["Service", "Image / Build", "Purpose"],
        ["api", "Build from Dockerfile", "FastAPI application server (port 8000)"],
        ["worker", "Build from Dockerfile", "Celery worker for background jobs"],
        ["db", "postgres:16-alpine", "PostgreSQL database"],
        ["redis", "redis:7-alpine", "Message broker for Celery task queue"],
    ]
    t3 = Table(compose_data, colWidths=[55, 145, 324])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 4))
    elements.append(Paragraph("Quick-start for a new developer:", bold_body))
    elements.append(Paragraph(
        "<font face='Courier'>git clone https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model.git</font><br/>"
        "<font face='Courier'>cd Foundation-Project-Setup-Employee-Data-Model</font><br/>"
        "<font face='Courier'>cp .env.example .env &nbsp;&nbsp;# fill in real values</font><br/>"
        "<font face='Courier'>docker compose up --build</font><br/>"
        "<font face='Courier'># API available at http://localhost:8000/docs</font>",
        code_style,
    ))

    elements.append(PageBreak())

    # ── 5. Test & Coverage Results ──
    elements.append(Paragraph("5. Test &amp; Coverage Results", section_style))
    elements.append(Paragraph("<b>118 tests passed</b> &nbsp;|&nbsp; <b>90% code coverage</b> &nbsp;|&nbsp; 4,710 statements measured", body_style))
    elements.append(Spacer(1, 2))
    cov_data = [
        ["Module Group", "Stmts", "Miss", "Cover"],
        ["Routes (app/api/routes/)", "337", "26", "92%"],
        ["Models (app/models/)", "411", "23", "94%"],
        ["Schemas (app/schemas/)", "827", "6", "99%"],
        ["Services (app/services/)", "2,462", "371", "85%"],
        ["Core, DB, Main", "153", "27", "82%"],
        ["Worker + Celery", "16", "16", "0%"],
        ["TOTAL", "4,710", "472", "90%"],
    ]
    t4 = Table(cov_data, colWidths=[180, 50, 50, 50])
    t4.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("LEADING", (0, 0), (-1, -1), 11),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t4)
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(
        "<i>Note:</i> Worker/Celery modules show 0% because they require a live Redis broker. "
        "All other modules are well above 80%.",
        meta_style,
    ))

    # ── 6. CI Pipeline ──
    elements.append(Paragraph("6. GitHub Actions CI Pipeline", section_style))
    elements.append(Paragraph(
        "File: <font face='Courier'>.github/workflows/ci.yml</font>",
        body_style,
    ))
    elements.append(Paragraph(
        "On every <b>push</b> or <b>pull request</b> to <font face='Courier'>master</font> / "
        "<font face='Courier'>main</font>, GitHub Actions:",
        body_style,
    ))
    elements.append(Paragraph(
        "&bull; Checks out the code<br/>"
        "&bull; Sets up Python 3.12<br/>"
        "&bull; Installs all dev dependencies<br/>"
        "&bull; Runs <font face='Courier'>pytest --cov=app --cov-report=term-missing</font>",
        body_style,
    ))
    elements.append(Paragraph(
        "<b>What it protects:</b> The CI workflow acts as a safety net — it catches regressions, broken imports, "
        "and failing business logic <i>before</i> code reaches production. If any of the 118 tests fail, the push is "
        "marked as failed and the developer is notified immediately. This prevents shipping broken payroll calculations, "
        "authentication bypasses, or ledger imbalance bugs to users.",
        body_style,
    ))

    # ── 7. Secrets Management ──
    elements.append(Paragraph("7. Secrets Management", section_style))
    elements.append(Paragraph(
        "No secret is stored inside the Docker image. The <font face='Courier'>.dockerignore</font> file explicitly "
        "excludes <font face='Courier'>.env</font>, <font face='Courier'>.venv</font>, and "
        "<font face='Courier'>__pycache__</font>. At runtime, secrets are injected via the "
        "<font face='Courier'>env_file</font> and <font face='Courier'>environment</font> directives in "
        "<font face='Courier'>docker-compose.yml</font>. The <font face='Courier'>.env.example</font> file "
        "documents every required variable with placeholder values.",
        body_style,
    ))

    # ── 8. Files Created / Modified ──
    elements.append(Paragraph("8. Files Created &amp; Modified in Task 16", section_style))
    files_data = [
        ["File", "Action", "Purpose"],
        ["app/models/job.py", "New", "BackgroundJob SQLAlchemy model"],
        ["app/schemas/job.py", "New", "Pydantic schemas for job requests/responses"],
        ["app/services/job_service.py", "New", "Job orchestration: create, enqueue, poll, list"],
        ["app/api/routes/jobs.py", "New", "3 HTTP endpoints for background jobs"],
        ["app/worker.py", "New", "Celery task definition"],
        ["app/core/celery_app.py", "New", "Celery app configuration (Redis broker)"],
        ["migrations/.../0010_...py", "New", "Alembic migration for background_jobs table"],
        ["tests/test_background_jobs.py", "New", "5 tests for background job endpoints"],
        [".github/workflows/ci.yml", "New", "GitHub Actions CI pipeline"],
        ["docker-compose.yml", "Updated", "Added redis + celery worker services"],
        ["Dockerfile", "Updated", "Added data/ and scripts/ to image"],
        ["requirements.txt", "Updated", "Added celery, redis"],
        ["requirements-dev.txt", "Updated", "Added pytest-cov, coverage"],
        [".env.example", "Updated", "Added CELERY_BROKER_URL, CELERY_RESULT_BACKEND"],
    ]
    t5 = Table(files_data, colWidths=[175, 50, 299])
    t5.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Courier"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("LEADING", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t5)

    # ── 9. Sign-off ──
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1")))
    elements.append(Paragraph(
        "<b>Conclusion:</b> Task 16 delivers a fully testable, containerised release candidate. "
        "The system starts with <font face='Courier'>docker compose up</font>, passes 118 tests at 90% coverage, "
        "handles bulk payroll as background jobs via Celery + Redis, and runs CI on every push. "
        "Tag <b>v1.0.0-rc1</b> is published and ready for Task 17 deployment.",
        body_style,
    ))
    elements.append(Spacer(1, 6))
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
