# Especificación 001 — Triaje manual (HTTP y CLI)

## Alcance

- H001: clasificar un reporte por solicitud, sin persistencia.
- REST y CLI delegan en el mismo caso de uso: `IncidentService.triage_incident`.
- HTTP: `POST /api/v1/incidents/triage` recibe un objeto JSON con `incident_id` y `raw_text`, ambos obligatorios y de tipo `string`.
- HTTP devuelve `200` con todos los campos de `TriageResult`, incluido `consistency_ratio`.
- CLI: `triage --incident-id ... --raw-text ...` devuelve el mismo resultado en JSON por stdout y termina con código `0`.
- Si algún valor CLI está vacío o contiene solo espacios, muestra un error y termina con código `1`.
- La clave de correlación expresa una coincidencia candidata, no una causa raíz.
- Fuera de alcance: lotes, autenticación, CORS y límites de longitud. Un texto no vacío sin señales conserva el comportamiento actual del clasificador.

## Escenarios

### Escenario 1: HTTP clasifica una caída de pagos con 502

Given el reporte canónico `INC-1001`: «URGENTE: El gateway de pagos devuelve HTTP 502 Bad Gateway en todas las transacciones con tarjeta de crédito desde hace 12 minutos. Ningún comercio puede cobrar.»

When se envía `POST /api/v1/incidents/triage` con `{"incident_id": "INC-1001", "raw_text": "<reporte anterior>"}`

Then la respuesta es `200` e incluye `severity: "P0"`, `component: "payments-gateway"`, `recommended_team: "Backend-Core"` y `duplicate_group_key: "payments-gateway:http-502-outage"`.

> Nota de implementación: la guía espera `payments-gateway:http-502-outage`; el código actual de `src/triage_rules.py` produce `payments-gateway:http-502` para este caso. Resolver la discrepancia durante la implementación.

### Escenario 2: HTTP clasifica una cuenta individual bloqueada con «hoy»

Given el reporte canónico `INC-1002`: «He intentado ingresar a mi cuenta tres veces y ahora aparece bloqueada. Necesito acceder hoy mismo porque debo enviar el informe de cierre a la junta directiva.»

When se envía `POST /api/v1/incidents/triage` con `{"incident_id": "INC-1002", "raw_text": "<reporte anterior>"}`

Then la respuesta es `200` e incluye `severity: "P2"` y `recommended_team: "Security-IAM"`.

### Escenario 3: HTTP rechaza campos vacíos

Given una solicitud a `POST /api/v1/incidents/triage` con `incident_id: ""` o con `raw_text: "   "`

When se envía la solicitud

Then el servicio devuelve `422` y no devuelve un `TriageResult`.

### Escenario 4: CLI devuelve el mismo JSON que HTTP

Given el mismo reporte del escenario 1

When se ejecuta `triage --incident-id INC-1001 --raw-text "<reporte anterior>"`

Then stdout contiene un JSON equivalente al cuerpo de la respuesta HTTP del escenario 1, con `severity: "P0"`, `component: "payments-gateway"`, `recommended_team: "Backend-Core"` y `duplicate_group_key: "payments-gateway:http-502-outage"`, y el proceso termina con código `0`.
