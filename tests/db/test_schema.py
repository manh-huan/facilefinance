"""Schema tests against a real PostgreSQL database (migrations applied by Alembic).

Set FACILEFINANCE_TEST_DATABASE_URL to run them, e.g.
``postgresql+psycopg://facilefinance:<password>@127.0.0.1:55432/facilefinance_test``.
The database name must end with ``_test``: the public schema is dropped and recreated.
"""

import datetime as dt
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

TEST_URL = os.environ.get("FACILEFINANCE_TEST_DATABASE_URL")
ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    TEST_URL is None, reason="FACILEFINANCE_TEST_DATABASE_URL is not set"
)


def _alembic(action: str, revision: str) -> None:
    assert TEST_URL is not None
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = TEST_URL
    try:
        cfg = Config(str(ROOT / "alembic.ini"))
        getattr(command, action)(cfg, revision)
    finally:
        if previous is None:
            del os.environ["DATABASE_URL"]
        else:
            os.environ["DATABASE_URL"] = previous


def _reset_schema(engine: Engine) -> None:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    assert TEST_URL is not None
    database = make_url(TEST_URL).database or ""
    assert database.endswith("_test"), "refusing to reset a database not named *_test"
    eng = create_engine(TEST_URL)
    _reset_schema(eng)
    _alembic("upgrade", "head")
    yield eng
    eng.dispose()


@pytest.fixture
def conn(engine: Engine) -> Iterator[Connection]:
    """A connection whose work is rolled back after each test."""
    with engine.connect() as connection:
        outer = connection.begin()
        yield connection
        outer.rollback()


def _insert(conn: Connection, sql: str, **params: object) -> int:
    return int(conn.execute(text(sql + " RETURNING id"), params).scalar_one())


def _violates(conn: Connection, sql: str, **params: object) -> None:
    """The statement must be rejected by a constraint (inside a savepoint)."""
    with pytest.raises(IntegrityError), conn.begin_nested():
        conn.execute(text(sql), params)


def _mapping(conn: Connection, file_type: str = "payables", version: int = 1) -> int:
    return _insert(
        conn,
        "INSERT INTO file_mappings (file_type, version, spec) VALUES (:t, :v, '{}')",
        t=file_type,
        v=version,
    )


def _source_file(
    conn: Connection, mapping_id: int, file_type: str = "payables", sha: str = "a" * 64
) -> int:
    return _insert(
        conn,
        "INSERT INTO source_files (file_type, filename, sha256, as_of, import_report, mapping_id)"
        " VALUES (:t, 'f.xlsx', :sha, '2026-11-30', '{}', :m)",
        t=file_type,
        sha=sha,
        m=mapping_id,
    )


def _counterparty(
    conn: Connection, kind: str, name: str, code: str | None = None, key: str | None = None
) -> int:
    return _insert(
        conn,
        "INSERT INTO counterparties (kind, code, name, name_key) VALUES (:k, :c, :n, :key)",
        k=kind,
        c=code,
        n=name,
        key=key or name.casefold(),
    )


LEDGER = (
    "INSERT INTO ledger_items (kind, counterparty_id, period, amount_vnd, site_code,"
    " expected_collection_day, source_file_id, source_ref)"
    " VALUES (:kind, :cp, :period, 100, :site, :day, :sf, '{}')"
)


def _ledger(conn: Connection, **overrides: object) -> None:
    params: dict[str, object] = {
        "kind": "payable",
        "period": dt.date(2026, 10, 1),
        "site": None,
        "day": None,
    }
    params.update(overrides)
    conn.execute(text(LEDGER), params)


def test_upgrade_downgrade_upgrade(engine: Engine) -> None:
    _alembic("downgrade", "base")
    with engine.connect() as conn:
        tables = conn.execute(
            text("SELECT count(*) FROM pg_tables WHERE schemaname = 'public'")
        ).scalar_one()
        views = conn.execute(
            text("SELECT count(*) FROM pg_views WHERE schemaname = 'public'")
        ).scalar_one()
    # Only alembic_version remains.
    assert (tables, views) == (1, 0)
    _alembic("upgrade", "head")


def test_settings_row_seeded_without_invented_threshold(conn: Connection) -> None:
    row = conn.execute(
        text("SELECT id, min_balance_vnd, timezone, default_recipient_language FROM settings")
    ).one()
    assert tuple(row) == (1, None, "Asia/Ho_Chi_Minh", "bilingual")
    _violates(conn, "INSERT INTO settings (id) VALUES (2)")


def test_same_file_new_mapping_version_is_a_new_snapshot(conn: Connection) -> None:
    m1 = _mapping(conn, version=1)
    m2 = _mapping(conn, version=2)
    _source_file(conn, m1)
    _source_file(conn, m2)  # same sha256, newer mapping: allowed
    with pytest.raises(IntegrityError), conn.begin_nested():
        _source_file(conn, m1)  # same sha256 + same mapping: idempotency key


def test_counterparty_keys(conn: Connection) -> None:
    _counterparty(conn, "customer", "Công ty Mẫu", key="công ty mẫu")
    with pytest.raises(IntegrityError), conn.begin_nested():
        _counterparty(conn, "customer", "CÔNG TY MẪU", key="công ty mẫu")
    # Same key for another kind, or with a code, is fine.
    _counterparty(conn, "bank", "Công ty Mẫu", key="công ty mẫu")
    _counterparty(conn, "supplier", "Công ty Mẫu", code="NCC_0001", key="công ty mẫu")
    _counterparty(conn, "supplier", "Công ty Mẫu", code="NCC_0002", key="công ty mẫu")
    with pytest.raises(IntegrityError), conn.begin_nested():
        _counterparty(conn, "supplier", "Other", code="NCC_0001", key="other")


def test_loan_snapshots_allow_instalments_but_not_duplicates(conn: Connection) -> None:
    sf = _source_file(conn, _mapping(conn, "loans"), "loans")
    bank = _counterparty(conn, "bank", "Bank A")
    loan = _insert(
        conn, "INSERT INTO loans (bank_id, loan_code) VALUES (:b, 'LD0000000001')", b=bank
    )
    insert = (
        "INSERT INTO loan_snapshots (loan_id, source_file_id, due_on, outstanding_vnd, source_ref)"
        " VALUES (:l, :sf, :due, :out, '{}')"
    )
    conn.execute(text(insert), {"l": loan, "sf": sf, "due": dt.date(2026, 12, 2), "out": 5})
    conn.execute(text(insert), {"l": loan, "sf": sf, "due": dt.date(2026, 12, 10), "out": 0})
    _violates(conn, insert, l=loan, sf=sf, due=dt.date(2026, 12, 2), out=5)
    _violates(conn, insert, l=loan, sf=sf, due=dt.date(2027, 1, 2), out=-1)
    _violates(
        conn,
        "INSERT INTO loans (bank_id, loan_code) VALUES (:b, 'LD0000000001')",
        b=bank,
    )


def test_ledger_constraints(conn: Connection) -> None:
    sf = _source_file(conn, _mapping(conn))
    supplier = _counterparty(conn, "supplier", "S", code="NCC_0001")
    customer = _counterparty(conn, "customer", "C")

    _ledger(conn, cp=supplier, sf=sf)
    # Payables have no site_code (NULL): a duplicate must still be rejected.
    with pytest.raises(IntegrityError), conn.begin_nested():
        _ledger(conn, cp=supplier, sf=sf)
    # Period must be the first day of a month.
    with pytest.raises(IntegrityError), conn.begin_nested():
        _ledger(conn, cp=supplier, sf=sf, period=dt.date(2026, 9, 15))
    # Site fields are for receivables only.
    with pytest.raises(IntegrityError), conn.begin_nested():
        _ledger(conn, cp=supplier, sf=sf, period=dt.date(2026, 9, 1), site="SITE_A")
    # Receivables: the same customer on several sites is fine; day must be 1-31.
    _ledger(conn, kind="receivable", cp=customer, sf=sf, site="SITE_A", day=25)
    _ledger(conn, kind="receivable", cp=customer, sf=sf, site="SITE_B")
    with pytest.raises(IntegrityError), conn.begin_nested():
        _ledger(conn, kind="receivable", cp=customer, sf=sf, site="SITE_A", day=25)
    with pytest.raises(IntegrityError), conn.begin_nested():
        _ledger(conn, kind="receivable", cp=customer, sf=sf, site="SITE_C", day=32)


def test_current_views_follow_the_latest_import_per_file_type(conn: Connection) -> None:
    supplier = _counterparty(conn, "supplier", "S", code="NCC_0001")
    customer = _counterparty(conn, "customer", "C")
    old = _source_file(conn, _mapping(conn, "payables", 1), "payables", "1" * 64)
    new = _source_file(conn, _mapping(conn, "payables", 2), "payables", "2" * 64)
    receivables = _source_file(conn, _mapping(conn, "receivables"), "receivables", "3" * 64)
    _ledger(conn, cp=supplier, sf=old)
    _ledger(conn, cp=supplier, sf=new, period=dt.date(2026, 11, 1))
    _ledger(conn, kind="receivable", cp=customer, sf=receivables, site="SITE_A")

    current = conn.execute(
        text("SELECT source_file_id, kind FROM current_ledger_items ORDER BY kind")
    ).all()
    assert [tuple(r) for r in current] == [(new, "payable"), (receivables, "receivable")]

    files = conn.execute(text("SELECT id FROM current_source_files ORDER BY id")).scalars().all()
    assert files == [new, receivables]
    assert conn.execute(text("SELECT count(*) FROM current_loan_snapshots")).scalar_one() == 0
