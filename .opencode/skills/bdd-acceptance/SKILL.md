---
name: bdd-acceptance
description: "bdd-acceptance, Given/When/Then, pytest, TestClient, CliRunner: explica cómo redactar escenarios en lenguaje de negocio y verificar cada uno con pytest en IncidentOps. Use when se pide escribir criterios de aceptación, pruebas de API o pruebas de CLI."
---

# Acceptance BDD en IncidentOps

## Cómo redactar escenarios

- Escribe cada criterio de aceptación en lenguaje de negocio, sin mencionar
  clases, rutas, frameworks ni sentencias SQL.
- Usa esta estructura y un solo comportamiento observable por escenario:

  ```text
  Dado <contexto de negocio con datos concretos>
  Cuando <acción que realiza el operador o el sistema>
  Entonces <resultado observable y verificable>
  ```

- Emplea `Given / When / Then` cuando el equipo trabaje en inglés; en español
  usa `Dado / Cuando / Entonces`, sin mezclar ambos formatos en un mismo
  escenario.
- Incluye casos positivos, límites y negativos: campos vacíos, severidad en el
  límite exacto del SLA, escalamiento al 75 % y paridad REST/CLI.
- Un escenario es verificable solo si permite nombrar la entrada, la acción y
  la aserción. Evita adjetivos como "rápido", "adecuado" o "correcto".

## Cómo comprobar cada escenario con pytest

1. Convierte cada escenario en una prueba de `pytest`, o en un caso de una
   parametrización si solo cambian los datos. El nombre de la prueba debe
   describir el comportamiento de negocio.
2. Para una regla de dominio, llama directamente a la función correspondiente
   en `src/domain/` y afirma el resultado, incluidas las excepciones.
3. Para REST, usa `TestClient` sobre `src.adapters.inbound.api.app.app` y
   comprueba código de estado y cuerpo JSON.
4. Para CLI, usa `CliRunner` sobre `src.adapters.inbound.cli.app` y comprueba
   `exit_code`, `stdout` y `stderr`.
5. Para paridad, envía la misma entrada a REST y a CLI y compara
   `response.json()` con `json.loads(result.stdout)`.
6. Ejecuta desde la raíz con `uv run pytest` y reporta el resultado solo
   después de haberlo ejecutado.

## Patrón de referencia

El archivo `tests/test_spec_001_triage.py` muestra el patrón vigente:

- `client` es una fixture `scope="module"` basada en `TestClient`.
- `cli_runner` es una fixture basada en `CliRunner`.
- `incidents` carga `data/sample_incidents.json` como fuente de datos de
  negocio compartida por REST y CLI.
- `test_cli_returns_same_json_as_http` verifica explícitamente la paridad.
- Los campos vacíos se cubren con `@pytest.mark.parametrize` y una aserción
  distinta para el error de REST y el de CLI.

## Checklist antes de dar por cerrado un escenario

- El escenario está escrito en lenguaje de negocio y usa `Dado/Cuando/Entonces`
  o `Given/When/Then`, de forma consistente.
- Existe al menos una prueba de `pytest` que fallaría si el comportamiento se
  rompiera.
- La prueba usa `TestClient`, `CliRunner` o la función de dominio adecuada, no
  una comprobación manual.
- Las aserciones verifican el resultado observable y los errores esperados.
- Si el caso de uso tiene dos interfaces, la paridad REST/CLI está cubierta.
- `uv run pytest` pasa desde la raíz del repositorio.
