"""
Control de acceso basico por rol para los modulos visibles del ERP.
"""

CONFIG_SECTION = "Configuración"
INVENTORY_SECTIONS = {"Productos", "Proveedores"}
BASE_SECTIONS = {
    "Dashboard",
    "Ventas (POS)",
    "Registro de Ventas",
    "Clientes",
    "Notificaciones",
}
ADMIN_SECTIONS = {CONFIG_SECTION, *INVENTORY_SECTIONS}


def _normalize_role(role):
    return str(role or "").strip().lower()


def has_admin_access(role):
    """Determina si el rol puede acceder a configuracion y operaciones sensibles."""
    normalized = _normalize_role(role)
    return any(
        token in normalized
        for token in ("admin", "administrador", "gerente", "owner", "dueno", "supervisor")
    )


def has_inventory_access(role):
    """Determina si el rol puede administrar inventario y proveedores."""
    normalized = _normalize_role(role)
    if has_admin_access(normalized):
        return True
    return any(
        token in normalized
        for token in ("inventario", "bodega", "almacen", "compras", "abastecimiento")
    )


def allowed_sections_for_role(role):
    """Calcula que secciones del menu lateral deben quedar visibles."""
    allowed = set(BASE_SECTIONS)
    if has_inventory_access(role):
        allowed.update(INVENTORY_SECTIONS)
    if has_admin_access(role):
        allowed.add(CONFIG_SECTION)
    return allowed


def can_access_section(role, section):
    """Valida acceso directo a una seccion aunque no este visible en la barra."""
    return section in allowed_sections_for_role(role)


def can_manage_legacy_registry(role):
    """Solo administracion puede depurar tablas legacy."""
    return has_admin_access(role)
