# CLI Contract: Resumen de incidentes activos

**Feature**: [spec.md](../spec.md) | **Data model**: [data-model.md](../data-model.md)

## Command

`incidentops summary`

## Options

| Option | Type | Required | Semantics |
|---|---|---|---|
| `--component TEXT` | `string` | No | Filtro por nombre completo. Se normaliza con `strip`, `casefold` y colapso de espacios internos. Omitido, vacío o solo espacios significa sin filtro. Sin coincidencias parciales. |
| `--reference-time TEXT` | `string` | No | ISO-8601 local naive, por ejemplo `2026-11-24T12:00:00`. Si se omite, el adaptador captura el instante de la consulta y lo pasa explícitamente al servicio; la salida muestra ese instante efectivo. Se rechaza texto malformado o con zona horaria. |

## Success output

La CLI escribe un único objeto JSON en `stdout` con `ensure_ascii=False` y termina con código `0`:

```json
{
  "reference_time": "2026-11-24T12:00:00",
  "component_filter": "payments-gateway",
  "total_active": 1,
  "breached_count": 1,
  "details": [
    {
      "title": "Fallo de pasarela de pagos",
      "component": "payments-gateway",
      "severity": "P0",
      "status": "IN_PROGRESS",
      "elapsed_minutes": 75,
      "requires_escalation": true
    }
  ]
}
```

| Field | Type | Constraint |
|---|---|---|
| `reference_time` | `string` | Instante efectivo serializado con `isoformat()`. |
| `component_filter` | `string | null` | Filtro normalizado o `null`. |
| `total_active` | `integer` | Igual a `len(details)`. |
| `breached_count` | `integer` | Entre cero y `total_active`. |
| `details[].title` | `string` | Título visible del incidente. |
| `details[].component` | `string` | Componente visible del incidente. |
| `details[].severity` | `string` | Uno de `P0`, `P1`, `P2`, `P3`. |
| `details[].status` | `string` | Uno de `OPEN`, `IN_PROGRESS`. |
| `details[].elapsed_minutes` | `integer` | Minutos calculados por el dominio. |
| `details[].requires_escalation` | `boolean` | Umbral del 75 % alcanzado. |

## Ordering

`details` se ordena por severidad P0→P3, luego `elapsed_minutes` descendente y finalmente `title` ascendente.

## Empty results

Un filtro sin coincidencias o la ausencia de incidentes activos produce código `0` con `total_active: 0`, `breached_count: 0` y `details: []`. No se produce un error.

## Errors

En caso de `reference_time` malformado, con zona horaria o anterior a `created_at` de algún incidente devuelto, no se calcula ni se escribe un resumen parcial:

- `stdout` queda vacío.
- El mensaje escrito en `stderr` es `reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior a created_at de un incidente devuelto.`.
- El proceso termina con código `1`.

El mensaje debe coincidir con el campo `detail` devuelto por REST para la misma entrada.

## Invariants

- Solo aparecen incidentes `OPEN` o `IN_PROGRESS`.
- Un incidente resuelto que incumplió su SLA no aparece.
- Alcanzar exactamente el límite de SLA no incrementa `breached_count`.
- Un incidente abierto puede tener incumplimiento y escalamiento a la vez.
- Para el mismo filtro y `reference_time`, `json.loads(stdout)` es idéntico al cuerpo de REST.
