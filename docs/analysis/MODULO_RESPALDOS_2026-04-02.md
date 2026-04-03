# Especificacion de Tarea

## Titulo

`Modulo de respaldos para ERP desktop`

## Objetivo

Agregar un modulo de respaldos seguro y simple que permita crear respaldos manuales, restaurar archivos validos, configurar respaldos automaticos, consultar historial basico y alertar cuando no exista un respaldo reciente.

## Contexto

La aplicacion usa una UI legacy en `frames/` y una organizacion nueva en `erp/` para servicios y repositorios. La persistencia principal vive en SQLite (`DBManager`) y ya existe una tabla `Configuracion` para preferencias simples. El cambio debe integrarse sin reescribir la UI ni mover modulos completos.

## Alcance

- Agregar un repositorio de respaldos para configuracion e historial persistidos en SQLite.
- Agregar un servicio para crear `.zip`, restaurar respaldos validados y verificar vigencia del ultimo respaldo.
- Integrar una UI minima en `Configuracion` para crear respaldo manual, restaurar, editar configuracion y ver historial.
- Ejecutar verificacion de alerta al iniciar y disparar respaldo automatico segun la configuracion minima soportada.

## Fuera de alcance

- Redisenar toda la pantalla de configuracion.
- Introducir un scheduler externo o dependencias pesadas.
- Reemplazar `DBManager` o migrar la persistencia a otro motor.
- Construir un sistema completo de auditoria o permisos nuevo.

## Archivos candidatos

- `erp/data/repositories/backup_repository.py`: persistencia del modulo usando `Configuracion` y una tabla de historial propia.
- `erp/domain/services/backup_service.py`: logica de creacion, restauracion, retencion y alerta.
- `frames/config.py` o un colaborador cercano de UI: punto visible para acciones manuales, configuracion e historial.
- `main.py`: integracion minima para chequeo al iniciar y respaldo automatico al cerrar/iniciar.
- `erp/domain/services/access_control.py`: reutilizar control sensible para restauracion.
- `tests/unit/`: validaciones del servicio y permisos.

## Restricciones

- Mantener compatibilidad con la arquitectura actual.
- Cambiar solo la superficie necesaria.
- Limitar eliminacion automatica a archivos de respaldo dentro de la carpeta configurada.
- Evitar sobreescritura directa riesgosa del archivo SQLite en uso; preferir una restauracion segura hacia la conexion actual.

## Comportamiento esperado

- El usuario administrador puede crear un respaldo manual en `.zip`.
- El sistema guarda historial basico persistente.
- La restauracion valida estructura, intenta respaldo preventivo y restaura la base actual.
- La app alerta si no hay respaldos o si el ultimo respaldo exitoso supera el umbral configurado.
- La configuracion minima permite elegir carpeta, frecuencia, retencion, alertas y dias de vigencia.

## Casos limite

- Carpeta de destino invalida o sin permisos.
- Error durante compresion del archivo.
- Archivo zip invalido o con estructura inesperada.
- Respaldo sin base SQLite valida.
- Restauracion mientras la base principal esta abierta por la app.

## Validacion esperada

- Crear respaldo manual exitoso.
- Registrar historial y ultimo respaldo exitoso.
- Restaurar un respaldo valido.
- Alertar cuando no hay respaldos.
- Alertar cuando el respaldo mas reciente supera el umbral configurado.
- Fallar con mensaje claro ante ruta invalida, error de compresion y zip invalido.

## Definicion de terminado

- El modulo cubre respaldo manual, historial, configuracion minima, restauracion segura y alerta de vigencia.
- El cambio queda acotado a servicios, repositorio, integracion de UI y puntos de arranque/cierre necesarios.
- Hay pruebas automatizadas sobre los escenarios minimos obligatorios.
- Los riesgos residuales quedan documentados.
