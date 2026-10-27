"""Payslip service and PDF generator (LF-08): Indian number formatting, ownership check, and ReportLab PDF layout."""

from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.department import Department
from app.models.employee import Employee
from app.models.payroll import PayrollItem, PayrollRun
from app.models.role import Role
from app.services.payroll_service import calculate_employee_month_from_db, round_money, to_dec

COMPANY_NAME = "Zenith Nova Technologies Pvt Ltd"
COMPANY_ADDRESS = "Tower B, Prestige Tech Park, Outer Ring Road, Bengaluru - 560103, Karnataka, India"

_ONES = [
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
]
_TENS = [
    "",
    "",
    "Twenty",
    "Thirty",
    "Forty",
    "Fifty",
    "Sixty",
    "Seventy",
    "Eighty",
    "Ninety",
]


def format_inr(amount: Decimal | int | float | str | None) -> str:
    """Format a monetary value in the Indian numbering system (e.g., 123456 -> '1,23,456.00')."""
    dec = round_money(to_dec(amount))
    is_negative = dec < Decimal("0.00")
    abs_dec = abs(dec)

    s = f"{abs_dec:.2f}"
    int_part, frac_part = s.split(".")

    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last_three = int_part[-3:]
        rest = int_part[:-3]
        groups: list[str] = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        formatted_int = ",".join(groups) + "," + last_three

    result = f"{formatted_int}.{frac_part}"
    return f"-{result}" if is_negative else result


def _two_digit_words(n: int) -> str:
    if n == 0:
        return ""
    if n < 20:
        return _ONES[n]
    tens_word = _TENS[n // 10]
    ones_word = _ONES[n % 10]
    return f"{tens_word}-{ones_word}" if ones_word else tens_word


def _int_to_indian_words(n: int) -> str:
    if n == 0:
        return "Zero"

    parts: list[str] = []
    crores = n // 10_000_000
    n %= 10_000_000
    lakhs = n // 100_000
    n %= 100_000
    thousands = n // 1_000
    n %= 1_000
    hundreds = n // 100
    remainder = n % 100

    if crores > 0:
        parts.append(f"{_int_to_indian_words(crores)} Crore")
    if lakhs > 0:
        parts.append(f"{_two_digit_words(lakhs)} Lakh")
    if thousands > 0:
        parts.append(f"{_two_digit_words(thousands)} Thousand")
    if hundreds > 0:
        parts.append(f"{_ONES[hundreds]} Hundred")
    if remainder > 0:
        parts.append(_two_digit_words(remainder))

    return " ".join(parts)


def number_to_indian_words(amount: Decimal | int | float | str | None) -> str:
    """Convert a monetary amount into Indian Rupees and Paise in words."""
    dec = abs(round_money(to_dec(amount)))
    rupees = int(dec)
    paise = int((dec - Decimal(rupees)) * 100)

    rupee_words = _int_to_indian_words(rupees)
    if paise > 0:
        paise_words = _two_digit_words(paise)
        return f"Rupees {rupee_words} and {paise_words} Paise Only"
    return f"Rupees {rupee_words} Only"


def enforce_payslip_access(
    target_employee_id: str,
    requester_id: str | None = None,
    requester_role: str | None = None,
) -> None:
    """Only the owner of the payslip or HR/ADMIN may fetch a payslip.
    Raises ForbiddenError (HTTP 403) when a non-HR stranger attempts access.
    """
    role_norm = (requester_role or "").strip().upper()
    req_emp = (requester_id or "").strip()

    if role_norm in ("HR", "ADMIN"):
        return

    if req_emp and req_emp == target_employee_id:
        return

    raise ForbiddenError(
        f"Access denied: caller (employee_id='{req_emp or 'anonymous'}', role='{role_norm or 'EMPLOYEE'}') "
        f"is not authorized to view payslip for '{target_employee_id}'. Only the owner or HR may access."
    )


def _parse_run_month(run_id: str) -> str:
    """Extract 'YYYY-MM' from run_id ('PR-2025-04' or '2025-04')."""
    clean = run_id.strip()
    if clean.upper().startswith("PR-"):
        month_part = clean[3:]
    else:
        month_part = clean
    parts = month_part.split("-")
    if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
        raise ValidationError(f"Invalid run_id '{run_id}'. Expected 'PR-YYYY-MM' or 'YYYY-MM'.")
    return f"{parts[0]}-{parts[1]}"


def get_payslip_data(
    session: Session,
    employee_id: str,
    run_id: str,
    requester_id: str | None = None,
    requester_role: str | None = None,
) -> dict[str, Any]:
    """Compute and format a complete payslip for an employee and payroll run using the calculation engine."""
    enforce_payslip_access(
        target_employee_id=employee_id,
        requester_id=requester_id,
        requester_role=requester_role,
    )

    emp = session.get(Employee, employee_id)
    if not emp:
        raise NotFoundError(f"Employee '{employee_id}' not found")

    month = _parse_run_month(run_id)
    canonical_run_id = f"PR-{month}"

    # Look up PayrollRun metadata (pay_date) and any variable_pay / other_deductions for this run
    pr_run = session.get(PayrollRun, canonical_run_id)
    pay_date: date | None = pr_run.pay_date if pr_run else None

    pi_row = session.scalar(
        select(PayrollItem).where(
            PayrollItem.run_id == canonical_run_id,
            PayrollItem.employee_id == employee_id,
        )
    )

    var_pay = Decimal(str(pi_row.variable_pay)) if pi_row else Decimal("0.00")
    var_pay_type = pi_row.variable_pay_type if pi_row else None
    other_ded = Decimal(str(pi_row.other_deductions)) if pi_row else Decimal("0.00")

    # Calculate all figures fresh from our payroll calculation engine (Task 7)
    calc = calculate_employee_month_from_db(
        session=session,
        employee_id=employee_id,
        month=month,
        variable_pay=var_pay,
        variable_pay_type=var_pay_type,
        other_deductions=other_ded,
    )

    dept = session.get(Department, emp.department_id)
    role = session.get(Role, emp.role_id)

    dept_name = dept.department_name if dept else emp.department_id
    role_title = role.role_title if role else emp.role_id

    earnings = [
        {"label": "Basic Salary", "amount": calc["basic"], "formatted_amount": format_inr(calc["basic"])},
        {"label": "House Rent Allowance (HRA)", "amount": calc["hra"], "formatted_amount": format_inr(calc["hra"])},
        {"label": "Conveyance Allowance", "amount": calc["conveyance"], "formatted_amount": format_inr(calc["conveyance"])},
        {"label": "Medical Allowance", "amount": calc["medical"], "formatted_amount": format_inr(calc["medical"])},
        {
            "label": "Special Allowance",
            "amount": calc["special_allowance"],
            "formatted_amount": format_inr(calc["special_allowance"]),
        },
    ]
    if calc["overtime_pay"] > Decimal("0.00"):
        earnings.append(
            {
                "label": f"Overtime Pay ({calc['overtime_hours_paid']} hrs)",
                "amount": calc["overtime_pay"],
                "formatted_amount": format_inr(calc["overtime_pay"]),
            }
        )
    if calc["variable_pay"] > Decimal("0.00"):
        vp_label = f"Variable Pay ({calc['variable_pay_type']})" if calc.get("variable_pay_type") else "Variable Pay"
        earnings.append(
            {
                "label": vp_label,
                "amount": calc["variable_pay"],
                "formatted_amount": format_inr(calc["variable_pay"]),
            }
        )

    deductions = [
        {
            "label": "Provident Fund (Employee 12%)",
            "amount": calc["pf_employee"],
            "formatted_amount": format_inr(calc["pf_employee"]),
        },
        {
            "label": "Employees' State Insurance (ESI)",
            "amount": calc["esi_employee"],
            "formatted_amount": format_inr(calc["esi_employee"]),
        },
        {
            "label": "Professional Tax (PT)",
            "amount": calc["professional_tax"],
            "formatted_amount": format_inr(calc["professional_tax"]),
        },
        {
            "label": "Income Tax (TDS)",
            "amount": calc["tds"],
            "formatted_amount": format_inr(calc["tds"]),
        },
    ]
    if calc["other_deductions"] > Decimal("0.00"):
        deductions.append(
            {
                "label": "Other Deductions / Loan Recovery",
                "amount": calc["other_deductions"],
                "formatted_amount": format_inr(calc["other_deductions"]),
            }
        )

    # Compute Year-To-Date (YTD) summary across the financial year up to period_end
    p_start: date = calc["period_start"]
    p_end: date = calc["period_end"]
    if p_start.month >= 4:
        fy_start = date(p_start.year, 4, 1)
        fy_label = f"FY{p_start.year}-{str(p_start.year + 1)[-2:]}"
    else:
        fy_start = date(p_start.year - 1, 4, 1)
        fy_label = f"FY{p_start.year - 1}-{str(p_start.year)[-2:]}"

    ytd_items = list(
        session.scalars(
            select(PayrollItem).where(
                PayrollItem.employee_id == employee_id,
                PayrollItem.period_start >= fy_start,
                PayrollItem.period_end <= p_end,
            )
        ).all()
    )

    if ytd_items:
        months_inc = len(ytd_items)
        ytd_gross = round_money(sum((Decimal(str(i.gross_pay)) for i in ytd_items), Decimal("0.00")))
        ytd_ded = round_money(sum((Decimal(str(i.total_deductions)) for i in ytd_items), Decimal("0.00")))
        ytd_tds = round_money(sum((Decimal(str(i.tds)) for i in ytd_items), Decimal("0.00")))
        ytd_pf = round_money(sum((Decimal(str(i.pf_employee)) for i in ytd_items), Decimal("0.00")))
        ytd_net = round_money(sum((Decimal(str(i.net_pay)) for i in ytd_items), Decimal("0.00")))
    else:
        months_inc = 1
        ytd_gross = calc["gross_pay"]
        ytd_ded = calc["total_deductions"]
        ytd_tds = calc["tds"]
        ytd_pf = calc["pf_employee"]
        ytd_net = calc["net_pay"]

    ytd_summary = {
        "financial_year": fy_label,
        "months_included": months_inc,
        "ytd_gross_pay": ytd_gross,
        "ytd_gross_pay_formatted": format_inr(ytd_gross),
        "ytd_total_deductions": ytd_ded,
        "ytd_total_deductions_formatted": format_inr(ytd_ded),
        "ytd_tds": ytd_tds,
        "ytd_tds_formatted": format_inr(ytd_tds),
        "ytd_pf_employee": ytd_pf,
        "ytd_pf_employee_formatted": format_inr(ytd_pf),
        "ytd_net_pay": ytd_net,
        "ytd_net_pay_formatted": format_inr(ytd_net),
    }

    return {
        "company_name": COMPANY_NAME,
        "company_address": COMPANY_ADDRESS,
        "run_id": canonical_run_id,
        "month": month,
        "period_start": p_start,
        "period_end": p_end,
        "pay_date": pay_date,
        "employee_id": emp.employee_id,
        "employee_name": f"{emp.first_name} {emp.last_name}",
        "work_email": emp.work_email,
        "department_id": emp.department_id,
        "department_name": dept_name,
        "role_id": emp.role_id,
        "role_title": role_title,
        "employment_type": emp.employment_type,
        "work_location": emp.work_location,
        "calendar_days": calc["calendar_days"],
        "days_employed": calc["days_employed"],
        "lop_days": calc["lop_days"],
        "payable_days": calc["payable_days"],
        "overtime_hours_paid": calc["overtime_hours_paid"],
        "monthly_fixed_gross": calc["monthly_fixed_gross"],
        "monthly_fixed_gross_formatted": format_inr(calc["monthly_fixed_gross"]),
        "basic": calc["basic"],
        "basic_formatted": format_inr(calc["basic"]),
        "hra": calc["hra"],
        "hra_formatted": format_inr(calc["hra"]),
        "conveyance": calc["conveyance"],
        "conveyance_formatted": format_inr(calc["conveyance"]),
        "medical": calc["medical"],
        "medical_formatted": format_inr(calc["medical"]),
        "special_allowance": calc["special_allowance"],
        "special_allowance_formatted": format_inr(calc["special_allowance"]),
        "earned_fixed_pay": calc["earned_fixed_pay"],
        "earned_fixed_pay_formatted": format_inr(calc["earned_fixed_pay"]),
        "overtime_pay": calc["overtime_pay"],
        "overtime_pay_formatted": format_inr(calc["overtime_pay"]),
        "variable_pay": calc["variable_pay"],
        "variable_pay_formatted": format_inr(calc["variable_pay"]),
        "variable_pay_type": calc["variable_pay_type"],
        "gross_pay": calc["gross_pay"],
        "gross_pay_formatted": format_inr(calc["gross_pay"]),
        "pf_employee": calc["pf_employee"],
        "pf_employee_formatted": format_inr(calc["pf_employee"]),
        "esi_employee": calc["esi_employee"],
        "esi_employee_formatted": format_inr(calc["esi_employee"]),
        "professional_tax": calc["professional_tax"],
        "professional_tax_formatted": format_inr(calc["professional_tax"]),
        "tds": calc["tds"],
        "tds_formatted": format_inr(calc["tds"]),
        "other_deductions": calc["other_deductions"],
        "other_deductions_formatted": format_inr(calc["other_deductions"]),
        "total_deductions": calc["total_deductions"],
        "total_deductions_formatted": format_inr(calc["total_deductions"]),
        "net_pay": calc["net_pay"],
        "net_pay_formatted": format_inr(calc["net_pay"]),
        "net_pay_in_words": number_to_indian_words(calc["net_pay"]),
        "pf_employer": calc["pf_employer"],
        "pf_employer_formatted": format_inr(calc["pf_employer"]),
        "esi_employer": calc["esi_employer"],
        "esi_employer_formatted": format_inr(calc["esi_employer"]),
        "employer_cost": calc["employer_cost"],
        "employer_cost_formatted": format_inr(calc["employer_cost"]),
        "earnings": earnings,
        "deductions": deductions,
        "ytd_summary": ytd_summary,
        "calculation_note": calc["calculation_note"],
    }


def generate_payslip_pdf(payslip: dict[str, Any], output_path: Path | None = None) -> bytes:
    """Render a professional single-page PDF payslip from payslip data using ReportLab.
    Net Pay is prominently styled as the largest, most visible figure on the page.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=32,
        rightMargin=32,
        topMargin=28,
        bottomMargin=28,
        title=f"Payslip - {payslip['employee_id']} - {payslip['run_id']}",
    )

    styles = getSampleStyleSheet()

    company_style = ParagraphStyle(
        "CompanyTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )
    address_style = ParagraphStyle(
        "CompanyAddress",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    banner_title_style = ParagraphStyle(
        "PayslipTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1d4ed8"),
        alignment=1,
        spaceBefore=4,
        spaceAfter=6,
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=6,
        spaceAfter=4,
    )
    cell_label = ParagraphStyle(
        "CellLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.2,
        leading=11,
        textColor=colors.HexColor("#334155"),
    )
    cell_val = ParagraphStyle(
        "CellVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
    )
    cell_val_right = ParagraphStyle(
        "CellValRight",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        alignment=2,
    )
    cell_bold_right = ParagraphStyle(
        "CellBoldRight",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
        alignment=2,
    )
    th_left = ParagraphStyle(
        "THLeft",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )
    th_right = ParagraphStyle(
        "THRight",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=2,
    )
    net_pay_label_style = ParagraphStyle(
        "NetPayLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#065f46"),
    )
    net_pay_amount_style = ParagraphStyle(
        "NetPayAmount",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#047857"),
        alignment=2,
    )
    net_words_style = ParagraphStyle(
        "NetWords",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
    )
    footer_style = ParagraphStyle(
        "FooterNote",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#64748b"),
        alignment=1,
    )

    story: list[Any] = []

    # 1. Company Header
    story.append(Paragraph(payslip["company_name"], company_style))
    story.append(Paragraph(payslip["company_address"], address_style))
    period_str = f"{payslip['period_start'].strftime('%d %b %Y')} to {payslip['period_end'].strftime('%d %b %Y')}"
    story.append(
        Paragraph(
            f"PAYSLIP FOR THE PERIOD: {period_str.upper()} ({payslip['run_id']})",
            banner_title_style,
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1"), spaceAfter=8))

    # 2. Employee & Period Metadata Grid
    pay_date_str = payslip["pay_date"].isoformat() if payslip.get("pay_date") else "Pending / End of Month"
    emp_meta_rows = [
        [
            Paragraph("Employee ID", cell_label),
            Paragraph(str(payslip["employee_id"]), cell_val),
            Paragraph("Department", cell_label),
            Paragraph(f"{payslip['department_name']} ({payslip['department_id']})", cell_val),
        ],
        [
            Paragraph("Employee Name", cell_label),
            Paragraph(str(payslip["employee_name"]), cell_val),
            Paragraph("Role / Designation", cell_label),
            Paragraph(f"{payslip['role_title']} ({payslip['role_id']})", cell_val),
        ],
        [
            Paragraph("Work Email", cell_label),
            Paragraph(str(payslip["work_email"]), cell_val),
            Paragraph("Employment Type", cell_label),
            Paragraph(f"{payslip['employment_type']} ({payslip['work_location']})", cell_val),
        ],
        [
            Paragraph("Monthly Fixed Gross", cell_label),
            Paragraph(f"INR {payslip['monthly_fixed_gross_formatted']}", cell_val),
            Paragraph("Pay Date", cell_label),
            Paragraph(pay_date_str, cell_val),
        ],
    ]
    emp_table = Table(emp_meta_rows, colWidths=[105, 160, 105, 160])
    emp_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(emp_table)
    story.append(Spacer(1, 8))

    # 3. Attendance & Payable Days Summary Strip
    att_rows = [
        [
            Paragraph("<b>Calendar Days</b>", th_left),
            Paragraph("<b>Days Employed</b>", th_left),
            Paragraph("<b>LOP Days</b>", th_left),
            Paragraph("<b>Payable Days</b>", th_left),
            Paragraph("<b>Paid Overtime Hours</b>", th_left),
        ],
        [
            Paragraph(str(payslip["calendar_days"]), cell_val),
            Paragraph(str(payslip["days_employed"]), cell_val),
            Paragraph(str(payslip["lop_days"]), cell_val),
            Paragraph(f"<b>{payslip['payable_days']}</b>", cell_val),
            Paragraph(f"{payslip['overtime_hours_paid']} hrs", cell_val),
        ],
    ]
    att_table = Table(att_rows, colWidths=[106, 106, 106, 106, 106])
    att_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(att_table)
    story.append(Spacer(1, 10))

    # 4. Side-by-Side Earnings & Deductions Breakdown
    earnings_list = payslip["earnings"]
    deductions_list = payslip["deductions"]
    max_rows = max(len(earnings_list), len(deductions_list))

    fin_rows: list[list[Any]] = [
        [
            Paragraph("EARNINGS", th_left),
            Paragraph("AMOUNT (INR)", th_right),
            Paragraph("DEDUCTIONS", th_left),
            Paragraph("AMOUNT (INR)", th_right),
        ]
    ]

    for idx in range(max_rows):
        if idx < len(earnings_list):
            e_item = earnings_list[idx]
            e_label = Paragraph(str(e_item["label"]), cell_val)
            e_amt = Paragraph(str(e_item["formatted_amount"]), cell_val_right)
        else:
            e_label = Paragraph("", cell_val)
            e_amt = Paragraph("", cell_val_right)

        if idx < len(deductions_list):
            d_item = deductions_list[idx]
            d_label = Paragraph(str(d_item["label"]), cell_val)
            d_amt = Paragraph(str(d_item["formatted_amount"]), cell_val_right)
        else:
            d_label = Paragraph("", cell_val)
            d_amt = Paragraph("", cell_val_right)

        fin_rows.append([e_label, e_amt, d_label, d_amt])

    # Totals Row
    fin_rows.append(
        [
            Paragraph("<b>GROSS EARNINGS</b>", cell_label),
            Paragraph(f"<b>INR {payslip['gross_pay_formatted']}</b>", cell_bold_right),
            Paragraph("<b>TOTAL DEDUCTIONS</b>", cell_label),
            Paragraph(f"<b>INR {payslip['total_deductions_formatted']}</b>", cell_bold_right),
        ]
    )

    fin_table = Table(fin_rows, colWidths=[170, 95, 170, 95])
    fin_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#1e3a8a")),
                ("BACKGROUND", (2, 0), (3, 0), colors.HexColor("#7f1d1d")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8fafc")]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(fin_table)
    story.append(Spacer(1, 12))

    # 5. Prominent NET PAY Callout Box (Most visible number on the document)
    net_pay_rows = [
        [
            Paragraph("NET PAYABLE (TAKE-HOME PAY)", net_pay_label_style),
            Paragraph(f"INR {payslip['net_pay_formatted']}", net_pay_amount_style),
        ],
        [
            Paragraph(f"<b>Amount in Words:</b> {payslip['net_pay_in_words']}", net_words_style),
            Paragraph("", net_words_style),
        ],
    ]
    net_box = Table(net_pay_rows, colWidths=[265, 265])
    net_box.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 1), (1, 1)),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ecfdf5")),
                ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#059669")),
                ("LINEABOVE", (0, 1), (1, 1), 0.5, colors.HexColor("#a7f3d0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 1), (-1, 1), 5),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(net_box)
    story.append(Spacer(1, 10))

    # 6. Employer Contributions & Year-to-Date (YTD) Summary
    ytd = payslip["ytd_summary"]
    story.append(
        Paragraph(
            f"Year-to-Date (YTD) Summary ({ytd['financial_year']} — {ytd['months_included']} Month(s)) & Employer Cost",
            section_heading,
        )
    )
    ytd_rows = [
        [
            Paragraph("<b>YTD Gross Pay</b>", cell_label),
            Paragraph(f"INR {ytd['ytd_gross_pay_formatted']}", cell_val_right),
            Paragraph("<b>Employer PF (12%)</b>", cell_label),
            Paragraph(f"INR {payslip['pf_employer_formatted']}", cell_val_right),
        ],
        [
            Paragraph("<b>YTD Total Deductions</b>", cell_label),
            Paragraph(f"INR {ytd['ytd_total_deductions_formatted']}", cell_val_right),
            Paragraph("<b>Employer ESI (3.25%)</b>", cell_label),
            Paragraph(f"INR {payslip['esi_employer_formatted']}", cell_val_right),
        ],
        [
            Paragraph("<b>YTD Income Tax (TDS)</b>", cell_label),
            Paragraph(f"INR {ytd['ytd_tds_formatted']}", cell_val_right),
            Paragraph("<b>Total Employer Cost</b>", cell_label),
            Paragraph(f"<b>INR {payslip['employer_cost_formatted']}</b>", cell_bold_right),
        ],
        [
            Paragraph("<b>YTD Net Pay</b>", cell_label),
            Paragraph(f"<b>INR {ytd['ytd_net_pay_formatted']}</b>", cell_bold_right),
            Paragraph("<b>Engine Rule Note</b>", cell_label),
            Paragraph(str(payslip["calculation_note"]), cell_val),
        ],
    ]
    ytd_table = Table(ytd_rows, colWidths=[135, 130, 135, 130])
    ytd_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(ytd_table)
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "This is a computer-generated payslip produced by the LedgerForge Payroll Engine and does not require a physical signature.",
            footer_style,
        )
    )

    doc.build(story)
    pdf_bytes = buffer.getvalue()

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pdf_bytes)

    return pdf_bytes
