# Implementation Plan: Ciclo de vida de incidentes y SLA

**Branch**: `003-incident-lifecycle-sla` | **Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-incident-lifecycle-sla/spec.md`

La entrada de planificación del usuario precisa la spec aclarada: `title` y `raw_text` son los únicos campos obligatorios; `incident_id`, `created_at` y `status` son opcionales; el aviso usa `duplicate_group_key`; y `reference_time` es opcional para quien consulta. Estas precisiones ya están incorporadas en `spec.md` y resueltas en [research.md](./research.md).

## Summary

Tres casos de uso en `IncidentService` —registro persistente, consulta por ID y consulta de SLA— son invocados por REST y CLI a través de los mismos DTOs y mensajes de error. El registro deriva componente, severidad y `duplicate_group_key` desde `raw_text` con `classify_incident_report`, aplica defaults para ID, fecha y estado, guarda mediante `IncidentRepositoryPort` y devuelve los IDs en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` que comparten clave, excluyendo `RESOLVED` y el propio incidente. La consulta de SLA delega el cálculo en `evaluate_sla_status`; los adaptadores capturan `reference_time` cuando falta y el servicio siempre recibe un `datetime` explícito.

Se reutilizan `IncidentService`, `IncidentRepositoryPort`, `SQLiteIncidentRepository`, `bootstrap.py`, `parse_reference_time` y las compuertas del Hito 002. La persistencia gana `raw_text` y `duplicate_group_key`, un índice por clave e inserción estricta por ID. `tasks.md` ya fue generado con `/speckit.tasks` y corregido tras `/speckit.analyze`; este plan no crea código de implementación.

## Technical Context

**Language/Version**: Python >=3.10, gestionado con `uv`.

**Primary Dependencies**: FastAPI y Pydantic v2 para REST; Typer para CLI; `sqlite3` de biblioteca estándar para persistencia; `pytest` y `httpx` para pruebas; Ruff >=0.17.6 para fronteras de imports.

**Storage**: SQLite detrás de `IncidentRepositoryPort`. Se extienden la tabla `incidents` y el modelo `Incident` con `raw_text` y `duplicate_group_key`, y se añade un índice por `(duplicate_group_key, status, incident_id)`. La fábrica existente mantiene `sqlite:///:memory:` por defecto.

**Testing**: `pytest` con `TestClient` y `CliRunner`; cinco escenarios BDD inmutables en `tests/test_spec_003_lifecycle_sla.py`, más casos complementarios de rutas negativas, 75 %, `resolved_at`, referencia inválida, ID inexistente, rendimiento <30 s y volumen de 1.000 incidentes; se conservan `tests/test_spec_001_triage.py` y `tests/test_spec_002_summary.py`.

**Target Platform**: Proceso Python local que expone una API HTTP y una CLI; sin despliegue nuevo.

**Project Type**: Servicio web + CLI en un único paquete Python con arquitectura hexagonal.

**Performance Goals**: Aviso completo y sin duplicados con al menos 1.000 incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED`, verificado por T034; registro, aviso y SLA observables en menos de 30 segundos, verificado por T033; paridad estricta REST/CLI.

**Constraints**: ADR-002 gobierna el SLA; ADR-003 gobierna las fronteras; la severidad y la clave de correlación se derivan del texto normalizado, nunca del ID; `created_at` y `reference_time` se resuelven en el adaptador y llegan explícitos al servicio; sin lógica de negocio en adaptadores; sin festivos ni zonas horarias; `INSERT` estricto por ID; sin autenticación ni nuevos estados.

**Scale/Scope**: Registro desde ambos canales, aviso por `duplicate_group_key`, consulta por ID y consulta de SLA con `reference_time` opcional. Quedan fuera cambios de estado posteriores al alta, motores de persistencia nuevos, paginación, autenticación y optimización de la deuda SQLite preexistente.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Pre-design result | Evidence |
|---|---|---|
| I. Dominio determinista | PASS | `classify_incident_report` deriva severidad, componente y `duplicate_group_key`; `evaluate_sla_status` calcula minutos, incumplimiento y escalamiento; el servicio recibe fechas explícitas y no lee el reloj. |
| II. Un solo caso de uso para REST y CLI | PASS | `register_incident`, `get_incident` y `get_incident_sla` viven en `IncidentService`; REST y CLI solo validan, capturan instantes y serializan los mismos DTOs. |
| III. Persistencia detrás de un puerto | PASS | El servicio depende solo de `IncidentRepositoryPort`; no importa `sqlite3`, SQL ni adaptadores; la búsqueda de duplicados pasa por el puerto. |
| IV. SQLite como adaptador inicial | PASS | Todo cambio de esquema, índice e inserción queda en `src/adapters/outbound/sqlite_repository.py`; no se introduce otro motor. |
| V. Criterios BDD y fronteras verificadas | PASS | Cinco escenarios Given/When/Then con comparación `response.json() == json.loads(result.stdout)`; `uv run pytest` y `uv run ruff check .` como compuertas. |

**Pre-design gate**: PASS. No hay violaciones que justificar.

**Post-design re-check**: PASS. [data-model.md](./data-model.md) mantiene las reglas en dominio y aplicación con fechas explícitas, define las identidades exactas de `SLARule` y `SLAEvaluation` y fija los estados del aviso de duplicados; los contratos describen adaptadores delgados y errores compartidos; [quickstart.md](./quickstart.md) fija los cinco escenarios BDD, incluido P2 viernes 17:00 a lunes 09:00 con 120 minutos hábiles y 360 restantes. La revisión posterior a `/speckit.tasks` preserva esos cinco escenarios, aclara la vista de confirmación, `resolved_at` y los estados no `RESOLVED`, y añade cobertura explícita para SC-005 y SC-006. No se requiere ADR ni excepción arquitectónica.

## Project Structure

### Documentation (this feature)

```text
specs/003-incident-lifecycle-sla/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── rest-lifecycle-sla.md
│   └── cli-lifecycle-sla.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

`tasks.md` fue generado con `/speckit.tasks` y se mantiene como lista ejecutable; este plan no lo genera.

### Source Code (repository root)

```text
src/
├── bootstrap.py
├── domain/
│   ├── __init__.py
│   ├── models.py
│   ├── sla_calculator.py
│   ├── triage_rules.py
│   └── ruff.toml
├── application/
│   ├── __init__.py
│   ├── ports.py
│   ├── services.py
│   └── ruff.toml
└── adapters/
    ├── __init__.py
    ├── inbound/
    │   ├── __init__.py
    │   ├── ruff.toml
    │   ├── api/
    │   │   ├── __init__.py
    │   │   ├── app.py
    │   │   └── schemas.py
    │   └── cli.py
    └── outbound/
        ├── __init__.py
        └── sqlite_repository.py

tests/
├── test_spec_001_triage.py
├── test_spec_002_summary.py
└── test_spec_003_lifecycle_sla.py

pyproject.toml
```

**Structure Decision**: Se conserva el paquete único y el layout hexagonal obligatorio. `src/bootstrap.py` sigue siendo la raíz de composición; los adaptadores de entrada reciben `IncidentService` y no importan el adaptador de salida. El modelo, el puerto, el servicio, los adaptadores y las pruebas se extienden en los archivos existentes indicados; la deuda SQLite preexistente queda fuera de alcance.

## Complexity Tracking

No violations; no complexity exceptions required.

## Phase 0: Outline & Research

No quedan marcadores `NEEDS CLARIFICATION` en la especificación ni en el contexto técnico. Las decisiones se consolidan en [research.md](./research.md):

- Campos obligatorios y opcionales del alta, derivación desde `raw_text` y defaults.
- Extensión del modelo, del esquema SQLite y de la semántica de `find_open_duplicates`.
- Tres casos de uso compartidos por REST y CLI.
- `reference_time` opcional en adaptadores y explícito en el servicio.
- Contratos espejo y estrategia BDD con cinco escenarios.

**Gate after research**: PASS. La constitución sigue sin violaciones.

## Phase 1: Design & Contracts

### Data model

[data-model.md](./data-model.md) define:

- `Incident` extendido con `raw_text` y `duplicate_group_key`.
- `RegistrationResult`, `IncidentSnapshot` y `SLAStatusResult` como DTOs de aplicación.
- Reglas de alta, unicidad de ID, equivalencia por clave y evaluación SLA.
- Semántica actualizada de `IncidentRepositoryPort.find_open_duplicates`.

### Contracts

- [REST lifecycle/SLA contract](./contracts/rest-lifecycle-sla.md): `POST /api/v1/incidents`, `GET /api/v1/incidents/{incident_id}` y `GET /api/v1/incidents/{incident_id}/sla`.
- [CLI lifecycle/SLA contract](./contracts/cli-lifecycle-sla.md): `incidentops register`, `incidentops show` y `incidentops sla`.

Ambos contratos comparten forma de respuesta, mensajes de error y resolución de `reference_time` para garantizar paridad REST/CLI.

### Quickstart

[quickstart.md](./quickstart.md) describe compuertas, validación por REST y CLI y el mapa de los cinco escenarios BDD, incluido el caso P2 de viernes 17:00 a lunes 09:00 con 120 minutos hábiles transcurridos y 360 restantes. No contiene código de implementación.

**Gate after Phase 1**: PASS. No hay cambios de ADR, nuevos estados ni excepciones a las fronteras.

## Post-Task Analysis Corrections

Tras `/speckit.analyze`, se conservan el alcance acordado y los cinco escenarios BDD de [quickstart.md](./quickstart.md); los casos añadidos son complementarios y no amplían ese mapa.

- A1: la confirmación y la consulta devuelven solo la vista acordada (`incident_id`, `title`, `component`, `severity`, `status`, `created_at` y `duplicate_group_key`); `raw_text` se persiste pero no se expone.
- A2: `resolved_at` no se acepta en el alta; solo puede existir en registros sembrados o futuros y prevalece sobre la referencia al evaluar SLA.
- A3: el escalamiento se conserva mientras el estado no sea `RESOLVED` (`OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED`); el aviso de equivalentes usa los mismos tres estados, excluye `RESOLVED` y el incidente recién registrado, y no cambia los estados aceptados en el alta (`OPEN` e `IN_PROGRESS`, con `OPEN` por defecto).
- C1: T033 verifica el límite de 30 segundos de SC-005 en registro, aviso y consulta de SLA; el 95 % de operadores queda como KPI operativo posterior.
- C2: T034 verifica SC-006 con al menos 1.000 incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` y aviso completo sin duplicados.
- C3-C5: T009, T017 y T023 añaden cobertura pytest complementaria para los escenarios de aceptación previamente sin tarea; T015, T021 y T028 ejecutan esas verificaciones sin crear nuevos escenarios BDD.
- C6: [data-model.md](./data-model.md) define ahora las identidades exactas `SLARule.max_resolution_minutes`, `SLARule.operates_24x7`, `SLARule.escalation_threshold_ratio`, `SLAEvaluation.elapsed_minutes`, `SLAEvaluation.is_breached` y `SLAEvaluation.requires_escalation`, citadas por T024.
