# Quickstart: Resumen de incidentes activos

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contracts**: [REST](./contracts/rest-summary.md) y [CLI](./contracts/cli-summary.md)

## Prerequisites

- Ejecutar todos los comandos desde la raíz del repositorio.
- Python >=3.10 y `uv`.
- Sin servicios externos: la fábrica usa SQLite en memoria cuando `DATABASE_URL` está ausente o vacía.

```bash
uv sync
```

Para apuntar a un archivo SQLite distinto, definir `DATABASE_URL=sqlite:///incidentops.db` antes de iniciar REST o CLI. Un valor con otro esquema debe rechazarse.

## Validation gates

Después de la implementación, ejecutar desde la raíz:

```bash
uv run pytest
uv run ruff check .
```

Resultados verificados:

- `uv run ruff check .` → `All checks passed!`
- `uv run ruff check src/` → `All checks passed!`
- `uv run pytest -v` → `18 passed, 1 warning in 0.80s`.
- La suite completa incluye las pruebas de Hito 001 sin cambios y los cuatro
  escenarios de `tests/test_spec_002_summary.py`, con la verificación SC-006 de
  hasta 1.000 activos sin omisiones ni duplicados.
- El único warning es `StarletteDeprecationWarning` de `fastapi/testclient.py`
  sobre el uso de `httpx` con `starlette.testclient`.

## Deterministic REST validation

1. Iniciar la API con `uv run uvicorn src.adapters.inbound.api.app:app --reload`.
2. Consultar `GET /api/v1/incidents/summary` con `component=payments-gateway` y `reference_time=2026-11-24T12:00:00`.
3. Verificar que la respuesta tiene `200`, `total_active`, `breached_count`, `reference_time`, `component_filter` y `details` con los seis campos definidos en el contrato REST.
4. Repetir sin `component` y con un valor con mayúsculas y espacios circundantes; el segundo debe coincidir con el filtro canónico.
5. Repetir con un componente inexistente; esperar ceros y `details: []`, no `404`.
6. Repetir sin `reference_time`; el adaptador debe capturar el instante de consulta y la respuesta debe mostrarlo como `reference_time` efectivo.
7. Repetir con `reference_time` malformado, con zona horaria o anterior a un `created_at`; esperar `422` con `detail`, sin resumen parcial.

## Deterministic CLI validation

```bash
uv run python -m src.adapters.inbound.cli summary --component " PAYMENTS-GATEWAY " --reference-time 2026-11-24T12:00:00
```

Resultado esperado: un único objeto JSON en `stdout`, código `0` y el mismo valor que la respuesta REST para los mismos parámetros.

Repetir sin `--reference-time`: el adaptador debe capturar el instante de consulta y la salida debe mostrarlo como `reference_time` efectivo, con el mismo valor que REST para el mismo momento.

Para validar errores:

```bash
uv run python -m src.adapters.inbound.cli summary --reference-time 2026-11-24T12:00:00+00:00
```

Resultado esperado: `stdout` vacío, mensaje en `stderr` y código `1`, con el mismo texto que el `detail` de REST.

## BDD scenario map

| Scenario | Observable outcome |
|---|---|
| Active summary parity | REST y CLI coinciden; excluded states do not appear; totals and ordering match. |
| Component filter | Case and surrounding spaces are ignored; totals and rows use only the requested component; blank or unknown filters behave as specified. |
| SLA interpretation | Exact limit is not a breach; exceeded open incidents show breach and escalation; P2 business-hours calculation matches in both channels. |
| Empty and invalid requests | Empty datasets return zeros; omitted `reference_time` is captured by the adapter; malformed/tz-aware/too-early values are rejected consistently by both channels. |
| SC-006 volume validation | Up to 1.000 active incidents appear in the detail with no omissions or duplicates. |

## Regression checks

- No modificar `tests/test_spec_001_triage.py`.
- El feature no usa ni modifica código SQLite fuera de `src/adapters/outbound/sqlite_repository.py`; la deuda preexistente queda fuera del alcance del hito.
- Verificar que `src/adapters/inbound/` no importa `src/adapters/outbound/`, `src/application/` no importa adaptadores y `src/domain/` no importa capas superiores.
