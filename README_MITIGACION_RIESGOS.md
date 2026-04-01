# Mitigacion de Riesgos en Ventas, Stock y Autenticacion

## Archivos clave por flujo

- `main.py`: login, sesion activa y visibilidad de modulos por rol.
- `database.py`: esquema SQLite, migraciones, autenticacion, transacciones y persistencia POS.
- `frames/sales.py`: flujo real del POS legacy, resumen, confirmacion y recibos.
- `frames/registro.py`: consulta del historial, reimpresion y mantenimiento legacy.
- `erp/domain/services/access_control.py`: reglas basicas de permisos por rol.

## Flujo real del login

1. `main.py` construye la pantalla en `show_login()`.
2. `authenticate()` valida si hay usuarios disponibles y consulta `DBManager.authenticate_user()`.
3. `database.py` compara contra hash PBKDF2 y migra credenciales legacy en texto plano.
4. Si la autenticacion es valida, `main.py` calcula las secciones permitidas por rol y arma la UI principal.

## Flujo real de la venta POS

1. `frames/sales.py` arma el carrito y valida cantidades en UI.
2. Al confirmar, `confirm_sale_and_process()` delega la persistencia a `DBManager.create_pos_sale()`.
3. `database.py` abre una transaccion atomica, inserta cabecera, revalida stock, descuenta inventario y registra detalle.
4. Si cualquier item falla, se hace rollback completo.
5. El recibo se genera despues del commit. Si falla su guardado, la venta queda registrada y se informa como advertencia, no como error de persistencia.

## Tablas principales y relaciones confirmadas

- `Ventas`: fuente principal de cabecera POS.
- `DetalleVenta`: fuente principal de detalle POS.
- `ventas_diarias`: tabla legacy de trazabilidad; no es la fuente principal del registro POS.
- `Ventas.usuario_id -> Usuarios.id`: FK real con `ON DELETE SET NULL`.
- `Ventas.id_cliente -> Clientes.id`: FK real con `ON DELETE SET NULL`.
- `DetalleVenta.venta_id -> Ventas.id`: FK real con `ON DELETE CASCADE`.
- `DetalleVenta.producto_id -> Productos.id`: FK real con `ON DELETE SET NULL`.

## Mitigaciones aplicadas

- Persistencia POS encapsulada en una transaccion explicita de alto nivel.
- Revalidacion de stock al confirmar, no solo en la UI.
- Triggers para evitar stock negativo y detalle con valores invalidos.
- Migracion de contrasenas a hash PBKDF2 con compatibilidad retroactiva.
- Eliminacion del relleno automatico `admin / 1234` en la pantalla de login.
- El admin por defecto solo se crea en bootstrap real de una base nueva; no se recrea automaticamente en bases existentes sin usuarios.
- Restriccion de modulos sensibles y depuracion legacy segun rol.
- Registro visual de que `Ventas/DetalleVenta` es la fuente principal y `ventas_diarias` es legacy.

## Riesgos que siguen vigentes

- La matriz de permisos es basica y por coincidencia de nombre de rol; si aparecen roles nuevos conviene formalizar permisos por tabla.
- No existe aun un flujo UI para alta, baja o cambio de contrasena de usuarios.
- `ventas_diarias` sigue coexistiendo por compatibilidad historica; conviene planificar su retiro o sincronizacion explicita.
