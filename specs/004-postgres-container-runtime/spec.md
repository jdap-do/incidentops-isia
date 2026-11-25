# Feature Specification: postgres-container-runtime

**Feature Branch**: `004-postgres-container-runtime`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Hito 004 — Operaciones necesita ejecutar IncidentOps con una base de datos dedicada en un entorno reproducible y verificar si la aplicación puede conectarse a ella. SQLite debe seguir siendo la opción local por defecto y PostgreSQL debe poder seleccionarse por configuración. La API y la CLI deben verificar la conexión con una consulta real. Usa el nombre corto postgres-container-runtime y registra cuatro escenarios Given/When/Then: conexión disponible, conexión fallida, selección del motor y arranque de la API con PostgreSQL mediante Docker Compose. Limita este paso a la especificación."

## Clarifications

### Session 2026-11-24

- Q: ¿Qué consulta y respuestas usa la verificación de la API? → A: `GET /health` ejecuta `SELECT 1` sobre la base configurada; con éxito devuelve `200` con `{"status":"ok","database":"connected"}`, y con fallo devuelve `503` con `{"status":"error","database":"unavailable"}`.
- Q: ¿Cómo se comporta la verificación desde la CLI? → A: el comando `health` devuelve el mismo JSON que la API y termina con código `0` si hay conexión o `1` si falla.
- Q: ¿Qué selecciona el motor de persistencia y cuál es el valor por defecto? → A: `DATABASE_URL` selecciona PostgreSQL o SQLite; si está ausente o vacía, el motor es SQLite en memoria.
- Q: ¿Qué debe ocurrir antes de iniciar la API en el entorno reproducible? → A: Docker Compose debe esperar a que el servicio PostgreSQL esté saludable antes de iniciar la API.
- Q: ¿Cómo se alinea este contrato con ADR-004? → A: la comprobación usa `SELECT 1` sobre el adaptador seleccionado y la composición arranca `api` solo después de que `db` esté saludable, tal como describe ADR-004.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verificar conexión disponible (Priority: P1)

Operaciones necesita confirmar que IncidentOps puede usar la base de datos seleccionada antes de confiar en los incidentes registrados. La API y la CLI deben ofrecer una verificación observable basada en una consulta real, no en una suposición.

**Why this priority**: Sin una confirmación fiable de conexión, cualquier operación posterior sobre incidentes podría realizarse contra un motor inaccesible o distinto al esperado.

**Independent Test**: Se puede verificar ejecutando `GET /health` y el comando `health` contra una base accesible y comprobando que ambos devuelven el mismo cuerpo JSON y el código de éxito acordado.

**Acceptance Scenarios**:

1. **Given** que `DATABASE_URL` apunta a una base accesible y la configuración es válida, **When** se llama a `GET /health` y se ejecuta `health` en la CLI, **Then** cada consulta ejecuta `SELECT 1` sobre la base configurada, la API devuelve `200` con `{"status":"ok","database":"connected"}` y la CLI imprime el mismo JSON y termina con código `0`.

---

### User Story 2 - Detectar conexión fallida (Priority: P1)

Operaciones necesita distinguir claramente entre una conexión disponible y una fallida para actuar antes de operar sobre incidentes.

**Why this priority**: Un falso éxito ocultaría problemas de disponibilidad, credenciales o configuración y dejaría a los usuarios trabajando sobre una base inalcanzable.

**Independent Test**: Se puede verificar haciendo la comprobación por API y por CLI contra un motor inaccesible o mal configurado y comprobando que ninguna de las dos devuelve éxito.

**Acceptance Scenarios**:

1. **Given** que la base configurada no está accesible, la configuración es inválida o `SELECT 1` falla, **When** se llama a `GET /health` y se ejecuta `health` en la CLI, **Then** la API devuelve `503` con `{"status":"error","database":"unavailable"}`, la CLI imprime el mismo JSON y termina con código `1`, y ninguna respuesta expone secretos.

---

### User Story 3 - Seleccionar el motor de persistencia (Priority: P2)

Operaciones necesita ejecutar IncidentOps localmente con SQLite en memoria por defecto y poder elegir PostgreSQL mediante `DATABASE_URL` sin cambiar el comportamiento funcional de la aplicación.

**Why this priority**: Mantiene la experiencia local simple y determinista mientras habilita el uso de una base dedicada en entornos reproducibles.

**Independent Test**: Se puede verificar iniciando la aplicación con `DATABASE_URL` ausente o vacía, con una URL PostgreSQL y con un esquema inválido o no soportado, comprobando el motor efectivo y que el último caso mantiene la API disponible con `GET /health` en `503` y `health` con código `1`.

**Acceptance Scenarios**:

1. **Given** una ejecución con `DATABASE_URL` ausente o vacía, otra con `DATABASE_URL` apuntando a PostgreSQL y otra con un esquema inválido o no soportado, **When** se inicia IncidentOps en cada caso y se solicitan `GET /health` y `health` en la CLI, **Then** la primera usa SQLite en memoria y devuelve el contrato de éxito, la segunda usa PostgreSQL y devuelve el contrato de éxito, y la tercera no selecciona SQLite como alternativa: la API puede iniciar, `GET /health` devuelve `503` con `{"status":"error","database":"unavailable"}` y la CLI imprime el mismo JSON y termina con código `1`.

---

### User Story 4 - Arranque reproducible de la API con PostgreSQL (Priority: P2)

Operaciones necesita un entorno reproducible que levante la API y una base PostgreSQL dedicada como servicios coordinados, y comprobar que la API puede conectarse antes de considerar el arranque correcto.

**Why this priority**: Reduce la variación entre entornos y evita que la API quede disponible antes de que la base dedicada esté lista.

**Independent Test**: Se puede verificar levantando la definición de contenedores desde un estado limpio, comprobando que la base PostgreSQL dedicada alcanza estado saludable antes de que arranque la API y que `GET /health` devuelve el contrato de éxito.

**Acceptance Scenarios**:

1. **Given** una definición de Docker Compose con un servicio PostgreSQL dedicado con healthcheck y una API configurada con `DATABASE_URL` apuntando a ese servicio, **When** el operador arranca la pila, **Then** la API no se inicia hasta que PostgreSQL está saludable y, una vez iniciada, `GET /health` ejecuta `SELECT 1` y devuelve `200` con `{"status":"ok","database":"connected"}`.

---

### Edge Cases

- `DATABASE_URL` ausente o vacía: el sistema debe usar SQLite en memoria por defecto.
- `DATABASE_URL` con esquema `sqlite:`: debe seleccionar SQLite; con esquema `postgresql:`, debe seleccionar PostgreSQL.
- El esquema de `DATABASE_URL` es desconocido o no soportado: no se selecciona SQLite como alternativa; la API debe poder iniciar y `GET /health` debe devolver `503` con `{"status":"error","database":"unavailable"}`, mientras que `health` imprime el mismo JSON y termina con código `1`.
- PostgreSQL existe pero aún no acepta conexiones, las credenciales son incorrectas o la red no está disponible: `GET /health` debe devolver `503` y la CLI debe terminar con código `1`.
- `SELECT 1` no llega a ejecutarse: el sistema no debe devolver el contrato de éxito.
- La API y la CLI devuelven cuerpos JSON distintos o códigos de salida/estado inconsistentes para la misma configuración y estado de la base: debe tratarse como fallo de este hito.
- La configuración contiene credenciales o datos sensibles: ningún mensaje de verificación debe exponer sus valores.
- La pila de contenedores se reinicia desde cero: la API debe esperar de nuevo a que PostgreSQL esté saludable antes de arrancar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE usar SQLite en memoria como motor por defecto cuando `DATABASE_URL` esté ausente o vacía.
- **FR-002**: El sistema DEBE usar `DATABASE_URL` para seleccionar SQLite o PostgreSQL; las URL `sqlite:` DEBEN seleccionar SQLite y las URL `postgresql:` DEBEN seleccionar PostgreSQL.
- **FR-003**: Cuando `DATABASE_URL` esté ausente o vacía, el sistema DEBE usar SQLite en memoria como valor por defecto; cuando el esquema sea inválido o no soportado, NO DEBE seleccionar SQLite como alternativa, la API DEBE poder iniciar y `GET /health` DEBE devolver `503` con `{"status":"error","database":"unavailable"}`, mientras que la CLI DEBE imprimir el mismo JSON y terminar con código `1` según FR-007.
- **FR-004**: La API DEBE exponer `GET /health` y la CLI DEBE exponer el comando `health` para verificar la conexión contra el motor seleccionado.
- **FR-005**: `GET /health` y el comando `health` DEBEN ejecutar `SELECT 1` sobre la base configurada y DERIVAR su resultado únicamente del desenlace de esa consulta.
- **FR-006**: Cuando `SELECT 1` tiene éxito, la API DEBE devolver `200` con `{"status":"ok","database":"connected"}` y la CLI DEBE imprimir el mismo JSON y terminar con código `0`.
- **FR-007**: Cuando `SELECT 1` falla o no puede ejecutarse, la API DEBE devolver `503` con `{"status":"error","database":"unavailable"}`, la CLI DEBE imprimir el mismo JSON y terminar con código `1`, y ninguna salida DEBE exponer secretos.
- **FR-008**: Para configuraciones y estados de base idénticos, la API y la CLI DEBEN producir el mismo cuerpo JSON de verificación.
- **FR-009**: Docker Compose DEBE definir un servicio PostgreSQL dedicado con healthcheck y un servicio de API.
- **FR-010**: Docker Compose NO DEBE iniciar la API hasta que el servicio PostgreSQL esté saludable, y DEBE proporcionar a la API una `DATABASE_URL` que apunte a ese servicio.
- **FR-011**: La selección del motor NO DEBE cambiar las reglas de negocio ni el comportamiento observable de las operaciones de incidentes ya especificadas.

### Key Entities *(include if feature involves data)*

- **Motor efectivo**: Motor de persistencia resultante de `DATABASE_URL`; SQLite en memoria cuando la variable está ausente o vacía, SQLite para URL `sqlite:` y PostgreSQL para URL `postgresql:`.
- **Verificación de conexión**: Resultado de ejecutar `SELECT 1` contra el motor efectivo, representado por el mismo JSON en API y CLI, con código de estado HTTP o código de salida según el canal.
- **Entorno reproducible**: Definición de Docker Compose con un servicio PostgreSQL dedicado, healthcheck y una API que arranca solo después de que la base esté saludable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las verificaciones contra una base accesible devuelve `200` con el contrato de éxito en 10 segundos o menos, y la CLI termina con código `0`.
- **SC-002**: El 100 % de los casos de base inaccesible, configuración inválida o `SELECT 1` fallido devuelve `503` con el contrato de error, la CLI termina con código `1` y no hay resultados falsamente exitosos.
- **SC-003**: El 100 % de las parejas de verificación realizadas por ambos canales sobre la misma configuración y estado devuelve el mismo cuerpo JSON.
- **SC-004**: Un operador puede arrancar el entorno reproducible con un único comando documentado, esperar a que PostgreSQL esté saludable y completar la verificación de conexión en 5 minutos o menos desde un estado limpio.
- **SC-005**: Los cuatro escenarios de aceptación Given/When/Then pueden demostrarse sin transformar los datos de incidentes existentes.
- **SC-006**: El 100 % de los mensajes de verificación omiten valores sensibles de la configuración.

## Assumptions

- Este paso se limita a la especificación: no se crean planes, tareas, código ni artefactos de despliegue.
- La ejecución local y las pruebas automatizadas usan SQLite en memoria cuando `DATABASE_URL` está ausente o vacía.
- `DATABASE_URL` es la única fuente de selección del motor; PostgreSQL se usa como base dedicada cuando la URL lo indica y en el entorno reproducible de contenedores.
- Las credenciales y datos de conexión se proporcionan externamente; la especificación no prescribe valores secretos.
- No se introducen nuevas reglas de negocio: triaje, duplicados y SLA conservan su comportamiento ya aceptado.
- Se reutiliza el modelo de datos y el contrato de incidentes existentes; este hito solo añade selección de motor y verificación de conexión.
- La decisión arquitectónica aceptada en ADR-004 y la constitución v1.1.0 son dependencias de este hito.
- Docker Compose es la herramienta de orquestación requerida por Operaciones; su healthcheck de PostgreSQL es condición de arranque de la API, no una opción de despliegue.
