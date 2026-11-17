"""Celery worker entry point and task definition (Task 16)."""

from typing import Any
from app.core.celery_app import celery_app
from app.services import job_service


@celery_app.task(name="app.worker.run_bulk_payroll_task", bind=True)
def run_bulk_payroll_task(self, job_id: str) -> dict[str, Any]:
    """Celery background queue task: executes the 18-month bulk payroll calculation."""
    return job_service.execute_18_month_payroll_job(job_id=job_id)


if __name__ == "__main__":
    celery_app.worker_main(argv=["worker", "--loglevel=info"])
