---
name: adr-writer
description: "Escribe y revisa ADR con la plantilla MADR del proyecto; úsalo cuando el usuario pida crear, actualizar o revisar docs/adr/*.md, decisiones arquitectónicas o reemplazos entre ADR."
---

# ADR Writer

## Alcance

Este skill guía la creación y revisión de Architecture Decision Records en `docs/adr/` siguiendo `docs/adr/000-template.md`.

## Reglas MADR del proyecto

- Registra **una sola decisión por ADR**. Si aparece una segunda decisión, crea otro ADR y deja una referencia cruzada.
- Usa el nombre `ADR-NNN: [Decisión única: problema y solución]` y el archivo `docs/adr/NNN-tema-en-kebab-case.md`.
- Incluye los metadatos obligatorios: `- **Estado**`, `- **Fecha**` y `- **Autores**`.
- Incluye `- **Reemplaza a**` solo cuando aplique; si la referencia es parcial, dilo explícitamente.
- Conserva exactamente estas cuatro secciones: `## 1. Contexto y problema`, `## 2. Opciones consideradas`, `## 3. Decisión arquitectónica` y `## 4. Consecuencias y trade-offs`.
- Presenta **al menos dos alternativas reales** con nombres concretos. Cada opción debe describirse con sus ventajas y desventajas; no uses opciones de relleno ni una alternativa deliberadamente inviable.
- La decisión elige una opción, la justifica frente a las demás y explica por qué descarta las otras.
- Si la decisión afecta estructura o dependencias, añade un diagrama Mermaid como en la plantilla.
- Las consecuencias separan puntos favorables y desfavorables, incluidos coste, complejidad y limitaciones asumidas.
- Si un ADR dice reemplazar una restricción de otro ADR, verifica primero que el archivo referenciado exista en `docs/adr/`. Si no existe, registra esa verificación en el propio ADR y no afirmes que se comprobó el texto del ADR ausente.

## Flujo de trabajo

1. Lista `docs/adr/` y lee `docs/adr/000-template.md`; comprueba qué ADR existen y cuál es el siguiente número libre.
2. Formula una única pregunta de decisión y delimita el contexto, las restricciones y el riesgo de no decidir.
3. Escribe dos o más opciones reales con ventajas y desventajas antes de escoger.
4. Redacta la decisión, justificación, diagrama cuando corresponda y consecuencias.
5. Revisa que el documento tenga los metadatos, las cuatro secciones y ninguna segunda decisión mezclada.
6. Reporta comprobaciones solo después de haber ejecutado la lectura o el comando que las respalda.
