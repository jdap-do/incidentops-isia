---
description: "Task list for Hito 003: Ciclo de vida de incidentes y SLA"
---

# Tasks: Ciclo de vida de incidentes y SLA

**Input**: Design documents from `/specs/003-incident-lifecycle-sla/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Incluidas porque la especificación define criterios BDD y `quickstart.md` fija cinco escenarios obligatorios. Los cinco escenarios BDD se conservan sin cambios; los casos complementarios añaden cobertura pytest sin ampliar ese mapa.

**Organization**: Las tareas se agrupan por historia de usuario para permitir implementación y validación independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin depender de tareas incompletas)
- **[Story]**: Usuario al que pertenece la tarea (US1, US2, US3)
- Todas las descripciones incluyen rutas de archivo exactas

## Path Conventions

- Proyecto único: `src/`, `tests/` en la raíz del repositorio
- Documentación de la feature: `specs/003-incident-lifecycle-sla/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirmar la estructura y las compuertas existentes antes de tocar superficies compartidas.

- [X] T001 Verify Python >=3.10, `uv` dependency set, pytest configuration and Ruff configuration in `pyproject.toml` against the structure in `specs/003-incident-lifecycle-sla/plan.md`
- [X] T002 [P] Confirm layer import bans remain active in `pyproject.toml`, `src/domain/ruff.toml`, `src/application/ruff.toml` and `src/adapters/inbound/ruff.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Superficies compartidas que deben existir antes de cualquier historia de usuario.

**CRITICAL**: No iniciar trabajo de US1, US2 ni US3 hasta completar esta fase.

- [X] T003 Extend `Incident` in `src/domain/models.py` with `raw_text` and `duplicate_group_key` per data-model.md (`Incident.incident_id`, `Incident.title`, `Incident.raw_text`, `Incident.component`, `Incident.severity`, `Incident.status`, `Incident.created_at`, `Incident.resolved_at`, `Incident.duplicate_group_key`)
- [X] T004 Update `IncidentRepositoryPort` in `src/application/ports.py` for strict ID insertion and key-based duplicate lookup per data-model.md (`IncidentRepositoryPort.save_incident`, `IncidentRepositoryPort.get_incident`, `IncidentRepositoryPort.find_open_duplicates`, `IncidentRepositoryPort.list_active_incidents`, `IncidentRepositoryPort.check_health`, `DuplicateGroupKey.value`, `DuplicateGroupKey.open_statuses`, `DuplicateGroupKey.excluded_id`)
- [X] T005 Add `RegistrationInput`, `RegistrationResult`, `IncidentSnapshot`, `SLAStatusResult` and shared error values in `src/application/services.py` per data-model.md (`RegistrationInput.title`, `RegistrationInput.raw_text`, `RegistrationInput.incident_id`, `RegistrationInput.created_at`, `RegistrationInput.status`, `RegistrationResult.incident`, `RegistrationResult.duplicate_incident_ids`, `IncidentSnapshot.incident_id`, `IncidentSnapshot.title`, `IncidentSnapshot.component`, `IncidentSnapshot.severity`, `IncidentSnapshot.status`, `IncidentSnapshot.created_at`, `IncidentSnapshot.duplicate_group_key`, `SLAStatusResult.incident_id`, `SLAStatusResult.reference_time`, `SLAStatusResult.effective_time`, `SLAStatusResult.elapsed_minutes`, `SLAStatusResult.allowed_minutes`, `SLAStatusResult.remaining_minutes`, `SLAStatusResult.is_breached`, `SLAStatusResult.requires_escalation`, `ReferenceTime.raw`, `ReferenceTime.value`, `ReferenceTime.serialized`, `ReferenceTime.invalid_message`)
- [X] T006 Update SQLite schema, index, strict insert and duplicate lookup in `src/adapters/outbound/sqlite_repository.py` per data-model.md (`Incident.raw_text`, `Incident.duplicate_group_key`, `Incident.component`, `Incident.status`, `IncidentRepositoryPort.save_incident`, `IncidentRepositoryPort.find_open_duplicates`, `DuplicateGroupKey.value`, `DuplicateGroupKey.open_statuses`, `DuplicateGroupKey.excluded_id`)
- [X] T007 Create the shared `build_stack()` fixture for API/CLI parity in `tests/test_spec_003_lifecycle_sla.py` using the same repository, `IncidentService`, `create_api_app(service)` and `create_cli_app(service)`

**Checkpoint**: Foundation ready; user story implementation can now begin.

---

## Phase 3: User Story 1 - Registrar incidentes desde ambos canales (Priority: P1) MVP

**Goal**: Registrar un incidente de forma persistente desde REST y CLI usando solo `title` y `raw_text` como campos obligatorios, con defaults para ID, fecha y estado.

**Independent Test**: Registrar desde ambos canales y verificar que una consulta posterior por ID devuelve exactamente la vista acordada sin `raw_text` y que las respuestas REST y CLI coinciden.

### Tests for User Story 1

> Escribir primero y comprobar que fallan antes de implementar.

- [X] T008 [P] [US1] Add BDD scenario 1 for minimal registration, generated defaults, REST/CLI parity and ID lookup in `tests/test_spec_003_lifecycle_sla.py`
- [X] T009 [US1] Add complementary pytest cases for US1 acceptance scenarios 3-6 in `tests/test_spec_003_lifecycle_sla.py`: duplicate ID rejection, empty or whitespace-only `title`/`raw_text`, invalid `status`, severity derived from text instead of ID, explicit and generated `INC-<HEX8>` IDs, per `specs/003-incident-lifecycle-sla/spec.md`

### Implementation for User Story 1

- [X] T010 [US1] Implement `IncidentService.register_incident` in `src/application/services.py` resolving inputs and defaults per data-model.md (`RegistrationInput.title`, `RegistrationInput.raw_text`, `RegistrationInput.incident_id`, `RegistrationInput.created_at`, `RegistrationInput.status`, `Incident.component`, `Incident.severity`, `Incident.created_at`)
- [X] T011 [US1] Add unique `INC-<HEX8>` generation and duplicate-ID rejection in `src/application/services.py` per data-model.md (`Incident.incident_id`, `IncidentRepositoryPort.save_incident`)
- [X] T012 [P] [US1] Add REST request/response models in `src/adapters/inbound/api/schemas.py` per data-model.md (`IncidentSnapshot.incident_id`, `IncidentSnapshot.title`, `IncidentSnapshot.component`, `IncidentSnapshot.severity`, `IncidentSnapshot.status`, `IncidentSnapshot.created_at`, `IncidentSnapshot.duplicate_group_key`, `RegistrationResult.incident`, `RegistrationResult.duplicate_incident_ids`), exposing no `raw_text`
- [X] T013 [US1] Add `POST /api/v1/incidents` and `GET /api/v1/incidents/{incident_id}` in `src/adapters/inbound/api/app.py` mapping validation, duplicate and not-found errors
- [X] T014 [US1] Add `register` and `show` commands in `src/adapters/inbound/cli.py` with stdout JSON and stderr errors matching the REST contract
- [X] T015 [US1] Run scenario 1 and the US1 complementary cases from `tests/test_spec_003_lifecycle_sla.py` and confirm they pass only after US1 implementation

**Checkpoint**: US1 es funcional y testeable de forma independiente; este es el MVP.

---

## Phase 4: User Story 2 - Avisar de incidentes equivalentes abiertos (Priority: P2)

**Goal**: Avisar, al registrar, de los IDs en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` que comparten `duplicate_group_key`, sin incluir el registro propio ni incidentes `RESOLVED`.

**Independent Test**: Registrar un incidente con la misma clave que incidentes en esos tres estados y comprobar que el aviso enumera solo esos IDs, igual en REST y CLI.

### Tests for User Story 2

> Escribir primero y comprobar que fallan antes de implementar.

- [X] T016 [P] [US2] Add BDD scenario 2 for duplicate warning by key in `tests/test_spec_003_lifecycle_sla.py` with one `OPEN`, one `IN_PROGRESS`, one `ESCALATION_REQUIRED` and one `RESOLVED` equivalent, asserting the warning contains only the three non-resolved IDs and not the new ID
- [X] T017 [US2] Add complementary pytest cases for US2 acceptance scenarios 2-4 in `tests/test_spec_003_lifecycle_sla.py`: equivalent `ESCALATION_REQUIRED` inclusion, self exclusion, no equivalent in `OPEN`/`IN_PROGRESS`/`ESCALATION_REQUIRED`, and same title with different `duplicate_group_key`, per `specs/003-incident-lifecycle-sla/spec.md`

### Implementation for User Story 2

- [X] T018 [US2] Wire key-based duplicate lookup into `register_incident` in `src/application/services.py` per data-model.md (`DuplicateGroupKey.value`, `TriageResult.duplicate_group_key`, `DuplicateGroupKey.open_statuses`, `DuplicateGroupKey.excluded_id`, `RegistrationResult.duplicate_incident_ids`, `IncidentRepositoryPort.find_open_duplicates`), including `OPEN`, `IN_PROGRESS` and `ESCALATION_REQUIRED`, excluding `RESOLVED` and the new incident
- [X] T019 [US2] Include `duplicate_incident_ids` in the REST registration response in `src/adapters/inbound/api/schemas.py` and `src/adapters/inbound/api/app.py` per data-model.md (`RegistrationResult.duplicate_incident_ids`)
- [X] T020 [US2] Include `duplicate_incident_ids` in CLI `register` output in `src/adapters/inbound/cli.py` per data-model.md (`RegistrationResult.duplicate_incident_ids`)
- [X] T021 [US2] Run scenario 2 and the US2 complementary cases from `tests/test_spec_003_lifecycle_sla.py` and confirm REST and CLI warnings are identical

**Checkpoint**: US1 y US2 funcionan de forma independiente y el aviso no altera el registro.

---

## Phase 5: User Story 3 - Consultar el estado del SLA en una fecha de referencia (Priority: P3)

**Goal**: Consultar el SLA de un incidente registrado con `reference_time` opcional para quien llama, devolviendo minutos, límite, restante, incumplimiento y escalamiento.

**Independent Test**: Registrar un incidente, consultar su SLA desde ambos canales y verificar los valores de política, incluido P2 viernes 17:00 a lunes 09:00 con 120 minutos hábiles transcurridos y 360 restantes.

### Tests for User Story 3

> Escribir primero y comprobar que fallan antes de implementar.

- [X] T022 [US3] Add BDD scenarios 3, 4 and 5 in `tests/test_spec_003_lifecycle_sla.py`, including the P2 Friday 17:00 to Monday 09:00 case with 120 elapsed and 360 remaining minutes
- [X] T023 [US3] Add complementary pytest cases for US3 acceptance scenarios 4-6 and the 75 % escalation threshold in `tests/test_spec_003_lifecycle_sla.py`: `resolved_at` precedence, timezone-aware or pre-creation `reference_time`, unknown ID, and 75 % escalation without breach, per `specs/003-incident-lifecycle-sla/spec.md`

### Implementation for User Story 3

- [X] T024 [US3] Implement `IncidentService.get_incident_sla` in `src/application/services.py` using existing domain evaluation per data-model.md (`ReferenceTime.raw`, `ReferenceTime.value`, `ReferenceTime.serialized`, `ReferenceTime.invalid_message`, `SLAStatusResult.incident_id`, `SLAStatusResult.reference_time`, `SLAStatusResult.effective_time`, `SLAStatusResult.elapsed_minutes`, `SLAStatusResult.allowed_minutes`, `SLAStatusResult.remaining_minutes`, `SLAStatusResult.is_breached`, `SLAStatusResult.requires_escalation`, `SLARule.max_resolution_minutes`, `SLARule.operates_24x7`, `SLARule.escalation_threshold_ratio`, `SLAEvaluation.elapsed_minutes`, `SLAEvaluation.is_breached`, `SLAEvaluation.requires_escalation`, `Incident.resolved_at`, `IncidentRepositoryPort.get_incident`)
- [X] T025 [US3] Add SLA response models in `src/adapters/inbound/api/schemas.py` per data-model.md (`SLAStatusResult.incident_id`, `SLAStatusResult.reference_time`, `SLAStatusResult.effective_time`, `SLAStatusResult.elapsed_minutes`, `SLAStatusResult.allowed_minutes`, `SLAStatusResult.remaining_minutes`, `SLAStatusResult.is_breached`, `SLAStatusResult.requires_escalation`)
- [X] T026 [US3] Add `GET /api/v1/incidents/{incident_id}/sla` with optional `reference_time` and shared 404/422 errors in `src/adapters/inbound/api/app.py`
- [X] T027 [US3] Add `sla` command with optional `--reference-time` in `src/adapters/inbound/cli.py` using the same parser and error message as REST
- [X] T028 [US3] Run scenarios 3, 4 and 5 plus the US3 complementary cases from `tests/test_spec_003_lifecycle_sla.py` and confirm identical JSON in REST and CLI

**Checkpoint**: Todas las historias son funcionales y testeables de forma independiente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Verificación integral, regresiones, rendimiento, volumen y fronteras arquitectónicas.

- [X] T029 Run full `uv run pytest -v` and `uv run ruff check .` gates from the repository root following `specs/003-incident-lifecycle-sla/quickstart.md`
- [X] T030 Run triage, SLA and both context-audit regression commands from `specs/003-incident-lifecycle-sla/quickstart.md` without `python -O`
- [X] T031 [P] Review final import boundaries in `src/domain/ruff.toml`, `src/application/ruff.toml` and `src/adapters/inbound/ruff.toml` so no business rule or SQLite import leaks into adapters or application
- [X] T032 [P] Validate final REST/CLI parity and the five BDD scenario map against `specs/003-incident-lifecycle-sla/quickstart.md`, `specs/003-incident-lifecycle-sla/contracts/rest-lifecycle-sla.md` and `specs/003-incident-lifecycle-sla/contracts/cli-lifecycle-sla.md`
- [X] T033 Add a pytest timing case in `tests/test_spec_003_lifecycle_sla.py` for SC-005 in `specs/003-incident-lifecycle-sla/spec.md`: registration, duplicate warning and SLA consultation each observable in one interaction and under 30 seconds; treat the 95 % operator target as a post-launch KPI
- [X] T034 Add a pytest volume case in `tests/test_spec_003_lifecycle_sla.py` for SC-006 in `specs/003-incident-lifecycle-sla/spec.md`: at least 1.000 incidents in `OPEN`, `IN_PROGRESS` or `ESCALATION_REQUIRED` with the same `duplicate_group_key`, complete warning list and no duplicate IDs in REST and CLI

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Sin dependencias; puede iniciar de inmediato
- **Foundational (Phase 2)**: Depende de Setup; bloquea todas las historias
- **User Stories (Phase 3-5)**: Dependen de Foundational; ejecutar en orden P1 → P2 → P3 para MVP incremental
- **Polish (Phase 6)**: Depende de las historias incluidas

### User Story Dependencies

- **User Story 1 (P1)**: Puede empezar tras Foundational; sin dependencias de otras historias
- **User Story 2 (P2)**: Depende del resultado de registro de US1 para el aviso, pero es testeable de forma independiente una vez completas Foundational y US1
- **User Story 3 (P3)**: Depende de un incidente registrado, pero su caso de uso y contrato son independientes; puede ejecutarse tras US1 o en paralelo si otro agente siembra datos por el puerto

### Within Each User Story

- Tests primero, con fallo esperado antes de la implementación
- Casos complementarios antes que la implementación; ejecución de cada historia al final de su fase
- Modelos y DTOs antes que servicios
- Servicios antes que endpoints o comandos
- Core antes que integración
- No marcar una historia como completa hasta ejecutar su escenario independiente y sus casos complementarios

### Parallel Opportunities

- T002 puede ejecutarse mientras T001 valida el proyecto base
- T008 y T012 pueden ejecutarse en paralelo porque escriben archivos distintos tras Foundational
- T016 y T020 pueden ejecutarse en paralelo porque escriben archivos distintos tras la implementación de US2
- T025 y T027 pueden ejecutarse en paralelo porque escriben archivos distintos tras T024
- T031 y T032 pueden ejecutarse en paralelo porque revisan artefactos distintos
- T033 debe preceder a T034 porque ambas escriben `tests/test_spec_003_lifecycle_sla.py`; secuenciar las ediciones de ese archivo

---

## Parallel Example: User Story 1

```text
Task: "Add BDD scenario 1 for minimal registration in tests/test_spec_003_lifecycle_sla.py"
Task: "Add REST request/response models in src/adapters/inbound/api/schemas.py"
```

---

## Parallel Example: User Story 2

```text
Task: "Add BDD scenario 2 for duplicate warning in tests/test_spec_003_lifecycle_sla.py"
Task: "Include duplicate_incident_ids in CLI register output in src/adapters/inbound/cli.py"
```

---

## Parallel Example: User Story 3

```text
Task: "Add SLA response models in src/adapters/inbound/api/schemas.py"
Task: "Add CLI sla command in src/adapters/inbound/cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 1 y Phase 2
2. Completar Phase 3 (US1)
3. Detener y validar el escenario 1 y los casos complementarios de US1 de forma independiente
4. Demo del registro persistente con paridad REST/CLI

### Incremental Delivery

1. Setup + Foundational → base lista
2. US1 → registro mínimo y paridad → MVP
3. US2 → aviso por `duplicate_group_key`
4. US3 → consulta de SLA con los cinco escenarios BDD y casos complementarios
5. Cada historia conserva las anteriores sin cambiar sus contratos

### Parallel Team Strategy

- Un agente completa Setup y Foundational
- Después, agentes distintos pueden trabajar en US1, US2 y US3 siempre que compartan el mismo servicio y respeten el orden de dependencias descrito

---

## Notes

- `[P]` significa archivos distintos y sin dependencias de tareas incompletas
- `[US1]`, `[US2]` y `[US3]` trazan cada tarea con su historia
- Todas las citas de campos apuntan a `data-model.md` con nombres exactos `Entity.field`
- Los cinco escenarios BDD de `specs/003-incident-lifecycle-sla/quickstart.md` no cambian; T009, T017, T023, T033 y T034 son casos pytest complementarios
- La búsqueda de duplicados incluye `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED`, y excluye `RESOLVED` y el incidente recién registrado; el alta sigue aceptando solo `OPEN` o `IN_PROGRESS`, con `OPEN` por defecto
- SC-005 se verifica en T033 solo para el límite de 30 segundos; el 95 % de operadores es un KPI operativo posterior
- No optimizar `src/incident_repository.py`: su escaneo completo y N+1 son deuda intencional
- No ejecutar auditoría SLA con `python -O`
- Reportar resultados de compuertas solo después de ejecutarlos desde la raíz del repositorio
