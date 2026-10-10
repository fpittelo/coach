# Contributing

## Governance

This project follows the **FPITTELO PROJECT STANDARD v1** ([`STANDARD.md`](https://github.com/fpittelo/project-template/blob/main/STANDARD.md)):

- **3-branch lifecycle:** all work happens on feature branches from `dev` (`feature/<issue-#>-<slug>`, `fix/<issue-#>-<slug>`, `chore/<issue-#>-<slug>`); squash-merge into `dev` only; promotions `dev` → `qa` → `main` require explicit Product Owner (@fpittelo) approval.
- **Zero-warning CI:** every PR must pass the pipeline with 0 warnings and 0 failures. Run the local pre-flight before pushing (below).
- **SCRUM board:** GitHub Issues with the standard label taxonomy (STANDARD.md §4); every PR references its issue (`Resolves #<issue-#>`).
- **KIS & YAGNI:** minimal diffs satisfying the acceptance criteria; over-delivery is a review finding.

## Local development

Coach MCP is a Python 3.11+ FastMCP server managed with [uv](https://docs.astral.sh/uv/) (see `pyproject.toml`).

```bash
# Create the virtual environment and install with dev dependencies
uv venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"

# Local pre-flight (mirrors the CI gate)
ruff check .
pytest -v --cov=src/coach_mcp tests/

# Recommended hygiene (dev dependencies; enforced locally, not yet in CI)
black --check . && isort --check-only . && mypy --strict src/coach_mcp
```

### MCP server specifics

- **stdio cleanliness:** all application logging goes to `stderr`; `stdout` is reserved for JSON-RPC framing. Never log to `stdout`.
- **Secrets:** Intervals.icu credentials are read from the environment only (`INTERVALS_API_KEY`, `INTERVALS_ATHLETE_ID`). Never hardcode tokens in source, tests, or docs; `.env` files are gitignored.
- **Container:** the OCI image runs non-root (`coach`, `UID:GID 10001:10001`). Do not weaken the `Dockerfile` user or add root-only steps.

## Pull requests

1. Branch from `dev`, named `feature|fix|chore/<issue-#>-<slug>`.
2. Reference the issue in the PR body (`Resolves #<issue-#>`).
3. CI must be green (0 warnings / 0 failures) before review; merges into `dev` are squash-only.
4. Promotions to `qa` and `main` are PO-approved release gates (STANDARD.md §2).

## License

This project is licensed under **GPL-3.0-or-later** (see [LICENSE](LICENSE)). License changes require an explicit PO decision recorded in an ADR.

## Commit style

Conventional Commits, referencing the issue: `feat: implement power curve calculation (#24)`.
