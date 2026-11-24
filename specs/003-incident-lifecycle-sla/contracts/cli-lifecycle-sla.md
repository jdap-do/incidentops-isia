# CLI Contract: Ciclo de vida de incidentes y SLA

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Data model**: [data-model.md](../data-model.md)

La CLI usa Typer y expone tres comandos. Todos reciben un `IncidentService` inyectado por `create_cli_app(service)` y comparten casos de uso, DTOs y mensajes con el contrato REST descrito en [rest-lifecycle-sla.md](./rest-lifecycle-sla.md).

## incidentops register

Registra un incidente y muestra la confirmación con el aviso de equivalentes.

```text
incidentops register --title "Fallo de pasarela de pagos" --raw-text "El gateway devuelve HTTP 502 ..." [--incident-id INC-2001] [--created-at 2026-11-24T10:00:00] [--status OPEN]
```

| Option | Type | Required | Constraints |
|---|---|---|---|
| `--title` | string | Yes | No vacío tras quitar espacios. |
| `--raw-text` | string | Yes | No vacío tras quitar espacios. |
| `--incident-id` | string | No | Si se omite, se genera `INC-<HEX8>`; si se envía, único y no vacío. |
| `--created-at` | string | No | ISO-8601 local naive; si se omite, se captura el instante de registro. |
| `--status` | string | No | `OPEN` o `IN_PROGRESS`; por defecto `OPEN`. |

### stdout (exit code 0)

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

La serialización usa `json.dumps(..., ensure_ascii=False)`, igual que en Hito 002.

### stderr (exit code 1)

| Message | Cause |
|---|---|
| `title y raw_text son obligatorios y no pueden estar vacíos.` | Falta `title` o `raw_text`, o están vacíos. |
| `incident_id debe estar vacío o tener formato INC-<HEX8>.` | ID proporcionado vacío o con formato inválido. |
| `incident_id ya existe: <id>.` | El ID ya existe; no se sobrescribe. |
| `status debe ser OPEN o IN_PROGRESS si se proporciona.` | Estado inicial inválido. |

En caso de error, stdout queda vacío.

## incidentops show

Muestra el registro persistido de un incidente.

```text
incidentops show INC-2001
```

| Argument | Type | Required | Constraints |
|---|---|---|---|
| `incident_id` | string | Yes | ID existente. |

### stdout (exit code 0)

El objeto `incident` definido en `register`.

### stderr (exit code 1)

| Message | Cause |
|---|---|
| `incidente no encontrado: <id>.` | No existe el ID. |

## incidentops sla

Consulta el estado SLA de un incidente. `reference_time` es opcional.

```text
incidentops sla INC-2003 [--reference-time 2026-11-23T09:00:00]
```

| Argument / Option | Type | Required | Constraints |
|---|---|---|---|
| `incident_id` | string | Yes | ID existente. |
| `--reference-time` | string | No | ISO-8601 local naive; si se omite, se captura el instante de consulta. |

### stdout (exit code 0)

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

### stderr (exit code 1)

| Message | Cause |
|---|---|
| `incidente no encontrado: <id>.` | No existe el ID. |
| `reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior a created_at de un incidente devuelto.` | Referencia malformada, tz-aware o anterior a la creación. |

## Invariants

- Para la misma entrada y el mismo instante resuelto, `json.loads(result.stdout)` es igual a `response.json()` del endpoint REST correspondiente.
- La omisión de `--reference-time` se resuelve en la CLI antes de invocar al servicio; el servicio recibe un `datetime` explícito.
- El aviso de equivalentes sigue las mismas reglas que REST: solo IDs en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` con el mismo `duplicate_group_key`, sin duplicados, sin `RESOLVED` y sin el ID recién registrado.
- La CLI no contiene reglas de triaje, correlación ni SLA; solo llama a los casos de uso de `IncidentService`.
- Los errores se escriben en `stderr` con el mismo texto que REST usa en `detail`.
