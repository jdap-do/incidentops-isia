# Research: Ciclo de vida de incidentes y SLA

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-11-24

No quedan marcadores `NEEDS CLARIFICATION`. La entrada de planificación del usuario precisa tres puntos que la especificación aclarada dejaba ambiguos: `title` y `raw_text` son los únicos campos obligatorios, `reference_time` es opcional para quien consulta y el aviso de equivalentes usa `duplicate_group_key`. Esas precisiones se reflejan en `spec.md` y se aplican en este plan.

## 1. Campos de alta y derivación del dominio

**Decision**: El caso de uso de registro recibe `title` y `raw_text` como únicos campos obligatorios. `incident_id`, `created_at` y `status` son opcionales. Si falta `incident_id`, se genera un valor único `INC-<HEX8>`; si falta `created_at`, se usa el instante resuelto por el adaptador; si falta `status`, se aplica `OPEN`. Si se proporciona `status`, solo se aceptan `OPEN` o `IN_PROGRESS`. El componente, la severidad y el `duplicate_group_key` se derivan con `classify_incident_report` desde `raw_text` normalizado. El identificador nunca interviene en la clasificación.

```text
register_incident(title, raw_text, *, incident_id=None, created_at, status=None)
  -> RegistrationResult(incident, duplicate_incident_ids)
```

**Rationale**: Coincide con el enunciado del usuario y con el principio I de la constitución: severidad y claves de correlación viven en el dominio y se derivan de señales normalizadas, nunca del ID. `title` se conserva como dato legible y no altera la regla de triaje ya auditada en Hito 001. Capturar `created_at` en el adaptador y pasarlo explícitamente al servicio conserva el determinismo exigido por la constitución.

**Alternatives considered**:

- Exigir `component` o `severity` en el alta: rechazado; contradice «`title` y `raw_text` son los únicos campos obligatorios» y traslada al usuario una decisión del dominio.
- Calcular el componente o la clave desde `title`: rechazado; modificaría `AUDIT_EXPECTATIONS` y convertiría el título en una señal de clasificación no acordada.
- Dejar que el servicio lea `datetime.now()`: rechazado; rompería el principio de dominio determinista y la práctica ya establecida en Hito 002.

## 2. Persistencia y unicidad

**Decision**: Reutilizar `SQLiteIncidentRepository` detrás de `IncidentRepositoryPort`, confinando todo SQL a `src/adapters/outbound/sqlite_repository.py`. Extender `Incident` con `raw_text: str` y `duplicate_group_key: str`, y extender la tabla `incidents` con `raw_text TEXT NOT NULL` y `duplicate_group_key TEXT NOT NULL`. Añadir `CREATE INDEX IF NOT EXISTS idx_incidents_duplicate_status ON incidents(duplicate_group_key, status, incident_id)`. Mantener `incident_id` como PRIMARY KEY y cambiar `save_incident` de `INSERT OR REPLACE` a inserción estricta: un ID repetido se rechaza con `DuplicateIncidentIdError` y no sobrescribe el registro anterior.

**Rationale**: El aviso por `duplicate_group_key` necesita que la clave esté disponible sin reconstruir la persistencia ni repetir triaje por fila. Persistir `raw_text` conserva la señal original auditada. La inserción estricta materializa FR-002 y evita que un alta con ID repetido destruya estado previo.

**Alternatives considered**:

- Recalcular la clave leyendo `raw_text` en cada consulta: rechazado; introduce triaje en la capa de persistencia y degrada el aviso con 1.000 incidentes en estados del aviso.
- Añadir `UNIQUE` sobre `title` o `raw_text`: rechazado; impediría registrar incidentes equivalentes, que es justamente lo que debe avisarse.
- Crear una tabla o motor nuevo: rechazado; la constitución mantiene SQLite como adaptador inicial y no hay causa para un ADR nuevo.
- Mantener `INSERT OR REPLACE`: rechazado; contradice el criterio de rechazo por ID duplicado.

## 3. Superficie de `IncidentRepositoryPort`

**Decision**: Conservar la firma de `find_open_duplicates(incident, *, exclude_incident_id=None)` pero redefinir su semántica: devuelve incidentes con `status in {"OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED"}` cuyo `duplicate_group_key` coincide con el del incidente recibido, excluye `RESOLVED` y el ID propio cuando se indica, y no compara componente ni título. El alta sigue aceptando solo `OPEN` o `IN_PROGRESS`, con `OPEN` por defecto. Se mantiene `save_incident`, `get_incident`, `list_active_incidents` y `check_health` sin cambios de firma.

**Rationale**: Reutiliza el puerto existente sin duplicar operaciones casi idénticas y deja la regla de equivalencia en un solo lugar. El índice por clave sostiene el caso de 1.000 incidentes en los tres estados del aviso sin escaneo adicional.

**Alternatives considered**:

- Añadir `find_open_duplicates_by_key`: rechazado; duplicaría una operación ya presente y dejaría dos caminos de equivalencia.
- Comparar `component` y `title` como en Hito 002: rechazado; el usuario pidió aviso por `duplicate_group_key` y la spec aclarada prohíbe esa comparación como regla definitiva.
- Exponer SQL desde el servicio: rechazado; rompe los principios III y IV.

## 4. Casos de uso compartidos

**Decision**: `IncidentService` gana tres operaciones y REST/CLI delegan en ellas sin reglas propias:

```text
register_incident(...)                 -> RegistrationResult
get_incident(incident_id)              -> Incident | None
get_incident_sla(incident_id, reference_time) -> SLAStatusResult
```

`register_incident` valida entradas, resuelve defaults, llama al dominio para clasificar, guarda por el puerto y consulta duplicados por clave en `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED`, excluyendo `RESOLVED` y el propio incidente. `get_incident_sla` obtiene el registro, llama a `evaluate_sla_status` y devuelve minutos transcurridos, permitidos y restantes, `is_breached` y `requires_escalation`. Un ID inexistente produce un error de no encontrado compartido por ambos canales.

**Rationale**: Cumple el principio II: un solo caso de uso por comportamiento, con adaptadores delgados y serialización común. `bootstrap.build_incident_service` sigue siendo la única raíz de composición; las pruebas inyectan el mismo servicio en `create_api_app` y `create_cli_app`.

**Alternatives considered**:

- Implementar registro o SLA por separado en REST y CLI: rechazado; generaría divergencia y violaría la constitución.
- Exponer el repositorio directamente a los adaptadores: rechazado; ADR-003 exige dependencia solo del servicio y del puerto.
- Devolver el `Incident` crudo como contrato público: rechazado; los contratos deben estabilizar DTOs observables y no acoplar a campos internos.

## 5. `reference_time` opcional y errores compartidos

**Decision**: REST y CLI aceptan `reference_time` opcional. Si se omite, el adaptador captura el instante de consulta y lo pasa como `datetime` explícito al servicio, reutilizando `parse_reference_time` de Hito 002. Se reutiliza el mensaje exacto `reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior a created_at de un incidente devuelto.` para valores malformados, tz-aware o anteriores a la creación. El dominio no lee el reloj y `evaluate_sla_status` sigue siendo la única fuente de SLA.

**Rationale**: Concuerda con el enunciado del usuario sin relajar ADR-002: la opcionalidad es una comodidad del adaptador, no una ambigüedad del caso de uso.

**Alternatives considered**:

- Hacer obligatorio `reference_time` en REST y CLI: rechazado; contradice el enunciado actual.
- Dejar que el servicio interprete una cadena o use `now`: rechazado; mezcla parseo con regla de negocio y rompe determinismo.
- Aceptar zonas horarias: rechazado; ADR-002 no las contempla.

## 6. Contratos REST y CLI

**Decision**: REST expone `POST /api/v1/incidents`, `GET /api/v1/incidents/{incident_id}` y `GET /api/v1/incidents/{incident_id}/sla`. CLI expone `incidentops register`, `incidentops show` y `incidentops sla`. Los tres pares comparten DTOs y mensajes de error. `register` devuelve el incidente persistido y `duplicate_incident_ids`; `sla` devuelve el instante efectivo y los cinco valores de evaluación. Las respuestas JSON de CLI se serializan con `ensure_ascii=False`, igual que en Hito 002.

Los mensajes compartidos son:

```text
title y raw_text son obligatorios y no pueden estar vacíos.
incident_id debe estar vacío o tener formato INC-<HEX8>.
incident_id ya existe: <id>.
status debe ser OPEN o IN_PROGRESS si se proporciona.
incidente no encontrado: <id>.
reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior a created_at de un incidente devuelto.
```

**Rationale**: Un contrato espejo permite comprobar paridad con `response.json() == json.loads(result.stdout)`, la práctica ya usada en Hitos 001 y 002. Los errores con texto idéntico evitan que REST y CLI divergean en mensajes.

**Alternatives considered**:

- Contratos distintos por canal: rechazado; contradice FR-019 y la constitución.
- Códigos de error solo numéricos: rechazado; no permiten verificar paridad semántica.
- Endpoints anidados bajo `/triage`: rechazado; el alta y la consulta de ciclo de vida no son triaje.

## 7. Verificación BDD

**Decision**: `tests/test_spec_003_lifecycle_sla.py` contiene cinco escenarios BDD, cada uno como prueba `pytest`, con `build_stack()` que inyecta el mismo repositorio en el servicio y el mismo servicio en API y CLI:

1. **Registro mínimo y paridad**: solo `title` y `raw_text`; defaults de ID, `created_at` y `status`; respuesta idéntica en REST y CLI y persistencia recuperable por ID.
2. **Aviso por `duplicate_group_key`**: un incidente en `OPEN`, uno en `IN_PROGRESS`, uno en `ESCALATION_REQUIRED` y uno `RESOLVED` con la misma clave; el aviso incluye solo los tres no resueltos, sin repetidos ni el propio incidente, igual en ambos canales.
3. **SLA P0 continuo**: creado a las 10:00, referencia 11:01; 61 minutos transcurridos, incumplimiento y escalamiento.
4. **SLA P2 en límite exacto**: lunes 08:00 a 16:00; 480 transcurridos, 0 restantes y sin incumplimiento.
5. **SLA P2 con fin de semana**: viernes 17:00 a lunes 09:00; 120 minutos hábiles transcurridos, 360 restantes, sin incumplimiento y resultado idéntico en REST y CLI.

El escenario 5 es obligatorio porque fija la interpretación de la ventana hábil de ADR-002 y el valor restante esperado. Las compuertas complementarias son `uv run pytest`, `uv run ruff check .` y las verificaciones de superficie compartida indicadas en `AGENTS.md`.

**Rationale**: Cinco escenarios acotados cubren registro, aviso y los límites SLA más frágiles sin fragmentar la paridad REST/CLI en pruebas separadas. Cada escenario sigue la skill `bdd-acceptance` con Given/When/Then y compara las dos respuestas observables.

**Alternatives considered**:

- Una prueba por valor límite: rechazado; el usuario pidió cinco escenarios y generaría ruido sin nueva cobertura de comportamiento.
- Probar solo el servicio: rechazado; la constitución exige evidencia de equivalencia REST/CLI.
- Sembrar datos directamente con SQL: rechazado; el repositorio es un puerto y las pruebas deben ejercitar los casos de uso.
