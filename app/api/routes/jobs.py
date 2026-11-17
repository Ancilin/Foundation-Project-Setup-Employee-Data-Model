"""Background Jobs HTTP routes: bulk 18-month payroll run and live progress tracking (Task 16)."""

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.job import (
    JobCreateRequest,
    JobProgressResponse,
    JobSummaryResponse,
)
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


@router.post(
    "/payroll/bulk-run",
    response_model=JobProgressResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue 18-Month Bulk Payroll Background Job",
)
def trigger_bulk_payroll_job(
    payload: JobCreateRequest | None = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Enqueue the 18-month payroll processing and ledger auto-posting job in the background queue.
    Returns 202 Accepted with a job_id for progress polling.
    """
    req = payload or JobCreateRequest()
    job = job_service.create_and_enqueue_bulk_payroll_job(
        session=db,
        payload=req,
        created_by=current_user.username,
        background_tasks=background_tasks,
    )
    return job_service.get_job_progress(session=db, job_id=job.job_id)


@router.get(
    "/payroll/{job_id}",
    response_model=JobProgressResponse,
    summary="Poll Background Job Progress & Results",
)
def get_bulk_payroll_job_progress(
    job_id: str,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """Retrieve real-time progress, status (PENDING, RUNNING, COMPLETED, FAILED),
    percentage (0-100%), and monthly summaries for the requested background job.
    """
    return job_service.get_job_progress(session=db, job_id=job_id)


@router.get(
    "",
    response_model=list[JobSummaryResponse],
    summary="List All Background Jobs",
)
def list_background_jobs(
    limit: int = 50,
    skip: int = 0,
    _current_user: User = Depends(require_role("ADMIN", "HR")),
    db: Session = Depends(get_db),
):
    """List recent background jobs and their completion status."""
    jobs = job_service.list_jobs(session=db, limit=limit, skip=skip)
    return [
        JobSummaryResponse(
            job_id=j.job_id,
            job_type=j.job_type,
            status=j.status,
            progress_percent=j.progress_percent,
            total_items=j.total_items,
            processed_items=j.processed_items,
            created_at=j.created_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]
