# Modulo de Respaldos

## Resumen

Este documento describe la implementacion del modulo de respaldos agregado al ERP desktop.

El objetivo del cambio fue incorporar una solucion segura, simple y mantenible para:

- crear respaldos manuales,
- restaurar respaldos validos,
- guardar configuracion minima del modulo,
- registrar historial basico,
- alertar cuando no exista un respaldo reciente,
- dejar una base preparada para respaldos automaticos simples.

## Alcance implementado

### 1. Respaldo manual

Desde `Configuracion > Respaldos` el usuario puede generar un respaldo manual.

Comportamiento actual:

- genera un archivo `.zip`,
- usa nombre automatico con fecha y hora,
- incluye una copia consistente de la base SQLite activa,
- incluye opcionalmente la carpeta de recibos configurada (`recibo_save_path`) si existe,
- incluye la carpeta local `data/` si existe,
- guarda el resultado en una carpeta configurable,
- registra el resultado en historial.

Formato de nombre:

- `backup_erp_YYYY-MM-DD_HH-MM-SS.zip`

### 2. Restauracion

Desde `Configuracion > Respaldos` el usuario puede seleccionar un `.zip` y restaurarlo.

Comportamiento actual:

- valida que el archivo sea ZIP valido,
- valida que exista `manifest.json`,
- valida que el respaldo contenga una base de datos SQLite con estructura minima esperada,
- solicita confirmacion antes de restaurar,
- intenta crear un respaldo preventivo antes de restaurar,
- restaura la base hacia la conexion SQLite activa,
- restaura tambien directorios auxiliares incluidos en el respaldo cuando aplican,
- registra exito o error en historial.

### 3. Configuracion minima

El modulo persiste estos parametros:

- carpeta destino de respaldos,
- frecuencia automatica,
- cantidad de respaldos a conservar,
- activar o desactivar alertas,
- cantidad de dias considerados sin respaldo reciente.

Valores por defecto:

- frecuencia: `daily`
- conservar: `7`
- alertas: activadas
- dias de vigencia: `3`

Frecuencias soportadas:

- `daily`: ejecuta un respaldo automatico al iniciar si ese dia todavia no existe uno exitoso,
- `on_close`: intenta generar respaldo al cerrar la app,
- `disabled`: desactiva automatizacion.

### 4. Historial basico

Se registra historial persistente con:

- fecha,
- tipo,
- nombre/ruta del archivo,
- estado,
- mensaje breve.

Tipos usados por el sistema:

- `manual`
- `automatico`
- `preventivo`
- `restauracion`

Estados:

- `exito`
- `error`

### 5. Alertas por respaldo desactualizado

La aplicacion verifica el estado del ultimo respaldo al iniciar sesion.

Casos cubiertos:

- si nunca hubo respaldo: muestra alerta,
- si el ultimo respaldo supera el umbral configurado: muestra alerta,
- si existe respaldo reciente: no alerta.

La alerta:

- se dispara con mensaje visible,
- tambien usa el sistema de notificaciones,
- ofrece abrir directamente `Configuracion > Respaldos`.

## Arquitectura y punto de insercion

El cambio se distribuyo en capas para no incrustar logica de ZIP, validacion y restauracion dentro de Tkinter.

### Persistencia

Archivo:

- [backup_repository.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/data/repositories/backup_repository.py)

Responsabilidades:

- asegurar la tabla `HistorialRespaldos`,
- leer y guardar configuracion del modulo usando `Configuracion`,
- registrar historial,
- consultar el ultimo respaldo exitoso.

### Servicio de negocio

Archivo:

- [backup_service.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/domain/services/backup_service.py)

Responsabilidades:

- crear ZIPs,
- extraer y validar respaldos,
- restaurar snapshots SQLite,
- aplicar retencion,
- calcular alertas,
- ejecutar automatizacion minima.

### UI

Archivos:

- [backup_panel.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/ui/backup_panel.py)
- [config.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/config.py)

Responsabilidades:

- disparar acciones manuales,
- editar configuracion,
- mostrar historial,
- mostrar mensajes claros al usuario.

### Integracion de aplicacion

Archivo:

- [main.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/main.py)

Responsabilidades:

- inicializar repositorio y servicio de respaldos,
- correr chequeo al iniciar,
- disparar respaldo automatico segun configuracion,
- navegar hacia la pestaña de respaldos desde la alerta.

### Permisos

Archivo:

- [access_control.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/domain/services/access_control.py)

Se agrego `can_manage_backups(role)` para reutilizar el criterio de administracion en operaciones sensibles como restauracion.

## Persistencia usada

### Tabla nueva

`HistorialRespaldos`

Campos:

- `fecha`
- `tipo`
- `archivo_nombre`
- `archivo_ruta`
- `estado`
- `mensaje`

### Configuracion reutilizada

Se guardan claves en la tabla `Configuracion`:

- `backup_destination_dir`
- `backup_frequency`
- `backup_retention_count`
- `backup_alerts_enabled`
- `backup_stale_days`
- `backup_last_success_at`

## Validaciones y seguridad

La implementacion contempla:

- ruta de destino vacia o invalida,
- ruta destino que apunta a archivo y no carpeta,
- ZIP invalido,
- manifiesto faltante o invalido,
- respaldo sin base SQLite valida,
- restauracion restringida por rol cuando se provee el rol actual,
- retencion limitada solo a archivos `backup_erp_*.zip` dentro de la carpeta configurada,
- intento de respaldo preventivo antes de restaurar,
- mensajes claros de error para el usuario.

## Retencion

La retencion elimina solamente archivos:

- dentro de la carpeta configurada de respaldos,
- con extension `.zip`,
- cuyo nombre inicia con `backup_erp_`.

Esto evita borrar archivos arbitrarios fuera del alcance del modulo.

## Flujo de uso recomendado

1. Ir a `Configuracion > Respaldos`.
2. Configurar carpeta destino, frecuencia y retencion.
3. Guardar configuracion.
4. Usar `Crear respaldo ahora` para generar uno manual.
5. Revisar el historial para confirmar fecha, estado y archivo.
6. Usar `Restaurar desde ZIP` solo con usuario autorizado y tras confirmar la operacion.

## Archivos del cambio

### Creados

- [MODULO_RESPALDOS_2026-04-02.md](/C:/Users/Hugo/Desktop/ERP-Facturacion/docs/analysis/MODULO_RESPALDOS_2026-04-02.md)
- [backup_repository.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/data/repositories/backup_repository.py)
- [backup_service.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/domain/services/backup_service.py)
- [backup_panel.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/ui/backup_panel.py)
- [test_backup_service.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/tests/unit/test_backup_service.py)

### Modificados

- [config.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/config.py)
- [main.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/main.py)
- [access_control.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/erp/domain/services/access_control.py)
- [test_security_controls.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/tests/unit/test_security_controls.py)

## Validacion realizada

Se ejecutaron estas validaciones automatizadas:

- compilacion con `py_compile` de los archivos tocados,
- `python -m unittest tests.unit.test_backup_service tests.unit.test_security_controls`

Resultado:

- `14` pruebas en verde.

Casos cubiertos:

- respaldo manual exitoso,
- historial persistente,
- deteccion de respaldo reciente sin alerta,
- alerta cuando no hay respaldos,
- alerta cuando el respaldo es antiguo,
- restauracion de respaldo valido,
- error por ruta invalida,
- error por fallo de compresion,
- error por ZIP invalido,
- permiso sensible para restauracion.

## Limitaciones actuales

- La automatizacion diaria se resuelve al iniciar, no con scheduler en segundo plano.
- La frecuencia `on_close` depende del flujo normal de cierre de la app.
- Tras una restauracion, puede ser recomendable reabrir modulos ya cargados para asegurar refresco visual completo.
- No se implemento una auditoria avanzada ni versionado de respaldos mas complejo.

## Siguientes mejoras posibles

- indicador persistente en dashboard,
- filtros de historial,
- opcion para excluir o incluir carpetas auxiliares desde UI,
- politicas mas avanzadas de automatizacion,
- aviso posterior a restauracion para reiniciar la app si el negocio lo requiere.
