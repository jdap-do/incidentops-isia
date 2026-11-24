# Quickstart: Ciclo de vida de incidentes y SLA

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md)

Este documento es una guía de validación posterior a `/speckit.implement`. Este paso de planificación no incluye código de implementación ni resultados de ejecución.

## Prerequisites

- Ejecutar todo desde la raíz del repositorio.
- Usar `uv run`; `python` directo puede caer a un estimador local de tokens en las auditorías.
- Python >=3.10 y dependencias fijadas en `pyproject.toml` / `uv.lock`.
- SQLite en memoria por defecto; no se necesitan servicios externos.
- Leer [contrato REST](./contracts/rest-lifecycle-sla.md), [contrato CLI](./contracts/cli-lifecycle-sla.md) y [data-model.md](./data-model.md) antes de ejecutar las verificaciones.

## Gate commands

Tras la implementación, ejecutar desde la raíz y reportar los resultados solo después de ejecutarlos:

```bash
uv run pytest -v
uv run ruff check .
uv run python -m src.triage_rules
uv run python -m src.sla_calculator
uv run python -m src.context_audit --symbol evaluate_sla_status
uv run python -m src.context_audit --symbol classify_incident_report
```

No ejecutar SLA con `python -O`: `src/sla_calculator.py` usa `assert`.

## BDD scenario map

`tests/test_spec_003_lifecycle_sla.py` debe contener exactamente cinco escenarios Given/When/Then. Cada escenario usa `build_stack()` con el mismo repositorio inyectado en `IncidentService` y el mismo servicio inyectado en `create_api_app(service)` y `create_cli_app(service)`.

| # | Escenario | Resultado observable |
|---|---|---|
| 1 | Registro mínimo y paridad | Con solo `title` y `raw_text`, se generan `incident_id` `INC-<HEX8>`, `created_at` y `status` `OPEN`; REST 201 y CLI stdout coinciden; el ID es recuperable. |
| 2 | Aviso por `duplicate_group_key` | Con incidentes en `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED` más uno `RESOLVED` que comparten clave, el aviso contiene solo los tres IDs no resueltos, sin duplicados ni el propio ID, igual en REST y CLI. |
| 3 | SLA P0 continuo | Creado 10:00 y referencia 11:01: 61 minutos transcurridos, `is_breached: true`, `requires_escalation: true`. |
| 4 | SLA P2 en límite exacto | Lunes 08:00 a 16:00: 480 transcurridos, 0 restantes, `is_breached: false`. |
| 5 | SLA P2 con fin de semana | Viernes 17:00 a lunes 09:00: 120 minutos hábiles transcurridos, 360 restantes, `is_breached: false`, mismo JSON en REST y CLI. |

El escenario 5 es obligatorio: fija que la ventana hábil de ADR-002 produce 120 minutos y que el tiempo restante es 360, no 480 ni 0.

## REST validation

Tras la implementación, los ejemplos mínimos son:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/incidents \
  -H 'Content-Type: application/json' \
  -d '{"title":"Fallo de pasarela de pagos","raw_text":"URGENTE: El gateway de pagos devuelve HTTP 502 en todas las transacciones con tarjeta."}'

curl http://127.0.0.1:8000/api/v1/incidents/INC-2001

curl 'http://127.0.0.1:8000/api/v1/incidents/INC-2003/sla?reference_time=2026-11-23T09:00:00'
```

Expected outcomes:

- El alta devuelve `201`, un ID `INC-<HEX8>` y `duplicate_incident_ids` como lista.
- La consulta por ID devuelve el mismo objeto `incident` que el alta.
- La consulta de SLA P2 viernes 17:00 a lunes 09:00 devuelve `elapsed_minutes: 120`, `allowed_minutes: 480`, `remaining_minutes: 360`, `is_breached: false`.
- Un ID repetido devuelve `409` con `incident_id ya existe: <id>.` y no modifica el registro previo.

## CLI validation

```bash
uv run python -m src.adapters.inbound.cli register --title "Fallo de pasarela de pagos" --raw-text "El gateway de pagos devuelve HTTP 502 en todas las transacciones con tarjeta."
uv run python -m src.adapters.inbound.cli show INC-2001
uv run python -m src.adapters.inbound.cli sla INC-2003 --reference-time 2026-11-23T09:00:00
```

Expected outcomes:

- `register` y `sla` escriben JSON en stdout y terminan con código `0`.
- Los errores escriben el mensaje compartido en `stderr`, dejan stdout vacío y terminan con código `1`.
- `json.loads(result.stdout)` es idéntico a `response.json()` del endpoint correspondiente para la misma entrada y el mismo instante resuelto.

## Regression checks

- No modificar los criterios de Hito 001: las 10 filas `INC-1001`..`INC-1010` y los pares `1001/1006`, `1003/1008` siguen cuadrando con `AUDIT_EXPECTATIONS`.
- No modificar el resumen del Hito 002: paridad REST/CLI, filtro canónico, límites SLA y rechazo de `reference_time` inválido.
- No optimizar `src/incident_repository.py`: su escaneo completo y N+1 son deuda intencional.
- Todo `sqlite3`, SQL y `DATABASE_URL` sigue confinado a `src/adapters/outbound/sqlite_repository.py`.
- La implementación queda para `/speckit.implement`; este plan y sus artefactos no crean código ni pruebas ejecutables.
