# Estado Actual Y Reestructuracion

Fecha de corte: `2026-04-01`

## Diagnostico Actual

El sistema ya no es solo `main.py + frames + database.py`, pero tampoco esta en una arquitectura totalmente desacoplada. El estado real hoy es hibrido y controlado:

- `database.py` sigue siendo backend legacy y motor de migraciones/transacciones.
- `erp/data/repositories/` encapsula acceso a datos para autenticacion, POS, productos y proveedores.
- `erp/domain/use_cases/` ya concentra Fase 1 y Fase 2:
  - `auth/`
  - `sales/`
  - `products/`
- `erp/domain/services/` concentra logica pura reutilizable:
  - recibos
  - validacion de producto
  - importacion de productos
  - ajuste de precios
  - calculo de factura
- `erp/infrastructure/` ahora agrupa adaptadores no dominiales:
  - `io/file_manager.py`
  - `printing/receipt_builder.py`
- `erp/ui/` ya existe como punto de entrada organizado para utilidades visuales y namespace de UI:
  - `shared.py`
  - `frames/__init__.py`
  - `notifications.py`

## Reestructuracion Cerrada En Esta Etapa

Se considero “cerrada” la reestructuracion de arquitectura para esta fase porque:

1. El codigo nuevo ya entra por `erp.*` y no por archivos sueltos en raiz.
2. Los servicios transversales dejaron de vivir como implementacion primaria en la raiz.
3. La documentacion dejo de estar dispersa.
4. La UI tiene namespace nuevo (`erp.ui`) sin romper la capa legacy actual.

## Compatibilidad Legacy Conservada

Para minimizar riesgo en produccion se mantuvieron wrappers de compatibilidad:

- `file_manager.py`
- `receipt_builder.py`
- `frames/ui.py`

Y la carpeta `frames/` sigue existiendo como capa legacy compatible para:

- imports ya existentes,
- pruebas actuales,
- modulos no migrados por completo.

## Decisiones Intencionales

### Lo que SI se reorganizo

- utilidades de UI a `erp/ui/shared.py`
- infraestructura de archivos a `erp/infrastructure/io/`
- infraestructura de recibos a `erp/infrastructure/printing/`
- namespace nuevo de frames en `erp/ui/frames/`
- documentacion en `docs/`

### Lo que NO se movio todavia

- `database.py`
- `main.py`
- implementaciones fisicas de `frames/*.py`

Estas piezas se dejaron estables por una razon de riesgo:

- `database.py` sigue siendo el backend operativo real;
- `main.py` sigue siendo el entrypoint desktop;
- mover fisicamente todos los `frames` aportaria mas riesgo inmediato que valor funcional.

## Resultado Arquitectonico

La arquitectura efectiva recomendada queda asi:

```text
ERP-Facturacion/
  main.py                        # entrypoint legacy estable
  database.py                    # backend SQLite legacy estable
  file_manager.py                # wrapper legacy
  receipt_builder.py             # wrapper legacy
  frames/                        # capa UI legacy compatible
  erp/
    data/
      repositories/
    domain/
      entities/
      services/
      use_cases/
    infrastructure/
      io/
      printing/
    ui/
      shared.py
      notifications.py
      frames/
  docs/
    architecture/
    analysis/
  tests/
```

## Pendientes Reales

La reestructuracion de carpetas puede considerarse terminada para esta etapa. Los pendientes que quedan ya no son de organizacion fisica sino de encapsulacion funcional:

- mover `clientes`, `registro` y `proveedores` a casos de uso propios,
- seguir reduciendo dependencias directas a `database.py`,
- eventualmente convertir `frames/` en wrappers y mover implementacion real a `erp/ui/frames/`.

## Conclusión

La arquitectura ya quedo alineada con la estrategia elegida:

- monolito desktop,
- modularizacion por capas internas,
- refactor progresivo,
- compatibilidad legacy controlada,
- bajo riesgo operativo.
