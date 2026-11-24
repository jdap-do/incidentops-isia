# Research: Resumen de incidentes activos

**Feature**: [spec.md](./spec.md) | **Date**: 2026-11-24

No hay marcadores `NEEDS CLARIFICATION` pendientes.

## 1. Persistencia detrás de un puerto

**Decision**: Definir `IncidentRepositoryPort` en `src/application/ports.py` con esta superficie:

```python
class IncidentRepositoryPort(Protocol):
    def save_incident(self, incident: Incident) -> None: ...

    def get_incident(self, incident_id: str) -> Incident | None: ...

    def find_open_duplicates(
        self,
        incident: Incident,
        *,
        exclude_incident_id: str | None = None,
    ) -> list[Incident]: ...

    def list_active_incidents(
        self,
        component_filter: str | None = None,
    ) -> list[Incident]: ...

    def check_health(self) -> bool: ...
```

El adaptador SQLite y la fábrica viven en `src/adapters/outbound/sqlite_repository.py`. `create_incident_repository(database_url: str | None = None) -> IncidentRepositoryPort` usa el argumento, o `DATABASE_URL` si está presente; vacío o ausente significa `sqlite:///:memory:`. Se aceptan `sqlite:///:memory:`, `sqlite:///ruta.db`, `sqlite:////ruta/absoluta.db`, `:memory:` y rutas simples. Cualquier otro esquema se rechaza.

La consulta del resumen usa una sola sentencia con `INNER JOIN sla_policies`, filtra estados activos y componente antes de construir objetos, y añade `CREATE INDEX IF NOT EXISTS idx_incidents_component_status ON incidents(component, status, incident_id)`. El join solo garantiza que exista política para la severidad; los minutos, el incumplimiento y el escalamiento se calculan después en el dominio. `save_incident` normaliza `component` con la regla del dominio antes de persistirlo; `list_active_incidents` compara ese valor canónico.

`find_open_duplicates` devuelve candidatos activos con el mismo `component` y `title`, excluyendo opcionalmente un ID. No añade columnas ni campos a `Incident`; `duplicate_group_key` sigue siendo una correlación candidata del triaje.

**Rationale**: La constitución y ADR-003 exigen que la aplicación dependa solo del puerto y que SQLite sea el único lugar con `sqlite3` y SQL. Reutilizar los campos existentes evita cambiar el dominio sin ADR. El join único evita consultas N+1, y el índice `(component, status)` evita el escaneo completo en el filtro principal. La normalización del componente es una regla de dominio; el adaptador solo la aplica al escribir y consultar.

**Alternatives considered**:

- Reutilizar código SQLite fuera de `src/adapters/outbound/`: rechazado; rompería el principio IV de la constitución.
- Calcular SLA dentro de SQL o desde `sla_policies`: rechazado; duplicaría ADR-002 y crearía dos fuentes de verdad.
- Añadir `duplicate_group_key` a `Incident` o a la tabla: rechazado; requeriría decisión de esquema y dominio fuera de alcance.
- Usar SQLAlchemy u otro motor: rechazado; añadiría dependencias y exigiría ADR.

## 2. Caso de uso y paridad REST/CLI

**Decision**: `IncidentService.get_active_incidents_summary(component_filter: str | None, reference_time: datetime)` normaliza el filtro, obtiene incidentes por el puerto, llama a `evaluate_sla_status`, calcula totales y ordena el detalle. El servicio no consulta el reloj: los adaptadores capturan el instante cuando falta la referencia. Devuelve un DTO con:

```text
reference_time: str
component_filter: str | None
total_active: int
breached_count: int
details: list[ActiveIncidentDetail]
```

`ActiveIncidentDetail` contiene exactamente `title`, `component`, `severity`, `status`, `elapsed_minutes` y `requires_escalation`. El orden es P0→P3, minutos descendentes y título ascendente.

Se añade `src/bootstrap.py` como raíz de composición con `build_incident_service()`. Los adaptadores exponen `create_api_app(service)` y `create_cli_app(service)` para inyección, y conservan un `app` module-level creado con el servicio compuesto. REST y CLI validan `reference_time` con la misma función de aplicación: ISO-8601 local naive; si falta, capturan el instante de consulta y lo pasan explícitamente; tz-aware, malformado o anterior a `created_at` produce el mismo mensaje sin calcular el resumen.

**Rationale**: Un solo método de servicio y un solo DTO son la forma más directa de cumplir FR-004 y SC-002. El parseo compartido evita que FastAPI y Typer acepten formatos distintos. La raíz de composición mantiene la regla de que los adaptadores de entrada no importan el adaptador de salida.

**Alternatives considered**:

- Llamar al repositorio SQLite desde REST y CLI: rechazado; rompe ADR-003.
- Implementar el resumen por separado en cada adaptador: rechazado; genera divergencia.
- Usar tipos `datetime` nativos de FastAPI y Typer: rechazado; parseo y errores distintos, además de aceptar zonas horarias.
- Devolver `incident_id` o `is_breached` por fila: rechazado; FR-003 define seis campos y el incumplimiento se expresa como agregado.

## 3. Verificación BDD

**Decision**: `tests/test_spec_002_summary.py` conserva cuatro escenarios BDD como cuatro pruebas `pytest`, con parametrización cuando solo cambian los datos:

1. `test_active_summary_matches_across_rest_and_cli`: conjunto mixto de `OPEN`, `IN_PROGRESS`, `RESOLVED` y `ESCALATION_REQUIRED`; compara respuesta HTTP con `json.loads(result.stdout)` y verifica totales, incumplimientos, seis campos por fila y orden.
2. `test_component_filter_scopes_totals_and_ignores_case_and_spaces`: filtro canónico, `" PAYMENTS-GATEWAY "`, filtro vacío u omitido y filtro sin coincidencia; comprueba que totales y filas se recalculan sobre el subconjunto.
3. `test_sla_boundary_and_business_hours_match_across_channels`: límite exacto, justo por encima, umbral del 75 % e intervalo P2 con noche/fin de semana; compara minutos e indicadores en ambos canales.
4. `test_empty_and_invalid_summary_requests_are_consistent`: sin activos devuelve ceros y detalle vacío; `reference_time` omitido se captura en el adaptador y se refleja en ambos canales; `reference_time` inválido, tz-aware o anterior a la creación produce 422 con `detail` en REST y código 1 con `stderr` en CLI.

La fixture `summary_incidents` siembra datos mediante `save_incident`, porque `data/sample_incidents.json` no tiene estados ni fechas. Las pruebas de Hito 001 no se modifican.

**Rationale**: Cuatro pruebas respetan la petición explícita del feature y agrupan parametrizaciones de un mismo comportamiento observable. Cada escenario usa `TestClient` y `CliRunner` con el mismo instante de referencia, siguiendo la skill `bdd-acceptance`.

**Alternatives considered**:

- Crear una prueba por caso límite: rechazado; contradice la petición de cuatro escenarios y fragmenta la paridad.
- Reutilizar `data/sample_incidents.json`: rechazado; no contiene `status`, `created_at` ni `component` persistible.
- Comprobar solo el servicio: rechazado; la constitución exige cobertura de equivalencia REST/CLI.

## 4. Fronteras de imports con Ruff

**Decision**: Configurar Ruff en la raíz y con archivos por capa.

```toml
[tool.ruff]
src = [".", "src"]

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "TID251", "TID252"]

[tool.ruff.lint.flake8-tidy-imports]
ban-relative-imports = "parents"
```

```toml
extend = "../../pyproject.toml"
src = ["../.."]

[lint.flake8-tidy-imports.extend-banned-api]
"src.application".msg = "Domain layer must not import application layer"
"src.adapters".msg = "Domain layer must not import adapters layer"
```

```toml
extend = "../../pyproject.toml"
src = ["../.."]

[lint.flake8-tidy-imports.extend-banned-api]
"src.adapters".msg = "Application layer must not import adapters layer"
"fastapi".msg = "Application layer must not import FastAPI"
"typer".msg = "Application layer must not import Typer"
"sqlite3".msg = "Application layer must not import sqlite3"
```

```toml
extend = "../../../pyproject.toml"
src = ["../../.."]

[lint.flake8-tidy-imports.extend-banned-api]
"src.adapters.outbound".msg = "Inbound adapters must not import outbound adapters"
```

Los archivos son `pyproject.toml`, `src/domain/ruff.toml`, `src/application/ruff.toml` y `src/adapters/inbound/ruff.toml`. `ban-relative-imports = "parents"` permite `from .models import ...` dentro del dominio y bloquea imports relativos hacia la capa superior.

**Rationale**: `extend-banned-api` permite añadir prohibiciones por capa sin reemplazar las heredadas. La opción `parents` respeta los imports entre hermanos ya existentes en `src/domain/`. La compuerta es `uv run ruff check .` desde la raíz.

**Alternatives considered**:

- `ban-relative-imports = "all"`: rechazado; rompería los imports válidos de `src/domain/`.
- Una única sección TID251 en `pyproject.toml`: rechazada; no puede expresar prohibiciones distintas según la capa importadora.
- `noqa` en adaptadores: rechazado; debilitaría la frontera inbound→outbound sin ADR.
