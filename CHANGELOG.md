# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

*History prior to v0.2.0 predates this changelog.*

## [Unreleased]

### Changed

- Documentation aligned with the FPITTELO PROJECT STANDARD v1 (lean README with architecture schema, `CHANGELOG.md`, `CONTRIBUTING.md`; displaced content relocated into `docs/`) and diff-scoped gitleaks secret scanning added to CI (fpittelo/opencode-home-config#192).

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

[Unreleased]: https://github.com/fpittelo/coach/compare/v0.4.1...dev
[0.4.1]: https://github.com/fpittelo/coach/compare/v0.4.0...v0.4.1
[0.4.0]: https://github.com/fpittelo/coach/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/fpittelo/coach/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/fpittelo/coach/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/fpittelo/coach/tags
