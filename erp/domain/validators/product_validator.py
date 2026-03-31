from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    message: str = ""


def validate_product_payload(nombre: str, precio: str, stock: str, proveedor_id: str) -> ValidationResult:
    if not nombre or not nombre.strip():
        return ValidationResult(False, "El nombre es obligatorio.")

    try:
        price_value = float(precio)
    except (TypeError, ValueError):
        return ValidationResult(False, "El precio debe ser numérico.")
    if price_value <= 0:
        return ValidationResult(False, "El precio debe ser mayor que 0.")

    try:
        stock_value = int(stock)
    except (TypeError, ValueError):
        return ValidationResult(False, "El stock debe ser un número entero.")
    if stock_value < 0:
        return ValidationResult(False, "El stock no puede ser negativo.")

    try:
        provider_value = int(proveedor_id)
    except (TypeError, ValueError):
        return ValidationResult(False, "El proveedor debe ser un número entero.")
    if provider_value <= 0:
        return ValidationResult(False, "El proveedor debe ser mayor que 0.")

    return ValidationResult(True)

