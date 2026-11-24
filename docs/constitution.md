# Constitución de IncidentOps

## 1. Dominio determinista

- Las reglas de triaje, los equipos válidos, los estados del incidente y la clave de correlación se centralizan como única fuente de verdad.
- La severidad se decide a partir de señales observables del reporte, no de su identificador.
- P0 y P1 operan 24/7.
- P2 y P3 se calculan de lunes a viernes de 08:00 a 18:00.
- El umbral de escalamiento es del 75 % del tiempo permitido.

## 2. Arquitectura hexagonal

- La arquitectura hexagonal se fundamenta en el ADR-003 (`docs/adr/003-arquitectura-hexagonal.md`).
- Las reglas viven en `src/domain/`.
- REST y CLI son adaptadores de entrada que delegan en `IncidentService`; no contienen reglas de negocio.
- `IncidentService` y el puerto de persistencia `IncidentRepositoryPort`, definido con `typing.Protocol`, residen en `src/application/`.
- SQLite es un adaptador de salida que implementa ese puerto.
- Un futuro adaptador MCP debe poder reutilizar los mismos casos de uso.

## 3. Tecnología y calidad

- La base tecnológica es Python 3.10 o superior gestionado con `uv`.
- REST usa FastAPI y Pydantic v2; CLI usa Typer; la persistencia inicial usa `sqlite3` de la biblioteca estándar.
- Un cambio de motor de base de datos requiere un ADR.
- Los criterios de aceptación se redactan en BDD (Given / When / Then) y se verifican con `pytest`.
