# Implementation Tasks: Resumen de incidentes activos

**Feature**: `specs/002-resumen-incidentes-activos/spec.md`
**Input**: Documentos de diseño de Hito 002
**Generated**: 2026-11-20
**Feature branch**: `002-resumen-incidentes-activos`

**Total tasks**: 24 | US1: 4 | US2: 2 | US3: 3

**Format**: `- [X] [TaskID] [P?] [Story?] Descripción con ruta de archivo`

## Phase 1: Setup

- [X] [T001] [P] Create `src/application/ports.py` with `IncidentRepositoryPort` as a `typing.Protocol`; cite `IncidentRepositoryPort` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T002] Configure Ruff in `pyproject.toml` with `select = ["E4", "E7", "E9", "F", "TID251", "TID252"]` and `ban-relative-imports = "parents"`; add `src/domain/ruff.toml`, `src/application/ruff.toml` and `src/adapters/inbound/ruff.toml` with the layer-specific bans declared in `specs/002-resumen-incidentes-activos/research.md`.
- [X] [T003] [P] Update `src/domain/models.py` with immutable `ActiveIncidentDetail` and `ActiveIncidentSummary` DTOs plus the six observable detail fields; cite `ActiveIncidentDetail` and `ActiveIncidentSummary` in `specs/002-resumen-incidentes-activos/data-model.md`.

## Phase 2: Core application and user scenarios

### US1: Ver resumen activo con totales y detalle (priority: P1)

- [X] [T004] [US1] Add `IncidentRepositoryPort.list_active_incidents(component_filter: str | None = None) -> list[Incident]` to `src/application/ports.py`; cite `IncidentRepositoryPort.list_active_incidents` and `ActiveIncident.status` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T005] [P] [US1] Create `src/adapters/outbound/sqlite_repository.py` implementing `IncidentRepositoryPort` with a single filtered `INNER JOIN sla_policies`, `CREATE INDEX IF NOT EXISTS idx_incidents_component_status`, canonical component matching and no N+1 queries; cite `Incident`, `IncidentRepositoryPort.list_active_incidents` and `ActiveIncident.status` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T006] [US1] Add `IncidentService.get_active_incidents_summary(component_filter: str | None, reference_time: datetime)` to `src/application/services.py`; require an explicit `reference_time`, normalize the filter via `ComponentFilter`, call `evaluate_sla_status`, aggregate `total_active` and `breached_count`, and return `ActiveIncidentSummary`; cite `ComponentFilter.normalized`, `ReferenceTime.value`, `ActiveIncidentDetail` and `ActiveIncidentSummary` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T007] [US1] Add `GET /api/v1/incidents/summary` to `src/adapters/inbound/api/app.py` with Pydantic response models in `src/adapters/inbound/api/schemas.py`; call the shared `reference_time` parser, pass an explicit `datetime` to the service and serialize the same DTO as CLI; cite `ActiveIncidentSummary` and `ReferenceTime.serialized` in `specs/002-resumen-incidentes-activos/data-model.md`.

### Core app integration and remaining scenarios

- [X] [T008] Add `incidentops summary` to `src/adapters/inbound/cli.py` with `--component` and `--reference-time`, the shared `reference_time` parser, JSON on `stdout` and the same success output as REST; cite `ActiveIncidentSummary` and `ReferenceTime.serialized` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T009] Add BDD parity tests in `tests/test_spec_002_summary.py` using `TestClient` and `CliRunner` to compare totals, counts, six detail fields and ordering for the same explicit `reference_time`, covering mixed states and component filtering; cite `ActiveIncidentSummary.details` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T010] [US2] Enforce deterministic ordering in `src/application/services.py`: severity P0→P3, `elapsed_minutes` descending, then `title` ascending; cite `ActiveIncidentSummary.details` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T011] [US2] Extend `tests/test_spec_002_summary.py` with pending, canonical, blank, unknown and equivalent mixed-case/spaced component filters, asserting totals and rows are scoped to the subset; cite `ComponentFilter.raw` and `ComponentFilter.normalized` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T012] [US3] Add `parse_reference_time` to `src/application/services.py` for shared ISO-8601 local-naive validation, including `created_at` checks; do not default to `datetime.now()` there; cite `ReferenceTime.value` and `ReferenceTime.invalid_message` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T013] [US3] Map invalid `reference_time` to HTTP 422 with `detail` in `src/adapters/inbound/api/app.py` and to exit code 1 with empty `stdout` plus the same message on `stderr` in `src/adapters/inbound/cli.py`, without returning partial summaries; cite `ReferenceTime.invalid_message` in `specs/002-resumen-incidentes-activos/data-model.md`.
- [X] [T014] [US3] Extend `tests/test_spec_002_summary.py` with omitted, malformed, tz-aware and too-early `reference_time` cases, asserting adapter capture of the omitted instant and identical rejection messages across REST and CLI; cite `ReferenceTime.value` and `ReferenceTime.invalid_message` in `specs/002-resumen-incidentes-activos/data-model.md`.

## Phase 3: Composition and polish

- [X] [T015] Create `src/bootstrap.py` with `build_incident_service()` that constructs `src/adapters/outbound/sqlite_repository.py` and injects it into `IncidentService`; keep module-level `app` and CLI wiring pointing to the composed service.
- [X] [T016] [P] Add docstrings to `src/application/ports.py`, `src/application/services.py`, `src/adapters/outbound/sqlite_repository.py`, `src/adapters/inbound/api/app.py` and `src/adapters/inbound/cli.py` describing the explicit `reference_time` boundary and the outbound-only SQLite boundary.
- [X] [T017] [P] Review `src/domain/ruff.toml`, `src/application/ruff.toml` and `src/adapters/inbound/ruff.toml` against the decisions in `specs/002-resumen-incidentes-activos/research.md`; confirm no inbound-to-outbound or application-to-adapter imports exist.
- [X] [T018] [P] Verify `AGENTS.md` and `docs/adr/002-calculo-sla-horario-habil.md` remain unchanged; confirm `evaluate_sla_status` is the only SLA calculation used by `src/application/services.py`.

## Phase 4: Validation gates

- [X] [T019] Run `uv run ruff check .` from the repository root after T002 and report the result.
- [X] [T020] Confirm `uv run python -m src.triage_rules`, `uv run python -m src.sla_calculator` and both `uv run python -m src.context_audit` commands still pass after T018; report each result.
- [X] [T021] Extend `test_active_summary_matches_across_rest_and_cli` in `tests/test_spec_002_summary.py` with a subcase that seeds 1.000 active incidents via `save_incident` and asserts `total_active == len(details) == 1000`, unique rows, and REST/CLI parity for SC-006.
- [X] [T022] Run the full suite with `uv run pytest` from the repository root and report the complete result; do not run a subset of test files.
- [X] [T023] Run `uv run ruff check .` from the repository root after T015–T021 and report the complete result.
- [X] [T024] Update `specs/002-resumen-incidentes-activos/quickstart.md` with the commands and results verified by T021, T022 and T023.

## Dependencies

- T001 → T002, T004; T003 → T006, T012.
- T004 → T005, T006; T006 → T007, T008, T010.
- T012 → T007, T008, T013; T007 → T008; T008 → T009.
- T009 → T011, T014, T021; T010 → T011; T013 → T014.
- T005, T007, T008, T010, T012, T013, T014 → T015.
- T015 → T016, T017, T018; T002 → T017, T019.
- T018 → T020; T021 → T022, T023; T022 + T023 → T024.

## Parallel Opportunities

- T001 and T003 can run in parallel; T002 starts after T001.
- T005, T010 and T012 can run in parallel after their dependencies; T007 and T008 remain sequential because the CLI mirrors the REST contract.
- T016, T017, T018 and T020 can run in parallel after T015.
- T022 and T023 can run in parallel after T021 and all implementation tasks; T024 follows both.

## Implementation Strategy

1. Phase 1 establishes the port, DTOs and per-layer Ruff boundaries, keeping all feature SQLite code in `src/adapters/outbound/sqlite_repository.py`.
2. Phase 2 delivers US1 first with a single explicit-`reference_time` service used by both channels, then fills US2 ordering and US3 validation without duplicating business rules.
3. Phase 3 wires composition, docs and boundary reviews without changing Hito 001 behavior, ADR-002 or ADR-003.
4. Phase 4 verifies SC-006, then runs the complete `uv run pytest` suite and `uv run ruff check .` before recording results in `quickstart.md`.

## Notes

- `[P]` = parallelizable; `[USn]` = user story association.
- Every test case MUST be expressed in Given/When/Then form and use `TestClient` or `CliRunner`.
- `reference_time` is always explicit inside `IncidentService`; inbound adapters capture it only when the operator omits it, and both channels reject malformed, tz-aware or too-early values with the same message before any summary is calculated.
- All feature SQLite code stays in `src/adapters/outbound/sqlite_repository.py`; no feature code imports or repoints pre-existing repository code outside that adapter.
- Do not change `src/domain/sla_calculator.py`, `AGENTS.md`, `docs/adr/002-calculo-sla-horario-habil.md`, `docs/adr/003-arquitectura-hexagonal.md` or `tests/test_spec_001_triage.py`.
- `uv run pytest` is the full validation gate; running only `tests/test_spec_001_triage.py` and `tests/test_spec_002_summary.py` is not sufficient.
