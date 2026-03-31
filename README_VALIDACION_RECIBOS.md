# Validacion Robusta de Guardado de Recibos

## Objetivo

Documentar el ajuste realizado para evitar que una venta falle cuando la ruta configurada para guardar recibos ya no existe, apunta a otro perfil de Windows o no tiene permisos de escritura.

## Problema Detectado

Al procesar una venta, el sistema intentaba guardar el recibo HTML en una ruta persistida en la configuracion `recibo_save_path`.

Caso reportado:

```text
No se pudo procesar la venta: (winError 5) Acceso denegado: 'C:\\Users\\elqui'
```

La causa era una ruta heredada o invalida que seguia almacenada en la base de datos y apuntaba a un perfil de usuario distinto al actual.

## Cambio Aplicado

Se reforzo el metodo `save_receipt` en `frames/sales.py` con un flujo mas tolerante a errores:

1. Lee la ruta configurada en `recibo_save_path`.
2. Intenta guardar el recibo en esa ruta si existe una configuracion previa.
3. Si ocurre un error de acceso o escritura, prueba automaticamente una ruta local segura:

```text
%LOCALAPPDATA%\\ERP-Facturacion\\Recibos
```

4. Si el guardado en la ruta alternativa funciona, actualiza la configuracion para futuras ventas.
5. Solo lanza error si fallan tanto la ruta configurada como la ruta predeterminada.

## Beneficios

- Evita que una venta completa falle por una ruta vieja o sin permisos.
- Corrige automaticamente configuraciones heredadas de otro usuario.
- Reduce soporte manual por errores de acceso en Windows.
- Mantiene persistida una ruta valida despues de la recuperacion.

## Archivos Modificados

- `frames/sales.py`
- `tests/unit/test_pos_receipt_path.py`

## Cobertura de Prueba

Se agrego una prueba unitaria que simula este escenario:

- La ruta configurada es `C:\\Users\\elqui`.
- El primer intento falla con `PermissionError`.
- El sistema hace fallback a una carpeta temporal valida.
- La nueva ruta se guarda en configuracion.
- El recibo termina generandose correctamente.

## Resultado Esperado

Despues de este cambio, cuando exista una ruta invalida en configuracion:

- la venta debe continuar,
- el recibo debe guardarse en una ruta segura del usuario actual,
- y la configuracion debe quedar autocorregida.

## Nota Tecnica

Este ajuste fortalece la validacion operativa del guardado, pero no modifica la logica de negocio de ventas ni el registro SQL de la transaccion. El cambio se enfoca exclusivamente en hacer mas robusto el manejo de rutas de salida para recibos.
