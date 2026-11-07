"""Salary service: effective-dated salary structures, revisions, and boundary checks (LF-05)."""

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import uuid
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models.salary import SalaryComponent, SalaryRevision, SalaryStructure


def get_structure(
    session: Session,
    employee_id: str,
    as_of_date: date,
) -> list[SalaryStructure]:
    """Retrieve salary structure components for an employee active on a specific date.

    Handles boundary logic: effective_from <= as_of_date AND (effective_to IS NULL OR effective_to >= as_of_date).
    """
    stmt = (
        select(SalaryStructure)
        .where(
            SalaryStructure.employee_id == employee_id,
            SalaryStructure.effective_from <= as_of_date,
            or_(
                SalaryStructure.effective_to.is_(None),
                SalaryStructure.effective_to >= as_of_date,
            ),
        )
        .order_by(SalaryStructure.component_id)
    )
    return list(session.scalars(stmt).all())


def revise_salary(
    session: Session,
    employee_id: str,
    new_components: list[dict],
    effective_from: date,
    revision_reason: str,
    role_id_after: str | None = None,
    approved_by: str | None = None,
) -> tuple[SalaryRevision, list[SalaryStructure], bool]:
    """Revise an employee's salary structure:
    1. Finds currently active structure rows and sets their effective_to to effective_from - 1 day.
    2. Computes previous annual fixed and new annual fixed using Decimal.
    3. Calculates percentage change (rounded half-up).
    4. Flags if raise is > 20%.
    5. Inserts a new SalaryRevision record and new SalaryStructure rows.
    """
    # 1. Fetch current open-ended structure rows
    prev_stmt = (
        select(SalaryStructure)
        .where(
            SalaryStructure.employee_id == employee_id,
            or_(
                SalaryStructure.effective_to.is_(None),
                SalaryStructure.effective_to >= effective_from,
            ),
        )
    )
    current_structures = list(session.scalars(prev_stmt).all())

    # Close previous structures
    day_before = effective_from - timedelta(days=1)
    prev_monthly_fixed = Decimal("0.00")
    for s in current_structures:
        if s.effective_from <= day_before:
            s.effective_to = day_before
        else:
            # Overlap protection: if already after, set to effective_from
            s.effective_to = effective_from
        prev_monthly_fixed += Decimal(str(s.monthly_amount))

    prev_annual_fixed = (prev_monthly_fixed * Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if prev_monthly_fixed > 0 else None

    # Calculate new fixed amounts
    new_monthly_fixed = Decimal("0.00")
    for comp in new_components:
        amount = Decimal(str(comp["monthly_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        new_monthly_fixed += amount

    new_annual_fixed = (new_monthly_fixed * Decimal("12")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Percentage change
    pct_change: Decimal | None = None
    if prev_annual_fixed and prev_annual_fixed > Decimal("0.00"):
        diff = new_annual_fixed - prev_annual_fixed
        pct_change = ((diff / prev_annual_fixed) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    is_high_raise = pct_change is not None and pct_change > Decimal("20.00")

    # Generate unique Revision ID
    revision_id = f"SR-{uuid.uuid4().hex[:8].upper()}"

    revision = SalaryRevision(
        revision_id=revision_id,
        employee_id=employee_id,
        effective_from=effective_from,
        revision_reason=revision_reason,
        previous_annual_fixed=prev_annual_fixed,
        new_annual_fixed=new_annual_fixed,
        pct_change=pct_change,
        role_id_after=role_id_after,
        approved_by=approved_by,
    )
    session.add(revision)

    # Insert new structure rows
    created_structures = []
    for comp in new_components:
        structure_id = f"SS-{uuid.uuid4().hex[:8].upper()}"
        amount = Decimal(str(comp["monthly_amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        structure = SalaryStructure(
            structure_id=structure_id,
            employee_id=employee_id,
            component_id=comp["component_id"],
            component_name=comp.get("component_name", comp["component_id"]),
            component_type=comp.get("component_type", "EARNING"),
            monthly_amount=amount,
            effective_from=effective_from,
            effective_to=None,
            revision_id=revision_id,
        )
        session.add(structure)
        created_structures.append(structure)

    session.commit()
    return revision, created_structures, is_high_raise
