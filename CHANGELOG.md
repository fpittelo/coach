# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

*History prior to v0.2.0 predates this changelog.*

## [Unreleased]

### Changed

- Documentation aligned with the FPITTELO PROJECT STANDARD v1 (lean README with architecture schema, `CHANGELOG.md`, `CONTRIBUTING.md`; displaced content relocated into `docs/`) and diff-scoped gitleaks secret scanning added to CI (fpittelo/opencode-home-config#192).

## [0.6.2] - 2026-10-11

### Fixed

- Markdown-injection defense applied class-wide: 3 sites escaped with injection tests, 2 documented safe via data-flow proofs; CI `uv` pinned to 0.11.17 (#113).

### Changed

- `user_guide` §4 rewritten — VIDAR sidecar topology (no host ports) and SHA-pinned production update flow, consistent with ADR 0001 (#76).

## [0.6.1] - 2026-10-11

### Security

- `pyjwt` 2.13.0 → 2.15.1; all 14 transitive CVEs cleared (#105).

### Changed

- Dependency audit now runs against the locked artifact (`uv export --frozen` + OSV source), closing the closure-drift blind spot (#105).

### Fixed

- Audit redaction regression assertion, markdown-safe formatters (`_escape_md_cell`), trend-direction boundary symmetry (#90).

## [0.6.0] - 2026-10-11

### Added

- `icu_batch_create_events` (token-gated batch upsert, #94), `icu_get_workout_compliance` (paired-event adherence join, #95), `icu_get_completed_sessions` (bounded listing, #96), `icu_get_trends` (CTL/ATL/TSB series, #97) — epic #82 complete, all 6 `icu_*` tools shipped.

### Security

- Bearer token authentication on both HTTP transports (legacy SSE `/sse` + streamable `/mcp`) with constant-time compare; MADR-0008 STRIDE pass (#61).

### Changed

- CI quality-gate parity: `black --check`, `isort --check-only`, `mypy --strict`, `pytest -W error`, `pip-audit --strict` (#60).

## [0.5.0] - 2026-10-10

### Added

- `icu_get_wellness` and `icu_add_session_comment` — first epic-#82 expansion tools (#84, #85).
- Structured JSON tool-invocation audit logging with hardened redaction (#64).
- Transport-aware container `HEALTHCHECK` (#75).
- ADR 0001: local-Docker-only deployment on VIDAR with sidecar consumption; arc42 §9 bootstrap (#72, #74).

### Security

- Docker secrets `_FILE` pattern with fail-fast ambiguity detection (#63).

### Changed

- CI: Node-24-native actions, `ubuntu-24.04` runner pin, `destroy.yaml` stub removed (#79, #73).

## [0.4.1] - 2026-10-03

### Fixed

- Structured workouts are now delivered through the calendar event `description` field: the server parses the Intervals.icu workout DSL from `description` and combines it with human-readable text instead of sending a raw DSL string to the structured `workout_doc` API field (#69).

## [0.4.0] - 2026-08-30

### Added

- `intervals_record_wellness_bulk` tool via the wellness-bulk endpoint (#50).
- TTL cache extended to hot read endpoints with write-through invalidation (#49).
- Parallelized independent upstream calls in `intervals_get_readiness_dashboard` (#48).

### Changed

- Remediated `mypy --strict` errors and added `black`/`isort` to the dev dependencies (#47).

## [0.3.0] - 2026-08-29

### Added

- `intervals_get_readiness_dashboard` composite tool (#32).
- Smart computed date defaults for date-range tools (#33).
- `intervals_get_power_model` tool for Critical Power (CP), W′, and Pmax modeling (#31).

### Fixed

- Power curve query parameter mapping (`curves` → `type`) (#36).
- Dict `workout_doc` payload handling in `intervals_get_event` (#35).
- Manual activity creation now uses the events endpoint (#34).
- Pytest `filterwarnings` configuration and missing tag-push trigger in the deploy workflow (#27).

## [0.2.1] - 2026-08-28

### Fixed

- CI/CD remediation: Pytest `filterwarnings` error and GHCR tag deployment triggers (#27).

## [0.2.0] - 2026-08-28

### Added

- `intervals_get_power_curve` tool for native MMP and power-duration curves (#16).
- In-memory TTL caching for semi-static athlete data (#17).

### Security

- Automated secret/PII redaction and input-validation hardening (#18).

[Unreleased]: https://github.com/fpittelo/coach/compare/v0.6.2...dev
[0.6.2]: https://github.com/fpittelo/coach/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/fpittelo/coach/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/fpittelo/coach/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/fpittelo/coach/compare/v0.4.1...v0.5.0
[0.4.1]: https://github.com/fpittelo/coach/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/fpittelo/coach/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/fpittelo/coach/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/fpittelo/coach/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/fpittelo/coach/tags
