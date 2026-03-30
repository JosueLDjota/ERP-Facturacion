from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Client:
    id: Optional[int]
    nombre: str
    apellido: str
    dni: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    direccion: Optional[str]
    activo: bool = True
    mayorista: bool = False
