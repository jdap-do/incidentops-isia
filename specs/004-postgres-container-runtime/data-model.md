# Data Model: postgres-container-runtime

**Feature**: `specs/004-postgres-container-runtime/spec.md`

**Date**: 2026-11-24

## Persisted entity: `Incident` (unchanged)

Ya definida en `src/domain/models.py:34-46` y reutilizada por ambos adaptadores de salida.

| Field | Rule |
|---|---|
| `incident_id` | Identificador único; el adaptador debe rechazar inserciones repetidas con `DuplicateIncidentId`. |
| `title` | Obligatorio en el registro; no vacío. |
| `raw_text` | Obligatorio en el registro; no vacío; se persiste. |
| `component` | Componente normalizado del incidente. |
| `severity` | Severidad derivada por el dominio, nunca desde el ID. |
| `status` | Estado del incidente; los estados no resueltos que participan en duplicados son `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED`. |
| `created_at` | Fecha local naive ISO 8601, almacenada como `TEXT`. |
| `resolved_at` | Fecha local naive ISO 8601 o `None`; prevalece sobre el instante de referencia en SLA. |
| `duplicate_group_key` | Clave de correlación candidata; no implica causa raíz. |

No hay transiciones de estado nuevas en este hito.

## Configuration entity: `DatabaseSelection`

| Field | Value | Effective engine | Rule |
|---|---|---|---|
| `DatabaseSelection.DATABASE_URL` | ausente o vacía | SQLite en memoria | Valor por defecto local y de pruebas. |
| `DatabaseSelection.DATABASE_URL` | esquema `sqlite:` | SQLite | Se mantiene el comportamiento observable actual. |
| `DatabaseSelection.DATABASE_URL` | esquema `postgresql:` | PostgreSQL | Motor dedicado en contenedores. |
| `DatabaseSelection.DATABASE_URL` | cualquier otro esquema | Ninguno | Rechazo claro, sin respaldo silencioso a SQLite. |

La selección se resuelve en `src/bootstrap.py`; ni el dominio ni la aplicación conocen el motor concreto.

## Application entity: `HealthStatusResult`

| Field | Type | Meaning |
|---|---|---|
| `status` | `"ok"` o `"error"` | Estado lógico devuelto por el caso de uso compartido. |
| `database` | `"connected"` o `"unavailable"` | Disponibilidad de la base configurada, derivada solo de `SELECT 1`. |
| `healthy` | `bool` | Flag interno para que la API elija `200`/`503` y la CLI elija `0`/`1`; no forma parte del JSON acordado. |

El caso de uso se añade a `IncidentService` y usa `IncidentRepositoryPort.check_health()`. La API y la CLI serializan el mismo DTO.

## Storage mapping for both adapters

- Tabla `incidents` con `incident_id TEXT PRIMARY KEY`, columnas de texto para el resto de campos y `resolved_at TEXT NULL`.
- Tabla `sla_policies` con la misma semántica que el adaptador SQLite actual.
- Índices para `component`, `status`, `created_at` y `duplicate_group_key`.
- Parámetros SQL: `?` en SQLite y `%s` en PostgreSQL; nunca interpolación de valores.
- Timestamps: `datetime.isoformat()` al escribir y `datetime.fromisoformat()` al leer; sin tipos nativos de fecha, zonas horarias ni conversiones.
- Errores de unicidad: mapear a `DuplicateIncidentId` en ambos adaptadores.

## Runtime entity: `RuntimeStack`

| Field | Definition |
|---|---|
| `RuntimeStack.db` | `postgres:16-alpine`, volumen persistente, credenciales desde entorno, healthcheck `pg_isready`. |
| `RuntimeStack.api` | Imagen construida desde `Dockerfile`, `DATABASE_URL` apuntando a `db`, arranque condicionado a `db` saludable, healthcheck HTTP sobre `/health`. |

La pila no introduce migraciones de datos ni cambia las reglas de triaje, duplicados o SLA.
