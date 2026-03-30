from __future__ import annotations

import re
from dataclasses import dataclass


EMAIL_PATTERN = re.compile(r"^[^@]+@[^@]+\.[^@]+$")
DNI_PATTERN = re.compile(r"^[0-9]{13}$")


@dataclass(slots=True)
class ValidationResult:
    valid: bool
    message: str = ""


def validate_client_payload(nombre: str, apellido: str, dni: str, email: str) -> ValidationResult:
    if not nombre or not nombre.strip():
        return ValidationResult(False, "El nombre es obligatorio.")

    if not apellido or not apellido.strip():
        return ValidationResult(False, "El apellido es obligatorio.")

    dni_clean = (dni or "").strip()
    if dni_clean and not DNI_PATTERN.match(dni_clean):
        return ValidationResult(False, "El DNI debe tener 13 dígitos.")

    email_clean = (email or "").strip()
    if email_clean and not EMAIL_PATTERN.match(email_clean):
        return ValidationResult(False, "Formato de email inválido.")

    return ValidationResult(True)

