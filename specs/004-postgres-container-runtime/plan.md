# Implementation Plan: postgres-container-runtime

**Branch**: `004-postgres-container-runtime` | **Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-postgres-container-runtime/spec.md`, constitution v1.1.0 and accepted ADR-004. The obsolete `Propuesto` note in ADR-004 was corrected to `Aceptado`; no other ADR text was changed.

**Note**: This plan stops before implementation. Code and container artifacts are left for `/speckit.implement`.

## Summary

Hito 004 adds a dedicated PostgreSQL execution path while preserving SQLite in memory as the local default. A second outbound adapter will implement the existing `IncidentRepositoryPort` with `psycopg[binary]`, parameterized SQL and naive local ISO 8601 timestamps in `TEXT` columns. `src/bootstrap.py` will select the engine from `DATABASE_URL`, rejecting unsupported schemes without silent fallback; invalid configuration must still resolve to the agreed health failure contract instead of an import-time crash.

One application use case will produce the health result consumed by both `GET /health` and CLI `health`. Each call will execute a real `SELECT 1` through the selected adapter and map the result to the exact agreed JSON: `200`/exit `0` with `{"status":"ok","database":"connected"}` or `503`/exit `1` with `{"status":"error","database":"unavailable"}`.

A reproducible Docker Compose stack will define `api` and `db` (`postgres:16-alpine`), a persistent volume, healthchecks for both services and `depends_on: condition: service_healthy` so the API starts only after PostgreSQL is healthy. Verification combines four BDD pytest scenarios, REST/CLI parity, Ruff, the existing domain audits and a real clean-state Compose check.

## Technical Context

**Language/Version**: Python 3.10+ managed with `uv`; container image targets Python 3.12-slim.

**Primary Dependencies**: Existing FastAPI, Pydantic v2, Typer, Uvicorn, pytest and Ruff; add `psycopg[binary]` and regenerate `uv.lock`.

**Storage**: SQLite in memory by default and for `sqlite:` URLs; PostgreSQL for `postgresql:` URLs. Both engines implement the same repository port with no ORM.

**Testing**: pytest with `TestClient`, `CliRunner`, fake repositories and static Compose assertions; opt-in `compose` marker for live container verification; `uv run ruff check .`.

**Target Platform**: Local development/tests on Python, and a Linux container runtime with Docker Compose for the API plus PostgreSQL 16 service.

**Project Type**: Web service and CLI in one Python package.

**Performance Goals**: Health verification returns within 10 seconds against a reachable engine (SC-001); a clean reproducible stack reaches successful verification within 5 minutes (SC-004).

**Constraints**: No ORM; no business rules in adapters; domain must not import application/adapters; application must not import concrete database modules or frameworks; timestamps remain local naive ISO 8601 strings in `TEXT`; no secret values in health output; no changes to triaje, duplicates or SLA rules; no optimization of the legacy benchmark repository.

**Scale/Scope**: One API service and one PostgreSQL service, no data migration, no additional database engine, no change to the existing incident contract.

**Clarifications**: None unresolved. All five clarification answers are recorded in `spec.md:11-19`.

## Constitution Check

*GATE: PASS before Phase 0; re-checked and PASS after Phase 1 design.*

| Principle / gate | Result | Evidence in design |
|---|---|---|
| I. Dominio determinista | PASS | No domain rule changes; `src/domain/` remains untouched. |
| II. Un solo caso de uso para REST y CLI | PASS | `IncidentService.check_database_health()` is the only health orchestration; REST and CLI only serialize its DTO. |
| III. Persistencia detrás de un puerto | PASS | Both engines implement `IncidentRepositoryPort`; application uses only the port; no concrete DB imports outside outbound adapters. |
| IV. Persistencia SQLite/PostgreSQL sin ORM | PASS | `psycopg[binary]`, parameterized SQL, `TEXT` ISO 8601 timestamps, `DATABASE_URL` dispatch in `src/bootstrap.py`, unsupported schemes rejected. |
| V. Criterios BDD y fronteras verificadas | PASS | Four BDD scenarios encoded in pytest with REST/CLI equivalence; Ruff gates remain mandatory. |
| Arquitectura y tecnología | PASS | Existing `src/domain`, `src/application`, `src/adapters/inbound`, `src/adapters/outbound` layout retained. |
| Flujo de trabajo y compuertas | PASS | `uv run pytest`, `uv run ruff check .`, domain audits and real Compose verification are part of quickstart. |
| Governance | PASS | ADR-004 already accepted and now internally consistent; no new ADR required. |

No violations were found; Complexity Tracking is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/004-postgres-container-runtime/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 validation guide
├── contracts/
│   ├── health-contract.md
│   ├── configuration-contract.md
│   └── compose-contract.md
└── tasks.md             # Phase 2 output (/speckit.tasks; NOT created here)
```

### Source Code (repository root)

```text
src/
├── bootstrap.py                              # modified: DATABASE_URL composition root
├── domain/                                   # unchanged
├── application/
│   ├── ports.py                              # existing: reuse IncidentRepositoryPort.check_health()
│   └── services.py                           # modified: HealthStatusResult + check_database_health()
└── adapters/
    ├── inbound/
    │   ├── api/
    │   │   ├── app.py                        # modified: GET /health
    │   │   └── schemas.py                    # modified: exact health response models
    │   └── cli.py                            # modified: health command and exit codes
    └── outbound/
        ├── sqlite_repository.py              # modified: no env read; accept sqlite: URLs
        └── postgres_repository.py            # new: psycopg[binary] adapter

tests/
├── test_spec_001_triage.py                   # unchanged
├── test_spec_002_summary.py                  # unchanged
├── test_spec_003_lifecycle_sla.py            # unchanged
├── test_spec_004_postgres_container_runtime.py  # new: four BDD + parity + selection tests
├── test_spec_004_compose_contract.py         # new: static compose.yaml assertions
└── test_spec_004_compose_live.py             # new: opt-in real Compose verification

pyproject.toml                                # modified: psycopg[binary] dependency + compose marker
uv.lock                                       # regenerated
Dockerfile                                    # new
.dockerignore                                 # new
compose.yaml                                  # new
docs/adr/004-persistencia-postgresql-y-runtime-contenedores.md  # already corrected
src/incident_repository.py                    # unchanged legacy benchmark
```

**Structure Decision**: Keep the existing single Python package and hexagonal layout. Do not add a configuration package, ORM, second service codebase or migrations. All engine-specific code stays in `src/adapters/outbound/`; selection stays in `src/bootstrap.py`.

## Implementation Outline for `/speckit.tasks`

1. Update dependencies and lock with `psycopg[binary]`; register the opt-in `compose` pytest marker.
2. Refactor `src/bootstrap.py` to resolve `DATABASE_URL`; remove env reading from the SQLite factory and keep legacy programmatic SQLite values working.
3. Add `src/adapters/outbound/postgres_repository.py` implementing every `IncidentRepositoryPort` method with `%s` parameters, idempotent schema, `TEXT` timestamps, duplicate-error mapping and `check_health()` with a real `SELECT 1`.
4. Add the shared health DTO and `check_database_health()` to `IncidentService`; map adapter `bool` to the exact agreed status strings without exposing driver details.
5. Add `GET /health` and CLI `health` as thin adapters over that use case, with exact JSON, `200`/`503`, exit `0`/`1` and REST/CLI parity.
6. Add `Dockerfile`, `.dockerignore` and `compose.yaml` with `api`, `db`, persistent volume, both healthchecks and DB-healthy gating.
7. Add BDD tests, engine-selection tests, static Compose assertions and opt-in live Compose tests; run Ruff, pytest, domain audits and the documented real `docker compose up -d --build --wait` verification.

## Complexity Tracking

No constitution violations; this section is intentionally unused.
