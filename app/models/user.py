"""User model for authentication and role-based access control (LF-13)."""

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("employee_id", name="uq_users_employee_id"),
        Index("ix_users_role", "role"),
    )

    user_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(16), ForeignKey("employees.employee_id"))
    username: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(24), default="EMPLOYEE", server_default="EMPLOYEE")
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[str] = mapped_column(String(4), default="Y", server_default="Y")
    mfa_enabled: Mapped[str] = mapped_column(String(4), default="N", server_default="N")
    last_login_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    password_policy_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.user_id} {self.username} role={self.role} active={self.is_active}>"
