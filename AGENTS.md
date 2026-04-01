# Guía de Entrada para Agentes

Este archivo define el punto de entrada obligatorio para cualquier agente de Codex que vaya a trabajar en este repositorio.

## Lectura obligatoria antes de editar

Antes de modificar código o estructura del proyecto, el agente debe revisar en este orden:

1. `agents/codex/README.md`
2. `agents/codex/rules/global-rules.md`
3. `agents/codex/rules/validation-checklist.md`
4. Las skills aplicables dentro de `agents/codex/skills/`

## Reglas de operación

- No iniciar cambios sin justificar primero el punto de inserción correcto.
- Antes de editar, identificar en qué capa debe vivir el cambio y por qué ese archivo o módulo es el lugar adecuado.
- Favorecer cambios pequeños, reversibles y con bajo radio de impacto.
- Prohibido hacer reescrituras masivas o refactors amplios si no fueron solicitados explícitamente.
- No mezclar correcciones puntuales con rediseños arquitectónicos oportunistas.
- Toda tarea relevante debe cerrarse usando `agents/codex/rules/validation-checklist.md`.
- Cuando el trabajo lo amerite, usar una especificación basada en `agents/codex/rules/task-spec-template.md`.
- Cuando exista una skill aplicable, usarla como guía operativa antes de tocar archivos.

## Criterio de intervención

Cada edición debe responder estas preguntas antes de ejecutarse:

- ¿Qué problema exacto se resuelve?
- ¿Cuál es el punto de inserción con menor riesgo?
- ¿Qué alternativa más invasiva se está evitando?
- ¿Qué contratos, flujos o dependencias podrían verse afectados?

Si el agente no puede responder estas preguntas con claridad, debe reducir el alcance o detener la intervención hasta definirlo mejor.

## Regla de seguridad

El principio rector del repositorio es **mejorar sin romper**:

- preservar compatibilidad con el comportamiento actual,
- evitar expandir alcance sin necesidad,
- dejar trazabilidad clara de archivos tocados, validación realizada y riesgos pendientes.
