---
name: hexagonal-architecture
description: "hexagonal-architecture, TID251, TID252, IncidentService: documenta las fronteras dominio/aplicación/adaptadores de IncidentOps, la paridad REST/CLI y la verificación de imports con Ruff. Use when se pide revisar capas, agregar un caso de uso o comprobar imports prohibidos."
---

# Hexagonal Architecture en IncidentOps

## Fronteras obligatorias

### Dominio (`src/domain/`)

- Contiene triaje, cálculo de SLA, modelos, estados, equipos y clave de correlación.
- NO importa `src.application.*`, `src.adapters.*`, FastAPI, Typer ni `sqlite3`.
- SÍ puede usar imports relativos dentro de la propia carpeta, por ejemplo
  `from .models import SeverityLevel, TriageResult`.
- Las reglas son deterministas: misma entrada y mismo instante de referencia
  producen el mismo resultado.

### Aplicación (`src/application/`)

- Contiene `IncidentService` y `IncidentRepositoryPort`, definido con
  `typing.Protocol`.
- `IncidentService` es el único punto de entrada de los casos de uso y llama
  directamente al dominio.
- Para persistir depende solo de `IncidentRepositoryPort`; NO importa
  `src.adapters.*` ni módulos concretos de base de datos o frameworks.
- Las operaciones que evalúan SLA reciben el instante de referencia como
  parámetro explícito.

### Adaptadores (`src/adapters/`)

- Entrada: `src/adapters/inbound/api/app.py` (FastAPI + Pydantic v2) y
  `src/adapters/inbound/cli.py` (Typer).
- Salida: el adaptador SQLite implementa `IncidentRepositoryPort` y es el único
  sitio autorizado para importar `sqlite3` o contener SQL.
- Los adaptadores SÍ pueden importar aplicación y dominio; la dependencia nunca
  apunta hacia la tecnología concreta desde el núcleo.
- Un adaptador de entrada NO importa directamente un adaptador de salida: usa el
  servicio o el puerto.

## Paridad REST/CLI mediante IncidentService

1. Agrega o cambia la lógica del caso de uso en `IncidentService`, nunca en el
   controlador FastAPI ni en el comando Typer.
2. Los dos adaptadores invocan el mismo método de servicio; por ejemplo, ambos
   usan `service.triage_incident(incident_id, raw_text)`.
3. Los adaptadores solo traducen entrada y salida: validación HTTP frente a
   validación CLI, `asdict(result)` frente a JSON serializado.
4. La paridad se comprueba con una prueba que llama a REST y a CLI con la misma
   entrada y compara `response.json()` con `json.loads(result.stdout)`.
5. Errores de dominio o de entrada se traducen, no se redefinen: HTTP 422 y
   mensaje en `detail`; CLI escribe el mensaje en stderr y termina con código 1.
6. Un futuro adaptador MCP debe reutilizar `IncidentService` sin copiar reglas.

## Verificación con Ruff (TID251 y TID252)

- `TID251` (`flake8-tidy-imports.banned-api`) detecta imports prohibidos entre
  capas. Las prohibiciones previstas son:
  - `src.domain.*` → `src.application.*` y `src.adapters.*`.
  - `src.application.*` → `src.adapters.*`, `fastapi`, `typer` y `sqlite3`.
  - `src.adapters.inbound.*` → `src.adapters.outbound.*`.
- `TID252` (`flake8-tidy-imports.ban-relative-imports`) detecta imports relativos
  que cruzan o difuminan capas, como `from ..application.services import IncidentService`.
  Para esos casos se prefiere el import absoluto
  `from src.application.services import IncidentService`. El alcance exacto de
  la regla (`all` o `parents`) se decidirá en Hito 002: hoy el dominio usa
  `from .models import ...` dentro de su propia carpeta.
- La compuerta prevista es `uv run ruff check .` desde la raíz del repo, junto
  con `uv run pytest`.
- En el paso 2.2 solo se instala Ruff como dependencia de desarrollo; la
  configuración de `[tool.ruff.lint.flake8-tidy-imports]` queda pendiente del
  plan del Hito 002. Verifica la instalación con `uv run ruff --version`.
- Si aparece una violación, mueve la regla al dominio o la coordinación al
  servicio. No silencies TID251/TID252 con `noqa` salvo decisión documentada
  en un ADR.
