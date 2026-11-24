# Data Model: Resumen de incidentes activos

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-24

## Entities

### Incident

Existente en `src/domain/models.py`; se reutiliza sin añadir campos.

| Field | Type | Constraints |
|---|---|---|
| `Incident.incident_id` | `str` | Identificador único no vacío. |
| `Incident.title` | `str` | Texto visible en el detalle; no vacío. |
| `Incident.component` | `str` | Nombre completo; se normaliza al persistir para filtrar sin distinguir mayúsculas ni espacios. |
| `Incident.severity` | `Literal["P0", "P1", "P2", "P3"]` | Debe existir en `SLA_POLICY_TABLE` y en `sla_policies`. |
| `Incident.status` | `Literal["OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED", "RESOLVED"]` | Solo `OPEN` e `IN_PROGRESS` entran en el resumen. |
| `Incident.created_at` | `datetime` | Local naive; instante inicial del cómputo SLA. |
| `Incident.resolved_at` | `datetime | None` | Local naive; prevalece sobre la referencia al evaluar SLA. |

### ActiveIncident

Proyección devuelta por `IncidentRepositoryPort.list_active_incidents`. Contiene los siete campos de `Incident` y respeta `ActiveIncident.status in {"OPEN", "IN_PROGRESS"}`.

| Field | Type | Constraints |
|---|---|---|
| `ActiveIncident.incident_id` | `str` | Copia de `Incident.incident_id`; no se expone en el detalle. |
| `ActiveIncident.title` | `str` | Copia de `Incident.title`. |
| `ActiveIncident.component` | `str` | Copia de `Incident.component`, normalizado al persistir. |
| `ActiveIncident.severity` | `Literal["P0", "P1", "P2", "P3"]` | Copia de `Incident.severity`. |
| `ActiveIncident.status` | `Literal["OPEN", "IN_PROGRESS"]` | Solo estados activos. |
| `ActiveIncident.created_at` | `datetime` | Copia de `Incident.created_at`; base del cómputo SLA. |
| `ActiveIncident.resolved_at` | `datetime | None` | Copia de `Incident.resolved_at`; `None` en activos. |

### ComponentFilter

| Field | Type | Constraints |
|---|---|---|
| `ComponentFilter.raw` | `str | None` | Valor recibido por REST o CLI. |
| `ComponentFilter.normalized` | `str | None` | `strip`, `casefold` y colapso de espacios internos; `""` o solo espacios se convierte en `None`. Sin coincidencias parciales. |

### ReferenceTime

| Field | Type | Constraints |
|---|---|---|
| `ReferenceTime.value` | `datetime` | Local naive y explícito en el servicio; si se omite, el adaptador captura el instante de consulta y lo pasa al servicio. |
| `ReferenceTime.serialized` | `str` | `value.isoformat()` en la respuesta compartida. |
| `ReferenceTime.invalid_message` | `str` | `reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior a created_at de un incidente devuelto.` |

Un valor malformado, con zona horaria o anterior al `created_at` de un incidente devuelto se rechaza antes de calcular el resumen: 422 con `detail` en REST y código 1 con mensaje en `stderr` en CLI.

### SLARule y SLAEvaluation

Existentes en `src/domain/models.py`; no se crean reglas nuevas.

| Field | Type | Constraints |
|---|---|---|
| `SLARule.max_resolution_minutes` | `int` | P0=60, P1=240, P2=480, P3=1440. |
| `SLARule.operates_24x7` | `bool` | `True` para P0/P1; `False` para P2/P3, con ventana lunes–viernes 08:00–18:00. |
| `SLARule.escalation_threshold_ratio` | `float` | `0.75`. |
| `SLAEvaluation.elapsed_minutes` | `int` | Minutos enteros calculados por el dominio. |
| `SLAEvaluation.is_breached` | `bool` | `True` solo si `elapsed_minutes > allowed_minutes`. |
| `SLAEvaluation.requires_escalation` | `bool` | `True` al alcanzar el 75 % del tiempo permitido; permanece tras el vencimiento mientras el incidente esté activo. |

### ActiveIncidentDetail

| Field | Type | Constraints |
|---|---|---|
| `ActiveIncidentDetail.title` | `str` | Copia de `Incident.title`. |
| `ActiveIncidentDetail.component` | `str` | Copia de `Incident.component`. |
| `ActiveIncidentDetail.severity` | `Literal["P0", "P1", "P2", "P3"]` | Copia de `Incident.severity`. |
| `ActiveIncidentDetail.status` | `Literal["OPEN", "IN_PROGRESS"]` | Copia de `Incident.status`. |
| `ActiveIncidentDetail.elapsed_minutes` | `int` | Copia de `SLAEvaluation.elapsed_minutes`. |
| `ActiveIncidentDetail.requires_escalation` | `bool` | Copia de `SLAEvaluation.requires_escalation`. |

El detalle no expone `incident_id` ni `is_breached`; el incumplimiento se informa de forma agregada.

### ActiveIncidentSummary

| Field | Type | Constraints |
|---|---|---|
| `ActiveIncidentSummary.reference_time` | `str` | ISO-8601 local naive efectivo. |
| `ActiveIncidentSummary.component_filter` | `str | None` | Valor normalizado o `None`. |
| `ActiveIncidentSummary.total_active` | `int` | `>= 0`; igual al número de filas de `details`. |
| `ActiveIncidentSummary.breached_count` | `int` | `0 <= breached_count <= total_active`; cuenta evaluaciones con `is_breached is True`. |
| `ActiveIncidentSummary.details` | `list[ActiveIncidentDetail]` | Vacía cuando no hay coincidencias; sin duplicados; ordenada por severidad P0→P3, minutos descendentes y título ascendente. |

### IncidentRepositoryPort

| Operation | Signature | Constraints |
|---|---|---|
| `IncidentRepositoryPort.save_incident` | `(incident: Incident) -> None` | Inserta o reemplaza por ID; normaliza `component`. |
| `IncidentRepositoryPort.get_incident` | `(incident_id: str) -> Incident | None` | Devuelve `None` si no existe. |
| `IncidentRepositoryPort.find_open_duplicates` | `(incident: Incident, *, exclude_incident_id: str | None = None) -> list[Incident]` | Solo estados activos; compara componente y título normalizados. |
| `IncidentRepositoryPort.list_active_incidents` | `(component_filter: str | None = None) -> list[Incident]` | Filtra `OPEN`/`IN_PROGRESS`; `None` devuelve todos los activos. |
| `IncidentRepositoryPort.check_health` | `() -> bool` | `False` ante error SQLite. |

## Relationships

```text
IncidentRepositoryPort.list_active_incidents -> ActiveIncident[]
ActiveIncident + ReferenceTime -> SLAEvaluation
SLAEvaluation + ActiveIncident -> ActiveIncidentDetail
ActiveIncidentDetail[] + ReferenceTime + ComponentFilter -> ActiveIncidentSummary
REST and CLI -> validar/capturar ReferenceTime.value -> IncidentService.get_active_incidents_summary
IncidentService.get_active_incidents_summary -> ActiveIncidentSummary
```

SQLite implementa el puerto; el dominio calcula SLA; la aplicación coordina y agrega; REST y CLI validan o capturan `reference_time` y solo luego serializan.

## State Transitions

No se introducen estados ni transiciones nuevas. `ESCALATION_REQUIRED` existe en el modelo pero queda fuera del conjunto activo de este feature. Un incidente `RESOLVED` que incumplió su SLA no aparece en el resumen. No se crean ni modifican incidentes desde los adaptadores de este feature.
