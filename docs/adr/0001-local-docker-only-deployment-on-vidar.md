# ADR 0001: Local-Docker-Only Deployment on VIDAR (Reject Cloud IaC)

| | |
| :--- | :--- |
| **Status** | accepted |
| **Date** | 2026-10-10 |
| **Deciders** | @fpittelo (Product Owner), @architect |
| **Technical story** | [fpittelo/coach#72](https://github.com/fpittelo/coach/issues/72) |
| **Consumer alignment** | [fpittelo/coach-web ADR-007 — Local-First Deployment](https://github.com/fpittelo/coach-web/blob/main/docs/architecture.md) (recorded in coach-web architecture doc §10; story: [coach-web#108](https://github.com/fpittelo/coach-web/issues/108)) |

## Context and Problem Statement

How and where is the Coach MCP server (`coach-mcp`) deployed and consumed?

The Coach MCP server is a FastMCP gateway to Intervals.icu, serving a single-user
personal coaching ecosystem. Its primary consumer, [fpittelo/coach-web](https://github.com/fpittelo/coach-web),
runs the server as part of a three-lane local Docker topology (dev/qa/prod).
An earlier cloud deployment path (GCP) existed in the consumer's history and was
retired on 2026-10-03 (coach-web ADR-007, issues #108–#111). This repository had
no recorded deployment decision of its own, leaving the deployment topology
implicit and the fate of proposed standalone compose stacks (#74) undecided.

## Decision Drivers

- **Single-user, single-host reality.** One athlete, one host (VIDAR), loopback
  consumption. Swiss nLPD data minimization favors keeping biometric data local.
- **Consumer decision already ratified.** coach-web ADR-007 (accepted 2026-10-03)
  retired GCP and standardized on local Docker lanes; the provider must not
  document a divergent topology.
- **Sidecar consumption model is production truth.** coach-web's lanes
  (`coach-web-dev/qa/prod`) run `coach-mcp` as a sidecar on the internal
  `coach-net` Docker network with no published host port, pulling
  `ghcr.io/fpittelo/coach:dev|qa|prod`.
- **KIS & YAGNI (home-governance §9).** No infrastructure should be built that
  no consumer uses.
- **Zero-warning quality gates** travel with the existing CI; no cloud-specific
  pipeline stages are required.

## Considered Options

1. **Local-Docker-only on VIDAR, sidecar consumption** — images published to
   GHCR per environment tag; deployment owned by the consumer's lane topology.
2. **Cloud IaC (GCP/Azure via OpenTofu)** — managed cloud deployment with
   remote state, per home-governance cloud patterns.
3. **Standalone per-environment compose stacks in this repo** with published
   host ports (proposed in #74 as dev:8000 / qa:8001 / prod:8002).

## Decision Outcome

**Chosen option 1: Local-Docker-only deployment on VIDAR, consumed as a sidecar
by fpittelo/coach-web lanes. Cloud IaC is rejected.**

The Coach MCP server ships exclusively as OCI images to GHCR with an
environment-tag contract; deployment, networking, and lifecycle are owned by
the consumer's (coach-web) lane topology. This repository maintains no
deployment stacks of its own.

### Tag contract (verified 2026-10-10 against `.github/workflows/deploy.yaml`)

| Source ref | GHCR tag(s) |
| :--- | :--- |
| push to `dev` | `:dev` + `:sha` |
| merge to `qa` | `:qa` + `:sha` |
| merge to `main` (or `v*` tag) | `:prod`, `:latest`, `v*` + `:sha` |

Verified against coach-web's `COACH_MCP_IMAGE` defaults
(`ghcr.io/fpittelo/coach:dev|qa|prod`) — no mismatch.

### Consequences

**Positive**

- Single source of deployment truth across the coach/coach-web pair; no
  divergent topologies to keep synchronized.
- Biometric data (nLPD Art. 5(c)) never leaves the local host boundary.
- No cloud cost, no IaC state to maintain, no cloud CI stages.
- MCP endpoint exposure is internal-only (Docker network), which simplifies
  the security posture (#61 bearer auth becomes defense-in-depth, not a
  primary control).

**Negative**

- Single-host availability: VIDAR downtime takes the coaching stack offline.
  Accepted for a single-user personal system.
- Deployment lifecycle is coupled to the consumer repo's lane scripts
  (`scripts/lane.sh`, `e2e-preflight.sh`); breaking changes there surface here.
- No standalone local run mode is ratified; local development of `coach-mcp`
  in isolation relies on stdio transport or ad-hoc `docker run`.

**Neutral / follow-ups**

- #74 (standalone compose stacks with host ports 8000/8001/8002) is
  **superseded by this ADR** (to be closed on merge): standalone stacks would
  duplicate coach-web's lane topology and conflict on host port 8000 (prod
  lane).
- #61 (bearer token auth) is re-scoped as defense-in-depth and must cover the
  SSE transport actually used by the consumer (`/sse`), not only
  `streamable_http`.
- Full arc42 documentation adoption for this repository is deferred; §9 index
  is bootstrapped now ([docs/architecture/arc42/09-architecture-decisions.md](../architecture/arc42/09-architecture-decisions.md)).

## Validation of the Decision

- Consumer evidence: coach-web `compose.{dev,qa,prod}.yml`, `scripts/lane.sh`,
  `scripts/e2e-preflight.sh`, `docs/admin_guide.md` (all reference the sidecar
  service set `coach-web`, `coach-mcp`, `github-mcp` with healthcheck gates).
- Tag evidence: this repo's `deploy.yaml` environment-tag mapping (above).
- PO decisions recorded in fpittelo/coach-web#163 (2026-10-10): personal API
  key for MVP, loopback single-user posture.

## Links

- [fpittelo/coach#72](https://github.com/fpittelo/coach/issues/72) — this ADR's story
- [fpittelo/coach#74](https://github.com/fpittelo/coach/issues/74) — superseded by this ADR
- [fpittelo/coach#61](https://github.com/fpittelo/coach/issues/61) — re-scoped by this ADR
- [fpittelo/coach-web#108](https://github.com/fpittelo/coach-web/issues/108) — consumer ADR-007 story
- [fpittelo/coach-web#163](https://github.com/fpittelo/coach-web/issues/163) — capability audit & PO decisions
