# AGENTS.md

## Ejecución

- Proyecto `uv` de un solo paquete (`tool.uv.package = false`), Python >=3.10; única dependencia: `tiktoken`. Todo se ejecuta desde la raíz del repo (`pyproject.toml`, `uv.lock`, `src/`, `data/`). El `cd week-1/starter-project/` del README es una ruta vieja que no existe aquí.
- No hay scripts de test/lint/typecheck ni CI. La verificación son los propios módulos ejecutables. Usa `uv run`: con `python` directo la auditoría de tokens cae silenciosamente a un estimador BPE local, no a `o200k_base`.
- No hay servicios externos: `IncidentRepository` usa SQLite en memoria por defecto.

## Comandos de verificación

```bash
uv run python -m src.triage_rules
uv run python -m src.sla_calculator
uv run python -m src.context_audit --symbol evaluate_sla_status
uv run python -m src.context_audit --symbol classify_incident_report
uv run python -m src.context_audit --compare-formats
uv run python -m src.incident_repository --records 10000 --iterations 20
```

- Cada auditoría termina con error si cambian sus expectativas. `src/sla_calculator.py` usa `assert`: no lo ejecutes con `python -O`.
- Tras cambiar `src/models.py` u otra superficie compartida, vuelve a ejecutar triaje, SLA y ambas auditorías de contexto.

## Reglas del dominio que no son obvias

- `docs/adr/002-calculo-sla-horario-habil.md` manda en SLA: P0/P1 acumulan tiempo continuo; P2/P3 solo lunes–viernes 08:00–18:00; `resolved_at` prevalece sobre `reference_time`; `elapsed > max` es incumplimiento (el límite exacto no); el escalamiento al 75 % permanece activo tras el vencimiento si el ticket sigue abierto. No hay festivos ni zonas horarias.
- `src/triage_rules.py` clasifica desde texto normalizado, nunca desde el ID. `AUDIT_EXPECTATIONS` y `data/sample_incidents.json` deben seguir cuadrando: 10 filas `INC-1001`..`INC-1010` y los pares `1001/1006`, `1003/1008`.
- `consistency_ratio` se conserva solo por compatibilidad; `duplicate_group_key` es una correlación candidata, no una causa raíz.
- `src/incident_repository.py` tiene deuda técnica intencional (escaneo completo + N+1). No la optimices salvo que la tarea lo pida explícitamente: el benchmark existe para medirla.

## Entregables de la práctica

- `CONTEXT_LOG.md`, `CONTEXT_LOG_TEMPLATE.md` y `PROMPT_*.txt` son evidencia de la actividad, no temporales; no los sobreescribas salvo petición explícita.
- Los ADR siguen `docs/adr/000-template.md` en formato MADR: una decisión por ADR, estado/fecha/autores y «Reemplaza a» opcional, cuatro secciones y al menos dos opciones reales. Reporta un resultado de verificación solo después de haber ejecutado el comando.
