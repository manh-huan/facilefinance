# Architecture

Status: bootstrap. This document describes the target design from CLAUDE.md; update it as
components land.

## Overview

FacileFinance is a modular monolith deployed with Docker Compose on one VPS, behind Caddy.
There is one user; authentication is handled by an external access layer in front of Caddy,
so the app contains no login code.

```
Excel files -> importers -> ledger_items / loans --+
                                                   +-> rules engine -> cash_events -> forecast
config/file_maps (versioned) ----------------------+        ^                           |
rules (versioned, in DB) ----------------------------------+                           v
                                        assistant_questions <-+          alerts, reports, UI
```

## Layers and dependency rule

- `src/facilefinance/` is the core: importers, rules, forecast, payroll (post-MVP), ai,
  notify, db. It never imports from `apps/`.
- `apps/api` (FastAPI, thin endpoints), `apps/web` (React + TypeScript), `apps/worker`
  (scheduler and jobs), `apps/mcp_server` (post-MVP) depend on the core only.
- Only `ai/` may import `anthropic`.

## Key design decisions

1. **Rules and file maps are data.** They live in the database or `config/`, carry a
   `version`, and are never overwritten.
2. **AI interprets and asks; code computes.** Every number enters the forecast through
   Python. Claude proposes file maps, calls read-only tools, explains, drafts reports.
3. **Traceability.** `cash_events` reference `ledger_item_id` or `loan_id` plus the exact
   `rule_id`; `ledger_items` keep `source_ref` (file, sheet, row).
4. **Money is `bigint` VND.** Dates are `date`, instants are `timestamptz`.
5. **i18n.** The backend returns codes and raw values (integer VND, ISO 8601, snake_case
   enums, error codes with params). The frontend owns UI language (`en`, `vi`). Server-side
   text exists only in email and AI-generated content, both rendered from the shared
   `locales/` catalogs.
6. **Jobs** run from a PostgreSQL-backed queue; no Redis.
7. **Humans approve every real payment.** The app proposes only.

## Data flow: board report (bilingual)

Claude drafts in English with placeholder ids only, a second call renders Vietnamese with the
same placeholders, code fills figures per locale, and a check fails the job on placeholder
mismatch or stray digits. Both versions are stored and approved together.

## Deployment

Docker Compose: `db` (PostgreSQL 16), `api`, `worker`, `caddy`; the web app is built to
static files served by Caddy.

See [adr/0001-monorepo-and-stack.md](adr/0001-monorepo-and-stack.md) for the stack decision.
