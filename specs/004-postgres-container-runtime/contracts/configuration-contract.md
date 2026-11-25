# Configuration Contract: postgres-container-runtime

**Feature**: `specs/004-postgres-container-runtime/spec.md`

**Date**: 2026-11-24

## `DATABASE_URL`

| Valor | Resultado |
|---|---|
| Variable ausente o cadena vacía | SQLite en memoria (`:memory:`). |
| `sqlite:///:memory:` | SQLite en memoria. |
| `sqlite:///<ruta>` | SQLite en la ruta indicada. |
| `postgresql://...` | PostgreSQL mediante `psycopg[binary]`. |
| Cualquier otro esquema | Error claro de configuración; sin caída silenciosa a SQLite. |

La URL se lee una sola vez en la raíz de composición (`src/bootstrap.py`). Los adaptadores reciben el valor ya resuelto; `src/adapters/outbound/sqlite_repository.py` deja de leer la variable directamente. Las URL programáticas heredadas como `":memory:"` o rutas simples siguen siendo aceptadas por la fábrica SQLite por compatibilidad con pruebas, pero no forman parte del contrato público de `DATABASE_URL`.

## Reglas de fallo

- Un esquema no soportado debe rechazarse con mensaje claro que no incluya contraseñas.
- Si el proceso ya está levantado y la configuración es inválida, `/health` debe devolver `503` y la CLI debe salir con `1`, sin usar SQLite como respaldo.
- Un error de conexión o de `SELECT 1` se traduce a `database: "unavailable"`; nunca se expone el mensaje original del driver en el cuerpo acordado.

## Trazabilidad

- FR-001 a FR-003: `spec.md:94-96`
- Clarificaciones: `spec.md:17,81-83,94-96`
- Constitución IV: `.specify/memory/constitution.md:54-70`
