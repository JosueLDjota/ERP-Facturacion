from __future__ import annotations

# Contexto del archivo:
# Servicio de validacion de producto. Reune reglas de nombre, precio, stock,
# proveedor y `codigo_producto` para que los formularios y la importacion CSV
# compartan exactamente los mismos criterios de negocio.

from dataclasses import dataclass

from erp.domain.entities.product import Product


def _normalize_amount(value) -> float:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0.0
    return round(number, 2)


def _parse_amount(value) -> float:
    cleaned = str(value or "").strip().upper()
    cleaned = cleaned.replace("HNL", "").replace("L", "").replace(",", "")
    if not cleaned:
        raise ValueError("El precio en HNL es obligatorio.")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError("Precio HNL invalido.") from exc


def _parse_optional_id(value, *, label: str, exists=None) -> int | None:
    if value in (None, ""):
        return None

    try:
        parsed_value = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Debe seleccionar una {label} valida.") from exc

    if parsed_value <= 0:
        raise ValueError(f"Debe seleccionar una {label} valida.")

    if exists and not exists(parsed_value):
        raise ValueError(f"La {label} seleccionada no existe.")

    return parsed_value


@dataclass(slots=True)
class ProductValidationService:
    def validate(
        self,
        *,
        nombre: str,
        precio,
        stock,
        proveedor_id,
        descripcion: str = "",
        codigo_producto: str = "",
        categoria_id=None,
        marca_id=None,
        current_product_id: int | None = None,
        supplier_exists=None,
        codigo_exists=None,
        category_exists=None,
        brand_exists=None,
    ) -> Product:
        nombre = str(nombre or "").strip()
        descripcion = str(descripcion or "").strip()
        codigo_producto = str(codigo_producto or "").strip()

        if not nombre:
            raise ValueError("El nombre es obligatorio.")

        precio_val = _normalize_amount(_parse_amount(precio))
        if precio_val <= 0:
            raise ValueError("El precio en HNL debe ser mayor que 0.")

        try:
            stock_val = int(stock)
        except (TypeError, ValueError) as exc:
            raise ValueError("El stock debe ser un numero entero valido.") from exc
        if stock_val < 0:
            raise ValueError("El stock no puede ser negativo.")

        try:
            prov_id_val = int(proveedor_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Debe seleccionar un proveedor valido.") from exc
        if prov_id_val <= 0:
            raise ValueError("Debe seleccionar un proveedor valido.")

        if supplier_exists and not supplier_exists(prov_id_val):
            raise ValueError("El proveedor seleccionado no existe.")

        if codigo_producto:
            if not codigo_producto.isdigit():
                raise ValueError("El codigo de producto solo puede contener numeros.")
            if len(codigo_producto) > 13:
                raise ValueError("El codigo de producto no puede exceder 13 digitos.")
            if codigo_exists and codigo_exists(codigo_producto, exclude_product_id=current_product_id):
                raise ValueError("El codigo de producto ya existe.")
        else:
            codigo_producto = None

        categoria_id_val = _parse_optional_id(
            categoria_id,
            label="categoria",
            exists=category_exists,
        )
        marca_id_val = _parse_optional_id(
            marca_id,
            label="marca",
            exists=brand_exists,
        )

        return Product(
            id=int(current_product_id) if current_product_id not in (None, "") else None,
            nombre=nombre,
            descripcion=descripcion,
            precio=precio_val,
            stock=stock_val,
            proveedor_id=prov_id_val,
            categoria_id=categoria_id_val,
            marca_id=marca_id_val,
            codigo_producto=codigo_producto,
        )
