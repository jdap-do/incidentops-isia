# Compose Contract: postgres-container-runtime

**Feature**: `specs/004-postgres-container-runtime/spec.md`

**Date**: 2026-11-24

## Services

| Service | Contract |
|---|---|
| `db` | Imagen `postgres:16-alpine`; usa `POSTGRES_USER`, `POSTGRES_PASSWORD` y `POSTGRES_DB`; volumen persistente montado en `/var/lib/postgresql/data`; healthcheck con `pg_isready`. |
| `api` | Construida desde `Dockerfile`; recibe `DATABASE_URL=postgresql://...@db:5432/...`; publica `${API_PORT:-8000}:8000`; healthcheck HTTP sobre `http://127.0.0.1:8000/health`. |

## Startup ordering

- `api.depends_on.db.condition` debe ser `service_healthy`.
- La API no debe iniciarse mientras `db` esté `starting` o `unhealthy`.
- Tras un reinicio limpio de la pila, la API debe repetir la comprobación real contra la base recién iniciada.

## Persistence

- El volumen `postgres_data` debe conservar los datos cuando se usa `docker compose down` sin `-v`.
- `docker compose down -v --remove-orphans` es el estado limpio para la verificación reproducible.

## Verification signals

- `docker compose ps` muestra `db` y `api` en estado `healthy`.
- La configuración YAML puede verificarse sin Docker mediante un test estático que compruebe imagen, volumen, ambos healthchecks y la condición `service_healthy`.
- La verificación real debe mostrar `GET /health` con `200` y el contrato de éxito, y CLI `health` con el mismo JSON y código `0`.

## Trazabilidad

- FR-009 y FR-010: `spec.md:102-103`
- SC-004: `spec.md:119`
- ADR-004: `docs/adr/004-persistencia-postgresql-y-runtime-contenedores.md:30`
