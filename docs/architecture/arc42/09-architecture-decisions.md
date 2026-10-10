# 9. Architecture Decisions

> **Status: bootstrap (2026-10-10).** This file is the MADR decision index for
> the Coach MCP server, created by [ADR 0001](../../adr/0001-local-docker-only-deployment-on-vidar.md)
> (issue #72). Full arc42 documentation adoption (§1–§12 as separate files) is
> deferred; this index is the authoritative decision record until then.
>
> Each decision is a separate MADR document under [`docs/adr/`](../../adr/).

| ADR | Title | Status | Date | Consumer impact |
| :--- | :--- | :--- | :--- | :--- |
| [0001](../../adr/0001-local-docker-only-deployment-on-vidar.md) | Local-Docker-only deployment on VIDAR (reject cloud IaC); sidecar consumption by coach-web lanes | accepted | 2026-10-10 | Aligns with [coach-web ADR-007](https://github.com/fpittelo/coach-web/blob/main/docs/architecture.md) (architecture doc §10; story [coach-web#108](https://github.com/fpittelo/coach-web/issues/108)); supersedes #74; re-scopes #61 |

## Decision conventions

- New ADRs are scaffolded as `docs/adr/NNNN-<slug>.md` in MADR format and
  indexed here upon acceptance (number, title, status, link).
- Decisions with security impact (new MCP tools, API integrations, permission
  changes, auth flows) are reviewed by @cyber-security against arc42 §8/§11
  before spec finalization (MADR-0008 routing).
- Cross-repo decisions that affect the coach/coach-web pair reference the
  counterpart ADR in the table's *Consumer impact* column.
