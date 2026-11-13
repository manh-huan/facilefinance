[Tiếng Việt](README.vi.md) · **English**

# FacileFinance

A personal assistant for corporate finance teams. It starts with cash-flow management for a
single user (the chief accountant of an industrial catering company with about 40 sites) and
is meant to grow into a multi-tenant SaaS later.

## What it does (MVP)

- Imports three Excel file types: bank loans, accounts payable, accounts receivable.
- Applies versioned business rules (supplier payment policy, fixed costs, payroll, taxes,
  social insurance, minimum cash balance).
- Proposes a weekly payment schedule with approval status. Humans approve every payment;
  the app never executes one.
- Builds a 13-week cash forecast with what-if scenarios.
- Sends a Monday 07:30 (Asia/Ho_Chi_Minh) alert email.
- AI layer: a management report for the board and an assistant that asks for rules when a
  situation is not covered.

Principles: rules and file maps are data, not code; AI interprets and asks while Python
computes every number; every number is traceable to its source. Full list in
[CLAUDE.md](CLAUDE.md). Architecture: [docs/architecture.md](docs/architecture.md).

The app is fully bilingual (English and Vietnamese). The backend returns codes and raw values;
the frontend owns all UI language.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) with Python 3.14
- Docker and Docker Compose (PostgreSQL 16)
- Node.js (frontend)

## Setup

```bash
uv sync                    # install Python dependencies
cp .env.example .env       # fill in secrets (never commit .env)
docker compose up -d db    # start PostgreSQL
uv run alembic upgrade head
```

## Commands

```bash
uv run uvicorn apps.api.main:app --reload   # API on :8000
cd apps/web && npm install && npm run dev   # web on :5173, proxies /api -> :8000
uv run pytest                               # tests
uv run python -m evals.run                  # evals
uv run ruff check . && uv run mypy          # lint + types
cd apps/web && npm run i18n:check           # verify en/vi keys match
```

Some commands only work once the matching bootstrap step in CLAUDE.md section 13 is done
(database, API, web, evals).

Database tests (schema, constraints, views) run only when `FACILEFINANCE_TEST_DATABASE_URL`
points to a PostgreSQL database whose name ends in `_test`; its `public` schema is dropped and
recreated. Without the variable they are skipped. `DATABASE_URL` must be set for
`alembic` commands.

## Data policy

No real data in the repository. Real Excel files stay outside it; tests, evals and demos use
synthetic files only (`data/sample/`, `evals/`).
