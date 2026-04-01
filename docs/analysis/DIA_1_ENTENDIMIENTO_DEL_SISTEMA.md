# Dia 1 - Entendimiento del Sistema

## Objetivo del dia

El Dia 1 del sprint es exclusivamente para entender el sistema antes de tocarlo. No se deben hacer cambios fuertes, refactors ni ajustes estructurales. La meta es comprender como fluye la informacion entre interfaz, logica y base de datos para evitar romper ventas, stock o integridad de datos en los siguientes dias.

## Alcance

### Que si se hace

- Levantar el sistema y recorrer los modulos clave manualmente.
- Leer el codigo que controla autenticacion, ventas, registro y base de datos.
- Confirmar que tablas usa cada flujo importante.
- Identificar consultas SQL, validaciones, dependencias y puntos fragiles.
- Documentar hallazgos, dudas, riesgos y oportunidades de mejora.

### Que NO se debe hacer

- No modificar `erp_profesional.db`.
- No alterar estructura de tablas ni relaciones.
- No refactorizar `frames/` ni mover logica entre capas.
- No cambiar consultas SQL sin entender primero quien las consume.
- No modificar descuentos, reglas fiscales ni logica de stock.
- No corregir bugs directamente en este dia.

## Mapa rapido del sistema

- `main.py`: punto de entrada, login, sesion actual y navegacion principal.
- `database.py`: conexion SQLite, creacion de tablas, datos semilla y consultas compartidas.
- `frames/sales.py`: POS unificado, carrito, cobro, confirmacion y guardado de ventas.
- `frames/registro.py`: consulta de ventas POS, filtros, exportacion y reimpresion.
- `frames/clients.py`: gestion y busqueda de clientes.
- `frames/products.py`: gestion y busqueda de productos.
- `erp/domain/services/invoice_calculator.py`: calculo de subtotales, impuestos, total, validaciones de pago y vuelto.

## Estado actual observado

Sobre la base `erp_profesional.db` existente se observo lo siguiente:

- `Usuarios`: 1 registro.
- `Clientes`: 50 registros.
- `Productos`: 298 registros.
- `Ventas`: 171 registros.
- `DetalleVenta`: 483 registros.

Esto confirma que no se trata de una base vacia o solo de ejemplo; hay historial suficiente para que cualquier cambio mal entendido afecte datos reales.

## 1. Login

### Como funciona hoy

El flujo de autenticacion esta controlado directamente desde `main.py`. La pantalla de acceso se construye en `show_login()` y la validacion se ejecuta en `authenticate()`.

Consulta actual:

```sql
SELECT id, nombre, rol
FROM Usuarios
WHERE usuario = ? AND contrasena = ?;
```

Flujo observado:

1. El usuario ingresa credenciales en la vista de login.
2. `main.py` consulta la tabla `Usuarios`.
3. Si hay coincidencia, se guarda `current_user`, se destruye el login y se muestra la interfaz principal.
4. Si no hay coincidencia, se muestra `messagebox.showerror("Error", "Usuario o contrasena incorrectos")`.

### Que revisar en Dia 1

- Que campos reales de `Usuarios` participan en autenticacion.
- Si existe o no alguna validacion adicional aparte de usuario y contrasena.
- Como se usa el `rol` despues del login.
- Que ocurre si la tabla `Usuarios` esta vacia.
- Que mensajes de error ve el usuario y en que casos.

### Hallazgos importantes

- La contrasena se valida en texto plano.
- Si `Usuarios` esta vacia, `database.py` inserta un usuario por defecto: `admin / 1234`.
- El `rol` se muestra en la interfaz, pero no se observo control granular de permisos por modulo.
- El login depende de acceso directo a SQLite desde `main.py`; no pasa por una capa de servicio o repositorio dedicada.

## 2. Modulo de Ventas

### Componente principal

El flujo POS actual esta centralizado en `frames/sales.py`, clase `UnifiedPOSFrame`.

### Flujo completo de una venta

1. Se cargan productos desde `Productos`.
2. El usuario busca y selecciona productos.
3. Se agrega cada producto al carrito con validacion de stock disponible.
4. Se selecciona cliente desde un combo. Si no se elige uno, se usa `Cliente General` con `id_cliente = NULL`.
5. Se aplican descuentos manuales o automaticos.
6. Se calculan subtotales, impuestos, total, monto recibido y vuelto usando `erp/domain/services/invoice_calculator.py`.
7. Se abre modal de cobro.
8. Se abre modal de resumen previo a confirmar.
9. Al confirmar, se inserta la cabecera en `Ventas`.
10. Se insertan lineas en `DetalleVenta`.
11. Se descuenta stock en `Productos`.
12. Se genera y guarda recibo HTML.

### Como se agregan productos

Carga inicial del catalogo:

```sql
SELECT id, nombre, descripcion, precio, stock
FROM Productos
ORDER BY nombre;
```

Validacion observada al agregar al carrito:

- La cantidad debe ser mayor que 0.
- La suma de la cantidad actual en carrito mas la nueva no puede superar `stock`.
- El control de stock ocurre en la logica del frame antes de guardar.

### Como se calculan los totales

Los totales no se calculan manualmente en una sola formula dentro del frame; se delegan al servicio `invoice_calculator.py`.

Ese servicio considera:

- Cantidad.
- Precio unitario.
- Descuento porcentual por linea.
- Configuracion `factura_tax_included`.
- Metodo de pago.
- Monto recibido.
- Calculo de vuelto.
- Validaciones fiscales y de consistencia.

### Como se guarda la venta

Insercion de cabecera:

```sql
INSERT INTO Ventas (
    id, fecha, total, monto_pagado, vuelto, metodo_pago, usuario_id, id_cliente, tipo_recibo
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
```

Insercion de detalle:

```sql
INSERT INTO DetalleVenta (
    venta_id, producto_id, nombre_producto, cantidad, precio_unitario, descuento, subtotal
) VALUES (?, ?, ?, ?, ?, ?, ?);
```

Actualizacion de stock:

```sql
UPDATE Productos
SET stock = stock - ?
WHERE id = ?;
```

### Relacion con `DetalleVenta`

`DetalleVenta` es la tabla que conserva las lineas de cada venta. Cada fila representa un producto vendido dentro de una venta especifica y guarda:

- `venta_id`
- `producto_id`
- `nombre_producto`
- `cantidad`
- `precio_unitario`
- `descuento`
- `subtotal`

### Hallazgos importantes

- El flujo operativo real del POS esta en `frames/sales.py`, no en la capa `erp/data/repositories/`.
- Los descuentos automaticos dependen de cantidad, tipo de descuento y si el cliente es mayorista o la venta esta en modo `ESPECIAL`.
- `Cliente General` no crea registro nuevo; simplemente deja `id_cliente` en `NULL`.
- Existe una tabla `ventas_diarias`, pero el flujo POS actual guarda en `Ventas` y `DetalleVenta`.

## 3. Base de Datos

### Tablas principales

| Tabla | Clave primaria | Campos clave | Observacion |
|---|---|---|---|
| `Clientes` | `id` | `nombre`, `apellido`, `dni`, `activo`, `mayorista` | Se usa en POS, gestion de clientes y registro |
| `Productos` | `id` | `nombre`, `precio`, `stock`, `proveedor_id` | Se usa en POS, productos y dashboard |
| `Ventas` | `id` tipo `TEXT` | `fecha`, `total`, `monto_pagado`, `vuelto`, `usuario_id`, `id_cliente`, `metodo_pago` | Cabecera principal de venta POS |
| `DetalleVenta` | `id` | `venta_id`, `producto_id`, `cantidad`, `precio_unitario`, `descuento`, `subtotal` | Detalle por producto |
| `Usuarios` | `id` | `nombre`, `usuario`, `contrasena`, `rol` | Autenticacion y contexto de sesion |

### Relaciones confirmadas

- `Ventas.id_cliente -> Clientes.id`
- `DetalleVenta.venta_id -> Ventas.id`
- `Productos.proveedor_id -> Proveedores.id`

### Relaciones que existen como columna pero NO como clave foranea real

- `Ventas.usuario_id` existe, pero no tiene `FOREIGN KEY` a `Usuarios.id`.
- `DetalleVenta.producto_id` existe e incluso tiene indice, pero no tiene `FOREIGN KEY` a `Productos.id`.

### Claves foraneas importantes para revisar

- `Ventas.id_cliente`
- `DetalleVenta.venta_id`
- `Productos.proveedor_id`

### Riesgo estructural a tener en cuenta

La integridad referencial esta protegida solo de forma parcial. Esto significa que el sistema puede quedar con referencias inconsistentes si se manipulan ventas, usuarios o productos sin revisar como se mantienen esas relaciones.

## 4. Busquedas

### Busqueda de clientes

En el modulo de clientes (`frames/clients.py`) la busqueda si usa SQL con `LIKE` y comparacion en minusculas:

```sql
SELECT id, nombre, apellido, dni, telefono, email, direccion,
       fecha_registro, activo, COALESCE(mayorista, 0)
FROM Clientes
WHERE LOWER(nombre) LIKE ?
   OR LOWER(apellido) LIKE ?
   OR LOWER(dni) LIKE ?
   OR LOWER(telefono) LIKE ?
   OR LOWER(email) LIKE ?
ORDER BY apellido, nombre;
```

Limitacion actual:

- No busca por direccion.
- Usa coincidencia parcial de texto, lo que puede devolver varios resultados ambiguos.

En el POS (`frames/sales.py`) no hay busqueda libre de clientes. Se cargan clientes activos en un `Combobox`:

```sql
SELECT id, nombre, apellido, COALESCE(mayorista, 0)
FROM Clientes
WHERE activo = 1
ORDER BY apellido, nombre;
```

Limitacion actual:

- Solo aparecen clientes activos.
- La seleccion es por lista, no por busqueda parcial libre.

### Busqueda de productos

En el POS:

```sql
SELECT id, nombre, descripcion, precio, stock
FROM Productos
ORDER BY nombre;
```

Despues de cargar todo el catalogo, el filtro se hace en memoria sobre:

- `nombre`
- `descripcion`
- `id`

Limitacion actual:

- No usa `LIKE` en SQL.
- Siempre carga todo el catalogo antes de filtrar.
- A mayor volumen de productos, mas dependiente queda del rendimiento del cliente.

En el modulo de productos (`frames/products.py`) tambien se cargan productos y el filtro se hace en memoria:

```sql
SELECT id, nombre, precio, stock, proveedor_id
FROM Productos;
```

Limitacion actual:

- El filtro revisa solo `nombre`.
- No filtra por descripcion, proveedor, codigo ni stock.

### Busqueda en registro de ventas

El registro POS (`frames/registro.py` + `database.py`) trabaja con filtros exactos o por fecha:

- Rango de fechas.
- Mes y ano.
- Producto por `producto_id`.
- Cliente por `cliente_id`.
- Venta por `v.id`.

Consulta base del registro:

```sql
SELECT
    v.id,
    v.fecha,
    v.total,
    COALESCE(v.monto_pagado, 0) AS monto_pagado,
    COALESCE(v.vuelto, 0) AS vuelto,
    COALESCE((c.nombre || ' ' || c.apellido), 'Cliente General') AS cliente_nombre,
    GROUP_CONCAT(DISTINCT COALESCE(p.nombre, dv.nombre_producto)) AS productos,
    COUNT(dv.id) AS lineas
FROM Ventas v
LEFT JOIN Clientes c ON c.id = v.id_cliente
LEFT JOIN DetalleVenta dv ON dv.venta_id = v.id
LEFT JOIN Productos p ON p.id = dv.producto_id
WHERE 1=1
...
GROUP BY v.id, v.fecha, v.total, v.monto_pagado, v.vuelto, c.nombre, c.apellido
ORDER BY datetime(v.fecha) DESC, v.id DESC;
```

Limitaciones actuales:

- Cliente y producto se filtran por seleccion exacta desde combo, no por texto libre.
- `venta_id` es exacto; no hay busqueda parcial.
- La experiencia de busqueda es distinta entre clientes, productos, POS y registro.

## Checklist de revision

### Login

- [ ] Confirmar que `main.py` controla el flujo completo de autenticacion.
- [ ] Verificar la consulta exacta contra `Usuarios`.
- [ ] Probar un acceso valido y uno invalido.
- [ ] Revisar que sucede si el usuario existe pero el rol cambia.
- [ ] Confirmar si hay o no permisos por modulo.
- [ ] Documentar el uso del usuario por defecto `admin / 1234`.

### Ventas

- [ ] Seguir el flujo completo desde seleccion de productos hasta confirmacion.
- [ ] Confirmar como se construye `venta_id`.
- [ ] Verificar en que punto se valida stock.
- [ ] Revisar como se calcula descuento manual y automatico.
- [ ] Confirmar si `Cliente General` guarda `NULL` en `id_cliente`.
- [ ] Validar insercion en `Ventas`.
- [ ] Validar insercion en `DetalleVenta`.
- [ ] Validar descuento de stock en `Productos`.
- [ ] Confirmar generacion y guardado del recibo.
- [ ] Revisar que pasa si falla un paso intermedio.

### Base de Datos

- [ ] Confirmar estructura real de `Clientes`, `Productos`, `Ventas`, `DetalleVenta` y `Usuarios`.
- [ ] Revisar claves primarias y tipos de dato.
- [ ] Validar claves foraneas existentes.
- [ ] Documentar columnas que parecen relacionales pero no tienen `FOREIGN KEY`.
- [ ] Revisar uso de `ventas_diarias` y su relacion con el POS actual.
- [ ] Confirmar indices relevantes para ventas y detalle.

### Busquedas

- [ ] Probar busqueda de clientes por nombre, apellido, DNI, telefono y email.
- [ ] Confirmar que en POS los clientes se eligen por combo y no por busqueda libre.
- [ ] Verificar que en POS el filtro de productos es en memoria.
- [ ] Confirmar que en productos el filtro actual revisa solo `nombre`.
- [ ] Validar que en registro de ventas el filtro de cliente y producto es exacto por ID.
- [ ] Registrar diferencias de comportamiento entre modulos.

## Riesgos detectados

### Riesgos sobre ventas

- El guardado de una venta no esta encapsulado en una transaccion explicita de alto nivel; `DBManager.execute()` hace `commit` por cada sentencia. Si algo falla a mitad del proceso, puede quedar cabecera guardada sin detalle completo o con stock parcialmente actualizado.
- El flujo POS actual depende fuertemente de `frames/sales.py`; tocarlo sin mapearlo bien puede romper cobro, descuento, recibo o persistencia.

### Riesgos sobre stock

- El control de stock esta principalmente en la logica de UI antes de guardar, no reforzado por restricciones de base de datos.
- El descuento de stock ocurre despues de insertar detalle; un error intermedio puede desincronizar inventario y venta.

### Riesgos sobre integridad de datos

- `DetalleVenta.producto_id` no tiene clave foranea real hacia `Productos`.
- `Ventas.usuario_id` no tiene clave foranea real hacia `Usuarios`.
- `Cliente General` usa `NULL` en `id_cliente`; si no se entiende este comportamiento, se pueden romper reportes o filtros.
- La coexistencia de `Ventas`/`DetalleVenta` con `ventas_diarias` puede generar confusion si se modifica el registro sin distinguir que tabla es fuente principal.

### Riesgos sobre autenticacion

- Las contrasenas estan en texto plano.
- Existe un usuario semilla por defecto si la tabla `Usuarios` esta vacia.
- El rol visible no implica necesariamente control real de permisos.

## Entregables del Dia 1

Al finalizar el dia, el equipo debe dejar documentado:

- Lista de archivos clave por flujo.
- Flujo real del login.
- Flujo real de la venta POS.
- Tablas principales y relaciones confirmadas.
- Consultas SQL relevantes de busqueda y registro.
- Riesgos funcionales y estructurales detectados.
- Problemas observados durante pruebas manuales.
- Propuestas iniciales de mejora, sin implementar.

## Recomendaciones

- Leer primero `main.py`, `database.py`, `frames/sales.py` y `frames/registro.py`.
- Probar manualmente login, venta completa, reimpresion y busquedas antes de cambiar codigo.
- No asumir que la capa `erp/` es la que gobierna el flujo real; la UI legacy todavia ejecuta parte critica del negocio.
- Antes de intervenir ventas o stock en dias posteriores, trabajar con una copia de la base y definir casos de prueba manuales.
- Si se va a tocar persistencia, primero documentar que pasos deben ser atomicos.
- Si se va a tocar busquedas, primero alinear criterios entre POS, clientes, productos y registro.
