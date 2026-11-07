"""Double-entry accounting ledger service (LF-09):
- Chart of accounts lookup
- create_journal_entry(lines) enforcing total_debit == total_credit
- Immutability of POSTED entries (refuses edits/deletes; offers reverse_journal_entry)
- account_balance(account, date)
- post_payroll_run_to_ledger(run_id) posting employer cost accounts (5001..5005) and payables (2100..2140, 1300)
"""

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
import uuid

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.ledger import ChartOfAccount, JournalEntry, JournalLine
from app.models.payroll import PayrollItem, PayrollRun

TWO_PLACES = Decimal("0.01")


def _to_dec(val: Decimal | int | float | str | None) -> Decimal:
    if val is None or val == "":
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def round_money(val: Decimal | int | float | str | None) -> Decimal:
    return _to_dec(val).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _derive_financial_year(d: date) -> str:
    if d.month >= 4:
        return f"{d.year}-{str(d.year + 1)[-2:]}"
    return f"{d.year - 1}-{str(d.year)[-2:]}"


def _next_entry_id(session: Session) -> str:
    count = session.scalar(select(func.count(JournalEntry.entry_id))) or 0
    candidate = f"JE-{count + 1:06d}"
    if session.get(JournalEntry, candidate) is not None:
        candidate = f"JE-{uuid.uuid4().hex[:6].upper()}"
    return candidate


def _next_line_number_base(session: Session) -> int:
    return (session.scalar(select(func.count(JournalLine.line_id))) or 0) + 1


# SQLAlchemy ORM guard: prevent modifying or deleting a POSTED JournalEntry or its JournalLines
@event.listens_for(JournalEntry, "before_update")
def _prevent_posted_entry_update(_mapper, _connection, target: JournalEntry) -> None:
    if target.status == "POSTED":
        raise ConflictError(
            f"Journal entry '{target.entry_id}' is POSTED and read-only. "
            "Edits are refused; create a reversing entry instead.",
            error_code="IMMUTABLE_POSTED_ENTRY",
        )


@event.listens_for(JournalEntry, "before_delete")
def _prevent_posted_entry_delete(_mapper, _connection, target: JournalEntry) -> None:
    if target.status == "POSTED":
        raise ConflictError(
            f"Journal entry '{target.entry_id}' is POSTED and read-only. "
            "Deletions are refused; create a reversing entry instead.",
            error_code="IMMUTABLE_POSTED_ENTRY",
        )


def list_chart_of_accounts(session: Session) -> list[ChartOfAccount]:
    """Return all accounts ordered by account_code."""
    return list(session.scalars(select(ChartOfAccount).order_by(ChartOfAccount.account_code)).all())


def get_journal_entry_with_lines(session: Session, entry_id: str) -> dict[str, Any]:
    """Retrieve a journal entry and all its ordered journal lines."""
    entry = session.get(JournalEntry, entry_id)
    if not entry:
        raise NotFoundError(f"Journal entry '{entry_id}' not found")

    lines = list(
        session.scalars(
            select(JournalLine)
            .where(JournalLine.entry_id == entry_id)
            .order_by(JournalLine.line_no)
        ).all()
    )
    return {
        "entry_id": entry.entry_id,
        "entry_date": entry.entry_date,
        "posting_period": entry.posting_period,
        "financial_year": entry.financial_year,
        "description": entry.description,
        "source_type": entry.source_type,
        "source_id": entry.source_id,
        "status": entry.status,
        "total_debit": round_money(entry.total_debit),
        "total_credit": round_money(entry.total_credit),
        "reversal_of_source_id": entry.reversal_of_source_id,
        "created_by": entry.created_by,
        "created_at": entry.created_at,
        "lines": lines,
    }


def create_journal_entry(
    session: Session,
    lines: list[dict[str, Any] | Any],
    entry_date: date | None = None,
    description: str = "Journal Entry",
    source_type: str = "MANUAL",
    source_id: str = "MANUAL-001",
    entry_id: str | None = None,
    created_by: str | None = "U-0099",
    reversal_of_source_id: str | None = None,
) -> dict[str, Any]:
    """Create and post a balanced double-entry journal entry.
    Refuses any entry where debits do not equal credits, where lines < 2, or where accounts are invalid.
    """
    if not lines or len(lines) < 2:
        raise ValidationError(
            "A double-entry journal entry requires at least 2 lines (at least one debit and one credit).",
            error_code="INVALID_JOURNAL_LINES",
        )

    eff_date = entry_date or date.today()
    normalized_lines: list[dict[str, Any]] = []
    total_debit = Decimal("0.00")
    total_credit = Decimal("0.00")

    for idx, raw_line in enumerate(lines, start=1):
        if hasattr(raw_line, "model_dump"):
            line_dict = raw_line.model_dump()
        elif isinstance(raw_line, dict):
            line_dict = dict(raw_line)
        else:
            raise ValidationError(f"Line {idx} has invalid format.")

        acct_code = int(line_dict["account_code"])
        dr = round_money(line_dict.get("debit", Decimal("0.00")))
        cr = round_money(line_dict.get("credit", Decimal("0.00")))

        if dr < Decimal("0.00") or cr < Decimal("0.00"):
            raise ValidationError(
                f"Line {idx} (account {acct_code}): debit and credit amounts must be non-negative.",
                error_code="NEGATIVE_AMOUNT",
            )
        if dr > Decimal("0.00") and cr > Decimal("0.00"):
            raise ValidationError(
                f"Line {idx} (account {acct_code}): a single journal line cannot have both debit ({dr}) and credit ({cr}) > 0.",
                error_code="BOTH_DEBIT_AND_CREDIT",
            )
        if dr == Decimal("0.00") and cr == Decimal("0.00"):
            raise ValidationError(
                f"Line {idx} (account {acct_code}): line must have a non-zero debit or credit amount.",
                error_code="ZERO_LINE_AMOUNT",
            )

        acct = session.get(ChartOfAccount, acct_code)
        if not acct:
            raise NotFoundError(f"Account code '{acct_code}' on line {idx} does not exist in chart_of_accounts.")
        if acct.is_group == "Y":
            raise ValidationError(
                f"Account '{acct_code} ({acct.account_name})' is a group header account and cannot be posted to directly.",
                error_code="GROUP_ACCOUNT_NOT_ALLOWED",
            )

        total_debit = round_money(total_debit + dr)
        total_credit = round_money(total_credit + cr)

        normalized_lines.append(
            {
                "line_no": idx,
                "account_code": acct_code,
                "debit": dr,
                "credit": cr,
                "cost_center_department_id": line_dict.get("cost_center_department_id"),
                "line_description": line_dict.get("line_description"),
            }
        )

    diff = round_money(total_debit - total_credit)
    if diff != Decimal("0.00"):
        raise ValidationError(
            f"Unbalanced journal entry refused: total_debit ({total_debit:.2f}) != total_credit ({total_credit:.2f}), "
            f"difference = {diff:.2f}. In double-entry accounting, every entry must balance to 0.00.",
            error_code="UNBALANCED_ENTRY",
        )

    final_entry_id = entry_id or _next_entry_id(session)
    if session.get(JournalEntry, final_entry_id) is not None:
        raise ConflictError(f"Journal entry '{final_entry_id}' already exists.")

    posting_period = eff_date.strftime("%Y-%m")
    fy = _derive_financial_year(eff_date)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    je = JournalEntry(
        entry_id=final_entry_id,
        entry_date=eff_date,
        posting_period=posting_period,
        financial_year=fy,
        description=description,
        source_type=source_type,
        source_id=source_id,
        status="POSTED",
        total_debit=total_debit,
        total_credit=total_credit,
        reversal_of_source_id=reversal_of_source_id,
        created_by=created_by,
        created_at=now_str,
    )
    session.add(je)

    base_line_num = _next_line_number_base(session)
    jl_objects: list[JournalLine] = []
    for offset, nl in enumerate(normalized_lines):
        line_id = f"JL-{base_line_num + offset:06d}"
        if session.get(JournalLine, line_id) is not None:
            line_id = f"JL-{uuid.uuid4().hex[:6].upper()}"
        jl = JournalLine(
            line_id=line_id,
            entry_id=final_entry_id,
            line_no=nl["line_no"],
            account_code=nl["account_code"],
            debit=nl["debit"],
            credit=nl["credit"],
            cost_center_department_id=nl["cost_center_department_id"],
            line_description=nl["line_description"],
        )
        session.add(jl)
        jl_objects.append(jl)

    session.commit()
    return get_journal_entry_with_lines(session, final_entry_id)


def update_journal_entry(
    session: Session,
    entry_id: str,
    description: str | None = None,
    entry_date: date | None = None,
) -> dict[str, Any]:
    """Refuses any edit to a POSTED journal entry. Corrections must be made via a reversing entry."""
    entry = session.get(JournalEntry, entry_id)
    if not entry:
        raise NotFoundError(f"Journal entry '{entry_id}' not found")

    if entry.status == "POSTED":
        raise ConflictError(
            f"Journal entry '{entry_id}' is POSTED and read-only. "
            "Posted entries cannot be edited or deleted; use reverse_journal_entry() to post a reversing entry.",
            error_code="IMMUTABLE_POSTED_ENTRY",
        )

    if description is not None:
        entry.description = description
    if entry_date is not None:
        entry.entry_date = entry_date
    session.commit()
    return get_journal_entry_with_lines(session, entry_id)


def delete_journal_entry(session: Session, entry_id: str) -> None:
    """Refuses deletion of a POSTED journal entry."""
    entry = session.get(JournalEntry, entry_id)
    if not entry:
        raise NotFoundError(f"Journal entry '{entry_id}' not found")

    if entry.status == "POSTED":
        raise ConflictError(
            f"Journal entry '{entry_id}' is POSTED and read-only. "
            "Posted entries cannot be deleted; use reverse_journal_entry() to post a reversing entry.",
            error_code="IMMUTABLE_POSTED_ENTRY",
        )


def reverse_journal_entry(
    session: Session,
    entry_id: str,
    reversal_date: date | None = None,
    description: str | None = None,
    created_by: str | None = "U-0099",
) -> dict[str, Any]:
    """Create and post an official reversing entry that swaps debits and credits of a posted entry."""
    orig = get_journal_entry_with_lines(session, entry_id)
    eff_date = reversal_date or date.today()
    rev_desc = description or f"Reversal of {orig['description']} ({orig['entry_id']})"

    reversed_lines = [
        {
            "account_code": line.account_code,
            "debit": round_money(line.credit),
            "credit": round_money(line.debit),
            "cost_center_department_id": line.cost_center_department_id,
            "line_description": f"Reversal: {line.line_description or ''}".strip(),
        }
        for line in orig["lines"]
    ]

    return create_journal_entry(
        session=session,
        lines=reversed_lines,
        entry_date=eff_date,
        description=rev_desc,
        source_type="MANUAL",
        source_id=f"REV-{orig['entry_id']}",
        created_by=created_by,
        reversal_of_source_id=orig["source_id"],
    )


def account_balance(
    session: Session,
    account_code: int,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Calculate the cumulative debit, credit, and balance of an account up to and including as_of_date."""
    acct = session.get(ChartOfAccount, account_code)
    if not acct:
        raise NotFoundError(f"Account '{account_code}' not found in chart_of_accounts")

    eff_date = as_of_date or date.today()

    stmt = (
        select(
            func.coalesce(func.sum(JournalLine.debit), 0),
            func.coalesce(func.sum(JournalLine.credit), 0),
        )
        .join(JournalEntry, JournalLine.entry_id == JournalEntry.entry_id)
        .where(
            JournalLine.account_code == account_code,
            JournalEntry.entry_date <= eff_date,
            JournalEntry.status == "POSTED",
        )
    )
    row = session.execute(stmt).one()
    tot_debit = round_money(row[0])
    tot_credit = round_money(row[1])
    dr_minus_cr = round_money(tot_debit - tot_credit)

    if acct.normal_balance.upper() == "DEBIT":
        normal_bal = dr_minus_cr
    else:
        normal_bal = round_money(tot_credit - tot_debit)

    return {
        "account_code": acct.account_code,
        "account_name": acct.account_name,
        "account_type": acct.account_type,
        "normal_balance": acct.normal_balance,
        "as_of_date": eff_date,
        "total_debit": tot_debit,
        "total_credit": tot_credit,
        "debit_minus_credit": dr_minus_cr,
        "balance": normal_bal,
    }


def build_payroll_journal_lines(items: list[PayrollItem]) -> list[dict[str, Any]]:
    """Build the exact double-entry journal lines for a payroll run from its PayrollItem rows:
    - Debits (by department D00..D10):
      5001: Salaries & Wages (earned_fixed_pay)
      5002: Overtime Expense (overtime_pay)
      5003: Incentives & Bonus (variable_pay)
      5004: Employer PF Contribution (pf_employer)
      5005: Employer ESI Contribution (esi_employer)
    - Credits (company-wide payables & recoveries):
      2100: Salaries Payable (net_pay)
      2110: PF Payable (pf_employee + pf_employer)
      2120: ESI Payable (esi_employee + esi_employer)
      2130: TDS on Salary Payable (tds)
      2140: Professional Tax Payable (professional_tax)
      1300: Employee Advances & Loans (other_deductions)
    """
    if not items:
        raise ValidationError("Cannot build payroll journal lines for an empty payroll run.")

    depts = sorted({i.department_id for i in items})
    lines: list[dict[str, Any]] = []

    # 1. Departmental Employer-Cost Debit Lines (5001 to 5005)
    for dept_id in depts:
        dept_items = [i for i in items if i.department_id == dept_id]
        sal_wages = round_money(sum((_to_dec(i.earned_fixed_pay) for i in dept_items), Decimal("0.00")))
        ot_exp = round_money(sum((_to_dec(i.overtime_pay) for i in dept_items), Decimal("0.00")))
        bonus_exp = round_money(sum((_to_dec(i.variable_pay) for i in dept_items), Decimal("0.00")))
        pf_er_exp = round_money(sum((_to_dec(i.pf_employer) for i in dept_items), Decimal("0.00")))
        esi_er_exp = round_money(sum((_to_dec(i.esi_employer) for i in dept_items), Decimal("0.00")))

        if sal_wages > Decimal("0.00"):
            lines.append(
                {
                    "account_code": 5001,
                    "debit": sal_wages,
                    "credit": Decimal("0.00"),
                    "cost_center_department_id": dept_id,
                    "line_description": f"Salaries & Wages - {dept_id}",
                }
            )
        if ot_exp > Decimal("0.00"):
            lines.append(
                {
                    "account_code": 5002,
                    "debit": ot_exp,
                    "credit": Decimal("0.00"),
                    "cost_center_department_id": dept_id,
                    "line_description": f"Overtime Expense - {dept_id}",
                }
            )
        if bonus_exp > Decimal("0.00"):
            lines.append(
                {
                    "account_code": 5003,
                    "debit": bonus_exp,
                    "credit": Decimal("0.00"),
                    "cost_center_department_id": dept_id,
                    "line_description": f"Incentives & Bonus - {dept_id}",
                }
            )
        if pf_er_exp > Decimal("0.00"):
            lines.append(
                {
                    "account_code": 5004,
                    "debit": pf_er_exp,
                    "credit": Decimal("0.00"),
                    "cost_center_department_id": dept_id,
                    "line_description": f"Employer PF Contribution - {dept_id}",
                }
            )
        if esi_er_exp > Decimal("0.00"):
            lines.append(
                {
                    "account_code": 5005,
                    "debit": esi_er_exp,
                    "credit": Decimal("0.00"),
                    "cost_center_department_id": dept_id,
                    "line_description": f"Employer ESI Contribution - {dept_id}",
                }
            )

    # 2. Liability & Recovery Credit Lines (2100, 2110, 2120, 2130, 2140, 1300)
    net_payable = round_money(sum((_to_dec(i.net_pay) for i in items), Decimal("0.00")))
    pf_payable = round_money(
        sum((_to_dec(i.pf_employee) + _to_dec(i.pf_employer) for i in items), Decimal("0.00"))
    )
    esi_payable = round_money(
        sum((_to_dec(i.esi_employee) + _to_dec(i.esi_employer) for i in items), Decimal("0.00"))
    )
    tds_payable = round_money(sum((_to_dec(i.tds) for i in items), Decimal("0.00")))
    pt_payable = round_money(sum((_to_dec(i.professional_tax) for i in items), Decimal("0.00")))
    adv_recovery = round_money(sum((_to_dec(i.other_deductions) for i in items), Decimal("0.00")))

    if net_payable > Decimal("0.00"):
        lines.append(
            {
                "account_code": 2100,
                "debit": Decimal("0.00"),
                "credit": net_payable,
                "cost_center_department_id": None,
                "line_description": "Net salaries payable",
            }
        )
    if pf_payable > Decimal("0.00"):
        lines.append(
            {
                "account_code": 2110,
                "debit": Decimal("0.00"),
                "credit": pf_payable,
                "cost_center_department_id": None,
                "line_description": "PF payable (employee + employer)",
            }
        )
    if esi_payable > Decimal("0.00"):
        lines.append(
            {
                "account_code": 2120,
                "debit": Decimal("0.00"),
                "credit": esi_payable,
                "cost_center_department_id": None,
                "line_description": "ESI payable (employee + employer)",
            }
        )
    if tds_payable > Decimal("0.00"):
        lines.append(
            {
                "account_code": 2130,
                "debit": Decimal("0.00"),
                "credit": tds_payable,
                "cost_center_department_id": None,
                "line_description": "TDS on salary payable",
            }
        )
    if pt_payable > Decimal("0.00"):
        lines.append(
            {
                "account_code": 2140,
                "debit": Decimal("0.00"),
                "credit": pt_payable,
                "cost_center_department_id": None,
                "line_description": "Professional tax payable",
            }
        )
    if adv_recovery > Decimal("0.00"):
        lines.append(
            {
                "account_code": 1300,
                "debit": Decimal("0.00"),
                "credit": adv_recovery,
                "cost_center_department_id": None,
                "line_description": "Recovery of employee advances",
            }
        )

    return lines


def post_payroll_run_to_ledger(
    session: Session,
    run_id: str,
    entry_id: str | None = None,
    created_by: str | None = "U-0237",
) -> dict[str, Any]:
    """Post a month's payroll run totals into the double-entry ledger (accounts 5001..5005 and 2100..2140, 1300).
    If already posted and present in journal_entries, returns the existing entry (idempotent).
    """
    existing = session.scalar(
        select(JournalEntry).where(
            JournalEntry.source_type == "PAYROLL_RUN",
            JournalEntry.source_id == run_id,
            JournalEntry.status == "POSTED",
        )
    )
    if existing:
        return get_journal_entry_with_lines(session, existing.entry_id)

    pr_run = session.get(PayrollRun, run_id)
    items = list(
        session.scalars(
            select(PayrollItem).where(PayrollItem.run_id == run_id)
        ).all()
    )
    if not items:
        raise NotFoundError(f"No payroll items found for run '{run_id}'")

    entry_date = pr_run.period_end if pr_run else items[0].period_end
    eff_created_by = (pr_run.run_by if pr_run and pr_run.run_by else created_by) or "U-0237"
    lines = build_payroll_journal_lines(items)

    return create_journal_entry(
        session=session,
        lines=lines,
        entry_date=entry_date,
        description=f"Payroll posting {run_id}",
        source_type="PAYROLL_RUN",
        source_id=run_id,
        entry_id=entry_id,
        created_by=eff_created_by,
    )
