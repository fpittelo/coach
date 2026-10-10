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
- **Storage residency:** the coaching stack stores biometric data
  (nLPD Art. 5(c)) only on VIDAR. This does **not** change *processing*
  residency: Intervals.icu remains an external processor (data origin and
  cloud storage), and coach-web sends biometric context to OpenRouter
  (US routing) — see coach-web `docs/security.md` and its OpenRouter
  cross-border assessment (coach-web #112). Local-first reduces
  storage-residency risk; it does not eliminate external processing.
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

### Security consequences / accepted risks

Accepted threats of the sidecar topology (STRIDE spot-check; the authoritative
local STRIDE model is coach-web `docs/security.md` B1–B10 — this repo's arc42
§8/§11 are deferred, so that document is the interim SSOT for threat modeling):

| # | STRIDE | Threat | Compensating control |
| :--- | :--- | :--- | :--- |
| T1 | EoP / Info Disclosure | coach-web compromise (incl. LLM/MCP content prompt injection) → MCP write tools → full Intervals.icu account mutation | #82 condition 2 (write-confirmation gate); #61 bearer auth (sequenced — see below) |
| T2 | Info Disclosure | `INTERVALS_API_KEY` env-var exposure (`docker inspect`, `/proc/<pid>/environ`) → full ICU account | #63 (Docker secrets `_FILE` pattern) + #82 condition 6 (per-lane env `chmod 600`, never logged, rotate on suspicion) — **residual until #63 lands**: the key is currently env-injected |
| T3 | EoP | Container escape from any `coach-net` peer → host (biometric data, docker socket) | Container hardening in coach-web compose (`read_only`, `cap_drop: ALL`, `no-new-privileges`); docker-group membership remains root-equivalent (coach-web security.md B3) |
| T4 | Spoofing | Any sibling container on `coach-net` impersonates coach-web toward `coach-mcp` (no transport auth) | #61 bearer auth — **sequencing condition: #61 must not slip past #82's write tools**; until then the #82 condition-2 write-confirmation gate is the interim control |

Supply-chain note: the prod lane currently consumes `coach-mcp` by the mutable
`:prod` tag while its sibling services are digest-pinned — a digest-pinning
asymmetry tracked as a coach-web-side follow-up (their `compose.prod.yml`).

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
