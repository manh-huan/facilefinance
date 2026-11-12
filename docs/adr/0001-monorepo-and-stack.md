# ADR 0001: Monorepo and technology stack

- Status: accepted
- Date: 2026-11-12

## Context

FacileFinance starts as a tool for one chief accountant and may become a multi-tenant SaaS.
It is built and operated by a very small team on a single VPS. Business logic must be
auditable (every number traceable) and fully bilingual (English and Vietnamese).

## Decision

- **One monorepo** with a framework-free core (`src/facilefinance/`) and thin applications
  (`apps/api`, `apps/web`, `apps/worker`, later `apps/mcp_server`). Dependencies point from
  `apps/` to the core, never the reverse.
- **Backend:** Python 3.14 with uv; FastAPI and Pydantic v2; SQLAlchemy 2 and Alembic on
  PostgreSQL 16; Polars for data frames; `python-calamine` to read Excel and `openpyxl` to
  fill templates.
- **Jobs:** PostgreSQL-backed queue; no Redis.
- **Frontend:** React, TypeScript, Vite, TanStack Table, ECharts, react-i18next; API client
  generated from the OpenAPI schema.
- **AI:** Anthropic Python SDK, imported only from `src/facilefinance/ai/`.
- **Deployment:** Docker Compose on one VPS with Caddy in front.
- **Quality:** ruff, mypy (`--strict` on `src/`), pytest; eslint, tsc, vitest.

## Consequences

- One repository and one deployment keep operations simple for a single user.
- The core/apps split keeps business logic testable without HTTP and reusable by the worker
  and a future MCP server.
- Staying on PostgreSQL for data and queue avoids extra infrastructure.
- Multi-tenancy (`company_id`, row-level security) is deliberately not prepared now; adding
  it later will require a migration.
- No Kubernetes, microservices, Kafka, Redis, vector databases or heavy agent frameworks.
  Any new dependency needs a one-line justification.
- Python 3.14 was verified: every core dependency resolves and imports with `uv sync`.
