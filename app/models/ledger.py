"""Double-entry accounting ledger models: ChartOfAccount, JournalEntry, and JournalLine (LF-09)."""

from datetime import date
from decimal import Decimal
from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChartOfAccount(Base):
    __tablename__ = "chart_of_accounts"

    account_code: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_name: Mapped[str] = mapped_column(String(128))
    account_type: Mapped[str] = mapped_column(String(32))
    normal_balance: Mapped[str] = mapped_column(String(16))
    parent_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_group: Mapped[str] = mapped_column(String(4), default="N", server_default="N")
    statement: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[str] = mapped_column(String(4), default="Y", server_default="Y")

    def __repr__(self) -> str:
        return f"<ChartOfAccount {self.account_code} {self.account_name} ({self.account_type})>"


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    __table_args__ = (
        Index("ix_journal_entries_entry_date", "entry_date"),
        Index("ix_journal_entries_source", "source_type", "source_id"),
    )

    entry_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date)
    posting_period: Mapped[str] = mapped_column(String(16))
    financial_year: Mapped[str] = mapped_column(String(16))
    description: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20), default="POSTED", server_default="POSTED")
    total_debit: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    total_credit: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    reversal_of_source_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[str | None] = mapped_column(String(32), nullable=True)

    def __repr__(self) -> str:
        return f"<JournalEntry {self.entry_id} date={self.entry_date} debit={self.total_debit} credit={self.total_credit}>"


class JournalLine(Base):
    __tablename__ = "journal_lines"
    __table_args__ = (
        Index("ix_journal_lines_entry_id", "entry_id"),
        Index("ix_journal_lines_account_code", "account_code"),
    )

    line_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    entry_id: Mapped[str] = mapped_column(String(20), ForeignKey("journal_entries.entry_id"))
    line_no: Mapped[int] = mapped_column(Integer)
    account_code: Mapped[int] = mapped_column(Integer, ForeignKey("chart_of_accounts.account_code"))
    debit: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    credit: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0.00"), server_default="0")
    cost_center_department_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    line_description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<JournalLine {self.line_id} entry={self.entry_id} acct={self.account_code} dr={self.debit} cr={self.credit}>"
