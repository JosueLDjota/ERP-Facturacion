from __future__ import annotations

# Contexto del archivo:
# Repositorio de catalogos auxiliares de productos. Encapsula el acceso a
# categorias y marcas para que la UI y los casos de uso reutilicen la misma
# logica de busqueda parcial y validacion de existencia.

from dataclasses import dataclass

from database import DBManager


@dataclass(slots=True)
class ProductTaxonomyRepository:
    db: DBManager

    def _list_choices(self, table_name: str) -> list[dict]:
        rows = self.db.fetch(f"SELECT id, nombre FROM {table_name} ORDER BY nombre")
        return [{"id": int(row[0]), "nombre": str(row[1] or "")} for row in rows]

    def _search_by_name(self, table_name: str, term: str = "", *, limit: int = 8) -> list[dict]:
        token = str(term or "").strip().lower()
        query = f"SELECT id, nombre FROM {table_name}"
        params = []
        if token:
            query += " WHERE LOWER(nombre) LIKE ?"
            params.append(f"%{token}%")
        query += " ORDER BY nombre LIMIT ?"
        params.append(int(limit))
        rows = self.db.fetch(query, tuple(params))
        return [{"id": int(row[0]), "nombre": str(row[1] or "")} for row in rows]

    def _exists(self, table_name: str, item_id: int) -> bool:
        rows = self.db.fetch(f"SELECT 1 FROM {table_name} WHERE id = ? LIMIT 1", (int(item_id),))
        return bool(rows)

    def list_category_choices(self) -> list[dict]:
        return self._list_choices("Categorias")

    def search_categories_by_name(self, term: str = "", *, limit: int = 8) -> list[dict]:
        return self._search_by_name("Categorias", term, limit=limit)

    def category_exists(self, category_id: int) -> bool:
        return self._exists("Categorias", category_id)

    def list_brand_choices(self) -> list[dict]:
        return self._list_choices("Marcas")

    def search_brands_by_name(self, term: str = "", *, limit: int = 8) -> list[dict]:
        return self._search_by_name("Marcas", term, limit=limit)

    def brand_exists(self, brand_id: int) -> bool:
        return self._exists("Marcas", brand_id)
