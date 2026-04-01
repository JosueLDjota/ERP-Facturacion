# ERP Facturacion (Desktop)

Sistema ERP de escritorio orientado a facturacion y punto de venta (POS), desarrollado en Python con interfaz Tkinter y base de datos SQLite.

## Funcion Del Proyecto

Este proyecto permite administrar el ciclo comercial basico de un negocio:

- Gestion de clientes (altas, edicion, estados, import/export CSV).
- Gestion de productos e inventario (CRUD, ajuste masivo de precios, import/export CSV).
- Gestion de proveedores.
- Punto de venta unificado (carrito, descuentos, metodos de pago, cambio, confirmacion de venta).
- Generacion de recibos en HTML (ticket/carta), guardado local y reimpresion.
- Registro historico de ventas con filtros por fecha, producto, cliente y venta.
- Dashboard con KPIs y graficas (ventas por mes/dia, stock bajo, producto mas vendido).
- Configuracion de descuentos y plantilla de recibo.

## Tecnologias Utilizadas

- Python 3.11+
- Tkinter / ttk (UI de escritorio)
- SQLite3 (persistencia local)
- matplotlib (graficas en dashboard)
- tkcalendar (selector de fechas en registro)
- unittest (pruebas)

## Arquitectura Del Proyecto

El proyecto combina una UI legacy funcional con una estructura organizada en `erp/` para evolucionar el sistema sin perder compatibilidad:

- `erp/domain/`: reglas de negocio y casos de uso.
- `erp/data/`: repositorios sobre SQLite.
- `erp/infrastructure/`: adaptadores de archivos e impresion.
- `erp/ui/`: namespace organizado de utilidades visuales y entrada futura para frames.
- `frames/`: capa legacy compatible mientras termina la migracion fisica de UI.

## Estructura Principal

```text
ERP-Facturacion/
  main.py                 # Punto de entrada
  database.py             # DBManager, esquema y consultas SQLite
  file_manager.py         # Wrapper legacy
  receipt_builder.py      # Wrapper legacy
  erp/                    # Dominio, datos, infraestructura y UI organizada
  frames/                 # Modulos UI legacy compatibles
  docs/                   # Documentacion tecnica y funcional
  tests/                  # Pruebas unitarias e integracion
  erp_profesional.db      # Base de datos local
```

## Documentacion

La documentacion tecnica ya no vive dispersa en la raiz.

- [Indice de documentacion](./docs/README.md)
- [Estado actual y reestructuracion](./docs/architecture/ESTADO_ACTUAL_Y_REESTRUCTURACION_2026-04-01.md)
- [Plan de refactor progresivo](./docs/architecture/PLAN_REFACTOR_PROGRESIVO.md)

## Requisitos

- Python 3.11 o superior
- pip

## Instalacion

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install matplotlib tkcalendar
```

## Ejecucion

```bash
python main.py
```

## Credenciales Iniciales

El sistema crea un usuario por defecto si la tabla `Usuarios` esta vacia:

- Usuario: `admin`
- Contrasena: `1234`

Recomendacion: cambiar estas credenciales en entornos reales.

## Base De Datos

- Archivo por defecto: `erp_profesional.db`
- Motor: SQLite local
- Inicializacion automatica de tablas y datos semilla desde `DBManager` (`database.py`).

## Pruebas

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Modulos UI Disponibles

- `Dashboard`: indicadores y graficas operativas.
- `Ventas (POS)`: venta normal/especial, descuentos, pagos y recibo.
- `Registro de Ventas`: consulta historica, exportacion e impresion.
- `Clientes`: CRUD, filtros y estadisticas.
- `Productos`: CRUD, busqueda, import/export y ajuste de precios.
- `Proveedores`: CRUD y exportacion.
- `Configuracion`: descuentos + editor de plantilla de recibo.

## Notas

- El proyecto actualmente es desktop-first (no web).
- Los recibos HTML se guardan en una ruta configurable desde el sistema.
- Existe codigo modular en `erp/` para facilitar refactor y escalabilidad.
