# REST Contract: Ciclo de vida de incidentes y SLA

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md)

Base path: `/api/v1`. Todas las respuestas exitosas usan JSON con claves estables. REST y CLI comparten los mismos DTOs y mensajes de error; la CLI espejo se describe en [cli-lifecycle-sla.md](./cli-lifecycle-sla.md).

## POST /api/v1/incidents

Registra un incidente y devuelve el registro persistido junto con el aviso de equivalentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED`.

### Request body

| Field | Type | Required | Constraints |
|---|---|---|---|
| `title` | string | Yes | No vacío tras quitar espacios. |
| `raw_text` | string | Yes | No vacío tras quitar espacios. Fuente de severidad, componente y `duplicate_group_key`. |
| `incident_id` | string | No | Si se omite, se genera `INC-<HEX8>`; si se envía, único y no vacío. |
| `created_at` | string | No | ISO-8601 local naive; si se omite, el adaptador captura el instante de registro. |
| `status` | string | No | `OPEN` o `IN_PROGRESS`; si se omite, `OPEN`. |

No se aceptan `component`, `severity` ni `duplicate_group_key` como entrada: se derivan del dominio desde `raw_text`.

Ejemplo mínimo:

```json
{
  "title": "Fallo de pasarela de pagos",
  "raw_text": "URGENTE: El gateway de pagos devuelve HTTP 502 en todas las transacciones con tarjeta."
}
```

### Success response (201)

```json
{
  "incident": {
    "incident_id": "INC-2001",
    "title": "Fallo de pasarela de pagos",
    "component": "payments-gateway",
    "severity": "P0",
    "status": "OPEN",
    "created_at": "2026-11-24T10:00:00",
    "duplicate_group_key": "payments-gateway:http-502-outage"
  },
  "duplicate_incident_ids": []
}
```

| Field | Type | Notes |
|---|---|---|
| `incident` | object | Campos definidos en `IncidentSnapshot`. |
| `duplicate_incident_ids` | string[] | IDs en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` con el mismo `duplicate_group_key`; sin duplicados; excluye `RESOLVED` y el ID recién registrado; puede estar vacío. |

### Errors

| Status | Message (`detail`) | Cause |
|---|---|---|
| 422 | `title y raw_text son obligatorios y no pueden estar vacíos.` | Falta `title` o `raw_text`, o están vacíos. |
| 422 | `incident_id debe estar vacío o tener formato INC-<HEX8>.` | `incident_id` vacío o no coincide con el formato acordado cuando se envía. |
| 409 | `incident_id ya existe: <id>.` | El ID ya existe; el registro anterior permanece intacto. |
| 422 | `status debe ser OPEN o IN_PROGRESS si se proporciona.` | `status` no es un estado inicial válido. |

## GET /api/v1/incidents/{incident_id}

Devuelve el registro persistido. No incluye aviso de duplicados.

### Success response (200)

El objeto `incident` definido arriba.

### Errors

| Status | Message (`detail`) | Cause |
|---|---|---|
| 404 | `incidente no encontrado: <id>.` | No existe el ID. |

## GET /api/v1/incidents/{incident_id}/sla

Consulta el estado SLA del incidente. `reference_time` es opcional.

### Query parameters

| Field | Type | Required | Constraints |
|---|---|---|---|
| `reference_time` | string | No | ISO-8601 local naive. Si se omite, el adaptador captura el instante de consulta y lo pasa al servicio. |

### Success response (200)

```json
{
  "incident_id": "INC-2003",
  "reference_time": "2026-11-23T09:00:00",
  "effective_time": "2026-11-23T09:00:00",
  "elapsed_minutes": 120,
  "allowed_minutes": 480,
  "remaining_minutes": 360,
  "is_breached": false,
  "requires_escalation": false
}
```

| Field | Type | Notes |
|---|---|---|
| `reference_time` | string | Instante efectivo solicitado o capturado. |
| `effective_time` | string | `resolved_at` si existe; si no, `reference_time`. |
| `elapsed_minutes` | int | Minutos calculados por `evaluate_sla_status`. |
| `allowed_minutes` | int | Límite de la política de severidad. |
| `remaining_minutes` | int | `allowed_minutes - elapsed_minutes`. |
| `is_breached` | bool | `true` solo si `elapsed_minutes > allowed_minutes`. |
| `requires_escalation` | bool | `true` desde el 75 % del límite; compatible con `is_breached`. |

### Errors

| Status | Message (`detail`) | Cause |
|---|---|---|
| 404 | `incidente no encontrado: <id>.` | No existe el ID. |
| 422 | `reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior a created_at de un incidente devuelto.` | Referencia malformada, tz-aware o anterior a la creación. |

## Invariants

- Los adaptadores no calculan severidad, componente, claves ni SLA; solo validan entrada, capturan instantes y serializan el resultado del servicio.
- `POST` y `GET` de incidente devuelven el mismo objeto `incident` para el mismo ID.
- La omisión de `reference_time` se resuelve en el adaptador y se refleja en la respuesta.
- Para la misma entrada y el mismo instante resuelto, la respuesta REST es igual al JSON de stdout de la CLI.
- El aviso incluye incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` con la misma clave; nunca incluye el ID recién registrado, incidentes `RESOLVED` ni IDs repetidos.
