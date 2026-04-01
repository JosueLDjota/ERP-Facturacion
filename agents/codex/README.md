# Gobernanza de Agentes Codex

## Propósito

Esta carpeta concentra la base operativa para que los agentes de Codex trabajen en el proyecto con criterios consistentes, bajo riesgo y sin introducir decisiones arquitectónicas improvisadas.

Su función es reducir tres fallas frecuentes:

- cambios ubicados en la capa incorrecta,
- refactors amplios hechos "de paso",
- modificaciones difíciles de validar o revertir.

## Cómo usar esta carpeta

La estructura se organiza en tres piezas complementarias:

- `rules/`: reglas obligatorias, checklist de validación y plantilla de especificación.
- `skills/`: guías prácticas para ejecutar tipos de trabajo concretos de forma segura.
- este `README.md`: flujo recomendado y criterio general de intervención.

## Flujo recomendado para trabajar con agentes

1. Definir el problema exacto antes de tocar archivos.
2. Leer los archivos implicados y sus dependencias cercanas.
3. Determinar la capa correcta para el cambio antes de editar.
4. Revisar `rules/global-rules.md` para confirmar límites de intervención.
5. Si la tarea no está bien acotada, redactar una spec usando `rules/task-spec-template.md`.
6. Si la tarea encaja en una skill disponible, usarla como procedimiento de trabajo.
7. Implementar el cambio mínimo seguro.
8. Validar con `rules/validation-checklist.md` antes de cerrar.

## Uso coordinado de rules, specs y skills

### Rules

Las rules son obligatorias. Definen qué no debe hacer un agente aunque la implementación parezca rápida o conveniente.

### Specs

La spec se usa cuando la tarea puede derivar en decisiones ambiguas, tocar varios archivos o afectar comportamiento existente. Su objetivo es congelar alcance y criterios antes de editar.

### Skills

Las skills se usan para ejecutar una clase de trabajo con una secuencia disciplinada. No reemplazan las rules: las complementan.

## Principio rector: mejorar sin romper

El repositorio debe evolucionar con cambios que:

- mantengan compatibilidad con el código existente cuando sea posible,
- eviten expandir el radio de impacto,
- permitan validar y revertir con facilidad,
- dejen claro qué se tocó y por qué.

Si una propuesta exige mover demasiadas piezas a la vez, mezclar refactor con rediseño o reemplazar módulos completos sin necesidad explícita, esa propuesta debe considerarse de alto riesgo y reformularse.
