# Tasks: postgres-container-runtime

**Input**: Design documents from `/specs/004-postgres-container-runtime/`

**Prerequisites**: `plan.md` (required), `spec.md` (required for user stories), `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included because the spec declares four BDD acceptance scenarios and the plan requires pytest, REST/CLI parity and real Compose verification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Single project: `src/` and `tests/` at repository root, per `plan.md`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the dependency and test configuration required by every story.

- [X] T001 Add `psycopg[binary]` to `[project].dependencies` in `pyproject.toml` and regenerate `uv.lock` with `uv lock`.
- [X] T002 Register the opt-in `compose` pytest marker in `[tool.pytest.ini_options]` in `pyproject.toml`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

⚠️ **CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Refactor `src/adapters/outbound/sqlite_repository.py` to accept explicit `sqlite:` URLs and programmatic `:memory:`/path values without reading `DATABASE_URL`, preserving the canonical timestamp rules from `data-model.md` `Incident.created_at` and `data-model.md` `Incident.resolved_at`.
- [X] T004 [P] Add `HealthStatusResult` and `IncidentService.check_database_health()` in `src/application/services.py`, deriving `data-model.md` `HealthStatusResult.status`, `data-model.md` `HealthStatusResult.database` and `data-model.md` `HealthStatusResult.healthy` solely from `IncidentRepositoryPort.check_health()`.
- [X] T005 [P] Add exact health response models in `src/adapters/inbound/api/schemas.py` for `data-model.md` `HealthStatusResult.status` and `data-model.md` `HealthStatusResult.database`.
- [X] T006 Refactor `src/bootstrap.py` to resolve `DATABASE_URL` once and build `IncidentService`, selecting SQLite for absent/empty and `sqlite:` values per `data-model.md` `DatabaseSelection.DATABASE_URL`; invalid or unsupported schemes must not fall back to SQLite, must allow API startup and must leave health able to report unavailable.

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Verificar conexión disponible (Priority: P1) 🎯 MVP

**Goal**: Operaciones can confirm through both channels that the configured database is reachable via a real `SELECT 1`.

**Independent Test**: Invoke `GET /health` and CLI `health` against a reachable configured database and assert both return `{"status":"ok","database":"connected"}`, with HTTP `200` and CLI exit `0`.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T007 [P] [US1] Add the successful-connection BDD test in `tests/test_spec_004_postgres_container_runtime.py` using a fake repository whose `check_health()` returns `True`, asserting `SELECT 1` is called once per channel and that `data-model.md` `HealthStatusResult.status` and `data-model.md` `HealthStatusResult.database` match the success contract.

### Implementation for User Story 1

- [X] T008 [US1] Add `GET /health` in `src/adapters/inbound/api/app.py`, returning `200` and the exact success JSON from `data-model.md` `HealthStatusResult.status` and `data-model.md` `HealthStatusResult.database`.
- [X] T009 [US1] Add the `health` command in `src/adapters/inbound/cli.py`, printing the same compact JSON and exiting `0` according to `data-model.md` `HealthStatusResult.healthy`.

**Checkpoint**: User Story 1 is fully functional and testable independently.

---

## Phase 4: User Story 2 - Detectar conexión fallida (Priority: P1)

**Goal**: Operaciones gets an unambiguous failure signal when the configured database cannot answer `SELECT 1`.

**Independent Test**: Invoke `GET /health` and CLI `health` against an unreachable or invalid configuration and assert HTTP `503`, CLI exit `1`, identical error JSON and no secret values in any output.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T010 [US2] Add the failed-connection BDD test in `tests/test_spec_004_postgres_container_runtime.py`, covering unreachable engine, query failure, invalid and unsupported `DATABASE_URL` schemes, and a sentinel secret, starting the API successfully before invoking both channels and asserting `data-model.md` `HealthStatusResult.status` and `data-model.md` `HealthStatusResult.database` produce the exact error JSON in both channels.

### Implementation for User Story 2

- [X] T011 [US2] Harden `IncidentService.check_database_health()` in `src/application/services.py` so repository exceptions and missing repository from invalid configuration map through `data-model.md` `HealthStatusResult.status` and `data-model.md` `HealthStatusResult.database` without including exception text.
- [X] T012 [US2] Return the exact `503` error JSON from `GET /health` in `src/adapters/inbound/api/app.py` for unreachable engine, failed query, invalid configuration and unsupported `DATABASE_URL` schemes, with API startup succeeding in those configuration-failure cases, according to `data-model.md` `HealthStatusResult.healthy`.
- [X] T013 [US2] Print the same error JSON on stdout and exit `1` from the `health` command in `src/adapters/inbound/cli.py` for unreachable engine, failed query, invalid configuration and unsupported `DATABASE_URL` schemes, without selecting SQLite as fallback, according to `data-model.md` `HealthStatusResult.healthy`.

**Checkpoint**: User Stories 1 and 2 both work independently; each adds value without breaking the other.

---

## Phase 5: User Story 3 - Seleccionar el motor de persistencia (Priority: P2)

**Goal**: SQLite in memory remains the local default while PostgreSQL becomes selectable through `DATABASE_URL` with equivalent repository behavior.

**Independent Test**: Start with `DATABASE_URL` absent/empty and then with `postgresql:`; assert SQLite memory versus PostgreSQL selection, and assert an unsupported scheme is rejected clearly without fallback.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T014 [US3] Add the engine-selection BDD test and a PostgreSQL adapter `check_health()` test in `tests/test_spec_004_postgres_container_runtime.py` for absent/empty, `sqlite:`, `postgresql:`, invalid and unsupported values of `data-model.md` `DatabaseSelection.DATABASE_URL`, asserting SQLite in memory for absent/empty, no SQLite fallback for invalid/unsupported values, API startup succeeding in those invalid cases, `GET /health` returning `503` with `{"status":"error","database":"unavailable"}`, CLI `health` printing the same JSON and exiting `1`, and the PostgreSQL adapter running a real `SELECT 1` probe that returns `False` on driver errors.

### Implementation for User Story 3

- [X] T015 [US3] Implement `src/adapters/outbound/postgres_repository.py` with `psycopg[binary]`, `%s` parameters, idempotent schema, duplicate-error mapping and `check_health()` executing `SELECT 1` against the configured PostgreSQL connection and returning `False` on driver errors, honoring the canonical constraints from `data-model.md` `Incident.incident_id`, `data-model.md` `Incident.title`, `data-model.md` `Incident.raw_text`, `data-model.md` `Incident.component`, `data-model.md` `Incident.severity`, `data-model.md` `Incident.status`, `data-model.md` `Incident.created_at`, `data-model.md` `Incident.resolved_at` and `data-model.md` `Incident.duplicate_group_key`.
- [X] T016 [US3] Wire the PostgreSQL adapter into `src/bootstrap.py` for `postgresql:` URLs per `data-model.md` `DatabaseSelection.DATABASE_URL`, keeping SQLite as the default when the variable is omitted or empty and ensuring invalid or unsupported schemes do not select SQLite while still allowing API startup and health failure.

**Checkpoint**: Engine selection works end to end without changing domain rules or the application-facing port.

---

## Phase 6: User Story 4 - Arranque reproducible de la API con PostgreSQL (Priority: P2)

**Goal**: Operaciones can start one reproducible stack where PostgreSQL becomes healthy before the API starts and `GET /health` verifies the real connection.

**Independent Test**: From a clean state, start the stack with one command, wait for `db` healthy, confirm `api` starts afterward and verify `GET /health` returns the success contract.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation.**

- [X] T017 [P] [US4] Add the static Compose contract test in `tests/test_spec_004_compose_contract.py`, asserting `data-model.md` `RuntimeStack.db` uses `postgres:16-alpine`, a persistent volume and a `pg_isready` healthcheck, and `data-model.md` `RuntimeStack.api` gates startup on `service_healthy`, uses `DATABASE_URL` pointing to `db` and defines an HTTP healthcheck that requests `/health`.
- [X] T018 [P] [US4] Add the opt-in real Compose test in `tests/test_spec_004_compose_live.py` marked `compose`, following `specs/004-postgres-container-runtime/quickstart.md` and asserting `data-model.md` `RuntimeStack.db` becomes healthy through `pg_isready` before `data-model.md` `RuntimeStack.api` starts and that API health succeeds through an HTTP request to `/health`.

### Implementation for User Story 4

- [X] T019 [P] [US4] Add `Dockerfile` with Python 3.12-slim, `uv sync --frozen --no-dev`, a non-root user and Uvicorn for `data-model.md` `RuntimeStack.api`.
- [X] T020 [P] [US4] Add `.dockerignore` excluding VCS metadata, virtualenvs, caches, `.env`, secrets, docs, specs and tests from the image for `data-model.md` `RuntimeStack.api`.
- [X] T021 [US4] Add `compose.yaml` defining `data-model.md` `RuntimeStack.db` and `data-model.md` `RuntimeStack.api`, with `postgres:16-alpine`, named volume, a `pg_isready` healthcheck for `db`, an HTTP `/health` healthcheck for `api`, `depends_on.db.condition: service_healthy` and `DATABASE_URL` from `data-model.md` `DatabaseSelection.DATABASE_URL`.

**Checkpoint**: All four user stories are independently functional; the Compose stack proves the reproducible runtime.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gates and operational validation.

- [X] T022 [P] Run `uv run ruff check .` from the repository root against `pyproject.toml`, then fix any import-boundary or lint violations in `src/` and `tests/`.
- [X] T023 [P] Run `uv run pytest` from the repository root over `tests/`, fixing failures in `src/` while preserving REST/CLI parity.
- [X] T024 [P] Run the domain regression commands listed in `specs/004-postgres-container-runtime/quickstart.md` for `src/` modules, including triage, SLA and all context audits.
- [X] T025 Run the real clean-state verification in `specs/004-postgres-container-runtime/quickstart.md` against `compose.yaml`, capture `docker compose ps`, REST health, CLI health, elapsed time and secret-leak check, then `docker compose down`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on T001-T002 - BLOCKS all user stories.
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion.
  - US1 establishes the health endpoint and CLI command.
  - US2 depends on US1 files (`app.py`, `cli.py`) for the failure path but has its own independent test criteria.
  - US3 can proceed after Foundation because it uses a new adapter file plus `bootstrap.py`.
  - US4 depends on US1 and US3 because it verifies the real PostgreSQL health path through Compose.
- **Polish (Phase 7)**: Depends on all selected stories being complete.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 2; no dependencies on other stories. MVP.
- **User Story 2 (P1)**: Starts after US1 endpoint/CLI files exist; independently testable through failure cases.
- **User Story 3 (P2)**: Starts after Phase 2; independent of US1/US2 tests because it works through `src/bootstrap.py` and a new outbound adapter.
- **User Story 4 (P2)**: Starts after US1 and US3; independently testable by clean-state Compose startup.

### Within Each User Story

- Tests MUST be written first and observed failing before implementation.
- Contracts and DTOs before services; services before endpoints/commands.
- Core implementation before integration and Compose verification.

### Parallel Opportunities

- T003, T004, T005 and T006 touch different files and can run in parallel after Phase 1.
- T007 can run in parallel with US1 implementation only if a separate worktree is used; otherwise keep it first in the phase.
- T017-T020 touch different files and can run in parallel.
- T022-T024 are read-only checks and can run in parallel once code is stable.
- US3 can be implemented in parallel with US1/US2 by a separate developer after Phase 2.

---

## Parallel Example: User Story 4

```bash
# Launch these together after Phase 2 and US3 are complete:
Task: "Add static Compose contract test in tests/test_spec_004_compose_contract.py"
Task: "Add opt-in real Compose test in tests/test_spec_004_compose_live.py"
Task: "Add Dockerfile"
Task: "Add .dockerignore"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: Run the US1 independent test; health success works through both channels.
5. Demo the MVP before adding failure, engine selection or Compose.

### Incremental Delivery

1. Complete Setup + Foundational.
2. Add US1 -> test independently -> MVP demo.
3. Add US2 -> test failure path independently.
4. Add US3 -> test engine selection and adapter equivalence.
5. Add US4 -> run real Compose verification.
6. Run Polish gates and report results.

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together.
2. Developer A: US1 then US2.
3. Developer B: US3.
4. Developer C: US4 after US1 and US3 are integrated.
5. Merge each story only after its independent test passes.

---

## Notes

- `[P]` tasks use different files or are read-only checks.
- `[US1]`-[US4] map directly to the four user stories in `spec.md`.
- Every constrained field from `data-model.md` is cited by exact `Entity.field` in at least one implementing task.
- Do not optimize `src/incident_repository.py`; its full scan and N+1 are intentional benchmark debt.
- Verify tests fail before implementing; commit after each task or logical group.
- Stop at any checkpoint to validate the story independently.
- Avoid vague tasks, same-file parallel conflicts and cross-story dependencies that break independence.
