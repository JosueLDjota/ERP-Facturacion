# Sistema ERP Profesional

Sistema de gestión empresarial (ERP) completo desarrollado en Python con Tkinter y SQLite.

## Características

- **Dashboard**: Panel de control con métricas de ventas, stock bajo y productos más vendidos
- **Sistema POS**: Punto de venta completo con búsqueda de productos, carrito y generación de recibos
- **Gestión de Productos**: CRUD completo con importación/exportación CSV
- **Gestión de Proveedores**: Administración de proveedores y contactos
- **Configuración**: Gestión de descuentos y plantillas de recibos personalizables
- **Base de datos SQLite**: Almacenamiento local sin necesidad de servidor

## Estructura del Proyecto

```
erp_app/
├── main.py              # Punto de entrada
├── database.py          # Gestor de base de datos
├── file_manager.py      # Importación/exportación
├── frames/
│   ├── __init__.py      # Paquete de frames
│   ├── dashboard.py     # Panel de control
│   ├── products.py      # Gestión de productos
│   ├── suppliers.py     # Gestión de proveedores
│   ├── config.py        # Configuración
│   └── sales.py         # Sistema POS
├── assets/              # Recursos (opcional)
└── README.md
```

## Requisitos

- Python 3.7 o superior
- Tkinter (incluido con Python)
- SQLite3 (incluido con Python)
- tkcalendar (DatePicker para filtros de fechas)

## Instalación

1. **Clonar o descargar el proyecto**

```bash
git clone https://github.com/tu-usuario/erp-sistema.git
cd erp-sistema
```

2. **Crear la estructura de carpetas**

```bash
mkdir -p erp_app/frames
mkdir -p erp_app/assets
```

3. **Colocar todos los archivos en sus respectivas carpetas**

- `main.py`, `database.py`, `file_manager.py` → raíz de `erp_app/`
- Todos los archivos de frames → `erp_app/frames/`

## Ejecución

```bash
cd erp_app
python main.py
```

### Dependencias adicionales

Si no está instalado `tkcalendar`, instálalo con:

```bash
pip install tkcalendar
```

## Credenciales por Defecto

- **Usuario**: `admin`
- **Contraseña**: `1234`

## Uso del Sistema

### 1. Login

Al iniciar, ingrese las credenciales por defecto o las que haya configurado.

### 2. Dashboard

Muestra métricas importantes:

- Total de ventas acumuladas
- Productos con stock bajo
- Producto más vendido
- Alertas de inventario

### 3. Sistema POS (Ventas)

**Atajos de teclado**:

- `F1`: Abrir búsqueda de productos
- `F2`: Finalizar venta

**Proceso de venta**:

1. Presione F1 o "Buscar Producto"
2. Busque y seleccione productos
3. Ingrese cantidad y añada al carrito
4. Aplique descuentos si es necesario
5. Ingrese monto recibido
6. Presione F2 o "Finalizar Venta"
7. Guarde el recibo HTML generado

### 4. Gestión de Productos

- **Agregar**: Click en "Nuevo Producto", complete el formulario y guarde
- **Editar**: Seleccione un producto de la lista, modifique y guarde
- **Eliminar**: Seleccione y click en "Eliminar"
- **Buscar**: Use la barra de búsqueda en tiempo real
- **Importar CSV**: Click en "Importar CSV" y seleccione el archivo
- **Exportar CSV**: Click en "Exportar CSV"

### 5. Gestión de Proveedores

CRUD completo para administrar proveedores:

- Nombre de la empresa
- Persona de contacto
- Teléfono

### 6. Configuración

**Pestaña Descuentos**:

- Crear descuentos por docena, mayorista o por producto
- Definir porcentajes
- Aplicar en el sistema POS

**Pestaña Plantilla de Recibo**:

- Editar plantilla HTML del recibo
- Variables disponibles:
  - `{{NOMBRE_NEGOCIO}}`
  - `{{ID_VENTA}}`
  - `{{FECHA}}`
  - `{{TOTAL}}`
  - `{{MONTO_PAGADO}}`
  - `{{VUELTO}}`
  - `<!-- ITEMS_PLACEHOLDER -->`
- Vista previa antes de guardar

## Formato CSV para Importación

### Productos.csv

```csv
id,nombre,descripcion,precio,stock,proveedor_id
1,Monitor 27",Monitor 4K,320.00,15,1
2,Teclado RGB,Mecánico switches blue,45.00,100,1
```

**Campos**:

- `id`: ID del producto (opcional para nuevos)
- `nombre`: Nombre del producto (obligatorio)
- `descripcion`: Descripción detallada
- `precio`: Precio en formato decimal (obligatorio)
- `stock`: Cantidad disponible (obligatorio)
- `proveedor_id`: ID del proveedor (obligatorio)

## Base de Datos

El sistema crea automáticamente un archivo `erp_profesional.db` con las siguientes tablas:

- **Productos**: Inventario completo
- **Proveedores**: Información de proveedores
- **Usuarios**: Credenciales de acceso
- **Descuentos**: Reglas de descuento
- **Ventas**: Registro de todas las ventas
- **DetalleVenta**: Items de cada venta
- **Configuracion**: Parámetros del sistema

## Personalización

### Cambiar Colores

Edite el método `configure_styles()` en `main.py`:

```python
self.style.configure('Accent.TButton',
    background='#tu_color',  # Color principal
    foreground='white'
)
```

### Agregar Nuevos Módulos

1. Crear nuevo archivo en `frames/nuevo_modulo.py`
2. Importar en `frames/__init__.py`
3. Agregar al diccionario en `main.py`:

```python
self.frames = {
    ...
    "Nuevo Módulo": NuevoModuloFrame
}
```

## Troubleshooting

### Error: ModuleNotFoundError

- Verifique que todos los archivos estén en las carpetas correctas
- Asegúrese de ejecutar desde la carpeta `erp_app/`

### Error: No module named 'tkinter'

En Linux:

```bash
sudo apt-get install python3-tk
```

### Base de datos bloqueada

- Cierre todas las instancias de la aplicación
- Elimine el archivo `erp_profesional.db` para reiniciar

## Mejoras Futuras

- [ ] Reportes en PDF
- [ ] Gráficos estadísticos
- [ ] Multi-usuario con roles avanzados
- [ ] Sincronización en la nube
- [ ] Código de barras
- [ ] Facturación electrónica

## Licencia

Este proyecto es de código abierto y puede ser usado libremente para fines educativos o comerciales.

## Contacto

Para soporte o consultas: [tu-email@ejemplo.com]

---

**Desarrollado con ❤️ usando Python y Tkinter**



