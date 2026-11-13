"""import tables

Import-stage tables, the "current state" views and the single settings row.

Revision ID: 0001
Revises:
Create Date: 2026-11-13 01:03:06.734989

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "counterparties",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("code", sa.Text(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_key", sa.Text(), nullable=False),
        sa.Column(
            "attrs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('supplier', 'customer', 'bank')", name=op.f("ck_counterparties_kind_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_counterparties")),
    )
    op.create_index(
        "uq_counterparties_kind_code",
        "counterparties",
        ["kind", "code"],
        unique=True,
        postgresql_where=sa.text("code IS NOT NULL"),
    )
    op.create_index(
        "uq_counterparties_kind_name_key_no_code",
        "counterparties",
        ["kind", "name_key"],
        unique=True,
        postgresql_where=sa.text("code IS NULL"),
    )
    op.create_table(
        "file_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="proposed", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_type IN ('loans', 'payables', 'receivables')",
            name=op.f("ck_file_mappings_file_type_valid"),
        ),
        sa.CheckConstraint(
            "status IN ('proposed', 'confirmed')", name=op.f("ck_file_mappings_status_valid")
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_file_mappings_version_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_file_mappings")),
        sa.UniqueConstraint(
            "file_type", "version", name=op.f("uq_file_mappings_file_type_version")
        ),
    )
    op.create_table(
        "settings",
        sa.Column("id", sa.SmallInteger(), nullable=False),
        sa.Column("min_balance_vnd", sa.BigInteger(), nullable=True),
        sa.Column(
            "timezone", sa.String(length=64), server_default="Asia/Ho_Chi_Minh", nullable=False
        ),
        sa.Column(
            "default_recipient_language",
            sa.String(length=16),
            server_default="bilingual",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "default_recipient_language IN ('en', 'vi', 'bilingual')",
            name=op.f("ck_settings_default_recipient_language_valid"),
        ),
        sa.CheckConstraint("id = 1", name=op.f("ck_settings_single_row")),
        sa.CheckConstraint(
            "min_balance_vnd >= 0", name=op.f("ck_settings_min_balance_non_negative")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_settings")),
    )
    op.create_table(
        "credit_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("limit_vnd", sa.BigInteger(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.CheckConstraint("limit_vnd >= 0", name=op.f("ck_credit_lines_limit_non_negative")),
        sa.ForeignKeyConstraint(
            ["bank_id"], ["counterparties.id"], name=op.f("fk_credit_lines_bank_id_counterparties")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_credit_lines")),
        sa.UniqueConstraint(
            "bank_id", "effective_from", name=op.f("uq_credit_lines_bank_id_effective_from")
        ),
    )
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bank_id", sa.Integer(), nullable=False),
        sa.Column("loan_code", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("disbursed_on", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["bank_id"], ["counterparties.id"], name=op.f("fk_loans_bank_id_counterparties")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loans")),
        sa.UniqueConstraint("bank_id", "loan_code", name=op.f("uq_loans_bank_id_loan_code")),
    )
    op.create_table(
        "source_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_type", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("import_report", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mapping_id", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "file_type IN ('loans', 'payables', 'receivables')",
            name=op.f("ck_source_files_file_type_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["mapping_id"],
            ["file_mappings.id"],
            name=op.f("fk_source_files_mapping_id_file_mappings"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_source_files")),
        sa.UniqueConstraint("sha256", "mapping_id", name=op.f("uq_source_files_sha256_mapping_id")),
    )
    op.create_table(
        "ledger_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("counterparty_id", sa.Integer(), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("amount_vnd", sa.BigInteger(), nullable=False),
        sa.Column("site_code", sa.Text(), nullable=True),
        sa.Column("expected_collection_day", sa.SmallInteger(), nullable=True),
        sa.Column("source_file_id", sa.Integer(), nullable=False),
        sa.Column("source_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "kind = 'receivable' OR (site_code IS NULL AND expected_collection_day IS NULL)",
            name=op.f("ck_ledger_items_site_fields_receivable_only"),
        ),
        sa.CheckConstraint(
            "kind IN ('payable', 'receivable')", name=op.f("ck_ledger_items_kind_valid")
        ),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM period) = 1", name=op.f("ck_ledger_items_period_first_of_month")
        ),
        sa.CheckConstraint(
            "expected_collection_day BETWEEN 1 AND 31",
            name=op.f("ck_ledger_items_expected_collection_day_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["counterparty_id"],
            ["counterparties.id"],
            name=op.f("fk_ledger_items_counterparty_id_counterparties"),
        ),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["source_files.id"],
            name=op.f("fk_ledger_items_source_file_id_source_files"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ledger_items")),
        sa.UniqueConstraint(
            "source_file_id",
            "kind",
            "counterparty_id",
            "site_code",
            "period",
            name="uq_ledger_items_snapshot_line",
            postgresql_nulls_not_distinct=True,
        ),
    )
    op.create_index(
        "ix_ledger_items_counterparty_id_period",
        "ledger_items",
        ["counterparty_id", "period"],
        unique=False,
    )
    op.create_index(
        "ix_ledger_items_source_file_id", "ledger_items", ["source_file_id"], unique=False
    )
    op.create_table(
        "loan_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("loan_id", sa.Integer(), nullable=False),
        sa.Column("source_file_id", sa.Integer(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("principal_vnd", sa.BigInteger(), nullable=True),
        sa.Column("repaid_vnd", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("outstanding_vnd", sa.BigInteger(), nullable=False),
        sa.Column("interest_rate_pct", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("source_ref", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.CheckConstraint(
            "outstanding_vnd >= 0", name=op.f("ck_loan_snapshots_outstanding_non_negative")
        ),
        sa.CheckConstraint(
            "principal_vnd >= 0", name=op.f("ck_loan_snapshots_principal_non_negative")
        ),
        sa.CheckConstraint("repaid_vnd >= 0", name=op.f("ck_loan_snapshots_repaid_non_negative")),
        sa.ForeignKeyConstraint(
            ["loan_id"], ["loans.id"], name=op.f("fk_loan_snapshots_loan_id_loans")
        ),
        sa.ForeignKeyConstraint(
            ["source_file_id"],
            ["source_files.id"],
            name=op.f("fk_loan_snapshots_source_file_id_source_files"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_loan_snapshots")),
        sa.UniqueConstraint(
            "loan_id",
            "source_file_id",
            "due_on",
            name=op.f("uq_loan_snapshots_loan_id_source_file_id_due_on"),
        ),
    )
    op.create_index(
        "ix_loan_snapshots_source_file_id", "loan_snapshots", ["source_file_id"], unique=False
    )

    # The single settings row; min_balance_vnd stays NULL until it is configured.
    op.execute("INSERT INTO settings (id) VALUES (1)")

    # "Current state" = rows from the latest import (highest id) per file_type.
    # A re-upload of the same file + mapping creates no new row, so an old file never
    # becomes current again; a newer mapping version does create one.
    op.execute(
        """
        CREATE VIEW current_source_files AS
        SELECT DISTINCT ON (file_type) *
        FROM source_files
        ORDER BY file_type, id DESC
        """
    )
    op.execute(
        """
        CREATE VIEW current_loan_snapshots AS
        SELECT ls.*
        FROM loan_snapshots ls
        JOIN current_source_files cf ON cf.id = ls.source_file_id
        """
    )
    op.execute(
        """
        CREATE VIEW current_ledger_items AS
        SELECT li.*
        FROM ledger_items li
        JOIN current_source_files cf ON cf.id = li.source_file_id
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP VIEW current_ledger_items")
    op.execute("DROP VIEW current_loan_snapshots")
    op.execute("DROP VIEW current_source_files")
    op.drop_index("ix_loan_snapshots_source_file_id", table_name="loan_snapshots")
    op.drop_table("loan_snapshots")
    op.drop_index("ix_ledger_items_source_file_id", table_name="ledger_items")
    op.drop_index("ix_ledger_items_counterparty_id_period", table_name="ledger_items")
    op.drop_table("ledger_items")
    op.drop_table("source_files")
    op.drop_table("loans")
    op.drop_table("credit_lines")
    op.drop_table("settings")
    op.drop_table("file_mappings")
    op.drop_index(
        "uq_counterparties_kind_name_key_no_code",
        table_name="counterparties",
        postgresql_where=sa.text("code IS NULL"),
    )
    op.drop_index(
        "uq_counterparties_kind_code",
        table_name="counterparties",
        postgresql_where=sa.text("code IS NOT NULL"),
    )
    op.drop_table("counterparties")
