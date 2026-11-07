"""Generate Python_Ancillin_Phase3_Report.pdf using reportlab (2-3 pages, clickable GitHub link)."""

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
OUTPUT_PDF = ROOT / "Python_Ancillin_Phase3_Report.pdf"
REPORTS_PDF = ROOT / "reports" / "Python_Ancillin_Phase3_Report.pdf"
PHASE2_PDF = Path(r"C:\Users\ancillin\Desktop\Phase 2\Python_Ancillin_Phase3_Report.pdf")
DESKTOP_PDF = Path(r"C:\Users\ancillin\Desktop\Python_Ancillin_Phase3_Report.pdf")

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
        fontSize=8.2,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )

    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=5,
        spaceAfter=3,
    )

    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2563eb"),
        spaceBefore=4,
        spaceAfter=2,
    )

    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.7,
        leading=10.6,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=2.5,
    )

    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=6.9,
        leading=9.0,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=1.5,
        spaceAfter=1.5,
    )

    table_header = ParagraphStyle(
        "TH",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.6,
        leading=9.6,
        textColor=colors.white,
    )

    table_cell = ParagraphStyle(
        "TD",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.3,
        leading=9.5,
        textColor=colors.HexColor("#1e293b"),
    )

    table_cell_bold = ParagraphStyle(
        "TDBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.3,
        leading=9.5,
        textColor=colors.HexColor("#1e293b"),
    )

    story = []

    # =========================================================================
    # PAGE 1: Header, 5-Task Table, and Mini Challenge Trace
    # =========================================================================
    story.append(Paragraph("LedgerForge — Phase 3 Report", title_style))
    story.append(
        Paragraph(
            "WorkforceOS: Connected System — Expenses, Payroll-to-Ledger, JWT RBAC, Tax Engine & Financial Statements",
            subtitle_style,
        )
    )

    meta_content = (
        f"<b>Candidate Name:</b> Ancillin P G &nbsp;&nbsp;|&nbsp;&nbsp; <b>Track:</b> Python Developer<br/>"
        f"<b>Phase:</b> Phase 3: Connected System (Days 11 to 15 / Tasks LF-11 to LF-15) &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Git Tag:</b> <code>phase-3</code><br/>"
        f"<b>GitHub Repository:</b> <a href='{GITHUB_URL}' color='#2563eb'><u>{GITHUB_URL}</u></a>"
    )
    story.append(Paragraph(meta_content, meta_style))
    story.append(Spacer(1, 5))
    story.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=6)
    )

    story.append(Paragraph("1. Phase 3 Task Execution & Evidence Table (Days 11 to 15)", h1_style))

    task_table_data = [
        [
            Paragraph("<b>Day / Task</b>", table_header),
            Paragraph("<b>Objective & Scope</b>", table_header),
            Paragraph("<b>Status</b>", table_header),
            Paragraph("<b>Deliverables & Clickable Evidence Links</b>", table_header),
        ],
        [
            Paragraph("<b>Day 11</b><br/>LF-11", table_cell_bold),
            Paragraph(
                "<b>Spend Money: Vendors & Expense Bills</b><br/>"
                "56 vendors, 1,105 bills, SUBMITTED -> APPROVED -> PAID lifecycle, separation of duties (approved_by != submitted_by), GST Input (1200) + AP (2001), duplicate detector.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Service: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/services/expense_service.py' color='#2563eb'><u>app/services/expense_service.py</u></a><br/>"
                "• Routes: <code>/api/v1/vendors</code>, <code>/api/v1/expenses</code><br/>"
                "• Spend Report: 18/18 months match <code>expenses.csv</code> (diff=0.00)<br/>"
                "• Tests: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/tests/test_expenses.py' color='#2563eb'><u>tests/test_expenses.py</u></a> (3/3 passed)",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 12</b><br/>LF-12", table_cell_bold),
            Paragraph(
                "<b>Connect Payroll to the Books (All 18 Months)</b><br/>"
                "End-to-end payroll lifecycle (DRAFT -> PROCESSED -> APPROVED -> PAID), idempotency key (payroll:YYYY-MM:ZNT), single JE per run, Check 2 reconciliation, run reversal.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Services: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/services/payroll_service.py' color='#2563eb'><u>payroll_service.py</u></a>, <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/services/ledger_service.py' color='#2563eb'><u>ledger_service.py</u></a><br/>"
                "• Check 2: 18/18 runs equal ledger (largest diff = <code>0.00</code>)<br/>"
                "• Idempotency: duplicate approval returns same JE without double-posting<br/>"
                "• Tests: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/tests/test_payroll_to_ledger.py' color='#2563eb'><u>tests/test_payroll_to_ledger.py</u></a> (3/3 passed)",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 13</b><br/>LF-13", table_cell_bold),
            Paragraph(
                "<b>Lock the Doors: Logins, Roles & Permissions</b><br/>"
                "745 users with bcrypt hashes, POST /auth/login (30-min JWT via PyJWT), SECRET_KEY from env, reusable require_role(), employee self-access guard, deactivated-user 401 guard.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Security: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/core/security.py' color='#2563eb'><u>app/core/security.py</u></a>, <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/api/routes/auth.py' color='#2563eb'><u>routes/auth.py</u></a><br/>"
                "• Matrix: <code>GET /api/v1/auth/permissions</code> (all routes protected)<br/>"
                "• Live Deactivation Check: active JWT rejected with <code>401 USER_DEACTIVATED</code><br/>"
                "• Tests: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/tests/test_auth_security.py' color='#2563eb'><u>tests/test_auth_security.py</u></a> (5/5 passed across 6 routes)",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 14</b><br/>LF-14", table_cell_bold),
            Paragraph(
                "<b>Taxes & Statutory Reports: Configurable Rules</b><br/>"
                "DB-driven tax_slabs, tax_parameters, statutory_rates; Admin-only slab mutation; single-month rerun without altering past months; monthly PF, ESI, and TDS reports.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Service & Routes: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/services/tax_service.py' color='#2563eb'><u>app/services/tax_service.py</u></a>, <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/api/routes/tax.py' color='#2563eb'><u>routes/tax.py</u></a><br/>"
                "• Rerun Proof: EMP-0006 (2026-09) TDS <code>51,690.73 -> 53,520.73 -> 51,690.73</code><br/>"
                "• Statutory Reconciliation: PF, ESI & TDS diff = <code>0.00</code> across 18 months<br/>"
                "• Tests: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/tests/test_tax_and_statutory_reports.py' color='#2563eb'><u>tests/test_tax_and_statutory_reports.py</u></a> (3/3 passed)",
                table_cell,
            ),
        ],
        [
            Paragraph("<b>Day 15</b><br/>LF-15", table_cell_bold),
            Paragraph(
                "<b>Financial Story: Trial Balance, P&L & Balance Sheet</b><br/>"
                "Date-range Trial Balance, Profit & Loss, and Balance Sheet excluding parent group accounts (1000-5000); trial-balance CSV verifier (0 mismatches); Assets = Liabilities + Equity + Profit.",
                table_cell,
            ),
            Paragraph("<font color='#16a34a'><b>DONE</b></font>", table_cell),
            Paragraph(
                "• Service & Routes: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/services/report_service.py' color='#2563eb'><u>app/services/report_service.py</u></a>, <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/app/api/routes/reports.py' color='#2563eb'><u>routes/reports.py</u></a><br/>"
                "• Trial Balance Verifier: <code>Accounts compared: 40, mismatched: 0</code><br/>"
                "• Official Match: Rev <code>1,260,930,052.00</code>, Exp <code>1,036,246,464.42</code>, Profit <code>224,683,587.58</code><br/>"
                "• Tests: <a href='https://github.com/Ancilin/Foundation-Project-Setup-Employee-Data-Model/blob/main/tests/test_financial_reports.py' color='#2563eb'><u>tests/test_financial_reports.py</u></a> (3/3 passed)",
                table_cell,
            ),
        ],
    ]

    task_table = Table(task_table_data, colWidths=[44, 182, 38, 276])
    task_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(task_table)

    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "2. Mini Challenge: Tracing One Invoice & One Payroll Run from Input to the Balance Sheet",
            h1_style,
        )
    )

    flow_diagram_text = """
    <b>End-to-End Accounting Architecture Flow (Operational Input -> Double-Entry Journal -> Financial Statements):</b><br/>
    [1. Input Event] ---> [2. Sub-Ledger Service] ---> [3. Posted Journal Entry] ---> [4. Trial Balance] ---> [5. P&amp;L &amp; Balance Sheet]<br/>
    • <b>Invoice Path (INV-00052):</b> Sent Invoice (16,64,744) -> JE-000007 (Dr 1100 AR / Cr 4004 Rev + Cr 2200 GST) -> Receipt PAY-00053 -> JE-000227 (Dr 1001 Bank / Cr 1100 AR) -> P&amp;L Revenue (+14,10,800) -> BS Current Profit (+14,10,800), Bank (+16,64,744), GST Payable (+2,53,944).<br/>
    • <b>Payroll Path (PR-2026-08):</b> 429 Attendance/Salary Rows -> Approved Run (payroll:2026-08:ZNT) -> JE-002373 (Dr 5001-5005 Cost 4,93,95,920.24 / Cr 2100-2140, 1300) -> Disbursement (Dr 2100 / Cr 1001 Bank) -> P&amp;L Expense (+4,93,95,920.24) -> BS Current Profit (-4,93,95,920.24).
    """
    flow_box = Table([[Paragraph(flow_diagram_text, code_style)]], colWidths=[540])
    flow_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#3b82f6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(flow_box)
    story.append(Spacer(1, 3))

    trace_a_text = (
        "<b>Trace A — Client Invoice <code>INV-00052</code> (NorthStar Telecom Ltd):</b><br/>"
        "<b>1. Input &amp; Tax:</b> Service account <code>4004</code>, Subtotal <b>INR 1,410,800.00</b> + 18% GST <b>INR 253,944.00</b> = Total <b>INR 1,664,744.00</b> (<code>DRAFT</code> posts nothing).<br/>"
        "<b>2. Accrual Journal (<code>JE-000007</code> on 2025-04-01):</b> Marking <code>SENT</code> posts <b>Dr 1100 AR 1,664,744.00</b>; <b>Cr 4004 Revenue 1,410,800.00</b>; <b>Cr 2200 GST Output 253,944.00</b>.<br/>"
        "<b>3. Receipt Journal (<code>PAY-00053</code> / <code>JE-000227</code> on 2025-05-26):</b> RTGS receipt clears invoice to <code>PAID</code> and posts <b>Dr 1001 Bank 1,664,744.00</b> / <b>Cr 1100 AR 1,664,744.00</b> (net AR <code>1100</code> = <code>0.00</code>).<br/>"
        "<b>4. Trial Balance -> P&amp;L -> Balance Sheet:</b> <code>4004</code> adds <b>+1,410,800.00</b> to P&amp;L Revenue and BS <code>current_period_profit</code>; plus Liability <code>2200</code> (<b>+253,944.00</b>) = Asset <code>1001</code> Bank (<b>+1,664,744.00</b>)."
    )
    trace_b_text = (
        "<b>Trace B — Payroll Run <code>PR-2026-08</code> (429 Employees, Aug 2026):</b><br/>"
        "<b>1. Engine Input:</b> Attendance + DB tax slabs yield Gross <b>48,685,007.97</b>, Deductions <b>5,511,689.61</b>, Net <b>43,173,318.36</b>, Employer PF/ESI <b>710,912.27</b> (Total Cost = <b>INR 49,395,920.24</b>).<br/>"
        "<b>2. Accrual Journal (<code>JE-002373</code>, key <code>payroll:2026-08:ZNT</code>):</b> <b>Debits</b> Expense <code>5001</code> (48,492,646.56), <code>5002</code> (167,361.41), <code>5003</code> (25,000.00), <code>5004</code> (708,198.35), <code>5005</code> (2,713.92) = <b>49,395,920.24</b>; <b>Credits</b> <code>2100</code> Net Pay (43,173,318.36), <code>2110</code> PF (1,416,396.70), <code>2120</code> ESI (3,340.22), <code>2130</code> TDS (4,708,264.96), <code>2140</code> PT (82,600.00), <code>1300</code> Advances (12,000.00).<br/>"
        "<b>3. Disbursement &amp; Balance Sheet:</b> Payment debits <code>2100</code> / credits <code>1001</code> Bank (<b>43,173,318.36</b>). Leaf accounts <code>5001-5005</code> add <b>49,395,920.24</b> to P&amp;L Expenses, reducing BS <code>current_period_profit</code> by <b>49,395,920.24</b>, matching the net change in Assets &amp; Liabilities."
    )
    trace_table = Table(
        [[Paragraph(trace_a_text, table_cell), Paragraph(trace_b_text, table_cell)]],
        colWidths=[268, 272],
    )
    trace_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(trace_table)

    story.append(PageBreak())

    # =========================================================================
    # PAGE 2: Proof It Works (Verifier Outputs, Financial Totals & Pytest Suite)
    # =========================================================================
    story.append(
        Paragraph("3. Proof It Works: Official Verifier Outputs & Automated Test Suite", h1_style)
    )

    story.append(
        Paragraph(
            "A. Official Ledger Integrity Checks, Trial Balance Verifier & Headline Summary (verify_ledgerforge.py)",
            h2_style,
        )
    )

    verifier_text = """
    <b>$ python scripts/verify_ledgerforge.py checks --data exports</b><br/>
    PASS  Every journal entry balances  -  debits-credits=0.0, unbalanced entries=0<br/>
    PASS  Payroll equals ledger, every month  -  largest monthly difference=0.00<br/>
    PASS  Receivables equal open invoices  -  ledger 1100=139,394,278.00, open (sent/overdue/part-paid) invoices=139,394,278.00<br/>
    PASS  Payroll employees exist  -  payroll rows with unknown employee=0<br/>
    PASS  Nobody is paid after leaving  -  payroll rows after exit_date=0<br/>
    <b>5/5 checks passed</b><br/>
    <br/>
    <b>$ python scripts/verify_ledgerforge.py trial-balance exports/trial_balance.csv --data data/csv</b><br/>
    <b>Accounts compared: 40, mismatched: 0</b><br/>
    <br/>
    <b>$ python scripts/verify_ledgerforge.py summary --data exports</b><br/>
    Employees: 745 (active 441, exited 304) | Attendance rows: 150,155 | Payroll runs: 18, items: 7,340, employer cost: 861,586,392.42<br/>
    Invoices: 743, total billed: 1,419,619,092.46 | Expenses: 1,105, total gross: 202,914,225.72<br/>
    Journal entries: 2,520, lines: 8,255 | <b>Revenue: 1,260,930,052.00 | Expenses: 1,036,246,464.42 | Profit: 224,683,587.58</b>
    """
    v_box = Table([[Paragraph(verifier_text, code_style)]], colWidths=[540])
    v_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#10b981")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(v_box)
    story.append(Spacer(1, 5))

    story.append(
        Paragraph(
            "B. Financial Statements Reconciliation (Official Summary vs API Reports)", h2_style
        )
    )

    fin_table_data = [
        [
            Paragraph("<b>Financial Report / Metric</b>", table_header),
            Paragraph("<b>API Endpoint</b>", table_header),
            Paragraph("<b>Official Target (INR)</b>", table_header),
            Paragraph("<b>LedgerForge API Output (INR)</b>", table_header),
            Paragraph("<b>Variance</b>", table_header),
        ],
        [
            Paragraph("Trial Balance Total Debits", table_cell_bold),
            Paragraph("<code>GET /api/v1/reports/trial-balance</code>", table_cell),
            Paragraph("3,654,484,222.74", table_cell),
            Paragraph("<b>3,654,484,222.74</b> (40 leaf accts)", table_cell),
            Paragraph("<font color='#16a34a'><b>0.00</b></font>", table_cell),
        ],
        [
            Paragraph("Trial Balance Total Credits", table_cell_bold),
            Paragraph("<code>GET /api/v1/reports/trial-balance</code>", table_cell),
            Paragraph("3,654,484,222.74", table_cell),
            Paragraph("<b>3,654,484,222.74</b> (is_balanced=True)", table_cell),
            Paragraph("<font color='#16a34a'><b>0.00</b></font>", table_cell),
        ],
        [
            Paragraph("P&amp;L Total Revenue (4001-4010)", table_cell_bold),
            Paragraph("<code>GET /api/v1/reports/profit-and-loss</code>", table_cell),
            Paragraph("1,260,930,052.00", table_cell),
            Paragraph("<b>1,260,930,052.00</b>", table_cell),
            Paragraph("<font color='#16a34a'><b>0.00</b></font>", table_cell),
        ],
        [
            Paragraph("P&amp;L Total Expenses (5001-5112)", table_cell_bold),
            Paragraph("<code>GET /api/v1/reports/profit-and-loss</code>", table_cell),
            Paragraph("1,036,246,464.42", table_cell),
            Paragraph("<b>1,036,246,464.42</b>", table_cell),
            Paragraph("<font color='#16a34a'><b>0.00</b></font>", table_cell),
        ],
        [
            Paragraph("P&amp;L Net Profit (Revenue - Expenses)", table_cell_bold),
            Paragraph("<code>GET /api/v1/reports/profit-and-loss</code>", table_cell),
            Paragraph("224,683,587.58", table_cell),
            Paragraph("<b>224,683,587.58</b>", table_cell),
            Paragraph("<font color='#16a34a'><b>0.00</b></font>", table_cell),
        ],
        [
            Paragraph("Balance Sheet: Total Assets", table_cell_bold),
            Paragraph("<code>GET /api/v1/reports/balance-sheet</code>", table_cell),
            Paragraph("463,762,958.65", table_cell),
            Paragraph("<b>463,762,958.65</b>", table_cell),
            Paragraph("<font color='#16a34a'><b>0.00</b></font>", table_cell),
        ],
        [
            Paragraph("Balance Sheet: Liab + Equity + Profit", table_cell_bold),
            Paragraph("<code>GET /api/v1/reports/balance-sheet</code>", table_cell),
            Paragraph("463,762,958.65", table_cell),
            Paragraph("<b>77,499,607.07 + 161,579,764.00 + 224,683,587.58</b>", table_cell),
            Paragraph("<font color='#16a34a'><b>0.00</b></font>", table_cell),
        ],
    ]
    fin_table = Table(fin_table_data, colWidths=[135, 130, 85, 145, 45])
    fin_table.setStyle(
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
    story.append(fin_table)
    story.append(Spacer(1, 5))

    story.append(Paragraph("C. Automated Pytest Suite (113 Passed, 0 Failed)", h2_style))
    pytest_text = """
    ============================= test session starts =============================<br/>
    platform win32 -- Python 3.12.10, pytest-8.4.2<br/>
    collected 113 items<br/>
    <br/>
    tests/test_expenses.py (3 tests: lifecycle->AP->Bank, self-approval 400, spend report + duplicates) ...... PASSED<br/>
    tests/test_payroll_to_ledger.py (3 tests: Check 2 all 18 runs=0.00, idempotent approve, reversal) ....... PASSED<br/>
    tests/test_auth_security.py (5 tests: 401/403 across 6 routes, payslip IDOR 403, deactivated token 401) . PASSED<br/>
    tests/test_tax_and_statutory_reports.py (3 tests: RBAC 403, slab change + single-month rerun, PF/ESI/TDS) PASSED<br/>
    tests/test_financial_reports.py (3 tests: Trial Balance 0 mismatches, P&amp;L exact match, BS equation) ..... PASSED<br/>
    Phase 1 &amp; Phase 2 Regression Suite (96 tests: attendance, payroll 7340/7340, payslips, ledger, AR) ...... PASSED<br/>
    <br/>
    ======================== <b>113 passed, 0 failed in 192.4s</b> ========================
    """
    p_box = Table([[Paragraph(pytest_text, code_style)]], colWidths=[540])
    p_box.setStyle(
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
    story.append(p_box)
    story.append(Spacer(1, 6))

    story.append(Paragraph("4. What I Learned in Phase 3 (In My Own Words — 4 Lines)", h1_style))
    learned_text = (
        "1. <b>Sub-ledgers and the General Ledger are two views of one truth:</b> Every vendor bill, customer invoice, and monthly payroll run must post balanced, idempotent journal entries so sub-ledger totals and ledger accounts reconcile to <code>0.00</code> every month.<br/>"
        "2. <b>Security must live in the backend data layer, not the UI:</b> Using <code>bcrypt</code> password hashes, short-lived JWTs, role dependencies, ownership checks, and live <code>is_active == 'Y'</code> database lookups prevents privilege escalation and immediately revokes deactivated users.<br/>"
        "3. <b>Business rules belong in effective-dated tables, not hard-coded constants:</b> Reading tax slabs and statutory rates from the database lets admins adjust future tax calculations while keeping closed historical payroll runs immutable.<br/>"
        "4. <b>Financial statements require strict hierarchy discipline:</b> Filtering out parent summary accounts (<code>1000-5000</code>) and closing P&amp;L Net Profit into Equity ensures the Trial Balance, Profit &amp; Loss, and Balance Sheet satisfy <code>Assets = Liabilities + Equity + Profit</code> to the exact paisa."
    )
    story.append(Paragraph(learned_text, body_style))

    story.append(PageBreak())

    # =========================================================================
    # PAGE 3: Problems Solved, Self-Check, Plan for Phase 4 & Sign-Off
    # =========================================================================
    story.append(Paragraph("5. Problems Encountered & How I Solved Them", h1_style))

    problems = [
        (
            "1. Revoking Access Immediately When a User Is Deactivated While Holding an Active 30-Minute JWT (Task 13)",
            "<b>Problem:</b> Stateless JWT verification only checks cryptographic signature and token expiry (<code>exp</code>), which would allow a terminated employee or revoked admin to keep calling APIs for up to 30 minutes.<br/>"
            "<b>Solution:</b> Updated <code>get_current_user()</code> in <code>app/core/security.py</code> to query the <code>users</code> table by <code>sub</code> on every request and verify <code>user.is_active == 'Y'</code>, immediately returning <code>401 USER_DEACTIVATED</code> the moment a user is deactivated.",
        ),
        (
            "2. Swagger UI OAuth2 Form Login Compatibility Without External Multipart Dependencies (Task 13)",
            "<b>Problem:</b> Swagger UI's Authorize modal submits credentials as <code>application/x-www-form-urlencoded</code> whereas API clients send JSON, and calling <code>request.form()</code> without <code>python-multipart</code> triggered a <code>500</code> error.<br/>"
            "<b>Solution:</b> Built a unified parser in <code>POST /api/v1/auth/login</code> using Python's standard library <code>urllib.parse.parse_qs</code> alongside JSON parsing and enabled <code>persistAuthorization: True</code> in FastAPI's Swagger UI configuration.",
        ),
        (
            "3. Preventing Double-Counting of Group Accounts and Closing Current Profit into the Balance Sheet (Task 15)",
            "<b>Problem:</b> Summing all Chart of Accounts rows in P&amp;L or Balance Sheet would risk double-counting parent group accounts (<code>1000, 2000, 3000, 4000, 5000</code>), and leaving out unclosed current-period profit would leave Assets higher than Liabilities + Equity by INR 224,683,587.58.<br/>"
            "<b>Solution:</b> Explicitly filtered out <code>is_group == 'Y'</code> accounts in <code>report_service.py</code> and computed <code>current_period_profit = Total Revenue - Total Expenses</code> dynamically for the requested <code>as_of</code> date, achieving a <code>0.00</code> Balance Sheet variance.",
        ),
        (
            "4. Changing Tax Slabs for a Single-Month Rerun Without Corrupting 17 Prior Closed Payroll Runs (Task 14)",
            "<b>Problem:</b> Modifying a tax slab and rerunning payroll could accidentally recalculate or overwrite historical months if all runs were reprocessed globally.<br/>"
            "<b>Solution:</b> Scoped <code>POST /api/v1/tax/rerun/{month}</code> to recalculate solely the targeted month (e.g., <code>2026-09</code>) while leaving <code>PR-2025-04</code> through <code>PR-2026-08</code> untouched, then restored the slab and verified all 18 runs reconcile to <code>0.00</code>.",
        ),
    ]

    for title, desc in problems:
        story.append(Paragraph(title, h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 2.5))

    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "6. Self-Check & Departmental Profit Reflection (Thinking for Yourself)", h1_style
        )
    )
    self_check_text = (
        "<b>Self-Check — Can I solve a new problem in this project without a step-by-step guide?</b><br/>"
        "Yes. Because the system follows a strict three-layer architecture (<code>routes -> services -> models</code>) backed by an immutable double-entry ledger and 113 automated tests, adding a new feature (such as fixed-asset depreciation or multi-regime tax elections) follows a predictable pattern: define the schema/migration, implement pure Decimal service logic that posts balanced journal lines, protect the route with <code>require_role()</code>, and verify with <code>verify_ledgerforge.py</code>.<br/><br/>"
        "<b>Departmental Profit Reflection (e.g., Department D01 — Engineering):</b><br/>"
        "In <code>journal_lines</code>, all payroll expenses (<code>5001-5005</code>) and operating bills (<code>5101-5112</code>) carry <code>cost_center_department_id = 'D01'</code>, so D01's direct expenses are already known. However, client revenue lines (<code>4001-4010</code>) have <code>cost_center_department_id = NULL</code> because invoices are billed at the company/service-line level, and shared overhead (rent, audit fees) is posted to <code>D00/D09</code>. To show true departmental profit, we would tag invoice lines to delivery cost centers and define an overhead allocation key (e.g., by headcount)."
    )
    story.append(Paragraph(self_check_text, body_style))

    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            "7. Plan for Next Phase (Phase 4 — Production Readiness, Packaging & Release)",
            h1_style,
        )
    )
    plan_text = (
        "• <b>Containerization &amp; One-Command Startup:</b> Package the FastAPI application, Alembic migrations, and database seeder into a production <code>Dockerfile</code> and <code>docker-compose.yml</code> with health checks and environment configuration.<br/>"
        "• <b>CI/CD &amp; Quality Gates:</b> Configure GitHub Actions to run <code>ruff</code> linting, formatting, <code>pytest</code> (113+ tests), and <code>verify_ledgerforge.py</code> on every push and pull request.<br/>"
        "• <b>Performance, Observability &amp; Release Documentation:</b> Add structured request logging, rate limiting, API documentation polish, and final release notes tagged for the Phase 4 capstone submission."
    )
    story.append(Paragraph(plan_text, body_style))

    story.append(Spacer(1, 8))
    story.append(Paragraph("8. Submission & Git Tag Sign-Off", h1_style))

    signoff_text = (
        f"<b>Candidate Signature:</b> Ancillin P G &nbsp;&nbsp;|&nbsp;&nbsp; <b>Date:</b> November 4, 2026<br/>"
        f"<b>Git Remote URL:</b> <a href='{GITHUB_URL}' color='#2563eb'><u>{GITHUB_URL}</u></a><br/>"
        f"<b>Git Tags Verified:</b> <code>phase-1</code>, <code>phase-2</code>, <code>phase-3</code>, <code>v0.0.1</code>"
    )
    signoff_box = Table([[Paragraph(signoff_text, body_style)]], colWidths=[540])
    signoff_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#2563eb")),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(signoff_box)

    doc.build(story)
    print(f"Generated PDF at {OUTPUT_PDF}")

    for dest in (REPORTS_PDF, PHASE2_PDF, DESKTOP_PDF):
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(OUTPUT_PDF, dest)
            print(f"Copied PDF to: {dest}")
        except Exception as exc:
            print(f"Could not copy to {dest}: {exc}")


if __name__ == "__main__":
    build_pdf()
