# Reglas Globales de Trabajo

Estas reglas aplican a cualquier intervención de agentes en el repositorio.

## 1. Alcance y tamaño del cambio

- No reescribir módulos completos salvo instrucción explícita.
- No hacer refactors amplios "de paso" mientras se resuelve otra tarea.
- Dividir el trabajo en cambios pequeños, reversibles y fáciles de validar.
- Evitar tocar archivos no necesarios para el objetivo declarado.

## 2. Ubicación correcta del cambio

- Antes de editar, justificar por qué el cambio pertenece a esa capa, módulo o archivo.
- Preferir el punto de inserción más cercano al problema y con menor radio de impacto.
- Si el cambio puede ubicarse en más de una capa, priorizar la opción que preserve mejor la estructura existente.

## 3. Compatibilidad y estabilidad

- Preservar compatibilidad con el código existente siempre que sea posible.
- No romper contratos públicos, firmas, flujos de datos o convenciones usadas por otros módulos sin necesidad explícita.
- Si una mejora requiere cambiar un contrato existente, primero encapsular o introducir compatibilidad transitoria.

## 4. Separación de responsabilidades

- Separar UI, dominio, persistencia e infraestructura cuando la estructura actual lo permita.
- Evitar mezclar lógica de negocio con detalles de interfaz o acceso a datos.
- No propagar lógica duplicada entre capas por conveniencia.

## 5. Complejidad y dependencias

- Evitar duplicación de lógica; extraer o reutilizar comportamiento cuando eso reduzca riesgo real.
- No introducir dependencias innecesarias, nuevos frameworks o tooling no solicitado.
- No cambiar el stack del proyecto ni rediseñar la arquitectura sin mandato explícito.

## 6. Disciplina de ejecución

- No combinar refactor, corrección funcional y rediseño en una sola intervención si eso dificulta validar el resultado.
- No mover muchos archivos en una misma tarea salvo justificación fuerte.
- Si hay archivos similares o trabajo previo, integrarse con cuidado antes de crear alternativas paralelas.

## 7. Cierre obligatorio

Al cerrar una tarea, documentar como mínimo:

- archivos tocados,
- validación realizada,
- pruebas ejecutadas o pendientes,
- riesgos o supuestos relevantes.
