# Implementation Plan: Resumen de incidentes activos

**Branch**: `002-resumen-incidentes-activos` | **Date**: 2026-11-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-resumen-incidentes-activos/spec.md`

## Summary

Un único caso de uso de aplicación, `IncidentService.get_active_incidents_summary`, consulta los incidentes activos a través de `IncidentRepositoryPort`, reutiliza `evaluate_sla_status` del dominio y produce totales, conteo de incumplimientos y detalle ordenado. REST y CLI capturan o validan `reference_time` antes de invocar el servicio, le pasan un `datetime` explícito y serializan el mismo DTO; SQLite es un adaptador de salida detrás del puerto.

La consulta SQLite filtra por estado y componente antes de materializar filas, elimina la consulta N+1 a `sla_policies` y deja el cálculo SLA exclusivamente en el dominio. Todo el código SQLite de este feature queda confinado a `src/adapters/outbound/sqlite_repository.py`.

## Technical Context

**Language/Version**: Python >=3.10, gestionado con `uv`.

**Primary Dependencies**: FastAPI y Pydantic v2 para REST; Typer para CLI; `sqlite3` de biblioteca estándar para persistencia; `pytest` y `httpx` para pruebas; Ruff >=0.17.6 para fronteras de imports.

**Storage**: SQLite. La fábrica por `DATABASE_URL` usa SQLite en memoria por defecto (`sqlite:///:memory:`); los adaptadores nuevos leen y escriben las columnas existentes de `incidents`.

**Testing**: `pytest` con `TestClient` y `CliRunner`; criterios BDD en `tests/test_spec_002_summary.py`; se conservan las pruebas de `tests/test_spec_001_triage.py`.

**Target Platform**: Proceso Python local que expone una API HTTP y una CLI; sin plataforma de despliegue nueva.

**Project Type**: Servicio web + CLI en un único paquete Python, organizado con arquitectura hexagonal.

**Performance Goals**: Devuelve hasta 1.000 incidentes activos sin omisiones ni duplicados; evita escaneo completo y N+1 en la consulta del resumen; mantiene determinismo para el mismo instante de referencia.

**Constraints**: SLA según ADR-002; incumplimiento solo con `elapsed > allowed`; escalamiento desde el 75 % y persistente tras el vencimiento; `reference_time: datetime` naive local, explícito en el servicio y capturado por el adaptador si se omite; rechazo de valores malformados, tz-aware o anteriores a `created_at`; filtro por componente sin distinguir mayúsculas ni espacios circundantes; orden P0→P3, minutos descendentes y título ascendente; paridad REST/CLI; sin lógica de negocio en adaptadores; sin festivos ni zonas horarias.

**Scale/Scope**: Alcance limitado a consultar incidentes `OPEN` e `IN_PROGRESS` desde los canales existentes; sin autenticación, channels nuevos, paginación, nuevos estados ni cambio de motor de persistencia.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Pre-design result | Evidence |
|---|---|---|
| I. Dominio determinista | PASS | El servicio llama a `evaluate_sla_status` con un `reference_time: datetime` recibido; minutos, incumplimiento y escalamiento se derivan del dominio, sin reloj dentro de aplicación. |
| II. Un solo caso de uso para REST y CLI | PASS | Ambos adaptadores validan o capturan `reference_time`, invocan `IncidentService.get_active_incidents_summary` y serializan el mismo DTO. |
| III. Persistencia detrás de un puerto | PASS | `IncidentRepositoryPort` vive en `src/application/` como `Protocol`; el servicio no importa SQLite ni adaptadores. |
| IV. SQLite como adaptador inicial | PASS | Todo `sqlite3`, SQL y `DATABASE_URL` de este feature quedan confinados en `src/adapters/outbound/`; no se reutiliza código SQLite fuera de ese adaptador. |
| V. Criterios BDD y fronteras verificadas | PASS | Cuatro escenarios BDD con cobertura REST/CLI en `tests/test_spec_002_summary.py`; Ruff TID251/TID252 con configuración por capa. |

**Pre-design gate**: PASS. No hay violaciones que justificar.

**Post-design re-check**: PASS. `data-model.md` mantiene las reglas en dominio/aplicación y el `datetime` explícito, los contratos describen adaptadores delgados que resuelven la omisión y `quickstart.md` incluye `uv run pytest` y `uv run ruff check .` como compuertas. No se introduce deuda ni excepción arquitectónica.

## Project Structure

### Documentation (this feature)

```text
specs/002-resumen-incidentes-activos/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── rest-summary.md
│   └── cli-summary.md
└── tasks.md
```

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
├── adapters/
│   ├── __init__.py
│   ├── inbound/
│   │   ├── __init__.py
│   │   ├── ruff.toml
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   └── schemas.py
│   │   └── cli.py
└── outbound/
    ├── __init__.py
    └── sqlite_repository.py

tests/
├── test_spec_001_triage.py
└── test_spec_002_summary.py

pyproject.toml
```

**Structure Decision**: Se conserva el paquete único y se usa el layout hexagonal obligatorio. `src/bootstrap.py` es la raíz de composición: construye el adaptador SQLite y lo inyecta en `IncidentService`. Los adaptadores de entrada reciben el servicio, resuelven `reference_time` antes de llamarlo y nunca importan el adaptador de salida. La deuda SQLite preexistente queda fuera del alcance de este hito.

## Complexity Tracking

No violations; no complexity exceptions required.

## Phase 0: Outline & Research

No quedan marcadores `NEEDS CLARIFICATION` en la especificación ni en el contexto técnico. Las decisiones técnicas se consolidan en [research.md](./research.md):

- Fábrica SQLite y superficie de `IncidentRepositoryPort`.
- Consulta filtrada e índices para reemplazar escaneo completo y N+1.
- Contrato compartido REST/CLI y manejo de `reference_time`.
- Configuración Ruff por capa con TID251/TID252.
- Estrategia de pruebas BDD que confina el SQLite del feature al adaptador de salida.

**Gate after research**: PASS. La constitución sigue sin violaciones.

## Phase 1: Design & Contracts

### Data model

[ data-model.md ](./data-model.md) define las entidades y reglas:

- `ActiveIncident`: incidente devuelto por el puerto con los campos existentes de `Incident`.
- `ActiveIncidentDetail`: vista derivada con seis campos observables.
- `ActiveIncidentSummary`: total, incumplimientos, instante, filtro normalizado y detalle ordenado.
- `ComponentFilter`: filtro opcional normalizado por el servicio.
- `IncidentRepositoryPort`: contrato de persistencia con cinco operaciones.

### Contracts

- [ REST summary contract ](./contracts/rest-summary.md): `GET /api/v1/incidents/summary`, parámetros, respuesta, captura de `reference_time` y errores 422.
- [ CLI summary contract ](./contracts/cli-summary.md): comando `summary`, opciones, JSON en stdout, captura de `reference_time` y errores.

Ambos contratos comparten la misma forma de respuesta y el mismo mensaje de error para garantizar paridad, incluido el rechazo de `reference_time` inválido.

### Quickstart

[ quickstart.md ](./quickstart.md) describe cómo ejecutar y validar el feature desde la raíz del repo, incluidas las compuertas `uv run pytest` y `uv run ruff check .`, sin incluir código de implementación.

**Gate after Phase 1**: PASS. No hay cambios a ADR, ni nuevos estados, ni excepciones a las fronteras.
