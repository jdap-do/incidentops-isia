# Health Contract: postgres-container-runtime

**Feature**: `specs/004-postgres-container-runtime/spec.md`

**Date**: 2026-11-24

## Shared behavior

Ambos canales invocan el mismo caso de uso de aplicación y ejecutan `SELECT 1` real contra la base seleccionada en cada solicitud. El resultado no se cachea y no se deriva del nombre del motor ni de variables de entorno por separado. Ninguna respuesta incluye credenciales, URLs completas ni detalles del driver.

## REST

### `GET /health`

**Success**

- Status: `200`
- Body: `{"status":"ok","database":"connected"}`

**Failure**

- Status: `503`
- Body: `{"status":"error","database":"unavailable"}`

El cuerpo es exacto: sin envoltorio `detail`, campos adicionales ni mensajes de excepción.

## CLI

### `health`

- Escribe en `stdout` el mismo JSON compacto que la API:
  - Éxito: `{"status":"ok","database":"connected"}`
  - Fallo: `{"status":"error","database":"unavailable"}`
- Código de salida: `0` si hay conexión, `1` si falla.
- Cualquier información diagnóstica adicional debe ir a `stderr` y nunca exponer secretos.

## Equivalence

Para la misma configuración y estado de la base, API y CLI deben devolver el mismo objeto JSON. Las pruebas deben comparar `response.json()` con `json.loads(result.stdout)` y verificar `200`/`0` o `503`/`1`.

## Traceability

- FR-004 a FR-008: `spec.md:97-101`
- SC-001 a SC-003 y SC-006: `spec.md:116-121`
- ADR-004: `docs/adr/004-persistencia-postgresql-y-runtime-contenedores.md:30,53`
