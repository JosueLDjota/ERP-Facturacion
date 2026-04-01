# Skill: Flujo de Modulo

Usar esta guía cuando la tarea esté centrada en uno o pocos módulos concretos del proyecto.

## Objetivo

Ejecutar cambios locales con disciplina de lectura previa, elección correcta de capa y validación suficiente.

## Flujo de trabajo

1. Leer primero los archivos implicados directamente por la tarea.
2. Identificar dependencias cercanas: llamadas, imports, consumidores y colaboradores inmediatos.
3. Decidir la capa correcta antes de editar: UI, dominio, persistencia, infraestructura u otra existente en el proyecto.
4. Elegir el punto de inserción con menor impacto y mejor coherencia con la estructura actual.
5. Implementar el cambio mínimo seguro.
6. Validar comportamiento, compatibilidad y efectos laterales probables.
7. Reportar resumen, archivos modificados y riesgos pendientes.

## Criterios de decisión

- Si el problema es de presentación, no empujar lógica innecesaria hacia dominio o persistencia.
- Si el problema es de negocio, evitar resolverlo únicamente en UI.
- Si el cambio afecta acceso a datos o servicios externos, aislar infraestructura de la lógica de negocio cuando sea posible.
- Si hay duplicación entre módulos cercanos, corregirla sin expandir la tarea más allá de lo necesario.

## Regla de mínima intervención

No editar un módulo hasta poder explicar:

- por qué ese módulo es el lugar correcto,
- qué dependencias cercanas podrían verse afectadas,
- qué alternativa implicaría mayor riesgo,
- cómo se validará el cambio.

## Salida esperada

El cierre de la tarea debe incluir:

- resumen breve de lo implementado,
- lista de archivos modificados,
- validación realizada,
- riesgos, supuestos o pruebas pendientes.
