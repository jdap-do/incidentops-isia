# Bitácora de Ingeniería de Prompts y Contexto — Semana 1 (`CONTEXT_LOG.md`)

**Estudiante(s)**: `Jose David Anacona Pira`  
**Fecha**: `2026-11-17`  
**Modelos / Asistentes Utilizados**: `ChatGPT: GPT-6.2 Sol Bajo (primera consulta) y GPT-6.2 Astra Medio (segunda consulta); acompañamiento y chats de generación de código`

---

## 1. De Prompts Pobres a Técnicas Clásicas de *Prompt Engineering* (Reto 1: `src/triage_rules.py`)

### 1.1 Diagnóstico de un Prompt Pobre y Ambiguo
Analiza el siguiente prompt deficiente para el Reto 1:
> *"El archivo `triage_rules.py` funciona mal con algunos tickets del JSON. Agrégale el equipo recomendado y una clave para duplicados, y no pongas P0 cuando no sea urgente."*

Documenta al menos **3 modos de fallo o ambigüedades** de este prompt (p. ej., ausencia de contexto de dominio, restricciones negativas difusas, falta de enumeración de equipos válidos o ausencia de ejemplos canónicos):
1. El prompt no define los criterios de severidad. La expresión “urgente” es subjetiva y puede confundir una necesidad individual con una caída general o una exposición de datos entre organizaciones.
2. No especifica los equipos permitidos ni el formato de la clave de duplicados, lo que puede producir valores inconsistentes y dificultar el enrutamiento.
3. No proporciona el código relevante, los incidentes de ejemplo ni los resultados esperados. Tampoco explica cómo reconocer reportes distintos del mismo problema.
4. La instrucción negativa “no pongas P0 cuando no sea urgente” no establece una regla verificable. Debe sustituirse por criterios afirmativos basados en impacto, disponibilidad y seguridad.

### 1.2 Consultas independientes, consistencia y Few-Shot

Se realizaron dos consultas en chats nuevos con el mismo prompt, conservado íntegramente en `PROMPT_COMPARACION_MODELOS.txt`. El estudiante identificó la primera configuración como Sol Bajo y la segunda como Astra Medio. La captura del selector confirmó GPT-6.2 Sol Bajo para la primera consulta. La segunda configuración mostrada fue GPT-6.2 Astra Medio. Las respuestas se compartieron completas en el chat de acompañamiento.

Ambas consultas asignaron P2 a INC-1002 por bloqueo individual, P0 a INC-1007 por exposición entre organizaciones y P2 a INC-1009 por lentitud con descarga completa. Se solicitaron justificaciones breves por impacto, disponibilidad y seguridad; se conservaron criterios observables para revisar las conclusiones.

| Elemento contrastado | Sol Bajo | Astra Medio | Concordancia |
| :--- | :--- | :--- | :--- |
| Severidades INC-1001 a INC-1010 | P0, P2, P2, P3, P1, P0, P0, P2, P2, P3 | P0, P2, P2, P3, P1, P0, P0, P2, P2, P3 | 10/10 |
| Equipos responsables | Coinciden con la tabla verificada localmente | Coinciden con la tabla verificada localmente | 10/10 |
| Pares candidatos | 1001/1006 y 1003/1008 | 1001/1006 y 1003/1008 | 2/2 |
| P2 viernes 18:30 a lunes 08:30 | 30 minutos; no incumple; no escala | Igual | Coincide |
| P2 lunes 08:00 a 17:00 abierto | 540 minutos; incumple y escala | Igual | Coincide |

Esta comprobación de consistencia entre dos respuestas independientes dio concordancia completa en los criterios anteriores; no demuestra exactitud general ni constituye una estimación estadística con una muestra amplia. No se trasladó esa concordancia al campo `consistency_ratio`, cuyo valor sigue siendo de compatibilidad.

Las cadenas de componentes y claves no coincidieron literalmente: Sol utilizó `historical-reports`, `excel-export` y guiones bajos; Astra utilizó `reporting` y guiones. El prompt comparativo no fijó un catálogo cerrado, por lo que se evaluó la coherencia semántica y la agrupación, no igualdad textual. Para integrar el código se conservó el catálogo del proyecto, por ejemplo `reporting-api` y `payments-gateway`.

El prompt inicial de refactorización incluyó rol, reglas, ejemplos canónicos y tarea; los ejemplos Few-Shot comprendían dos reportes HTTP 502, dos reportes de lentitud con alto volumen y una exposición entre organizaciones. En la evidencia del primer chat quedó un marcador de contexto sin sustituir. La consulta de triaje se repitió posteriormente con contexto real completo en `PROMPT_TRIAJE_CORREGIDO.txt`; su resultado se incorporó y verificó localmente. El flujo del SLA también transfirió contexto y plantilla completos en `PROMPT_SLA_CHAT2.txt`.
### 1.3 Implementación y verificación local del triaje

Se incorporaron `models.py` y `triage_rules.py` del archivo `incidentops-refactor.zip` generado en un chat nuevo. Se conservaron los modelos de SLA y se agregaron el equipo recomendado y la clave de correlación al resultado del triaje.

La ejecución local del 17 de noviembre de 2026 finalizó con código de salida 0: `uv --cache-dir C:\workspace\uv-cache run python -m src.triage_rules`. Se verificaron las diez severidades esperadas, los dos pares de claves de correlación y el enrutamiento de INC-1007 a Security-IAM conservando reporting-api como componente.

| Incidentes | Severidad | Equipo |
| :--- | :--- | :--- |
| INC-1001 / INC-1006 | P0 | Backend-Core |
| INC-1002 | P2 | Security-IAM |
| INC-1003 / INC-1008 | P2 | Backend-Core |
| INC-1004 | P3 | Backend-Core |
| INC-1005 | P1 | Data-DBA |
| INC-1007 | P0 | Security-IAM |
| INC-1009 | P2 | Backend-Core |
| INC-1010 | P3 | Platform-SRE |

Las claves compartidas fueron `payments-gateway:http-502` y `reporting-api:high-volume-latency`. Estas claves sugieren correlaciones; no prueban una causa raíz común. El campo `consistency_ratio` se conserva por compatibilidad y no mide consultas independientes. Las reglas dependen de vocabulario explícito y requieren revisión ante negaciones o reportes ambiguos. La auditoría ejecutada no demuestra cobertura de todos los reportes posibles.

### 1.4 Medición inicial del contexto de triaje

| Estrategia | Alcance | Caracteres | Tokens o200k_base |
| :--- | :--- | ---: | ---: |
| Fuerza bruta | 8 archivos | 32718 | 8219 |
| Búsqueda textual | 2 archivos Python | 5522 | 1412 |
| Contexto semántico estilo LSP | Definición y referencias | 3987 | 1069 |

La medición inicial proporcionada por el estudiante muestra un ahorro de 7150 tokens (87,0 %) frente al proyecto completo y de 343 tokens (24,3 %) frente a la búsqueda textual. No corresponde al estado refactorizado.

---
## 2. Flujo Explorar → Destilar → Ejecutar en Contexto Limpio

### 2.1 Exploración y resumen destilado

Se compararon el recorrido minuto a minuto, la resta de fines de semana y las intersecciones diarias. Se eligió la última alternativa por precisión en extremos y costo O(D). El siguiente resumen se transfirió al chat nuevo:

1. P0/P1 acumulan tiempo continuo; P2/P3 solo lunes a viernes de 08:00 a 18:00.
2. Se suman las intersecciones diarias de la ventana hábil con el intervalo del incidente, en O(D).
3. Se descarta contar minutos uno por uno por su costo y restar fines de semana sin recortar noches por su inexactitud.
4. No se incorporan dependencias externas, festivos ni conversiones de zona horaria; se usan fechas locales naive coherentes.
5. Se acumulan segundos y se convierten una sola vez a minutos enteros.
6. El cierre usa resolved_at; un incidente resuelto no requiere escalamiento.
7. Un intervalo invertido produce ValueError.
8. El incumplimiento conserva la comparación estricta elapsed_minutes > allowed_minutes.
9. El escalamiento se activa al alcanzar el 75 % y permanece activo después del vencimiento para incidentes abiertos.
10. La verificación incluye fines de semana, creación fuera de horario, varios fines de semana, 24/7, límite exacto y resolución.

### 2.2 Prompt ejecutado en el chat limpio

Se transfirió el siguiente prompt completo y se recibieron el ADR-002 y el módulo SLA. La separación permitió conservar únicamente contexto, decisión y restricciones relevantes.

``xml
<context>
<lsp_context symbol="evaluate_sla_status">
  <!-- 1. Definiciones de Tipos y Pol├¡ticas (LSP Hover / Type Definition) -->
# [LSP textDocument/hover type] src\models.py:12
class SLARule:
    """Define el acuerdo de nivel de servicio (SLA) para un nivel de severidad."""

    severity: SeverityLevel
    max_resolution_minutes: int
    operates_24x7: bool
    escalation_threshold_ratio: float = 0.75

# [LSP textDocument/hover type] src\models.py:22
class Incident:
    """Representa un incidente registrado en la plataforma IncidentOps."""

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None

# [LSP textDocument/hover type] src\models.py:35
class SLAEvaluation:
    """Resultado determinista de la evaluaci├│n de SLA de un incidente."""

    incident_id: str
    severity: SeverityLevel
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool

# [LSP textDocument/hover type] src\models.py:48
class TriageResult:
    """Resultado del triaje determinista.

    consistency_ratio se conserva por compatibilidad; su valor predeterminado
    no mide consultas independientes, confianza ni exactitud del clasificador.
    """

    incident_id: str
    severity: SeverityLevel
    component: str
    rationale: str
    consistency_ratio: float = 1.0
    recommended_team: str = "Backend-Core"
    duplicate_group_key: str = "unknown:unclassified"

# [LSP textDocument/hover symbol] src\sla_calculator.py:17
SLA_POLICY_TABLE: Dict[SeverityLevel, SLARule] = {
    "P0": SLARule(severity="P0", max_resolution_minutes=60, operates_24x7=True),
    "P1": SLARule(severity="P1", max_resolution_minutes=240, operates_24x7=True),
    "P2": SLARule(severity="P2", max_resolution_minutes=480, operates_24x7=False),
    "P3": SLARule(severity="P3", max_resolution_minutes=1440, operates_24x7=False),
}

  <!-- 2. Definici├│n Exacta del S├¡mbolo (LSP GoToDefinition) -->
# [LSP textDocument/definition] src\sla_calculator.py:25
def get_sla_rule_for_severity(severity: SeverityLevel) -> SLARule:
    """Obtiene la regla de SLA aplicable a una severidad validada contra la tabla."""
    if severity not in SLA_POLICY_TABLE:
        raise ValueError(f"Severidad no v├ílida: {severity}")
    return SLA_POLICY_TABLE[severity]

# [LSP textDocument/definition] src\sla_calculator.py:32
def evaluate_sla_status(incident: Incident, reference_time: datetime) -> SLAEvaluation:
    """Eval├║a si un incidente ha incumplido su SLA o requiere escalamiento preventivo.

    Args:
        incident: Entidad del incidente a evaluar.
        reference_time: Marca de tiempo actual o de cierre contra la cual medir.

    Returns:
        SLAEvaluation con los minutos transcurridos, restantes y banderas de estado.
    """
    rule = get_sla_rule_for_severity(incident.severity)
    end_time = incident.resolved_at or reference_time

    if end_time < incident.created_at:
        raise ValueError("El tiempo de referencia no puede ser anterior a la creaci├│n.")

    # TODO(week-1-taller): Cuando rule.operates_24x7 es False (P2 y P3), solo deben
    # contabilizarse los minutos dentro del horario h├íbil (Lunes-Viernes 08:00-18:00).
    delta_seconds = (end_time - incident.created_at).total_seconds()
    elapsed_minutes = int(delta_seconds // 60)

    remaining_minutes = rule.max_resolution_minutes - elapsed_minutes
    is_breached = elapsed_minutes > rule.max_resolution_minutes

    escalation_limit = int(rule.max_resolution_minutes * rule.escalation_threshold_ratio)
    requires_escalation = (
        incident.status != "RESOLVED"
        and not is_breached
        and elapsed_minutes >= escalation_limit
    )

    return SLAEvaluation(
        incident_id=incident.incident_id,
        severity=incident.severity,
        elapsed_minutes=elapsed_minutes,
        allowed_minutes=rule.max_resolution_minutes,
        remaining_minutes=remaining_minutes,
        is_breached=is_breached,
        requires_escalation=requires_escalation,
    )

  <!-- 3. Referencias de Invocaci├│n en el Proyecto (LSP FindReferences) -->
# [LSP textDocument/references] src\incident_repository.py:146
  L145:             )
  L146:             sla_eval = evaluate_sla_status(incident, reference_time=reference_time)
  L147:             results.append(

# [LSP textDocument/references] src\sla_calculator.py:87
  L86:     monday_morning = datetime(2026, 11, 9, 9, 0, 0)
  L87:     evaluation = evaluate_sla_status(sample_incident, reference_time=monday_morning)
  L88: 
</lsp_context>
<adr_template>
# ADR-000: [Título Corto de la Decisión Arquitectónica]

- **Estado**: Propuesto | Aceptado | Reemplazado
- **Fecha**: YYYY-MM-DD
- **Autor(es)**: [Nombre del Ingeniero / Equipo]
- **Componentes Afectados**: [`src/...`]

---

## 1. Contexto y Problema

Describe el problema técnico o de negocio actual, las limitaciones del código existente (por ejemplo, latencia, consultas N+1, errores de cálculo de SLA o limitaciones de escalabilidad) y las restricciones del sistema (p. ej., mantener cero dependencias externas, seguridad contra inyección SQL, determinismo).

---

## 2. Opciones Consideradas

1. **Opción A — [Nombre de la opción]**:
   - *Ventajas*: ...
   - *Desventajas*: ...
2. **Opción B — [Nombre de la opción]**:
   - *Ventajas*: ...
   - *Desventajas*: ...
3. **Opción C — [Nombre de la opción]**:
   - *Ventajas*: ...
   - *Desventajas*: ...

---

## 3. Tipos de Modelos y Matriz de Decisión Arquitectónica

### 3.1 Comparación de configuraciones observadas

Se compararon Sol Bajo y GPT-6.2 Astra Medio en conversaciones nuevas con el mismo prompt. La captura final confirmó GPT-6.2 Sol Bajo para la primera consulta. Cambiaron tanto la familia del modelo como el esfuerzo, por lo que no se atribuyen las diferencias exclusivamente a uno de esos factores.

Sol Bajo resolvió correctamente las diez severidades, equipos, agrupaciones y ambos casos SLA. Astra Medio alcanzó los mismos resultados y explicó explícitamente que INC-1009 debía separarse de la lentitud de consultas por tratarse de una exportación. Ambos señalaron que los pares requieren confirmar episodio y servicio afectado.

En esta muestra no se observó una mejora de exactitud con Astra Medio ni se demostró que fuera indispensable un mayor esfuerzo. Sol Bajo resultó suficiente para las reglas cerradas evaluadas. La exploración de alternativas y extremos temporales justifica considerar mayor esfuerzo en tareas más complejas, pero esa recomendación no se presenta como una mejora medida aquí. No se registraron latencia, costo ni tokens de salida para comparar eficiencia. Las pruebas locales establecieron la corrección del código para los casos cubiertos.
### 3.2 Matriz de decisión arquitectónica

| Escenario | Paradigma | Justificación técnica |
| :--- | :--- | :--- |
| Contabilizar minutos hábiles y comprobar el 75 % del SLA | Código determinista | Reglas exactas y auditables, baja latencia, sin costo por inferencia ni variabilidad generativa. |
| Explorar casos borde y redactar un ADR antes de modificar consultas SQL | Asistente GenAI en chat | Facilita comparar alternativas y redactar; la revisión humana y las pruebas controlan errores antes de implementar. |
| Detectar anomalías en millones de métricas CPU/RAM por minuto | ML clásico | Modelos estadísticos o de detección de anomalías aprovechan patrones numéricos a escala; requieren calibración, seguimiento de deriva y control de falsos positivos. |
| Clasificar reportes en lenguaje natural con patrones nuevos | LLM en tiempo de ejecución | Aporta flexibilidad semántica; exige salida estructurada, controles de privacidad, evaluación, presupuesto de latencia/costo y derivación a revisión ante incertidumbre. |

## 4. Economía de tokens y curaduría de contexto

### 4.1 Mediciones empíricas con tiktoken o200k_base

Las siguientes mediciones corresponden a las ejecuciones aportadas por el estudiante antes de cada refactorización. Los estados del proyecto son distintos; no se comparan entre sí como si fueran una misma versión.

| Símbolo | Estrategia | Alcance | Caracteres | Tokens | Reducción frente a fuerza bruta |
| :--- | :--- | :--- | ---: | ---: | ---: |
| classify_incident_report | Fuerza bruta | 8 archivos | 32718 | 8219 | 0 % |
| classify_incident_report | Búsqueda textual | 2 archivos Python | 5522 | 1412 | 82,8 % |
| classify_incident_report | Semántica estilo LSP | Definición y referencias | 3987 | 1069 | 87,0 % |
| evaluate_sla_status | Fuerza bruta | 8 archivos | 36438 | 9063 | 0 % |
| evaluate_sla_status | Búsqueda textual | 4 archivos Python | 24239 | 5868 | 35,3 % |
| evaluate_sla_status | Semántica estilo LSP | Definición y referencias | 4636 | 1180 | 87,0 % |

Para triaje, la extracción semántica ahorró 7150 tokens frente al proyecto completo y 343 frente a la búsqueda textual. Para SLA, ahorró 7883 y 4688 tokens, respectivamente. La búsqueda textual sigue incluyendo funciones y contenido ajenos al cambio; el contexto semántico selecciona definiciones y referencias. La herramienta simula extracción estilo LSP mediante AST/símbolos; estas cifras describen el payload extraído, no todo el prompt final con ejemplos e instrucciones.

### 4.2 Comparación de formatos de serialización

Ejecución local: `uv --cache-dir C:\workspace\uv-cache run python -m src.context_audit --compare-formats`.

| Formato | Caracteres | Tokens |
| :--- | ---: | ---: |
| JSON indentado | 2942 | 878 |
| JSON compacto | 2641 | 728 |
| YAML equivalente | 2579 | 755 |
| CSV delimitado por barra vertical | 2171 | 617 |

Para estos diez incidentes tabulares se elegiría CSV con encabezados y escape correcto del delimitador: consumió 261 tokens menos que JSON indentado (29,7 %). Si existen estructuras anidadas o tipos que deban preservarse, JSON compacto ofrece mayor fidelidad estructural y ahorró 150 tokens (17,1 %). YAML tuvo menos caracteres que JSON compacto pero más tokens, lo que demuestra que caracteres y tokens no son equivalentes. El formato debe seleccionarse mediante medición y conservar el significado de los datos.

### 4.3 Verificación local del SLA

Se incorporaron el ADR-002 y `sla_calculator.py` recibidos del segundo chat. La ejecución `uv --cache-dir C:\workspace\uv-cache run python -m src.sla_calculator` finalizó con código 0 y 16 casos correctos usando los modelos reales. Se comprobaron minutos, permitidos, restantes, incumplimiento y escalamiento; fines de semana, creación fuera de horario, varios fines de semana, P0/P1 continuos, P3 hábil, 75 %, límite exacto, cierre, intervalo vacío, suma de segundos e intervalo invertido.

El intervalo viernes 17:00 a lunes 09:00 produjo 120 minutos para P2 y 3840 para P0/P1. El algoritmo O(D) excluye festivos y conversiones de zona horaria. El diagrama Mermaid está incluido en la sección 3 del ADR-002.
## 5. Subsanación del contexto del primer prompt

Se repitió la solicitud de refactorización en una conversación nueva con el prompt completo conservado en `PROMPT_TRIAJE_CORREGIDO.txt`, sin marcadores pendientes. Se incluyeron modelos reales, el módulo de triaje de referencia, diez incidentes, reglas de dominio y ejemplos Few-Shot. El bloque se etiquetó como contexto, pero incluyó módulos completos; por tanto, esta repetición no se presenta como el payload mínimo de 1069 tokens medido inicialmente.

Se recibió `IncidentOps_triaje.zip`. Su auditoría se ejecutó primero en una carpeta de revisión y aprobó los diez incidentes en severidad, componente, equipo y clave, además de los dos pares de correlación. Se incorporaron sus dos módulos al proyecto y se volvió a comprobar el SLA con los modelos integrados.

La versión final conserva las claves compartidas `payments-gateway:http-502` y `reporting-api:high-volume-latency`. Las categorías individuales finales son `connection-pool-saturation`, `export-latency` y `certificate-renewal` para INC-1005, INC-1009 e INC-1010, respectivamente. Los nombres difieren de la primera implementación sin alterar severidad, equipo ni pares requeridos.

La omisión inicial queda subsanada mediante una ejecución posterior documentada; no se afirma que el primer envío incluyera el contexto. Las reglas siguen siendo heurísticas: las negaciones, síntomas mixtos y vocabulario nuevo requieren revisión. La clasificación de respaldo P3 para reportes desconocidos es una limitación fuera de los diez casos de la actividad.
### Prompt completo de subsanación

``xml
<role>
Actúa como ingeniero de software responsable del motor de triaje de IncidentOps.
</role>
<domain_rules>
P0: caída de servicio crítico o exposición de datos entre organizaciones.
P1: degradación severa de infraestructura compartida con riesgo de caída.
P2: bloqueo individual o lentitud con servicio disponible.
P3: cambio cosmético o mantenimiento preventivo en staging.
La urgencia verbal no determina severidad.
Equipos válidos: Backend-Core (pagos, reportes e interfaz), Platform-SRE (infraestructura y certificados), Data-DBA (base de datos), Security-IAM (identidad y accesos indebidos).
Conservar el catálogo de componentes: payments-gateway, auth-identity, reporting-api, frontend-ui, database-cluster, infra-certificates.
La clave component:symptom_category usa categorías estables y señala correlación candidata, no causa raíz confirmada.
</domain_rules>
<examples>
Pagos HTTP 502 y pasarela de cobros con error 502: P0, payments-gateway, Backend-Core, payments-gateway:http-502.
Reportes con 4.5 segundos y 10000 órdenes, y listado histórico con más de 3 segundos y 10000 registros: P2, reporting-api, Backend-Core, reporting-api:high-volume-latency.
Facturas de otra organización al cambiar company_id: P0, reporting-api, Security-IAM, reporting-api:cross-tenant-access.
</examples>
<context>
<lsp_context symbol="classify_incident_report">
<models>
"""Entidades de dominio y tipos de datos para IncidentOps."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

SeverityLevel = Literal["P0", "P1", "P2", "P3"]
IncidentStatus = Literal["OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED", "RESOLVED"]


@dataclass(frozen=True)
class SLARule:
    """Define el acuerdo de nivel de servicio (SLA) para un nivel de severidad."""

    severity: SeverityLevel
    max_resolution_minutes: int
    operates_24x7: bool
    escalation_threshold_ratio: float = 0.75


@dataclass
class Incident:
    """Representa un incidente registrado en la plataforma IncidentOps."""

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None


@dataclass(frozen=True)
class SLAEvaluation:
    """Resultado determinista de la evaluación de SLA de un incidente."""

    incident_id: str
    severity: SeverityLevel
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool


@dataclass(frozen=True)
class TriageResult:
    """Resultado del triaje determinista.

    consistency_ratio se conserva por compatibilidad; su valor predeterminado
    no mide consultas independientes, confianza ni exactitud del clasificador.
    """

    incident_id: str
    severity: SeverityLevel
    component: str
    rationale: str
    consistency_ratio: float = 1.0
    recommended_team: str = "Backend-Core"
    duplicate_group_key: str = "unknown:unclassified"


</models>
<triage_module>
"""Motor determinista de clasificación y enrutamiento de incidentes (IncidentOps).

NOTA PEDAGÓGICA (Semana 1 — Enfoque 100% AI for Software Engineering):
Este módulo implementa las reglas de negocio para clasificar reportes entrantes y
asignarlos a un equipo de ingeniería (`Backend-Core`, `Platform-SRE`, `Data-DBA`,
`Security-IAM`).

Actualmente presenta deuda técnica que los estudiantes diagnosticarán y refactorizarán
asistidos por IA (usando Context Engineering, Few-Shot, Chain-of-Thought y Self-Consistency):
1. Clasificación frágil con cadenas `if/elif` acopladas y sensibles a palabras aisladas
   (p. ej., cualquier mensaje con la palabra "hoy" se clasifica erróneamente como `P0`).
2. No asigna el equipo responsable (`recommended_team`) ni genera una clave de
   correlación (`duplicate_group_key`) para detectar incidentes repetidos del mismo
   componente.
"""

import json
from pathlib import Path
from typing import Dict, List

from src.models import SeverityLevel, TriageResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_incidents.json"


def classify_incident_report(incident_id: str, raw_text: str) -> TriageResult:
    """Clasifica un reporte de incidente aplicando reglas heurísticas iniciales.

    DEUDA TÉCNICA INTENCIONAL:
    - Evalúa palabras sueltas ("hoy", "urgente") antes de analizar el impacto real
      (caída global vs. cuenta individual vs. entorno de staging).
    - No normaliza componentes ni identifica el equipo de guardia correspondiente.
    """
    text_lower = raw_text.lower()

    # Bug de diseño: si un usuario dice "necesito acceder hoy" por su cuenta bloqueada,
    # se dispara como P0 antes de verificar si es una caída global o un caso individual.
    if "urgente" in text_lower or "hoy" in text_lower or "502" in text_lower:
        severity: SeverityLevel = "P0"
    elif "94%" in text_lower or "timeout" in text_lower:
        severity = "P1"
    elif "lenta" in text_lower or "segundos" in text_lower:
        severity = "P2"
    else:
        severity = "P3"

    if "pago" in text_lower or "cobro" in text_lower or "tarjeta" in text_lower:
        component = "payments-gateway"
    elif "cuenta" in text_lower or "ingresar" in text_lower:
        component = "auth-identity"
    elif "postgresql" in text_lower or "conexiones" in text_lower:
        component = "database-cluster"
    elif "certificado" in text_lower or "tls" in text_lower:
        component = "infra-certificates"
    elif "botón" in text_lower or "color" in text_lower:
        component = "frontend-ui"
    else:
        component = "reporting-api"

    return TriageResult(
        incident_id=incident_id,
        severity=severity,
        component=component,
        rationale=f"Clasificación heurística legacy asignada a {component} ({severity}).",
    )


def _run_triage_audit() -> None:
    """Ejecuta el motor actual sobre los 10 incidentes de prueba para evidenciar fallos."""
    incidents: List[Dict[str, str]] = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))

    print("=== Auditoría del Motor de Triaje Actual (`src/triage_rules.py`) ===")
    print(f"{'ID':<10} | {'Sev.':<5} | {'Componente':<20} | {'Extracto del Reporte'}")
    print("-" * 88)
    for item in incidents:
        result = classify_incident_report(item["id"], item["raw_text"])
        snippet = item["raw_text"][:45] + "..." if len(item["raw_text"]) > 45 else item["raw_text"]
        print(f"{result.incident_id:<10} | {result.severity:<5} | {result.component:<20} | {snippet}")
    print("-" * 88)
    print(
        "Observa los problemas en la salida actual:\n"
        "  - INC-1002 (cuenta individual bloqueada) y INC-1009 (exportación Excel lenta)\n"
        "    se clasifican como P0 solo porque el usuario escribió la palabra 'hoy'.\n"
        "  - INC-1007 (fuga crítica de facturas entre empresas por company_id en URL)\n"
        "    se clasifica como P3 porque no contiene las palabras 'urgente' ni '502'."
    )


if __name__ == "__main__":
    _run_triage_audit()


</triage_module>
</lsp_context>
<incidents>
[
  {
    "id": "INC-1001",
    "reporter": "carlos.mendoza@clientes-corp.com",
    "created_at": "2026-11-05T08:15:00",
    "raw_text": "URGENTE: El gateway de pagos devuelve HTTP 502 Bad Gateway en todas las transacciones con tarjeta de crédito desde hace 12 minutos. Ningún comercio puede cobrar."
  },
  {
    "id": "INC-1002",
    "reporter": "ana.gomez@clientes-corp.com",
    "created_at": "2026-11-05T09:10:00",
    "raw_text": "He intentado ingresar a mi cuenta tres veces y ahora aparece bloqueada. Necesito acceder hoy mismo porque debo enviar el informe de cierre a la junta directiva."
  },
  {
    "id": "INC-1003",
    "reporter": "soporte-nivel1@incidentops.internal",
    "created_at": "2026-11-05T10:05:00",
    "raw_text": "El dashboard de reportes históricos tarda cerca de 4.5 segundos en cargar cuando un cliente tiene más de 10,000 órdenes registradas. No da error, pero la experiencia es muy lenta."
  },
  {
    "id": "INC-1004",
    "reporter": "luis.torres@logistica-express.co",
    "created_at": "2026-11-05T11:20:00",
    "raw_text": "Sería excelente si pudieran cambiar el color del botón de exportar CSV a verde oscuro porque el gris actual casi no resalta en mi monitor secundario."
  },
  {
    "id": "INC-1005",
    "reporter": "alertas-monitoreo@incidentops.internal",
    "created_at": "2026-11-05T11:45:00",
    "raw_text": "El nodo primario de PostgreSQL muestra un uso de conexiones del 94% y timeouts intermitentes en el pool de conexiones del servicio de facturación."
  },
  {
    "id": "INC-1006",
    "reporter": "maria.rodriguez@retail-latam.com",
    "created_at": "2026-11-05T13:00:00",
    "raw_text": "Otra vez cayó la pasarela de cobros con tarjeta, a nuestros clientes les sale error 502 al intentar pagar el carrito de compras."
  },
  {
    "id": "INC-1007",
    "reporter": "auditoria@seguridad-fin.com",
    "created_at": "2026-11-05T14:30:00",
    "raw_text": "Detectamos que al cambiar el parámetro company_id en la URL del reporte PDF se pueden visualizar facturas pertenecientes a otra organización."
  },
  {
    "id": "INC-1008",
    "reporter": "pedro.sanchez@ventas-norte.com",
    "created_at": "2026-11-05T15:10:00",
    "raw_text": "El listado de planes e historial tarda más de 3 segundos en responder cada vez que abrimos la pestaña de clientes corporativos con más de 10,000 registros."
  },
  {
    "id": "INC-1009",
    "reporter": "elena.vargas@contabilidad-global.com",
    "created_at": "2026-11-05T16:40:00",
    "raw_text": "La exportación mensual a Excel se queda pensando unos 20 segundos pero al final sí descarga el archivo completo. Hoy tenemos cierre contable y nos preocupa que falle más tarde."
  },
  {
    "id": "INC-1010",
    "reporter": "devops-ci@incidentops.internal",
    "created_at": "2026-11-05T17:25:00",
    "raw_text": "El certificado TLS del entorno de staging vencerá en 14 días. Requiere rotación programada antes del próximo sprint."
  }
]


</incidents>
</context>
<task>
Esta consulta subsana una anterior cuyo contexto quedó como marcador sin sustituir. Revisar el contexto real y entregar completos src/models.py y src/triage_rules.py refactorizados. Conservar modelos SLA, campos existentes y firma pública. Agregar recommended_team y duplicate_group_key si faltan. Mantener consistency_ratio por compatibilidad sin presentarlo como medición de confianza o consultas independientes. Normalizar mayúsculas y acentos, combinar señales de impacto y no depender del ID. Usar solo biblioteca estándar.
La auditoría ejecutable debe comprobar las diez severidades P0,P2,P2,P3,P1,P0,P0,P2,P2,P3, equipos, componentes y claves iguales para 1001/1006 y 1003/1008. Entregar archivos descargables y justificación breve. No afirmar pruebas ejecutadas si no se ejecutaron. Si el código ya cumple, explicar qué se conserva y cualquier corrección estrictamente necesaria.
</task>
``
