# Research: postgres-container-runtime

**Feature**: `specs/004-postgres-container-runtime/spec.md`

**Date**: 2026-11-24

**Status**: Complete — no unresolved `NEEDS CLARIFICATION`

## Clarification resolution

The clarification session in `spec.md:11-19` resolved the only material ambiguities: exact `SELECT 1` health contract, CLI parity and exit codes, `DATABASE_URL` selection with SQLite in-memory default, and Docker Compose gating on PostgreSQL health. No further clarification is required before implementation.

## 1. PostgreSQL persistence adapter

- **Decision**: Add one outbound adapter implementing `IncidentRepositoryPort` with `psycopg[binary]`, parameterized `%s` SQL, and `TEXT` columns for local naive ISO 8601 timestamps. Its `check_health()` must execute `SELECT 1` and return `False` on driver errors. Keep the SQLite adapter unchanged in behavior and add a PostgreSQL implementation with equivalent schema, indexes and error mapping (`DuplicateIncidentId` on SQLSTATE `23505`).
- **Rationale**: The port already defines `save_incident`, `get_incident`, `find_open_duplicates`, `list_active_incidents` and `check_health` at `src/application/ports.py:8-33`. The SQLite adapter demonstrates the observable contract at `src/adapters/outbound/sqlite_repository.py:32-192`. ADR-004 (`docs/adr/004-persistencia-postgresql-y-runtime-contenedores.md:19-30`) and constitution v1.1.0 (`.specify/memory/constitution.md:54-70`) mandate dual persistence without an ORM, with `psycopg[binary]` confined to outbound code.
- **Alternatives considered**:
  - SQLite with a persistent volume: rejected because it is not a dedicated database (ADR-004:18-21).
  - An ORM or query builder: rejected by constitution IV and ADR-004:22-26 because it adds a layer and changes SQL behavior.
  - Native `TIMESTAMPTZ`: rejected by ADR-004:28 because it would break the shared local naive ISO 8601 contract.
  - Sharing mutable row-mapping helpers across engines: accepted only if they remain inside `src/adapters/outbound/`; SQL placeholder dialects must not be generalized into the application layer.

## 2. Engine selection from `DATABASE_URL`

- **Decision**: Make `src/bootstrap.py` the composition root that reads `DATABASE_URL` once. Absent/empty selects SQLite in memory; `sqlite:` URLs select SQLite; `postgresql:` URLs select PostgreSQL; any other scheme is rejected clearly with no silent fallback.
- **Rationale**: ADR-004:26 and `.specify/memory/constitution.md:62-66` place selection in the composition root. Today the env read is buried in `src/adapters/outbound/sqlite_repository.py:210-215`, and any `://` value is rejected at `:205-206`, so PostgreSQL cannot be selected. Moving the decision to `bootstrap.py` prevents application/domain changes.
- **Alternatives considered**:
  - Selecting by environment flag separate from `DATABASE_URL`: rejected because the clarified spec and ADR-004 both name `DATABASE_URL`.
  - Auto-detecting installed drivers: rejected because it would hide invalid configuration and weaken FR-003.
  - Building repository instances at module import time: rejected because an invalid URL would break `/health` before it can return the agreed `503` contract (`src/adapters/inbound/api/app.py:142`, `src/adapters/inbound/cli.py:119-123`).

## 3. Health use case shared by REST and CLI

- **Decision**: Add `check_database_health()` to `IncidentService`, reusing the existing `check_health() -> bool` method on `IncidentRepositoryPort`. Return one application DTO that maps to `{"status":"ok","database":"connected"}` or `{"status":"error","database":"unavailable"}`. `GET /health` turns that DTO into `200`/`503`; CLI `health` prints the identical compact JSON and exits `0`/`1`.
- **Rationale**: Constitution II (`.specify/memory/constitution.md:31-41`) requires one use case for REST and CLI. The seam already exists at `src/application/ports.py:31-33` and SQLite `SELECT 1` at `src/adapters/outbound/sqlite_repository.py:170-176`; adding the orchestration to the service avoids business logic in adapters and guarantees parity.
- **Alternatives considered**:
  - Calling the repository directly from API/CLI: rejected because inbound adapters cannot import outbound adapters (`src/adapters/inbound/ruff.toml:4-5`) and would duplicate logic.
  - Returning driver exceptions or credentials in the health body: rejected by FR-007 and SC-006 (`spec.md:100,121`).
  - Using the existing `HTTPException(detail=...)` path: rejected because the 503 body must be exactly the agreed JSON, without a `detail` wrapper.

## 4. Container runtime

- **Decision**: Add `Dockerfile`, `.dockerignore` and `compose.yaml`. The image uses Python 3.12-slim, `uv sync --frozen --no-dev`, a non-root user and Uvicorn for the API. Compose defines `api` and `db`; `db` uses `postgres:16-alpine` with a named volume and `pg_isready` healthcheck; `api` uses `depends_on.db.condition: service_healthy`, receives `DATABASE_URL` pointing at `db`, and has an HTTP healthcheck against `/health` using Python stdlib `urllib`.
- **Rationale**: FR-009/FR-010 (`spec.md:102-103`) and ADR-004:30 require a dedicated PostgreSQL service, persistent volume and health-gated startup. No Dockerfile, `.dockerignore` or Compose file currently exists. `urllib` avoids adding `curl` to a slim image.
- **Alternatives considered**:
  - Publishing the database port unconditionally: rejected because it is unnecessary for internal API connectivity; an optional localhost binding can be documented for debugging.
  - Retrying API startup without Compose health gating: rejected because it does not satisfy FR-010 literally.
  - Testcontainers in pytest: rejected because it would add an unrequested development dependency; real Compose verification remains an explicit quickstart step.

## 5. Validation strategy

- **Decision**: Keep default `uv run pytest` container-free with fake repositories and static Compose-config assertions; add an opt-in `compose` test for live verification. Run `uv run ruff check .`, the existing domain audits, and a documented clean-state `docker compose up -d --build --wait` sequence as the real proof of the four BDD scenarios.
- **Rationale**: Constitution V (`.specify/memory/constitution.md:72-81`) requires BDD tests and REST/CLI equivalence; constitution workflow (`:101-106`) requires `pytest` and Ruff. SC-004 (`spec.md:119`) requires a real reproducible stack. Existing test factories at `tests/test_spec_002_summary.py:21-29` and `tests/test_spec_003_lifecycle_sla.py:54-62` support dependency injection without containers.
- **Alternatives considered**:
  - Running Docker inside the default pytest suite: rejected because it is slow, environment-dependent and flaky.
  - Only manual verification: rejected because the four scenarios must be encoded as tests.
  - Reusing the legacy benchmark repository: rejected because `AGENTS.md:28` marks its full scan and N+1 as intentional debt unrelated to Hito 004.

## 6. Dependency and boundary updates

- **Decision**: Add `psycopg[binary]` to `pyproject.toml:7-13` and regenerate `uv.lock`. Keep all driver imports, SQL text and URL parsing details inside `src/adapters/outbound/`. Register the `compose` pytest marker to keep opt-in live tests warning-free.
- **Rationale**: Constitution IV requires the driver and forbids ORM or engine knowledge in domain/application. Current Ruff layer bans are split across `src/domain/ruff.toml` and `src/application/ruff.toml`; root rules at `pyproject.toml:28-35` must still pass.
- **Alternatives considered**:
  - Using `psycopg` instead of `psycopg[binary]`: rejected by constitution IV and ADR-004:19.
  - Adding a configuration package: rejected as unnecessary scope; `bootstrap.py` is the existing composition root.
  - Banning driver imports globally instead of by layer: rejected because outbound adapters legitimately need them.
