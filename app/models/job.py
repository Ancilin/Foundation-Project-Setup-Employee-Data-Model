"""Background Job SQLAlchemy model for asynchronous tasks (e.g. 18-month bulk payroll run)."""

from datetime import datetime, timezone
import json
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BackgroundJob(Base):
    """Tracks background jobs, their queue status, and progress metrics."""

    __tablename__ = "background_jobs"
    __table_args__ = (
        Index("ix_background_jobs_status", "status"),
        Index("ix_background_jobs_created_at", "created_at"),
    )

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, default="PAYROLL_18_MONTH_BULK_RUN")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=18)
    processed_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    def set_result(self, data: Any) -> None:
        self.result_json = json.dumps(data)

    def get_result(self) -> Any:
        if self.result_json:
            try:
                return json.loads(self.result_json)
            except Exception:
                return self.result_json
        return None

    def set_payload(self, data: Any) -> None:
        self.payload_json = json.dumps(data)

    def get_payload(self) -> Any:
        if self.payload_json:
            try:
                return json.loads(self.payload_json)
            except Exception:
                return self.payload_json
        return None
