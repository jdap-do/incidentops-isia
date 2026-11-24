# Data Model: Ciclo de vida de incidentes y SLA

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-24

## Entities

### Incident

Existente en `src/domain/models.py`; se extiende con `raw_text` y `duplicate_group_key`. El resto de campos se reutiliza sin cambiar su significado.

| Field | Type | Constraints |
|---|---|---|
| `Incident.incident_id` | `str` | Único y no vacío. Proporcionado por quien registra o generado con formato `INC-<HEX8>`. Nunca influye en severidad ni correlación. |
| `Incident.title` | `str` | Obligatorio; no vacío después de quitar espacios. No interviene en `duplicate_group_key`. |
| `Incident.raw_text` | `str` | Obligatorio; no vacío después de quitar espacios. Fuente de triaje, severidad, componente y clave de duplicados. |
| `Incident.component` | `str` | Derivado por `classify_incident_report`; no se solicita al registrar. Se normaliza al persistir como en Hito 002. |
| `Incident.severity` | `Literal["P0", "P1", "P2", "P3"]` | Derivada por el dominio desde `raw_text`. Debe existir en `SLA_POLICY_TABLE`. |
| `Incident.status` | `Literal["OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED", "RESOLVED"]` | Opcional al registrar; por defecto `OPEN`. Si se envía, solo `OPEN` o `IN_PROGRESS`. `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED` participan en el aviso; `ESCALATION_REQUIRED` solo puede venir de datos sembrados. |
| `Incident.created_at` | `datetime` | Opcional al registrar; por defecto el instante resuelto por el adaptador. Local naive; inicio del cómputo SLA. |
| `Incident.resolved_at` | `datetime | None` | No se acepta en el alta. Puede existir en registros sembrados o futuros; prevalece sobre la referencia al evaluar SLA. Local naive. |
| `Incident.duplicate_group_key` | `str` | Derivado por `classify_incident_report` desde `raw_text` normalizado. Persistido e indexado. Ejemplo: `payments-gateway:http-502-outage`. |

### RegistrationInput

DTO de aplicación que contiene la entrada observable del caso de uso `register_incident`.

| Field | Type | Constraints |
|---|---|---|
| `RegistrationInput.title` | `str` | Obligatorio; `strip()` no vacío. |
| `RegistrationInput.raw_text` | `str` | Obligatorio; `strip()` no vacío. |
| `RegistrationInput.incident_id` | `str | None` | `None` significa autogenerar `INC-<HEX8>`; si se envía, no vacío y único. |
| `RegistrationInput.created_at` | `datetime | None` | `None` significa usar el instante resuelto por el adaptador. Local naive. |
| `RegistrationInput.status` | `IncidentStatus | None` | `None` significa `OPEN`; si se envía, `OPEN` o `IN_PROGRESS`. |

### RegistrationResult

| Field | Type | Constraints |
|---|---|---|
| `RegistrationResult.incident` | `IncidentSnapshot` | Registro efectivamente persistido. |
| `RegistrationResult.duplicate_incident_ids` | `list[str]` | IDs de incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` con el mismo `duplicate_group_key`; sin duplicados; excluye `RESOLVED` y el incidente recién registrado; vacío cuando no hay equivalentes. |

### IncidentSnapshot

Vista estable expuesta por REST y CLI; no expone `raw_text` ni campos internos de clasificación distintos de los ya acordados.

| Field | Type | Constraints |
|---|---|---|
| `IncidentSnapshot.incident_id` | `str` | Copia de `Incident.incident_id`. |
| `IncidentSnapshot.title` | `str` | Copia de `Incident.title`. |
| `IncidentSnapshot.component` | `str` | Copia de `Incident.component`. |
| `IncidentSnapshot.severity` | `Literal["P0", "P1", "P2", "P3"]` | Copia de `Incident.severity`. |
| `IncidentSnapshot.status` | `IncidentStatus` | Copia de `Incident.status`. |
| `IncidentSnapshot.created_at` | `str` | `datetime.isoformat()` local naive. |
| `IncidentSnapshot.duplicate_group_key` | `str` | Copia de `Incident.duplicate_group_key`. |

### DuplicateGroupKey

| Field | Type | Constraints |
|---|---|---|
| `DuplicateGroupKey.value` | `str` | Resultado de `TriageResult.duplicate_group_key` sobre `raw_text` normalizado. |
| `DuplicateGroupKey.open_statuses` | `frozenset[IncidentStatus]` | `{OPEN, IN_PROGRESS, ESCALATION_REQUIRED}`. `RESOLVED` queda fuera del aviso; el alta sigue aceptando solo `OPEN` o `IN_PROGRESS`. |
| `DuplicateGroupKey.excluded_id` | `str | None` | ID del incidente recién registrado; evita que aparezca en su propio aviso. |

### ReferenceTime

| Field | Type | Constraints |
|---|---|---|
| `ReferenceTime.raw` | `str | None` | Valor opcional recibido por REST o CLI. |
| `ReferenceTime.value` | `datetime` | Local naive y explícito en el servicio. Si `raw` falta, el adaptador captura el instante de consulta. |
| `ReferenceTime.serialized` | `str` | `value.isoformat()` en la respuesta compartida. |
| `ReferenceTime.invalid_message` | `str` | `reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior a created_at de un incidente devuelto.` |

### SLAStatusResult

| Field | Type | Constraints |
|---|---|---|
| `SLAStatusResult.incident_id` | `str` | ID consultado. |
| `SLAStatusResult.reference_time` | `str` | ISO-8601 local naive efectivo. |
| `SLAStatusResult.effective_time` | `str` | ISO-8601 local naive usado por el dominio: `resolved_at` si existe, si no `reference_time`. |
| `SLAStatusResult.elapsed_minutes` | `int` | Minutos enteros producidos por `evaluate_sla_status`. |
| `SLAStatusResult.allowed_minutes` | `int` | Límite de la política: P0=60, P1=240, P2=480, P3=1440. |
| `SLAStatusResult.remaining_minutes` | `int` | `allowed_minutes - elapsed_minutes`; puede ser negativo tras el incumplimiento. |
| `SLAStatusResult.is_breached` | `bool` | `True` solo si `elapsed_minutes > allowed_minutes`. |
| `SLAStatusResult.requires_escalation` | `bool` | `True` al alcanzar el 75 % del permitido; permanece tras el vencimiento mientras el estado no sea `RESOLVED` (`OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED`). Puede ser `True` junto con `is_breached`. |

### SLARule y SLAEvaluation

Existentes en `src/domain/models.py`; no se crean reglas nuevas. `SLARule` fija el límite, la ventana y el umbral de escalamiento. `SLAEvaluation` es la fuente de los campos de `SLAStatusResult`.

| Field | Type | Constraints |
|---|---|---|
| `SLARule.max_resolution_minutes` | `int` | Límite de la política: P0=60, P1=240, P2=480, P3=1440. Debe existir en `SLA_POLICY_TABLE`. |
| `SLARule.operates_24x7` | `bool` | `True` para P0 y P1; `False` para P2 y P3, que usan lunes a viernes 08:00-18:00. |
| `SLARule.escalation_threshold_ratio` | `float` | `0.75`; el umbral entero es `int(max_resolution_minutes * 0.75)`. |
| `SLAEvaluation.elapsed_minutes` | `int` | Minutos enteros producidos por `evaluate_sla_status`; fuente de `SLAStatusResult.elapsed_minutes`. |
| `SLAEvaluation.is_breached` | `bool` | `True` solo si `elapsed_minutes > allowed_minutes`; fuente de `SLAStatusResult.is_breached`. |
| `SLAEvaluation.requires_escalation` | `bool` | `True` al alcanzar el umbral del 75 % mientras el estado no sea `RESOLVED`; fuente de `SLAStatusResult.requires_escalation`. |

### IncidentRepositoryPort

| Operation | Signature | Constraints |
|---|---|---|
| `IncidentRepositoryPort.save_incident` | `(incident: Incident) -> None` | Inserción estricta por ID; un ID repetido se rechaza sin sobrescribir; normaliza `component` y persiste `raw_text` y `duplicate_group_key`. |
| `IncidentRepositoryPort.get_incident` | `(incident_id: str) -> Incident | None` | Devuelve `None` si no existe. |
| `IncidentRepositoryPort.find_open_duplicates` | `(incident: Incident, *, exclude_incident_id: str | None = None) -> list[Incident]` | Filtra `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED` por `duplicate_group_key`; excluye `RESOLVED` y el ID propio; sin duplicados. |
| `IncidentRepositoryPort.list_active_incidents` | `(component_filter: str | None = None) -> list[Incident]` | Sin cambios respecto a Hito 002. |
| `IncidentRepositoryPort.check_health` | `() -> bool` | Sin cambios respecto a Hito 002. |

### SQLite schema

```text
sla_policies(
  severity TEXT PRIMARY KEY,
  max_resolution_minutes INTEGER NOT NULL,
  operates_24x7 INTEGER NOT NULL
)

incidents(
  incident_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  raw_text TEXT NOT NULL,
  component TEXT NOT NULL,
  severity TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  resolved_at TEXT,
  duplicate_group_key TEXT NOT NULL
)

CREATE INDEX idx_incidents_component_status
  ON incidents(component, status, incident_id)
CREATE INDEX idx_incidents_duplicate_status
  ON incidents(duplicate_group_key, status, incident_id)
```

Las fechas se serializan con `isoformat()` y se reconstruyen con `datetime.fromisoformat()`. No hay `UNIQUE` sobre `title` ni `raw_text`. No se introduce `FOREIGN KEY` nuevo. La deuda `src/incident_repository.py` queda intacta.

## Validation rules

- `title` y `raw_text` son los únicos campos obligatorios y no pueden quedar vacíos tras quitar espacios.
- `incident_id` omitido se genera con `INC-<HEX8>`; proporcionado debe ser único y no vacío.
- `created_at` omitido se resuelve en el adaptador y llega explícito al servicio; proporcionado debe ser ISO-8601 local naive.
- `status` omitido se resuelve a `OPEN`; proporcionado debe ser `OPEN` o `IN_PROGRESS`.
- `component`, `severity` y `duplicate_group_key` se derivan del dominio; el usuario no los envía.
- `resolved_at` no se acepta en el alta; cuando existe en un registro, prevalece sobre `reference_time`.
- `reference_time` es opcional para quien consulta; el servicio recibe siempre un `datetime` local naive.
- `reference_time` malformado, tz-aware o anterior a `created_at` se rechaza con el mensaje compartido.
- Solo `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED` entran en el aviso de duplicados; se excluyen `RESOLVED` y el incidente recién registrado.
- El alta sigue aceptando solo `OPEN` o `IN_PROGRESS`, con `OPEN` por defecto; `ESCALATION_REQUIRED` puede existir solo en datos sembrados.

## Relationships

```text
RegistrationInput + captured_time -> IncidentService.register_incident
IncidentService.register_incident -> classify_incident_report -> severity/component/duplicate_group_key
IncidentService.register_incident -> IncidentRepositoryPort.save_incident
IncidentService.register_incident -> IncidentRepositoryPort.find_open_duplicates -> duplicate_incident_ids
REST and CLI -> parse_reference_time -> IncidentService.get_incident_sla(reference_time)
IncidentRepositoryPort.get_incident + evaluate_sla_status -> SLAStatusResult
REST and CLI -> same DTOs and error messages
```

El dominio calcula clasificación y SLA; la aplicación coordina y produce DTOs; SQLite implementa el puerto; REST y CLI solo validan, capturan instantes y serializan.

## State Transitions

```text
(alta sin status)        -> OPEN
(alta con OPEN)          -> OPEN
(alta con IN_PROGRESS)   -> IN_PROGRESS
(alta con otro status)   -> rechazada
OPEN | IN_PROGRESS | ESCALATION_REQUIRED -> aviso de equivalentes por duplicate_group_key
RESOLVED                 -> fuera del aviso; su resolved_at prevalece en SLA
```

No se implementan transiciones posteriores en este hito. `ESCALATION_REQUIRED` existe en el modelo y puede aparecer en datos sembrados: no se crea en el alta, pero participa en el aviso de equivalentes y cuenta como estado no `RESOLVED` para conservar el escalamiento de SLA. El escalamiento de SLA es una evaluación calculada, no un cambio de estado.
