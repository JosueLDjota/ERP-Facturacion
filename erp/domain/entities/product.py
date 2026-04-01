from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Product:
    id: Optional[int]
    nombre: str
    descripcion: str
    precio: float
    stock: int
    proveedor_id: int
    categoria_id: Optional[int] = None
    marca_id: Optional[int] = None
    codigo_producto: Optional[str] = None
