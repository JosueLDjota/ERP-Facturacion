# Skill: Refactor Seguro

Usar esta guía cuando la tarea requiera reorganizar código existente sin alterar el objetivo funcional principal.

## Objetivo

Refactorizar con el menor riesgo posible, manteniendo compatibilidad y capacidad de validación.

## Reglas operativas

- Encapsular antes de reemplazar.
- No mezclar refactor con rediseño.
- No mover demasiados archivos en una sola intervención.
- No romper contratos públicos ni firmas consumidas por otros módulos.
- Priorizar compatibilidad, aislamiento del cambio y testabilidad.

## Secuencia recomendada

1. Identificar el comportamiento actual que debe preservarse.
2. Ubicar el punto exacto de duplicación, acoplamiento o complejidad que motiva el refactor.
3. Introducir una capa de encapsulación o adaptación antes de sustituir comportamiento existente.
4. Migrar el uso de forma incremental si el cambio toca más de un consumidor.
5. Mantener el refactor separado de mejoras de diseño no esenciales.
6. Validar que el contrato observable no cambió.

## Señales de riesgo

Detener o recortar el cambio si ocurre alguna de estas condiciones:

- el refactor exige reescribir un módulo completo,
- aparecen efectos laterales fuera del área objetivo,
- la única forma de avanzar es cambiar contratos públicos de inmediato,
- el número de archivos tocados crece sin mejorar claridad ni seguridad.

## Resultado esperado

El refactor debe dejar:

- comportamiento funcional intacto o explícitamente preservado,
- código más fácil de entender o validar,
- superficie de cambio acotada,
- riesgos residuales documentados.
