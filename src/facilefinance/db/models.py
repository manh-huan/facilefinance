"""Import-stage tables (bootstrap step 4).

Conventions (CLAUDE.md section 7): money is ``bigint`` VND, dates are ``date``, instants are
``timestamptz``. Enumerations are stored as text with CHECK constraints (stable English
snake_case codes) rather than PostgreSQL enum types, so adding a value is a simple migration.

Other tables (rules, forecast_runs, cash_events, ...) are added with their features.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from facilefinance.db.base import Base

FILE_TYPES = ("loans", "payables", "receivables")
MAPPING_STATUSES = ("proposed", "confirmed")
COUNTERPARTY_KINDS = ("supplier", "customer", "bank")
LEDGER_KINDS = ("payable", "receivable")
RECIPIENT_LANGUAGES = ("en", "vi", "bilingual")


def _in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{v}'" for v in values)
    return f"{column} IN ({quoted})"


class Settings(Base):
    """Single-row application settings (the row id is always 1)."""

    __tablename__ = "settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="single_row"),
        CheckConstraint("min_balance_vnd >= 0", name="min_balance_non_negative"),
        CheckConstraint(
            _in("default_recipient_language", RECIPIENT_LANGUAGES),
            name="default_recipient_language_valid",
        ),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    # NULL until the chief accountant configures it; never defaulted to an invented threshold.
    min_balance_vnd: Mapped[int | None] = mapped_column(BigInteger)
    timezone: Mapped[str] = mapped_column(
        String(64), server_default="Asia/Ho_Chi_Minh", nullable=False
    )
    # Default email language for new recipients (en | vi | bilingual). Not the UI locale.
    default_recipient_language: Mapped[str] = mapped_column(
        String(16), server_default="bilingual", nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class FileMapping(Base):
    """Versioned description of how to read one file type. Never overwritten: new version."""

    __tablename__ = "file_mappings"
    __table_args__ = (
        UniqueConstraint("file_type", "version"),
        CheckConstraint(_in("file_type", FILE_TYPES), name="file_type_valid"),
        CheckConstraint(_in("status", MAPPING_STATUSES), name="status_valid"),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    spec: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), server_default="proposed", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SourceFile(Base):
    """An uploaded file. Only metadata is kept; originals are not retained long-term."""

    __tablename__ = "source_files"
    __table_args__ = (
        # Same file + same mapping version = same import (idempotent re-upload).
        # Same file + newer mapping version = a new snapshot.
        UniqueConstraint("sha256", "mapping_id"),
        CheckConstraint(_in("file_type", FILE_TYPES), name="file_type_valid"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    # The period the file's data refers to (not the upload time).
    as_of: Mapped[dt.date] = mapped_column(Date, nullable=False)
    # Totals read vs file totals, match flag, warnings (e.g. "#REF!" in a total cell).
    import_report: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    mapping_id: Mapped[int] = mapped_column(ForeignKey("file_mappings.id"), nullable=False)
    uploaded_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    mapping: Mapped[FileMapping] = relationship()


class Counterparty(Base):
    """Supplier, customer or bank."""

    __tablename__ = "counterparties"
    __table_args__ = (
        CheckConstraint(_in("kind", COUNTERPARTY_KINDS), name="kind_valid"),
        # Suppliers have codes (NCC_0001); customers and banks may not.
        Index(
            "uq_counterparties_kind_code",
            "kind",
            "code",
            unique=True,
            postgresql_where=text("code IS NOT NULL"),
        ),
        Index(
            "uq_counterparties_kind_name_key_no_code",
            "kind",
            "name_key",
            unique=True,
            postgresql_where=text("code IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    code: Mapped[str | None] = mapped_column(Text)
    # As displayed (verbatim from the file).
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Matching key: see facilefinance.db.normalize.name_key. Writers must set it. Suppliers
    # are identified by code first; the key only matters for counterparties without a code.
    name_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Free-form: tax ID (MST), supplier category (MÃ HÀNG HÓA), ...
    attrs: Mapped[dict[str, Any]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), nullable=False
    )


class Loan(Base):
    """Stable identity of a bank loan. Amounts and dates live in ``LoanSnapshot``."""

    __tablename__ = "loans"
    __table_args__ = (UniqueConstraint("bank_id", "loan_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("counterparties.id"), nullable=False)
    # Always text: some codes look numeric (3000#######) and others contain spaces.
    loan_code: Mapped[str] = mapped_column(Text, nullable=False)
    # `Nội dung khoản vay` verbatim (e.g. "NCC HCM", "LUONG 05.2026"); used for categorising.
    purpose: Mapped[str | None] = mapped_column(Text)
    disbursed_on: Mapped[dt.date | None] = mapped_column(Date)

    bank: Mapped[Counterparty] = relationship()


class LoanSnapshot(Base):
    """One scheduled principal repayment of a loan, as read from one imported file.

    Never updated in place: a later file produces new rows.
    """

    __tablename__ = "loan_snapshots"
    __table_args__ = (
        # A row is one scheduled principal repayment of a loan as seen in one file, not
        # "the loan": one code can have several maturity dates (instalments). Conflict and
        # duplicate handling, skipping fully repaid loans (outstanding = 0) and checking
        # principal = repaid + outstanding are importer decisions (reported in
        # source_files.import_report); the database does not enforce them.
        UniqueConstraint("loan_id", "source_file_id", "due_on"),
        CheckConstraint("principal_vnd >= 0", name="principal_non_negative"),
        CheckConstraint("repaid_vnd >= 0", name="repaid_non_negative"),
        CheckConstraint("outstanding_vnd >= 0", name="outstanding_non_negative"),
        Index("ix_loan_snapshots_source_file_id", "source_file_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    loan_id: Mapped[int] = mapped_column(ForeignKey("loans.id"), nullable=False)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id"), nullable=False)
    due_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    # `Số tiền vay`: original principal.
    principal_vnd: Mapped[int | None] = mapped_column(BigInteger)
    repaid_vnd: Mapped[int] = mapped_column(BigInteger, server_default="0", nullable=False)
    outstanding_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Not in the maturity report; unit (per month / per year) to be confirmed.
    interest_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    # {"file": ..., "sheet": ..., "row": ...}
    source_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    loan: Mapped[Loan] = relationship()


class CreditLine(Base):
    """Credit limit per bank, valid from a date (a new limit is a new row)."""

    __tablename__ = "credit_lines"
    __table_args__ = (
        UniqueConstraint("bank_id", "effective_from"),
        CheckConstraint("limit_vnd >= 0", name="limit_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_id: Mapped[int] = mapped_column(ForeignKey("counterparties.id"), nullable=False)
    limit_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    effective_from: Mapped[dt.date] = mapped_column(Date, nullable=False)

    bank: Mapped[Counterparty] = relationship()


class LedgerItem(Base):
    """One amount owed to a supplier or by a customer for one month, read from a file.

    A file import produces a snapshot: every row carries its ``source_file_id``.
    Importers must not create rows for zero amounts (empty cells and 0 both mean zero).
    """

    __tablename__ = "ledger_items"
    __table_args__ = (
        CheckConstraint(_in("kind", LEDGER_KINDS), name="kind_valid"),
        CheckConstraint(
            "expected_collection_day BETWEEN 1 AND 31", name="expected_collection_day_valid"
        ),
        CheckConstraint("EXTRACT(DAY FROM period) = 1", name="period_first_of_month"),
        CheckConstraint(
            "kind = 'receivable' OR (site_code IS NULL AND expected_collection_day IS NULL)",
            name="site_fields_receivable_only",
        ),
        # One row per (file, kind, counterparty, site, month). NULLS NOT DISTINCT
        # (PostgreSQL 15+) makes rows with a NULL site_code (all payables) collide too.
        UniqueConstraint(
            "source_file_id",
            "kind",
            "counterparty_id",
            "site_code",
            "period",
            name="uq_ledger_items_snapshot_line",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_ledger_items_source_file_id", "source_file_id"),
        Index("ix_ledger_items_counterparty_id_period", "counterparty_id", "period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    counterparty_id: Mapped[int] = mapped_column(ForeignKey("counterparties.id"), nullable=False)
    # First day of the month in which the amount arose (month + year headers combined).
    period: Mapped[dt.date] = mapped_column(Date, nullable=False)
    amount_vnd: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Receivables only: `Note` column. (customer, site) identifies a receivable line.
    site_code: Mapped[str | None] = mapped_column(Text)
    # Receivables only: `Ngày thu dự kiến`, day of month; often empty.
    expected_collection_day: Mapped[int | None] = mapped_column(SmallInteger)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id"), nullable=False)
    # {"file": ..., "sheet": ..., "row": ...}
    source_ref: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    counterparty: Mapped[Counterparty] = relationship()
