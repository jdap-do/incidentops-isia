# Feature Specification: Resumen de incidentes activos

**Feature Branch**: `002-resumen-incidentes-activos`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "El equipo de Operaciones necesita consultar desde la web y la terminal un resumen de los incidentes activos (OPEN e IN_PROGRESS). El resumen debe mostrar el total activo, cuántos incumplieron su SLA y el detalle de cada incidente: título, componente, severidad, estado, minutos transcurridos y si requiere escalamiento. Debe permitir filtrar por componente."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar el resumen desde web y terminal (Priority: P1)

Operaciones abre el resumen desde la web o desde la terminal y obtiene una vista
única de los incidentes que siguen activos. La vista muestra cuántos incidentes
están activos, cuántos incumplieron su SLA y una fila por incidente con título,
componente, severidad, estado, minutos transcurridos y necesidad de escalamiento.
Ambos canales presentan exactamente los mismos datos para la misma situación.

**Why this priority**: Es el valor central de la petición: sin una vista
consistente y compartida, Operaciones no puede priorizar la operación en curso.

**Independent Test**: Con un conjunto mixto de incidentes activos y resueltos,
consultar el resumen sin filtro desde ambos canales usando el mismo instante de
referencia y comprobar totales, conteo de incumplimientos y filas.

**Acceptance Scenarios**:

1. **Given** existen incidentes en estado OPEN e IN_PROGRESS y otros resueltos,
   **When** Operaciones consulta el resumen desde la web, **Then** ve el total de
   activos, el número que incumplió su SLA y una fila por cada incidente activo con
   todos los campos solicitados.
2. **Given** el mismo conjunto de incidentes y el mismo instante de referencia,
   **When** Operaciones consulta el resumen desde la terminal, **Then** obtiene los
   mismos totales y los mismos valores de detalle que en la web.
3. **Given** no hay incidentes activos, **When** se consulta el resumen, **Then**
   el total activo y el conteo de incumplimientos son cero y no se muestra ninguna
   fila de detalle.

---

### User Story 2 - Filtrar el resumen por componente (Priority: P2)

Operaciones necesita enfocarse en un componente concreto, por ejemplo pagos o
identidad. Al aplicar el filtro, tanto los totales como las filas de detalle se
recalculan exclusivamente sobre los incidentes activos de ese componente.

**Why this priority**: Reduce el ruido en operaciones con muchos incidentes y
permite pasar de la vista general a la revisión de un área responsable.

**Independent Test**: Con incidentes activos de al menos dos componentes,
filtrar por uno de ellos desde cada canal y verificar que solo aparecen sus
incidentes y que los totales coinciden con las filas mostradas.

**Acceptance Scenarios**:

1. **Given** hay incidentes activos de los componentes pagos e identidad,
   **When** Operaciones filtra el resumen por pagos, **Then** solo se muestran los
   incidentes de pagos y el total activo y el conteo de incumplimientos se calculan
   sobre ese subconjunto.
2. **Given** un componente se escribe con distinta capitalización o espacios
   circundantes, **When** se aplica el filtro, **Then** se reconocen los incidentes
   de ese componente.
3. **Given** un filtro de componente que no coincide con ningún incidente activo,
   **When** se consulta el resumen, **Then** se devuelve un detalle vacío con total
   activo y conteo de incumplimientos en cero.

---

### User Story 3 - Interpretar SLA y escalamiento con criterio uniforme (Priority: P3)

Operaciones distingue entre incidentes que consumieron exactamente su tiempo
permitido, incidentes que ya lo superaron e incidentes que requieren escalamiento.
La interpretación es la misma en la web y en la terminal y respeta la política de
SLA vigente para cada severidad.

**Why this priority**: Evita priorizar mal incidentes en el límite del SLA o
perder escalamientos que siguen vigentes después del incumplimiento.

**Independent Test**: Evaluar incidentes en el límite exacto, justo por encima del
límite y al umbral de escalamiento, y comprobar los minutos transcurridos y las
indicaciones de incumplimiento y escalamiento en ambos canales.

**Acceptance Scenarios**:

1. **Given** un incidente activo cuyo tiempo transcurrido es exactamente el
   permitido para su severidad, **When** se genera el resumen, **Then** no se cuenta
   como incumplimiento.
2. **Given** un incidente activo cuyo tiempo transcurrido supera el permitido,
   **When** se genera el resumen, **Then** se cuenta como incumplimiento y se
   indica que requiere escalamiento.
3. **Given** un incidente de severidad P2 que abarca noche y fin de semana,
   **When** se calculan sus minutos transcurridos, **Then** se contabiliza solo la
   ventana de atención aplicable y el resultado coincide en ambos canales.

---

### Edge Cases

- No existen incidentes activos: total y conteo en cero, detalle vacío.
- El filtro no coincide con ningún componente activo: resultado vacío, no un error.
- El filtro se omite o llega vacío: se muestra el resumen completo sin filtrar.
- Un incidente alcanza exactamente el límite de su SLA: no cuenta como incumplimiento.
- Un incidente supera el SLA y permanece abierto: incumplimiento y escalamiento
  pueden mostrarse a la vez.
- Un incidente resuelto incumplió antes de cerrarse: no aparece en el resumen activo.
- Las consultas se hacen en instantes distintos: los valores pueden cambiar; la
  paridad entre canales se evalúa usando el mismo instante de referencia.
- `reference_time` se omite: el adaptador captura el instante de consulta, lo pasa
  explícitamente al servicio y la respuesta refleja ese valor.
- `reference_time` es malformado, tiene zona horaria o es anterior al `created_at` de
  un incidente devuelto: se rechaza antes de calcular; REST responde 422 con `detail`
  y CLI termina con código 1, `stdout` vacío y el mismo mensaje en `stderr`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE incluir únicamente incidentes cuyo estado sea OPEN o
  IN_PROGRESS.
- **FR-002**: El resumen DEBE mostrar el total de incidentes activos y cuántos de
  ellos incumplieron su SLA, calculados sobre el conjunto efectivamente mostrado.
- **FR-003**: Cada incidente del detalle DEBE mostrar título, componente,
  severidad, estado, minutos transcurridos e indicación de si requiere escalamiento.
- **FR-004**: La web y la terminal DEBEN producir los mismos totales y los mismos
  valores de detalle para el mismo instante de referencia y el mismo filtro.
- **FR-005**: Operaciones DEBE poder filtrar el resumen por componente desde
  cualquiera de los dos canales.
- **FR-006**: El filtro DEBE aplicarse tanto a las filas de detalle como al total
  activo y al conteo de incumplimientos.
- **FR-007**: El filtro DEBE reconocer el nombre del componente sin distinguir
  mayúsculas de minúsculas ni espacios circundantes.
- **FR-008**: Un filtro omitido o vacío DEBE devolver todos los incidentes activos.
- **FR-009**: Un filtro que no coincida con ningún componente activo DEBE devolver
  cero incidentes, total cero y conteo de incumplimientos cero.
- **FR-010**: Cuando no hay incidentes activos, el resumen DEBE devolver total cero,
  conteo de incumplimientos cero y detalle vacío.
- **FR-011**: Los minutos transcurridos y el incumplimiento DEBEN seguir la política
  de SLA vigente por severidad: cómputo continuo para P0 y P1, y cómputo de lunes a
  viernes de 08:00 a 18:00 para P2 y P3.
- **FR-012**: Un incidente DEBE contarse como incumplimiento solo cuando su tiempo
  transcurrido supera estrictamente el permitido; alcanzar el límite exacto no
  constituye incumplimiento.
- **FR-013**: Un incidente activo DEBE marcarse como escalado cuando alcanza el 75 %
  del tiempo permitido, y esa indicación DEBE permanecer aunque ya exista
  incumplimiento.
- **FR-014**: El resumen DEBE calcularse para un instante de referencia explícito.
  Si el operador lo omite, el adaptador de entrada DEBE capturar el momento de la
  consulta y pasarlo explícitamente al caso de uso; la respuesta DEBE mostrar el
  instante efectivo.
- **FR-015**: Las filas DEBEN ordenarse por severidad de P0 a P3, luego por minutos
  transcurridos de mayor a menor y, en caso de empate, por título de forma
  ascendente.
- **FR-016**: Un `reference_time` malformado, con zona horaria o anterior a
  `created_at` de un incidente devuelto DEBE rechazarse antes de calcular el resumen:
  la web DEBE responder 422 con `detail` y la terminal DEBE terminar con código 1,
  `stdout` vacío y el mismo mensaje en `stderr`.

### Key Entities *(include if feature involves data)*

- **Resumen de incidentes activos**: total de incidentes activos, número de
  incumplimientos de SLA, instante de referencia, filtro aplicado y lista de detalle.
- **Detalle de incidente activo**: título, componente, severidad, estado, minutos
  transcurridos e indicación de escalamiento.
- **Política de SLA**: tiempo permitido por severidad, ventana de cómputo aplicable
  y umbral de escalamiento.
- **Filtro de componente**: nombre del componente, normalizado para comparación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de los incidentes en estado OPEN o IN_PROGRESS aparece en el
  resumen y ningún incidente resuelto aparece en él.
- **SC-002**: Para el mismo instante de referencia y el mismo filtro, la web y la
  terminal muestran totales, conteos y valores de detalle idénticos en el 100 % de
  los escenarios verificados.
- **SC-003**: En el 100 % de los casos con filtro, el total activo coincide con el
  número de filas devueltas y todas las filas pertenecen al componente solicitado.
- **SC-004**: El 100 % de los incidentes exactamente en el límite de su SLA se
  reporta sin incumplimiento y el 100 % de los que lo superan se cuenta como
  incumplimiento.
- **SC-005**: El 90 % de los operadores encuentra un incidente incumplido en menos
  de 30 segundos desde que abre el resumen, usando la web o la terminal.
- **SC-006**: El resumen muestra el detalle completo de hasta 1.000 incidentes
  activos sin omisiones ni filas duplicadas.

## Assumptions

- Operaciones ya tiene acceso a los canales web y terminal existentes; la
  autenticación y los permisos quedan fuera de este feature.
- Los canales web y terminal son los ya disponibles en IncidentOps; no se incorpora
  un canal nuevo en esta entrega.
- El instante de referencia es un `datetime` local naive indicado explícitamente para
  comparaciones deterministas; si se omite, el adaptador captura el momento de la
  consulta y lo pasa al servicio.
- El servicio no consulta el reloj: recibe siempre un `reference_time` explícito.
  Un valor malformado, con zona horaria o anterior a un `created_at` se rechaza antes
  de calcular, con paridad entre REST y CLI.
- El filtro por componente compara el nombre completo, ignorando capitalización y
  espacios circundantes; las coincidencias parciales quedan fuera de alcance.
- La ordenación de las filas es determinista según FR-015 para evitar diferencias
  entre canales.
- La política de SLA, las severidades y los estados vigentes son la fuente
  autorizada; no se crean nuevos estados ni reglas de SLA en este feature.
- No se contemplan festivos ni conversiones de zona horaria más allá de lo ya
  definido en la política de SLA existente.
- Los incidentes resueltos y el ciclo de vida de registro quedan fuera del alcance;
  este feature solo consulta el estado activo.
