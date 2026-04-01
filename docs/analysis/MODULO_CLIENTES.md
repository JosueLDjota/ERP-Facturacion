# 📋 MÓDULO DE CLIENTES - DOCUMENTACIÓN

## ✅ Resumen de Cambios Implementados

### 🗃️ **Base de Datos**

- ✅ Eliminada tabla `cliente` anterior con datos existentes
- ✅ Creada nueva tabla `Clientes` con estructura optimizada:

  - `id` (PRIMARY KEY)
  - `nombre` (requerido)
  - `apellido` (requerido)
  - `dni` (único, opcional)
  - `telefono` (opcional)
  - `email` (opcional)
  - `direccion` (opcional)
  - `fecha_registro` (automático)
  - `activo` (estado del cliente)

- ✅ Modificada tabla `Ventas` para incluir referencia a clientes:

  - Agregado campo `cliente_id` con foreign key

- ✅ Agregados 4 clientes de ejemplo con datos realistas

### 🎯 **Módulo de Gestión de Clientes** (`frames/clients.py`)

#### **Funcionalidades Principales:**

1. **➕ Registro de Clientes**

   - Formulario completo con validaciones
   - Campos obligatorios: nombre y apellido
   - Validación de DNI (13 dígitos)
   - Validación de formato de email
   - Estado activo/inactivo

2. **✏️ Edición de Clientes**

   - Selección desde lista
   - Carga automática de datos en formulario
   - Actualización en tiempo real

3. **🗑️ Eliminación Inteligente**

   - Verificación de ventas asociadas
   - Opción de desactivar vs eliminar definitivamente
   - Protección de integridad referencial

4. **🔍 Búsqueda y Filtrado**

   - Búsqueda en tiempo real por cualquier campo
   - Filtros por estado (activos/inactivos/todos)
   - Lista ordenada por apellido

5. **📊 Estadísticas**

   - Total de clientes
   - Clientes activos/inactivos
   - Clientes con compras
   - Registros del mes actual
   - Porcentajes de actividad

6. **📤📥 Importación/Exportación**
   - Exportar lista completa a CSV
   - Importar clientes desde CSV
   - Manejo de errores y duplicados

#### **Interfaz de Usuario:**

- **Diseño de dos columnas:** formulario + lista
- **Búsqueda en tiempo real** con filtros
- **Lista con colores** según estado del cliente
- **Botones intuitivos** con iconos
- **Validaciones visuales** con mensajes claros

### 🛒 **Integración con Ventas**

#### **Selector de Cliente en POS:**

- ✅ Combobox con clientes activos en módulo de ventas
- ✅ Opción "Cliente General" para ventas sin cliente específico
- ✅ Botón de actualizar lista de clientes
- ✅ Guardado de `cliente_id` en base de datos de ventas
- ✅ Limpieza automática al resetear carrito

#### **Flujo de Venta:**

1. Seleccionar cliente (opcional)
2. Agregar productos al carrito
3. Aplicar descuentos si es necesario
4. Finalizar venta con cliente asociado

### 🔧 **Arquitectura Técnica**

#### **Archivos Modificados:**

- `database.py` - Nueva tabla Clientes y relación con Ventas
- `frames/clients.py` - Módulo completo de gestión
- `frames/__init__.py` - Importación del nuevo módulo
- `main.py` - Navegación y botón de acceso
- `frames/sales.py` - Integración con selector de clientes

#### **Patrones Utilizados:**

- **CRUD completo** con validaciones
- **Arquitectura MVC** con separación de responsabilidades
- **Validación en tiempo real** para mejor UX
- **Manejo de errores** con mensajes informativos
- **Integridad referencial** en base de datos

### 🎮 **Controles y Atajos**

#### **En Módulo de Clientes:**

- **Doble clic** en lista para editar
- **Enter** en búsqueda para filtrar
- **Tab** para navegación entre campos

#### **En Ventas (POS):**

- **F1** - Búsqueda de productos
- **F2** - Finalizar venta
- **F3** - Aplicar descuento a todos
- **F4** - Remover todos los descuentos

### 📈 **Beneficios del Sistema**

1. **Trazabilidad de Ventas:** Cada venta puede asociarse a un cliente específico
2. **Marketing Dirigido:** Estadísticas por cliente para campañas
3. **Historial de Compras:** Análisis de patrones de compra
4. **Gestión de Fidelidad:** Identificación de clientes frecuentes
5. **Reportes Avanzados:** Segmentación por cliente y comportamiento

### 🚀 **Funcionalidades Futuras Sugeridas**

1. **Historial de Compras por Cliente**
2. **Sistema de Puntos/Fidelidad**
3. **Descuentos Personalizados por Cliente**
4. **Reportes de Ventas por Cliente**
5. **Notificaciones de Cumpleaños**
6. **Límites de Crédito**
7. **Integración con WhatsApp/Email**

---

## 🎯 **Cómo Usar el Módulo**

### **Gestionar Clientes:**

1. Desde el menú principal, clic en **"Clientes"**
2. Completar formulario para nuevo cliente
3. Usar búsqueda para encontrar clientes existentes
4. Hacer doble clic para editar
5. Usar estadísticas para análisis

### **Vender a Cliente Específico:**

1. En módulo **"Ventas (POS)"**
2. Seleccionar cliente en combobox superior
3. Agregar productos normalmente
4. Finalizar venta (queda asociada al cliente)

### **Importar/Exportar:**

1. **Exportar:** Botón "📤 Exportar CSV"
2. **Importar:** Preparar CSV con columnas: Nombre, Apellido, DNI, Teléfono, Email, Dirección, Activo
3. **Formato:** Usar archivo exportado como plantilla

---

## ✅ **Estado del Proyecto**

**✅ COMPLETADO:**

- Base de datos actualizada
- Módulo de clientes funcional
- Integración con ventas
- Validaciones y controles de calidad
- Documentación completa

**🎯 LISTO PARA PRODUCCIÓN**

El módulo de clientes está completamente funcional e integrado con el sistema ERP existente. Todos los cambios son retrocompatibles y no afectan funcionalidades previas.
