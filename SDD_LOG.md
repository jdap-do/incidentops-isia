# SDD_LOG.md — IncidentOps, Semana 2

- **Estudiante:** José David Anacona
- **Fecha:** 24 de noviembre de 2026
- **Herramienta y modelo:** OpenCode con Big Pickle para la ejecución del flujo Spec Kit y las validaciones reportadas.

## Flujo de trabajo y decisiones

| Hito | Alcance | Evidencia |
| --- | --- | --- |
| 001 | Triaje de incidentes por REST y CLI. | Commit `157ce47` |
| 002 | Resumen de incidentes activos y evaluación de SLA. | Commit `ed0773c` |
| 003 | Registro, consulta, aviso de duplicados y evaluación individual de SLA. | [Especificación y aclaraciones](specs/003-incident-lifecycle-sla/spec.md) · `a4bf21a` |
| 004 | Persistencia SQLite/PostgreSQL y ejecución con Docker Compose. | [Especificación](specs/004-postgres-container-runtime/spec.md) · [ADR 004](docs/adr/004-persistencia-postgresql-y-runtime-contenedores.md) · `5d2d615` |

En el Hito 003, `/speckit.clarify` fijó que la severidad se deriva del texto normalizado, el alta admite `OPEN` e `IN_PROGRESS` y el identificador es opcional. El aviso reutiliza `duplicate_group_key` e incluye incidentes equivalentes en `ESCALATION_REQUIRED` junto con los demás estados abiertos. El análisis inicial detectó requisitos sin tareas y criterios que necesitaban precisión. Se agregaron pruebas y verificaciones de aceptación, de 29 a 34 tareas.

En el Hito 004, el análisis detectó señales contradictorias sobre el arranque con una `DATABASE_URL` inválida. Se acordó que la API arranca, `GET /health` responde 503 y la CLI termina con código 1. La ausencia de la variable selecciona SQLite en memoria. También se exigió un `SELECT 1` real en PostgreSQL y se precisaron los healthchecks de Compose. La revisión posterior encontró tareas para los 17 requisitos y cero hallazgos altos o críticos.

## Comparación de enfoques

| Aspecto | Asistencia mediante prompts | Spec-Driven Development |
| --- | --- | --- |
| Contexto | Se aporta por turno, como en la revisión inicial de triaje y SLA. | Se conserva en la constitución, las especificaciones, los contratos y las tareas. |
| Revisión | Se contrasta la respuesta con ejemplos y pruebas del dominio. | Se revisa la coherencia entre requisitos y tareas antes de implementar y se vuelven a ejecutar pruebas al finalizar. |
| Costo | Menor preparación para correcciones focalizadas. | Mayor esfuerzo de documentación, con trazabilidad para cambios que afectan varios adaptadores. |

En términos de Birgitta Böckeler, este ejercicio se aproxima a un uso *spec-anchored*: la especificación se mantiene como referencia junto al código y cambia cuando se resuelve una contradicción. Las decisiones de alcance y la aceptación de la evidencia requieren revisión humana.

Los comandos de Spec Kit ejecutan etapas del flujo. Las skills reúnen pautas reutilizables para redactar ADR, revisar arquitectura hexagonal y formular escenarios BDD. En IncidentOps, REST y CLI llaman a los servicios de aplicación, que dependen del puerto de persistencia. La raíz de composición selecciona SQLite o PostgreSQL mediante `DATABASE_URL`. El ADR 004 conserva la restricción de trabajar sin ORM.

## Evidencia de verificación

| Comando o comprobación | Resultado registrado |
| --- | --- |
| `uv run ruff check .` | Todas las comprobaciones aprobadas. |
| `uv run pytest -v` | 49 aprobadas, 1 omitida por ser opt-in y 1 advertencia de deprecación de Starlette. |
| `uv run pytest -q tests/test_spec_004_compose_live.py` con `RUN_COMPOSE_TESTS=1` | 1 prueba aprobada con Docker activo. |
| `uv run --no-sync python -m src.adapters.inbound.cli health` | `{"status":"ok","database":"connected"}` en SQLite local. |
| `uv run --no-sync python -m src.adapters.inbound.cli summary --reference-time 2026-11-24T12:00:00` | `total_active=0`, `breached_count=0` y `details=[]` con el repositorio local vacío. |
| `docker compose config` | Código 0. Configuración con `api`, `db`, `postgres:16-alpine`, volumen y ambos healthchecks. |
| `docker compose up -d --build --wait` y `docker compose ps` | Arranque limpio en 15,43 s según OpenCode. Ambos servicios quedaron `healthy`. |
| `GET /health` y `docker compose exec -T api uv run --frozen python -m src.adapters.inbound.cli health` | PostgreSQL conectado. HTTP 200, CLI con código 0 y el mismo JSON en ambos canales. |

Las regresiones reportadas incluyeron 10 incidentes de triaje, dos pares de correlación, 16 casos SLA y auditorías de contexto.
