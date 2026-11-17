"""Pydantic schemas for asynchronous background jobs (Task 16)."""

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    """Request payload to kick off the 18-month bulk payroll run."""

    start_month: str = Field(default="2025-04", pattern=r"^\d{4}-\d{2}$", description="First month to process (YYYY-MM)")
    end_month: str = Field(default="2026-09", pattern=r"^\d{4}-\d{2}$", description="Last month to process (YYYY-MM)")
    auto_approve: bool = Field(default=True, description="Whether to automatically approve and post journal entries to the ledger")
    allow_rerun: bool = Field(default=True, description="Allow re-calculating months if already processed")
    run_by: str = Field(default="U-0099", description="User ID triggering the bulk run")


class MonthRunResult(BaseModel):
    """Result summary for an individual processed month."""

    month: str
    run_id: str
    status: str
    headcount: int
    total_gross: float
    total_deductions: float
    total_net: float
    total_employer_cost: float
    journal_entry_id: str | None = None
    is_balanced: bool = True


class JobProgressResponse(BaseModel):
    """Real-time job progress response."""

    job_id: str
    job_type: str
    status: str
    progress_percent: float
    total_items: int
    processed_items: int
    current_stage: str | None = None
    created_by: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    results: list[dict[str, Any]] | None = None
    error_message: str | None = None


class JobSummaryResponse(BaseModel):
    """Summary representation for job listing."""

    job_id: str
    job_type: str
    status: str
    progress_percent: float
    total_items: int
    processed_items: int
    created_at: datetime
    completed_at: datetime | None = None
