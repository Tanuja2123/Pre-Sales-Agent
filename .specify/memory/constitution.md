# Pre-Sales AI Agent — Project Constitution

## Purpose

Build a production-structured pre-sales RFP pipeline: specs define behaviour; code implements specs; tests prove acceptance criteria.

## Principles

1. **Spec before code** — No behaviour change without a versioned spec update (see `specs/`).
2. **MAF governance** — Minimum (M) gates are non-negotiable; pipeline may halt with explicit blockers.
3. **Typed contracts** — Public APIs and agent outputs use Pydantic models aligned with output specs.
4. **Test-first for parsers and models** — Deterministic components require unit tests before features ship.
5. **Observable runs** — Every pipeline run has a `run_id`; structured logging includes agent and duration.
6. **Secrets in environment** — Never commit keys; use `.env` locally and Key Vault in production.

## Quality bar

- Lint: Ruff on backend; ESLint on frontend.
- CI runs unit tests and spec validation on every PR.
- LLM-backed agents must degrade gracefully when Ollama/Azure is unavailable (clear errors, no silent failure).

## Review

Spec changes and code changes follow the same review discipline: traceability from user story → task spec → tests → implementation.
