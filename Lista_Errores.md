# README de Errores del Sistema

## Alcance

Este documento resume los errores y riesgos funcionales identificados en el sistema `ERP-Facturacion` a fecha `2026-03-30`.

No representa una auditoria exhaustiva de todo el proyecto. Incluye:

- Errores confirmados por pruebas automatizadas.
- Defectos funcionales observados directamente en el codigo.
- Riesgos de integridad y seguridad con impacto real.

## Estado General

- Las pruebas ejecutadas con `python -m unittest discover -s tests -p "test_*.py"` terminan con `16` pruebas corridas y `2` errores.
- La compilacion sintactica de los modulos principales con `python -m py_compile ...` no reporto errores de sintaxis.

## Errores Confirmados

### 1. Falla al abrir bases de datos temporales en pruebas e integracion

**Severidad:** Alta

**Evidencia**

- Archivo: `database.py`
- Linea clave: `21`
- Codigo: `self.conn = sqlite3.connect(db_name)`
- Prueba que falla: `tests/integration/test_product_repository.py`

**Descripcion**

La inicializacion de `DBManager` falla con `sqlite3.OperationalError: unable to open database file` cuando se intenta crear una base temporal en pruebas de integracion.

**Impacto**

- Rompe pruebas de integracion.
- Indica que el sistema no maneja de forma robusta rutas de base de datos fuera del archivo por defecto.
- Si se quisiera parametrizar la BD por ambiente o por usuario, el comportamiento actual es fragil.

**Traza observada**

`tests/integration/test_product_repository.py` crea una ruta temporal y llama `DBManager(self.db_path)`. La excepcion ocurre dentro de `database.py:21`.

### 2. La ruta de respaldo para recibos no garantiza recuperacion ante permisos denegados

**Severidad:** Alta

**Evidencia**

- Archivo: `frames/sales.py`
- Lineas clave: `1406-1425`
- Prueba que falla: `tests/unit/test_pos_receipt_path.py`

**Descripcion**

El metodo `save_receipt()` intenta guardar el recibo en varias rutas candidatas, pero en el escenario probado no logra recuperarse cuando la ruta configurada no tiene permisos. La prueba esperaba que el sistema cambiara a un directorio alterno y persistiera la nueva ruta, pero termina lanzando:

`PermissionError: No se pudo guardar el recibo en la ruta configurada ni en la ruta local predeterminada.`

**Impacto**

- El recibo puede perderse aunque exista una ruta de respaldo prevista.
- Se afecta el flujo POS despues de confirmar la venta.
- El usuario puede terminar con una venta registrada pero sin comprobante disponible.

## Defectos Funcionales Importantes

### 3. El flujo principal de venta no es transaccional y puede dejar datos a medias

**Severidad:** Critica

**Evidencia**

- Archivo: `frames/sales.py`
- Lineas clave: `1183-1229`

**Descripcion**

`confirm_sale_and_process()` inserta la venta, luego inserta detalles, luego descuenta stock y al final intenta generar/guardar el recibo. Todo esto se hace con llamadas repetidas a `self.db.execute(...)`, y cada llamada hace `commit` inmediato en `database.py:730-739`.

Si algo falla a mitad del proceso:

- La venta puede quedar insertada.
- Algunos detalles pueden quedar guardados.
- El inventario puede quedar parcialmente descontado.
- El recibo puede no existir.

El `except` solo muestra un mensaje, pero no revierte lo ya confirmado en la base.

**Impacto**

- Riesgo real de corrupcion funcional del negocio.
- Ventas inconsistentes.
- Inventario desalineado.
- Dificultad para auditar o corregir operaciones fallidas.

**Nota**

Ya existe una implementacion mas segura en `erp/data/repositories/sale_repository.py:90-153`, donde la venta se procesa con `BEGIN`, `commit` y `rollback`. El flujo UI actual no la usa.

### 4. El modulo de productos reporta exito aunque la operacion de base de datos falle

**Severidad:** Alta

**Evidencia**

- Archivo: `frames/products.py`
- Guardado: `240-258`
- Eliminacion: `338-349`
- Manejador DB: `database.py:730-739`

**Descripcion**

`DBManager.execute()` no lanza excepciones: cuando hay error devuelve `None` y guarda el fallo en `self.last_error`. Sin embargo, `ProductFrame.save_product()` y `ProductFrame.delete_product()` no verifican ni el retorno ni `last_error`.

Eso significa que la interfaz puede mostrar:

- `"Producto actualizado correctamente."`
- `"Producto agregado correctamente."`
- `"Producto eliminado."`

incluso si SQLite rechazo la operacion por llave foranea, datos invalidos u otro error.

**Impacto**

- La UI puede mentirle al usuario.
- Se pierden errores reales de persistencia.
- El operador cree que guardo o elimino algo que en realidad no cambio.

### 5. El sistema guarda y valida contrasenas en texto plano

**Severidad:** Critica

**Evidencia**

- Esquema: `database.py:80-90`
- Usuario semilla: `database.py:248-253`
- Login: `main.py:127-143`

**Descripcion**

La tabla `Usuarios` almacena `contrasena TEXT NOT NULL`, el sistema crea por defecto `admin / 1234`, y la autenticacion compara el valor escrito directamente contra la base:

`SELECT id, nombre, rol FROM Usuarios WHERE usuario = ? AND contrasena = ?`

**Impacto**

- Cualquier acceso al archivo SQLite expone las credenciales.
- No existe hashing ni endurecimiento minimo.
- El usuario administrador por defecto es trivialmente adivinable.

### 6. El manejo de errores del acceso al icono silencia fallos sin registrar nada

**Severidad:** Media

**Evidencia**

- Archivo: `main.py`
- Lineas: `47-59`

**Descripcion**

En `_setup_window_icon()` cualquier excepcion se descarta con `except Exception: pass`.

**Impacto**

- Si hay problemas de recursos o empaquetado, no quedan rastros para diagnostico.
- Hace mas dificil detectar errores de despliegue.

## Riesgos Secundarios Detectados

### 7. El proyecto mezcla dos caminos de negocio para ventas

**Severidad:** Media

**Evidencia**

- Flujo inseguro en UI: `frames/sales.py:1183-1229`
- Flujo mas robusto en repositorio: `erp/data/repositories/sale_repository.py:90-153`

**Descripcion**

Hay logica de negocio duplicada: una en la capa UI y otra en repositorio. Esto aumenta el riesgo de que una se corrija y la otra no.

**Impacto**

- Bugs inconsistentes entre capas.
- Mayor costo de mantenimiento.
- Mas probabilidad de regresiones.

## Resumen de Prioridades

Corregir primero:

1. Transaccionalidad del flujo de ventas.
2. Credenciales en texto plano y usuario por defecto inseguro.
3. Manejo real de errores en CRUD de productos.
4. Falla de guardado de recibos con fallback.
5. Apertura robusta de bases de datos parametrizadas o temporales.

## Comandos Usados Para Validacion

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile main.py database.py file_manager.py receipt_builder.py erp\data\repositories\product_repository.py erp\data\repositories\client_repository.py erp\data\repositories\config_repository.py erp\data\repositories\sale_repository.py erp\data\repositories\supplier_repository.py frames\clients.py frames\config.py frames\dashboard.py frames\notificaciones.py frames\products.py frames\registro.py frames\sales.py frames\sales_may.py frames\suppliers.py frames\ui.py
```

## Conclusión

El sistema es funcional, pero hoy tiene errores importantes de confiabilidad y seguridad. El mayor problema no es visual ni de interfaz: es la posibilidad de dejar ventas inconsistentes y operar con credenciales inseguras sin que el usuario reciba mensajes fiables sobre lo que realmente pasó.
