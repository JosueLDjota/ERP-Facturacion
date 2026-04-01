# Plan De Refactor Progresivo

## Decision Arquitectonica
Se adopta una arquitectura hibrida de refactor progresivo:

- `frames/` se mantiene como capa de presentacion Tkinter.
- `erp/domain/use_cases/` concentra orquestacion de casos de uso.
- `erp/domain/services/` concentra reglas de negocio puras.
- `erp/data/repositories/` encapsula acceso a SQLite a traves de `DBManager`.
- `database.py` se conserva temporalmente como backend legacy y motor de migraciones/transacciones.

Objetivo operativo:

- sacar negocio y SQL directo de las pantallas criticas sin reescribir la aplicacion,
- reducir el radio de cambio en ventas, stock y autenticacion,
- permitir evolucion incremental por modulo.

## Estado Real Del Codigo

- La arquitectura operativa actual es `main.py` + `frames/*.py` + `database.py`.
- `erp/` existe, pero hoy solo se usa de forma parcial.
- `database.py` es un servicio central con demasiadas responsabilidades:
  autenticacion, migraciones, reglas de integridad, operaciones POS, reportes, configuracion y CRUD basico.
- El acoplamiento principal hoy es `UI -> DBManager`.

Conclusiones de riesgo:

- `Ventas` y `stock` siguen siendo el nucleo de mayor riesgo.
- `Autenticacion` ya esta endurecida, pero aun depende de `database.py` directo desde `main.py`.
- `Productos` sigue mezclando UI, validacion, busqueda de proveedores y persistencia.

## Principios De Ejecucion

- No reescribir `database.py` de una vez.
- No mover SQL critico sin pruebas o wrappers.
- Primero encapsular, luego sustituir llamadas desde UI.
- Cambiar una sola ruta critica por fase.
- Dejar la UI intacta visualmente mientras se cambia la orquestacion.

## Fase 1
### Ventas Y Autenticacion

### Objetivo
Encapsular login y venta POS para que la UI deje de decidir persistencia y validaciones centrales.

### Archivos Fuente

- [main.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/main.py)
- [frames/sales.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/sales.py)
- [database.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/database.py)
- [receipt_builder.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/receipt_builder.py)

### Funciones A Migrar Primero

- De [main.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/main.py)
  - `authenticate`
- De [database.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/database.py)
  - `authenticate_user`
  - `transaction`
  - `create_pos_sale`
  - `fetch_sale_header`
  - `fetch_sale_items`
- De [frames/sales.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/sales.py)
  - `load_products`
  - `load_clients`
  - `load_discounts`
  - `recalculate_item_discount`
  - `recalculate_cart_discounts`
  - `_build_sale_snapshot`
  - `_calculate_invoice_totals`
  - `confirm_sale_and_process`
  - `_receipt_items`
  - `generate_receipt_html`

### Archivos Destino

- `erp/data/repositories/user_repository.py`
- `erp/data/repositories/sale_repository.py`
- `erp/data/repositories/product_repository.py`
- `erp/data/repositories/client_repository.py`
- `erp/data/repositories/config_repository.py`
- `erp/domain/services/password_service.py`
- `erp/domain/services/discount_policy.py`
- `erp/domain/services/stock_policy.py`
- `erp/domain/services/receipt_service.py`
- `erp/domain/use_cases/auth/login_user.py`
- `erp/domain/use_cases/sales/create_pos_sale.py`
- `erp/domain/use_cases/sales/load_pos_context.py`
- `erp/domain/use_cases/sales/reprint_sale_receipt.py`

### Movimiento Concreto

- `main.py` deja de llamar `self.db.authenticate_user(...)`.
- `main.py` llama `login_user.execute(username, password)`.
- `user_repository` encapsula la lectura/escritura de usuarios sobre `DBManager`.
- `password_service` absorbe hash y verificacion; `database.py` queda solo como compatibilidad temporal.
- `frames/sales.py` deja de consultar directamente descuentos, clientes y productos.
- `load_pos_context` devuelve catalogo, clientes y descuentos para poblar la UI.
- `create_pos_sale` de caso de uso:
  - valida metodo de pago,
  - valida carrito,
  - calcula totales,
  - llama al repositorio transaccional,
  - construye resultado de venta listo para recibo.
- `sale_repository` usa internamente el bloque atomico hoy existente en `database.py:create_pos_sale`.
- `receipt_service` usa [receipt_builder.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/receipt_builder.py) como adaptador, no desde la UI.

### Que Se Queda Temporalmente En UI

- `Treeview`, modales, atajos teclado, preview windows, estados visuales.
- Seleccion de filas y edicion de cantidades.
- Mensajes `messagebox`.

### Criterio De Salida De Fase 1

- `main.py` sin autenticacion directa contra `DBManager`.
- `frames/sales.py` sin SQL directo para cargar contexto ni confirmar venta.
- Toda venta POS pasa por un unico caso de uso.
- Las pruebas unitarias cubren:
  - login valido/invalido,
  - venta atomica,
  - stock insuficiente,
  - descuento,
  - recibo generado.

## Fase 2
### Productos E Inventario

### Objetivo
Separar validacion, CRUD, importacion y ajustes de precio de la pantalla de productos.

### Archivos Fuente

- [frames/products.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/products.py)
- [file_manager.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/file_manager.py)
- [database.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/database.py)
- [frames/taxonomy.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/taxonomy.py)

### Funciones A Migrar Primero

- De [frames/products.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/products.py)
  - `load_products`
  - `filter_products`
  - `select_product`
  - `_load_supplier_options`
  - `_validate_codigo_producto`
  - `_validate_product_payload`
  - `save_product`
  - `_fetch_supplier_matches`
  - `open_price_optimizer`
  - `delete_product`
- De [file_manager.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/file_manager.py)
  - `get_data_from_db`
  - `import_products`
  - `show_import_preview`
  - `confirm_import` interno

### Archivos Destino

- `erp/data/repositories/product_repository.py`
- `erp/data/repositories/supplier_repository.py`
- `erp/data/repositories/taxonomy_repository.py`
- `erp/domain/services/product_validation_service.py`
- `erp/domain/services/product_code_service.py`
- `erp/domain/services/product_import_service.py`
- `erp/domain/services/price_adjustment_service.py`
- `erp/domain/use_cases/products/list_products.py`
- `erp/domain/use_cases/products/save_product.py`
- `erp/domain/use_cases/products/delete_product.py`
- `erp/domain/use_cases/products/search_suppliers.py`
- `erp/domain/use_cases/products/bulk_import_products.py`
- `erp/domain/use_cases/products/adjust_prices.py`

### Movimiento Concreto

- `ProductFrame` deja de hacer `self.db.fetch(...)` y `self.db.execute(...)`.
- `list_products` devuelve DTOs de producto ya enriquecidos con proveedor y codigo.
- `save_product` centraliza:
  - validacion de nombre, precio, stock, proveedor,
  - validacion de `codigo_producto`,
  - control de duplicado,
  - insercion o actualizacion.
- `product_repository` deja de ser solo un CRUD minimo y pasa a soportar:
  - lectura con joins,
  - busqueda por nombre y `codigo_producto`,
  - persistencia de categoria y marca,
  - actualizacion de precio por lote.
- `product_import_service` absorbe la logica de importacion hoy repartida en [file_manager.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/file_manager.py).
- `taxonomy_repository` expone `Categorias` y `Marcas` para que productos y configuracion no consulten SQL directo.

### Que Se Queda Temporalmente En UI

- Ventana flotante de nuevo producto.
- Suggestion box de proveedores.
- Treeview y formularios.
- Flujo de preview antes de importar.

### Criterio De Salida De Fase 2

- [frames/products.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/frames/products.py) sin validacion de negocio relevante ni SQL directo.
- [file_manager.py](/C:/Users/Hugo/Desktop/ERP-Facturacion/file_manager.py) reducido a adaptador de archivos/dialogos.
- CRUD de productos usable desde caso de uso y testeable sin Tkinter.
- Importacion de productos protegida por pruebas de integridad y rollback.

## Secuencia Recomendada De Commits

- Commit 1: repositorios de auth y login use case, sin cambiar UI.
- Commit 2: `main.py` usando `login_user`.
- Commit 3: repositorios/contexto POS y use case de carga POS.
- Commit 4: `frames/sales.py` consume contexto desde use case.
- Commit 5: caso de uso `create_pos_sale` + wrapper sobre `database.py:create_pos_sale`.
- Commit 6: `frames/sales.py` confirma venta via caso de uso.
- Commit 7: repositorio de productos extendido.
- Commit 8: `save_product` use case + sustitucion en `frames/products.py`.
- Commit 9: importacion por servicio.
- Commit 10: ajuste de precios y taxonomia via casos de uso.

## Antiobjetivos

- No mover todavia `dashboard`, `registro`, `clientes` ni `proveedores` completos.
- No eliminar `database.py`.
- No cambiar SQLite.
- No reestructurar carpetas de UI en esta etapa.

## Siguiente Modulo Despues De Fase 2

- `Clientes`
- `Registro de ventas`
- `Configuracion`

Razon:

- ya dependeran de repositorios y use cases estabilizados,
- tendran menos riesgo que ventas,
- reutilizaran patrones ya probados.
