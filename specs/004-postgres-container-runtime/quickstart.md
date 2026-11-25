# Quickstart: postgres-container-runtime

**Feature**: `specs/004-postgres-container-runtime/spec.md`

**Date**: 2026-11-24

## Prerequisites

- Ejecutar todos los comandos desde la raíz del repositorio.
- `uv` disponible.
- Docker con el plugin `docker compose` para la verificación real.
- No usar `python -O` para los módulos SLA.

## Local gates

```bash
uv run ruff check .
uv run pytest
uv run pytest -v tests/test_spec_004_postgres_container_runtime.py
```

Expected: Ruff sin errores; pytest en verde; los cuatro escenarios BDD del Hito 004 ejecutados y la paridad REST/CLI verificada con el mismo service inyectado.

## Regresión del dominio compartido

```bash
uv run python -m src.triage_rules
uv run python -m src.sla_calculator
uv run python -m src.context_audit --symbol evaluate_sla_status
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.context_audit --compare-formats
```

Expected: todas las auditorías terminan sin error. Estas comprobaciones se repiten porque el cambio toca la superficie compartida de persistencia y arranque.

## Verificación real con Docker Compose

En PowerShell sustituye `echo $?` por `$LASTEXITCODE`.

```bash
docker compose down -v --remove-orphans
docker compose config
docker compose up -d --build --wait
docker compose ps
curl -i "http://localhost:${API_PORT:-8000}/health"
docker compose exec -T api uv run --frozen python -m src.adapters.inbound.cli health
```

Expected:

- `docker compose config` muestra `api`, `db`, `postgres:16-alpine`, volumen, ambos healthchecks y `depends_on.db.condition: service_healthy`.
- `docker compose ps` muestra ambos servicios `healthy`.
- `GET /health` devuelve `200` con `{"status":"ok","database":"connected"}`.
- La CLI imprime el mismo JSON y termina con código `0`.
- El tiempo total desde `up` hasta la verificación es `<= 300` segundos (SC-004).

## Fallo de conexión

```bash
docker compose stop db
curl -i "http://localhost:${API_PORT:-8000}/health"
docker compose exec -T api uv run --frozen python -m src.adapters.inbound.cli health
docker compose start db
```

Expected: API `503` con `{"status":"error","database":"unavailable"}`; CLI mismo JSON y código `1`; sin secretos en la salida.

## Limpieza

```bash
docker compose down
```

Para descartar también los datos:

```bash
docker compose down -v --remove-orphans
```

## Referencias

- Contratos: `contracts/health-contract.md`, `contracts/configuration-contract.md`, `contracts/compose-contract.md`
- Modelo de datos: `data-model.md`
- Decisiones técnicas: `research.md`
