# Feature Specification: Ciclo de vida de incidentes y SLA

**Feature Branch**: `003-incident-lifecycle-sla`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Hito 003 — Ciclo de vida de incidentes y SLA. Operaciones necesita registrar incidentes de forma persistente desde la API y la terminal, recibir un aviso con los identificadores de incidentes equivalentes que sigan abiertos y consultar el estado del SLA de un incidente en una fecha de referencia. Usa el nombre corto incident-lifecycle-sla y redacta criterios de aceptación en Given/When/Then. Limita este paso a la especificación."

## Clarifications

### Session 2026-11-24

- Q: ¿Debe obtenerse la severidad del incidente a partir del texto normalizado del reporte, o debe aceptarse como un dato proporcionado por Operaciones al registrar? → A: Derivar la severidad del texto normalizado del reporte; el registro no acepta una severidad manual.
- Q: ¿Qué regla debe decidir que dos incidentes son equivalentes para el aviso al registrar? → A: Reutilizar la clave de correlación vigente del dominio sobre las señales normalizadas; el aviso incluye los incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` que comparten esa clave.
- Q: ¿Qué estados iniciales debe aceptar el registro de un incidente nuevo? → A: Solo `OPEN` o `IN_PROGRESS`, con `OPEN` por defecto; no se puede indicar `ESCALATION_REQUIRED` ni `RESOLVED` al registrar.
- Q: ¿Qué formato debe tener el identificador del incidente al registrarlo? → A: ID opcional; autogenerar `INC-<HEX8>`; único y no vacío.
- Q: ¿Cuáles campos son obligatorios al registrar un incidente? → A: `title` y `raw_text` son los únicos campos obligatorios; `incident_id`, `created_at` y `status` son opcionales; el componente se deriva del triaje.
- Q: ¿Cómo se determina la equivalencia entre incidentes para el aviso? → A: Por `duplicate_group_key` del dominio, calculada desde el texto normalizado; `title` no interviene en la clave.
- Q: ¿Es `reference_time` obligatorio en la consulta de SLA? → A: No para quien llama; si se omite, el adaptador captura el instante y el servicio recibe un instante explícito.
- Q: ¿Qué datos incluye la confirmación de registro? → A: La vista acordada de `incident_id`, `title`, `component`, `severity`, `status`, `created_at` y `duplicate_group_key`; `raw_text` se persiste pero no se devuelve.
- Q: ¿Puede `resolved_at` enviarse al registrar? → A: No. `resolved_at` solo puede existir en registros sembrados o futuros y se usa para el SLA.
- Q: ¿Qué significa «abierto» para el escalamiento de SLA? → A: Estado distinto de `RESOLVED` (`OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED`); el aviso de equivalentes usa los mismos tres estados.
- Q: ¿Qué estados participan en la búsqueda de duplicados? → A: `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED` que compartan `duplicate_group_key`; se excluyen `RESOLVED` y el incidente recién registrado. El alta sigue aceptando solo `OPEN` o `IN_PROGRESS`, con `OPEN` por defecto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar incidentes desde ambos canales (Priority: P1)

Operaciones crea un incidente indicando solo título y texto del reporte como campos obligatorios. `incident_id`, `created_at` y `status` son opcionales: si no se indica identificador, el sistema lo genera con formato `INC-<HEX8>`; si no se indica fecha de creación, usa el momento del registro; si no se indica estado, usa `OPEN`. El sistema deriva componente y severidad del texto normalizado, conserva el registro y lo pone a disposición de consultas posteriores tanto desde el canal web como desde la terminal.

**Why this priority**: Sin un registro persistente y equivalente en los dos canales, no se puede avisar de incidentes equivalentes ni consultar su SLA de forma fiable.

**Independent Test**: Registrar un incidente desde el canal web y desde la terminal, y verificar en cada caso que una consulta posterior por identificador devuelve exactamente la vista acordada: `incident_id`, `title`, `component`, `severity`, `status`, `created_at` y `duplicate_group_key`, sin `raw_text`.

**Acceptance Scenarios**:

1. **Given** el identificador nuevo `INC-2001`, un `title` y un `raw_text` válidos, **When** Operaciones registra el incidente desde el canal web, **Then** el sistema confirma el registro, lo conserva para consultas posteriores y devuelve `incident_id`, `title`, `component`, `severity`, `status`, `created_at` y `duplicate_group_key`, sin `raw_text`, con la severidad derivada del texto.
2. **Given** los mismos datos de un incidente nuevo, **When** Operaciones lo registra desde la terminal, **Then** la confirmación y los datos recuperables coinciden con los del canal web.
3. **Given** un identificador ya registrado, **When** Operaciones intenta registrar otro incidente con ese identificador, **Then** el sistema rechaza el registro, conserva el registro original y explica el conflicto.
4. **Given** un registro con título o texto del reporte vacío, o con un `status` proporcionado que no sea `OPEN` ni `IN_PROGRESS`, **When** Operaciones intenta registrarlo, **Then** el sistema rechaza el registro y explica qué dato debe corregirse.
5. **Given** un texto del reporte con señales que corresponden a P1 y un identificador que sugiere otra prioridad, **When** Operaciones registra el incidente, **Then** el sistema asigna severidad P1 por el texto y no por el identificador.
6. **Given** un registro sin identificador, **When** Operaciones lo registra desde cualquiera de los dos canales, **Then** el sistema genera un identificador único `INC-<HEX8>`, lo devuelve en la confirmación y lo conserva con el registro.

---

### User Story 2 - Avisar de incidentes equivalentes abiertos (Priority: P2)

Al registrar un incidente, Operaciones recibe un aviso con los identificadores de otros incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` que comparten el `duplicate_group_key` calculado por el dominio desde el texto normalizado del reporte. El aviso excluye `RESOLVED` y el propio incidente, y permite detectar trabajo duplicado sin impedir el registro.

**Why this priority**: Evita que dos personas trabajen en paralelo sobre el mismo problema y reduce la duplicación de esfuerzo desde el momento del alta.

**Independent Test**: Registrar un incidente que comparte la clave de correlación del dominio con incidentes en `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED`, y comprobar que el aviso enumera los identificadores correctos desde cualquiera de los dos canales, sin incluir el propio incidente ni incidentes `RESOLVED`.

**Acceptance Scenarios**:

1. **Given** un incidente abierto `INC-2001` con `duplicate_group_key` `payments-gateway:http-502-outage`, **When** Operaciones registra `INC-2002` con un reporte que produce la misma clave, **Then** la confirmación incluye un aviso con `INC-2001` y permite continuar con el registro de `INC-2002`.
2. **Given** tres incidentes equivalentes, uno en `OPEN`, uno en `IN_PROGRESS` y uno en `ESCALATION_REQUIRED`, y un incidente `RESOLVED` equivalente, **When** Operaciones registra otro incidente equivalente desde la terminal, **Then** el aviso contiene los tres identificadores no resueltos, sin repetirlos, sin incluir el resuelto ni el incidente recién registrado.
3. **Given** ningún incidente en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` equivalente, **When** Operaciones registra un incidente desde cualquiera de los dos canales, **Then** la confirmación no presenta identificadores de equivalentes.
4. **Given** incidentes con el mismo título pero `duplicate_group_key` distinto, **When** Operaciones registra uno de ellos, **Then** el aviso no incluye los incidentes con otra clave.

---

### User Story 3 - Consultar el estado del SLA en una fecha de referencia (Priority: P3)

Operaciones selecciona un incidente registrado y consulta su estado de SLA para una fecha de referencia que puede omitir. El sistema informa del tiempo transcurrido, el tiempo permitido, el tiempo restante y si el incidente incumple o requiere escalamiento.

**Why this priority**: Convierte el registro persistente en información accionable para priorizar la respuesta y justificar el escalamiento.

**Independent Test**: Registrar un incidente, consultar su SLA en una fecha determinada desde ambos canales y verificar que los valores coinciden con la política vigente y con la fecha de cierre cuando exista.

**Acceptance Scenarios**:

1. **Given** un incidente P0 creado a las 10:00 y aún abierto, **When** Operaciones consulta su SLA con referencia a las 11:01 del mismo día, **Then** el sistema informa 61 minutos transcurridos, incumplimiento y escalamiento.
2. **Given** un incidente P2 creado el lunes a las 08:00, **When** Operaciones consulta su SLA con referencia a las 16:00 del mismo lunes, **Then** el sistema informa 480 minutos transcurridos y ningún incumplimiento, porque el límite exacto no cuenta como incumplimiento.
3. **Given** un incidente P2 creado el viernes a las 17:00, **When** Operaciones consulta su SLA con referencia al lunes a las 09:00, **Then** el sistema informa 120 minutos transcurridos por la ventana hábil y mantiene el resultado igual en ambos canales.
4. **Given** un incidente con fecha de cierre anterior a la fecha de referencia, **When** Operaciones consulta su SLA, **Then** el cálculo usa la fecha de cierre y no la fecha de referencia.
5. **Given** una fecha de referencia anterior a la creación del incidente, **When** Operaciones intenta consultar el SLA, **Then** el sistema rechaza la consulta, explica el motivo y no devuelve un estado parcial.
6. **Given** un identificador de incidente inexistente, **When** Operaciones consulta su SLA, **Then** el sistema informa que el incidente no existe sin inventar un estado.

---

### Edge Cases

- El identificador proporcionado ya existe y pertenece a otro incidente.
- El identificador se omite y debe generarse automáticamente.
- El identificador proporcionado está vacío.
- El título o el texto del reporte llegan vacíos o solo con espacios.
- El `status` se omite y debe aplicarse `OPEN`, o se proporciona un valor distinto de `OPEN` e `IN_PROGRESS`.
- El texto del reporte no permite derivar una severidad vigente o el estado inicial no es `OPEN` ni `IN_PROGRESS`.
- No se indica fecha de creación y el sistema debe usar el momento del registro.
- La fecha de referencia tiene zona horaria, es ambigua o es anterior a la creación.
- Existen equivalentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` registrados desde el otro canal.
- Un equivalente en `ESCALATION_REQUIRED` debe aparecer en el aviso aunque no pueda indicarse al registrar.
- Un equivalente se resolvió antes del registro del nuevo incidente.
- Dos incidentes comparten título pero producen `duplicate_group_key` distinto.
- El incidente consultado se cerró antes de la fecha de referencia.
- Un incidente alcanza exactamente el límite de su SLA o el umbral del 75 % de escalamiento.
- Se registran muchos incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` y el aviso debe seguir enumerando todos los equivalentes sin repetidos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir registrar incidentes desde el canal web y desde la terminal con `title` y `raw_text` como únicos campos obligatorios; `incident_id`, `created_at` y `status` son opcionales.
- **FR-002**: Cuando el identificador se omita, el sistema DEBE generar uno único con formato `INC-<HEX8>`; cuando se proporcione, DEBE rechazarlo si está vacío o ya existe y NO DEBE sobrescribir el registro anterior.
- **FR-003**: Todo registro válido DEBE quedar disponible para consultas posteriores desde cualquiera de los dos canales.
- **FR-004**: El sistema DEBE validar que `title` y `raw_text` no estén vacíos; si se proporciona `status`, DEBE ser `OPEN` o `IN_PROGRESS`; si se omite, DEBE aplicar `OPEN`.
- **FR-005**: Cuando se omita la fecha de creación, el sistema DEBE usar el momento del registro como fecha de creación.
- **FR-006**: La confirmación de registro DEBE incluir `incident_id`, `title`, `component`, `severity`, `status`, `created_at` y `duplicate_group_key`; NO DEBE incluir `raw_text`, aunque DEBE conservarse en persistencia.
- **FR-007**: Al registrar, el sistema DEBE usar el `duplicate_group_key` calculado por el dominio desde `raw_text` normalizado y considerar equivalentes solo a los incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` que comparten esa clave; NO DEBE usar `incident_id`, `title` ni una comparación textual de componente y título como regla definitiva.
- **FR-008**: El aviso DEBE incluir los identificadores de todos los incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` que comparten la clave de correlación calculada, sin duplicados, sin incluir los `RESOLVED` y sin incluir el incidente recién registrado.
- **FR-009**: Cuando no haya equivalentes en `OPEN`, `IN_PROGRESS` ni `ESCALATION_REQUIRED`, el registro DEBE completarse sin presentar identificadores de equivalentes.
- **FR-010**: El aviso de equivalentes DEBE tener el mismo contenido cuando el registro se realiza desde el canal web o desde la terminal.
- **FR-011**: El sistema DEBE permitir consultar el SLA de un incidente registrado mediante su identificador y una fecha de referencia opcional; si se omite, el adaptador captura el instante y el servicio recibe un instante explícito.
- **FR-012**: La consulta de SLA DEBE informar minutos transcurridos, minutos permitidos, minutos restantes, si hay incumplimiento y si requiere escalamiento.
- **FR-013**: El cálculo DEBE seguir la política de SLA vigente: tiempo continuo para P0 y P1, y tiempo de lunes a viernes de 08:00 a 18:00 para P2 y P3.
- **FR-014**: Un incidente DEBE contarse como incumplido solo cuando el tiempo transcurrido supera estrictamente el permitido; alcanzar el límite exacto NO DEBE contarse como incumplimiento.
- **FR-015**: Un incidente DEBE marcarse para escalamiento al alcanzar el 75 % del tiempo permitido y DEBE conservar esa indicación aunque ya exista incumplimiento mientras su estado no sea `RESOLVED` (`OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED`).
- **FR-016**: Cuando exista fecha de cierre, el cálculo DEBE usarla en lugar de la fecha de referencia.
- **FR-017**: El sistema DEBE rechazar fechas de referencia con zona horaria o anteriores a la creación del incidente, y NO DEBE devolver un estado parcial.
- **FR-018**: La consulta de un identificador inexistente DEBE informar que el incidente no existe.
- **FR-019**: Para la misma entrada válida, el canal web y la terminal DEBEN producir la misma confirmación de registro, el mismo aviso de equivalentes y el mismo estado de SLA.
- **FR-020**: El sistema DEBE derivar la severidad del texto normalizado del reporte, NUNCA del identificador, y DEBE rechazar el registro cuando no pueda derivar una severidad vigente.

### Key Entities *(include if feature involves data)*

- **Registro de incidente**: `title` y `raw_text` obligatorios; identificador único y no vacío, proporcionado o generado con formato `INC-<HEX8>`; componente y severidad derivados; `created_at` y `status` opcionales; `resolved_at` no se acepta en el alta y solo puede existir en registros sembrados o futuros.
- **Vista de confirmación**: `incident_id`, `title`, `component`, `severity`, `status`, `created_at` y `duplicate_group_key`; `raw_text` se conserva en persistencia pero no se expone en la confirmación ni en la consulta.
- **Regla de derivación de severidad**: señales normalizadas del texto del reporte que determinan la severidad; el identificador del incidente no interviene.
- **Aviso de equivalentes**: lista de identificadores de incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` que comparten la clave de correlación del incidente que se está registrando; excluye `RESOLVED` y el propio incidente.
- **Regla de equivalencia**: `duplicate_group_key` calculado por el dominio desde `raw_text` normalizado; incluye los tres estados no `RESOLVED` indicados, excluye el incidente recién registrado y no usa `incident_id` ni `title`.
- **Consulta de SLA**: identificador del incidente y fecha de referencia opcional para quien llama; el servicio evalúa siempre con un instante resuelto.
- **Estado de SLA**: minutos transcurridos, permitidos y restantes, indicación de incumplimiento, indicación de escalamiento e instante efectivo usado en el cálculo.
- **Política de SLA**: límites por severidad, ventana de cómputo aplicable y umbral de escalamiento ya vigentes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de los registros válidos realizados desde ambos canales queda disponible para una consulta posterior por identificador con la misma vista de datos acordada: `incident_id`, `title`, `component`, `severity`, `status`, `created_at` y `duplicate_group_key`, sin `raw_text`.
- **SC-002**: El 100 % de los incidentes equivalentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` aparece en el aviso al registrar, sin identificadores repetidos, sin incluir incidentes `RESOLVED` y sin incluir el incidente recién registrado.
- **SC-003**: El 100 % de las consultas de SLA sobre casos límite acordados —límite exacto, 75 % de escalamiento, fin de semana, cierre anterior a la referencia— coincide con la política de SLA vigente en ambos canales.
- **SC-004**: El 100 % de las operaciones de registro y consulta produce el mismo resultado observable en el canal web y en la terminal para la misma entrada.
- **SC-005**: Al menos el 95 % de los operadores obtiene la confirmación de registro, el aviso de equivalentes o el estado de SLA en una sola interacción y en menos de 30 segundos; el 95 % es un resultado operativo y el límite verificable en este hito es el tiempo de respuesta inferior a 30 segundos.
- **SC-006**: El sistema mantiene completos y sin duplicados los avisos de equivalentes cuando existen al menos 1.000 incidentes en `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED` con la misma clave.

## Assumptions

- Operaciones ya tiene acceso al canal web y a la terminal; la autenticación y los permisos quedan fuera de este feature.
- El identificador del incidente es opcional; si Operaciones lo omite, el sistema lo genera con formato `INC-<HEX8>`. Si se proporciona, debe ser único y no vacío. El sistema no lo usa para derivar la severidad ni para correlacionar incidentes.
- La severidad no se suministra como dato independiente; se deriva del texto normalizado del reporte según las reglas vigentes del dominio.
- A los efectos de este feature, «abiertos» para el aviso de equivalentes significa `OPEN`, `IN_PROGRESS` y `ESCALATION_REQUIRED`; `RESOLVED` queda fuera del aviso.
- Para el escalamiento de SLA, «no resuelto» significa cualquier estado distinto de `RESOLVED`: `OPEN`, `IN_PROGRESS` o `ESCALATION_REQUIRED`; coincide con los estados considerados en el aviso.
- El alta de un incidente NO DEBE crear estados `ESCALATION_REQUIRED` ni `RESOLVED`; `ESCALATION_REQUIRED` puede existir en datos sembrados y participa en el aviso, sin ampliar los estados aceptados al registrar.
- `RESOLVED` queda fuera del aviso de equivalentes.
- `status` es opcional al registrar; si se omite, se aplica `OPEN`. Si se proporciona, solo se aceptan `OPEN` o `IN_PROGRESS`.
- La equivalencia se rige por el `duplicate_group_key` calculado por el dominio desde `raw_text`; `title` y el identificador no intervienen.
- Las fechas son locales sin zona horaria; no se contemplan festivos ni conversiones entre zonas.
- Si no se indica fecha de creación, se usa el momento del registro.
- La consulta de SLA permite omitir `reference_time`; el adaptador captura el instante de consulta y se lo pasa explícitamente al servicio, que nunca lee el reloj.
- Registrar un incidente no cambia su estado ni cierra incidentes existentes; los cambios de ciclo de vida distintos del alta quedan fuera de alcance.
- La política de SLA, las severidades y los estados vigentes son la fuente autorizada; este feature no crea nuevas reglas.
