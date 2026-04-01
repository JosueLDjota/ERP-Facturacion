"""
database.py - Gestor de Base de Datos SQLite
Maneja todas las operaciones CRUD y estructura de la base de datos
"""

from contextlib import contextmanager
from datetime import datetime
import hashlib
import hmac
import os
from pathlib import Path
import random
import re
import sqlite3
import unicodedata


class DBManager:
    """Maneja la conexión a SQLite y operaciones CRUD/Setup."""
    METODOS_PAGO_VALIDOS = (
        "EFECTIVO",
        "TARJETA",
        "TRANSFERENCIA",
        "QR",
        "CREDITO",
        "NO_DEFINIDO",
    )

    PASSWORD_SCHEME = "pbkdf2_sha256"
    PASSWORD_ITERATIONS = 390000
    BOOTSTRAP_COMPLETED_KEY = "security_bootstrap_completed"
    PRODUCT_CODE_INDEX = "idx_productos_codigo_producto_unique"
    PRODUCT_CATEGORY_INDEX = "idx_productos_categoria_id"
    PRODUCT_BRAND_INDEX = "idx_productos_marca_id"

    DEFAULT_CATEGORIES = (
        ("Laptops", "Equipos portatiles y notebooks para uso corporativo o personal."),
        ("Monitores", "Pantallas y monitores de escritorio."),
        ("Teclados", "Teclados alfanumericos, mecanicos o inalambricos."),
        ("Mouse", "Mouse y dispositivos apuntadores."),
        ("Impresoras", "Impresoras laser, tinta y multifuncionales."),
        ("Routers", "Equipos de enrutamiento de red."),
        ("Switches", "Switches de red administrables o no administrables."),
        ("Access Points", "Puntos de acceso inalambricos empresariales o domesticos."),
        ("UPS", "Sistemas de respaldo electrico y proteccion de energia."),
        ("Camaras IP", "Camaras de vigilancia IP y CCTV."),
        ("SSD", "Unidades de estado solido."),
        ("Memorias RAM", "Modulos de memoria RAM y componentes afines."),
        ("Licencias", "Licencias de software, antivirus y suites de oficina."),
        ("Tablets", "Tablets y dispositivos tactiles."),
        ("Docking Stations", "Docks, hubs y estaciones de acoplamiento."),
        ("Auriculares", "Headsets, audifonos y auriculares."),
        ("Webcams", "Camaras web para videollamadas o streaming."),
        ("Mochilas", "Mochilas, maletines y bolsos para equipos."),
        ("Cargadores", "Cargadores, adaptadores de corriente y fuentes."),
        ("Accesorios", "Accesorios generales de tecnologia."),
        ("Consumibles", "Toner, tinta, papel y otros consumibles."),
        ("Almacenamiento", "Discos HDD, USB, memorias externas y almacenamiento general."),
        ("Wearables", "Relojes inteligentes y accesorios vestibles."),
        ("Redes", "Tarjetas de red y otros componentes de conectividad general."),
        ("Componentes", "Tarjetas madre y componentes internos no clasificados en otra categoria."),
        ("Otros", "Productos que no se pudieron clasificar con reglas seguras."),
    )

    DEFAULT_BRANDS = (
        ("Acer", "Fabricante de equipos de computo y accesorios."),
        ("Asus", "Fabricante de computadoras, componentes y perifericos."),
        ("Dell", "Fabricante de equipos empresariales y de consumo."),
        ("HP", "Hewlett-Packard y sus lineas de tecnologia."),
        ("Lenovo", "Fabricante de laptops, desktops y perifericos."),
        ("Logitech", "Marca de perifericos y accesorios."),
        ("TP-Link", "Marca de conectividad y redes."),
        ("Ubiquiti", "Marca de infraestructura de red y conectividad."),
        ("Hikvision", "Marca de videovigilancia y seguridad."),
        ("Kingston", "Marca de memoria y almacenamiento."),
        ("Crucial", "Marca de memoria y almacenamiento."),
        ("Samsung", "Marca de electronica y almacenamiento."),
        ("Epson", "Marca de impresion y perifericos."),
        ("Canon", "Marca de impresion y fotografia."),
        ("Brother", "Marca de impresion y etiquetado."),
        ("Cisco", "Marca de redes empresariales."),
        ("Intel", "Fabricante de procesadores y componentes."),
        ("AMD", "Fabricante de procesadores y graficos."),
        ("Microsoft", "Marca de software, licencias y hardware."),
        ("MSI", "Marca de hardware, gaming y perifericos."),
        ("Corsair", "Marca de componentes y accesorios."),
        ("Generica", "Marca por defecto cuando no se puede inferir una marca confiable."),
    )

    BRAND_INFERENCE_RULES = (
        ("TP-Link", (r"\btp[\s-]?link\b",)),
        ("Ubiquiti", (r"\bubiquiti\b", r"\bunifi\b")),
        ("Hikvision", (r"\bhikvision\b",)),
        ("Kingston", (r"\bkingston\b",)),
        ("Crucial", (r"\bcrucial\b",)),
        ("Samsung", (r"\bsamsung\b",)),
        ("Logitech", (r"\blogitech\b",)),
        ("Lenovo", (r"\blenovo\b",)),
        ("Epson", (r"\bepson\b",)),
        ("Canon", (r"\bcanon\b",)),
        ("Brother", (r"\bbrother\b",)),
        ("Cisco", (r"\bcisco\b",)),
        ("Microsoft", (r"\bmicrosoft\b", r"\boffice\b", r"\bwindows\b", r"\bdefender\b")),
        ("Intel", (r"\bintel\b", r"\bcore i[3579]\b")),
        ("AMD", (r"\bamd\b", r"\bryzen\b", r"\bradeon\b")),
        ("Acer", (r"\bacer\b",)),
        ("Asus", (r"\basus\b",)),
        ("Dell", (r"\bdell\b",)),
        ("HP", (r"\bhp\b", r"\bhewlett packard\b")),
        ("MSI", (r"\bmsi\b",)),
        ("Corsair", (r"\bcorsair\b",)),
    )

    CATEGORY_INFERENCE_RULES = (
        ("Consumibles", (r"\btoner\b", r"\btinta\b", r"\bcartucho\b", r"\bpapel\b", r"\bdrum\b", r"\bribbon\b")),
        ("Webcams", (r"\bwebcam\b",)),
        ("Docking Stations", (r"\bdocking station\b", r"\bdock\b", r"\bhub\b")),
        ("Access Points", (r"\baccess point\b", r"\baccesspoint\b", r"\bap\b")),
        ("Routers", (r"\brouter\b",)),
        ("Switches", (r"\bswitch(?:es)?\b",)),
        ("UPS", (r"\bups\b", r"\bnobreak\b", r"\bno break\b")),
        ("Camaras IP", (r"\bcamara\b", r"\bcamera\b", r"\bip cam\b", r"\bcctv\b")),
        ("Laptops", (r"\blaptops?\b", r"\bnotebook\b", r"\bultrabook\b")),
        ("Monitores", (r"\bmonitor(?:es)?\b", r"\bpantalla\b", r"\bdisplay\b")),
        ("Teclados", (r"\bteclad(?:o|os)\b", r"\bkeyboard\b")),
        ("Mouse", (r"\bmouse\b", r"\braton\b")),
        ("Impresoras", (r"\bimpresora\b", r"\bprinter\b", r"\bmultifuncional\b", r"\blaserjet\b")),
        ("SSD", (r"\bssd\b", r"\bnvme\b", r"\bm 2\b", r"\bm2\b")),
        ("Memorias RAM", (r"\bram\b", r"\bmemoria\b", r"\bddr[345]\b", r"\bsodimm\b", r"\bdimm\b")),
        ("Licencias", (r"\blicencia\b", r"\boffice\b", r"\bantivirus\b", r"\bwindows\b", r"\bsoftware\b")),
        ("Tablets", (r"\btablet\b",)),
        ("Auriculares", (r"\bauricular(?:es)?\b", r"\bheadset\b", r"\baudifono(?:s)?\b", r"\bheadphone(?:s)?\b", r"\baudio\b")),
        ("Mochilas", (r"\bmochila\b", r"\bbackpack\b", r"\bmaletin\b", r"\bbolso\b")),
        ("Cargadores", (r"\bcargador(?:es)?\b", r"\bcharger\b", r"\badaptador(?:es)?\b", r"\bfuente\b")),
        ("Almacenamiento", (r"\balmacenamiento\b", r"\bhdd\b", r"\busb\b", r"\bpendrive\b", r"\bflash drive\b", r"\bdisco\b")),
        ("Wearables", (r"\breloj inteligente\b", r"\bsmartwatch\b", r"\bsmart fit\b", r"\bsmartfit\b", r"\bwearable\b")),
        ("Redes", (r"\bredes\b", r"\btarjeta de red\b", r"\bethernet\b", r"\bnic\b")),
        ("Componentes", (r"\bcomponentes\b", r"\btarjeta madre\b", r"\bmotherboard\b", r"\bmainboard\b")),
        ("Accesorios", (r"\baccesorio(?:s)?\b", r"\bbase\b", r"\bsoporte\b", r"\bstand\b", r"\bcable\b")),
    )

    def __init__(self, db_name="erp_profesional.db"):
        self.db_path = Path(db_name).resolve()
        self.is_new_database = not self.db_path.exists()
        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()
        self.last_error = None
        self._explicit_transaction_depth = 0
        self.last_product_taxonomy_report = None
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        """Crea todas las tablas necesarias del sistema."""

        # Tabla de Clientes
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                dni TEXT UNIQUE,
                telefono TEXT,
                email TEXT,
                direccion TEXT,
                fecha_registro TEXT NOT NULL,
                activo INTEGER DEFAULT 1,
                mayorista INTEGER DEFAULT 0
            )
        """
        )
        self._ensure_column(
            "Clientes",
            "mayorista",
            "INTEGER DEFAULT 0",
        )

        # Tabla de Proveedores
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Proveedores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                contacto TEXT,
                telefono TEXT
            )
        """
        )

        # Tabla de Productos
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL CHECK (stock >= 0),
                proveedor_id INTEGER,
                FOREIGN KEY (proveedor_id) REFERENCES Proveedores(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            )
        """
        )

        # Tabla de Usuarios
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                contrasena TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        """
        )

        # Tabla de Descuentos
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Descuentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                tipo TEXT,
                porcentaje REAL NOT NULL
            )
        """
        )

        # Tabla de Configuración
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        """
        )

        # Tabla de Ventas
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Ventas (
                id TEXT PRIMARY KEY,
                fecha TEXT NOT NULL,
                total REAL NOT NULL CHECK (total >= 0),
                monto_pagado REAL,
                vuelto REAL,
                metodo_pago TEXT DEFAULT 'NO_DEFINIDO' CHECK (
                    metodo_pago IN (
                        'EFECTIVO',
                        'TARJETA',
                        'TRANSFERENCIA',
                        'QR',
                        'CREDITO',
                        'NO_DEFINIDO'
                    )
                ),
                usuario_id INTEGER,
                id_cliente INTEGER,
                tipo_recibo TEXT,
                FOREIGN KEY (usuario_id) REFERENCES Usuarios(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL,
                FOREIGN KEY (id_cliente) REFERENCES Clientes(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            )
        """
        )
        self._ensure_column(
            "Ventas",
            "metodo_pago",
            "TEXT DEFAULT 'NO_DEFINIDO'",
        )

        # Tabla de Detalle de Venta
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS DetalleVenta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id TEXT NOT NULL,
                producto_id INTEGER,
                nombre_producto TEXT,
                cantidad INTEGER NOT NULL CHECK (cantidad > 0),
                precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
                descuento REAL DEFAULT 0 CHECK (descuento >= 0),
                subtotal REAL NOT NULL CHECK (subtotal >= 0),
                FOREIGN KEY (venta_id) REFERENCES Ventas(id)
                    ON UPDATE CASCADE
                    ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES Productos(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            )
        """
        )

        self.create_ventas_diarias_table()
        self._ensure_sales_indexes()
        self._ensure_stock_guards()
        self._ensure_bootstrap_state()
        self._ensure_sales_schema_integrity()
        self._migrate_password_storage()
        self.conn.commit()
        self.insert_initial_data()
        self._ensure_product_codes()
        self.last_product_taxonomy_report = self._ensure_product_taxonomy()

    def _ensure_column(self, table_name, column_name, column_definition):
        """Agrega una columna solo si todavía no existe."""
        existing_columns = {
            row[1]
            for row in self.fetch(f"PRAGMA table_info({table_name})")
        }
        if column_name not in existing_columns:
            self.cursor.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            )
            return True
        return False

    def _table_exists(self, table_name):
        """Indica si una tabla ya existe en la base."""
        rows = self.fetch(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = ?
            """,
            (table_name,),
        )
        return bool(rows)

    def _get_table_columns(self, table_name):
        """Devuelve el conjunto de columnas declaradas en una tabla."""
        return {
            row[1]
            for row in self.fetch(f"PRAGMA table_info({table_name})")
        }

    @staticmethod
    def _normalize_inference_text(value):
        """Normaliza texto para reglas de inferencia robustas y sin acentos."""
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = normalized.lower()
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return f" {normalized} " if normalized else " "

    @classmethod
    def _infer_from_rules(cls, raw_text, rules, default_name):
        """Aplica reglas ordenadas para inferir una marca o categoría."""
        haystack = cls._normalize_inference_text(raw_text)
        for resolved_name, patterns in rules:
            for pattern in patterns:
                if re.search(pattern, haystack):
                    return resolved_name
        return default_name

    @classmethod
    def infer_brand_name(cls, product_name, description=""):
        """Infiere la marca más probable para un producto existente."""
        return cls._infer_from_rules(
            f"{product_name or ''} {description or ''}",
            cls.BRAND_INFERENCE_RULES,
            "Generica",
        )

    @classmethod
    def infer_category_name(cls, product_name, description=""):
        """Infiere la categoría más probable para un producto existente."""
        return cls._infer_from_rules(
            f"{product_name or ''} {description or ''}",
            cls.CATEGORY_INFERENCE_RULES,
            "Otros",
        )

    @staticmethod
    def _calculate_ean13_check_digit(base_digits):
        """Calcula el digito verificador EAN-13 a partir de 12 digitos."""
        digits = [int(char) for char in str(base_digits)]
        if len(digits) != 12:
            raise ValueError("EAN-13 requiere exactamente 12 digitos base.")

        weighted_sum = 0
        for index, digit in enumerate(digits):
            weighted_sum += digit if index % 2 == 0 else digit * 3
        return str((10 - (weighted_sum % 10)) % 10)

    @classmethod
    def generate_ean13_code(cls, seed_value):
        """Genera un codigo EAN-13 numerico y deterministico a partir de una semilla."""
        seed_token = str(seed_value or "")
        numeric_seed = "".join(char for char in seed_token if char.isdigit())
        if not numeric_seed:
            numeric_seed = str(abs(hash(seed_token)))
        base_digits = numeric_seed[-12:].zfill(12)
        return f"{base_digits}{cls._calculate_ean13_check_digit(base_digits)}"

    def _generate_unique_product_code(self, product_id, used_codes):
        """Genera un EAN-13 unico para un producto sin sobrescribir codigos existentes."""
        candidate = self.generate_ean13_code(f"20{int(product_id):010d}")
        if candidate not in used_codes:
            return candidate

        rng = random.Random(int(product_id))
        for _attempt in range(10000):
            prefix = rng.randint(200, 999)
            body = rng.randint(0, 999999999)
            base_digits = f"{prefix:03d}{body:09d}"
            candidate = f"{base_digits}{self._calculate_ean13_check_digit(base_digits)}"
            if candidate not in used_codes:
                return candidate

        raise sqlite3.IntegrityError(
            f"No se pudo generar un codigo_producto unico para el producto {product_id}."
        )

    def _ensure_product_codes(self):
        """Agrega y puebla codigo_producto de forma segura sin perder datos existentes."""
        self._ensure_column("Productos", "codigo_producto", "TEXT")

        with self.transaction() as cursor:
            duplicates = cursor.execute(
                """
                SELECT codigo_producto, COUNT(*)
                FROM Productos
                WHERE codigo_producto IS NOT NULL
                  AND TRIM(codigo_producto) <> ''
                GROUP BY codigo_producto
                HAVING COUNT(*) > 1
                """
            ).fetchall()
            if duplicates:
                duplicate_codes = ", ".join(row[0] for row in duplicates[:5])
                raise sqlite3.IntegrityError(
                    f"Existen codigos de producto duplicados antes de crear el indice unico: {duplicate_codes}"
                )

            invalid_codes = cursor.execute(
                """
                SELECT id, codigo_producto
                FROM Productos
                WHERE codigo_producto IS NOT NULL
                  AND TRIM(codigo_producto) <> ''
                  AND (
                      LENGTH(TRIM(codigo_producto)) > 13
                      OR TRIM(codigo_producto) GLOB '*[^0-9]*'
                  )
                """
            ).fetchall()
            if invalid_codes:
                product_ids = ", ".join(str(row[0]) for row in invalid_codes[:5])
                raise sqlite3.IntegrityError(
                    f"Existen codigo_producto invalidos en Productos: {product_ids}"
                )

            existing_codes = {
                str(row[0]).strip()
                for row in cursor.execute(
                    """
                    SELECT codigo_producto
                    FROM Productos
                    WHERE codigo_producto IS NOT NULL
                      AND TRIM(codigo_producto) <> ''
                    """
                ).fetchall()
            }

            products_without_code = cursor.execute(
                """
                SELECT id
                FROM Productos
                WHERE codigo_producto IS NULL
                   OR TRIM(codigo_producto) = ''
                ORDER BY id
                """
            ).fetchall()

            for (product_id,) in products_without_code:
                new_code = self._generate_unique_product_code(product_id, existing_codes)
                cursor.execute(
                    "UPDATE Productos SET codigo_producto = ? WHERE id = ?",
                    (new_code, product_id),
                )
                existing_codes.add(new_code)

            cursor.execute(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS {self.PRODUCT_CODE_INDEX}
                ON Productos(codigo_producto)
                WHERE codigo_producto IS NOT NULL
                  AND TRIM(codigo_producto) <> ''
                """
            )

    def _ensure_product_taxonomy(self, assign_only_missing=True):
        """Crea y puebla Marcas/Categorias y clasifica productos existentes sin sobrescribir datos válidos."""
        report = {
            "tables_created": [],
            "columns_added": [],
            "brands_inserted": [],
            "categories_inserted": [],
            "products_updated_brand": 0,
            "products_updated_category": 0,
            "generic_products": [],
            "other_products": [],
            "assign_only_missing": bool(assign_only_missing),
        }

        categories_previously_exists = self._table_exists("Categorias")
        brands_previously_exists = self._table_exists("Marcas")
        product_columns = self._get_table_columns("Productos")

        with self.transaction() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Categorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    descripcion TEXT
                )
                """
            )
            if not categories_previously_exists:
                report["tables_created"].append("Categorias")

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS Marcas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL UNIQUE,
                    descripcion TEXT
                )
                """
            )
            if not brands_previously_exists:
                report["tables_created"].append("Marcas")

            if "categoria_id" not in product_columns:
                cursor.execute("ALTER TABLE Productos ADD COLUMN categoria_id INTEGER")
                report["columns_added"].append("Productos.categoria_id")

            if "marca_id" not in product_columns:
                cursor.execute("ALTER TABLE Productos ADD COLUMN marca_id INTEGER")
                report["columns_added"].append("Productos.marca_id")

            for category_name, category_description in self.DEFAULT_CATEGORIES:
                cursor.execute(
                    "INSERT OR IGNORE INTO Categorias (nombre, descripcion) VALUES (?, ?)",
                    (category_name, category_description),
                )
                if cursor.rowcount == 1:
                    report["categories_inserted"].append(category_name)

            for brand_name, brand_description in self.DEFAULT_BRANDS:
                cursor.execute(
                    "INSERT OR IGNORE INTO Marcas (nombre, descripcion) VALUES (?, ?)",
                    (brand_name, brand_description),
                )
                if cursor.rowcount == 1:
                    report["brands_inserted"].append(brand_name)

            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {self.PRODUCT_CATEGORY_INDEX} ON Productos(categoria_id)"
            )
            cursor.execute(
                f"CREATE INDEX IF NOT EXISTS {self.PRODUCT_BRAND_INDEX} ON Productos(marca_id)"
            )

            cursor.executescript(
                """
                CREATE TRIGGER IF NOT EXISTS trg_productos_categoria_ref_insert
                BEFORE INSERT ON Productos
                FOR EACH ROW
                WHEN NEW.categoria_id IS NOT NULL
                     AND NOT EXISTS (SELECT 1 FROM Categorias WHERE id = NEW.categoria_id)
                BEGIN
                    SELECT RAISE(ABORT, 'La categoria asignada no existe.');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_productos_categoria_ref_update
                BEFORE UPDATE OF categoria_id ON Productos
                FOR EACH ROW
                WHEN NEW.categoria_id IS NOT NULL
                     AND NOT EXISTS (SELECT 1 FROM Categorias WHERE id = NEW.categoria_id)
                BEGIN
                    SELECT RAISE(ABORT, 'La categoria asignada no existe.');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_productos_marca_ref_insert
                BEFORE INSERT ON Productos
                FOR EACH ROW
                WHEN NEW.marca_id IS NOT NULL
                     AND NOT EXISTS (SELECT 1 FROM Marcas WHERE id = NEW.marca_id)
                BEGIN
                    SELECT RAISE(ABORT, 'La marca asignada no existe.');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_productos_marca_ref_update
                BEFORE UPDATE OF marca_id ON Productos
                FOR EACH ROW
                WHEN NEW.marca_id IS NOT NULL
                     AND NOT EXISTS (SELECT 1 FROM Marcas WHERE id = NEW.marca_id)
                BEGIN
                    SELECT RAISE(ABORT, 'La marca asignada no existe.');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_categorias_delete_restrict
                BEFORE DELETE ON Categorias
                FOR EACH ROW
                WHEN EXISTS (SELECT 1 FROM Productos WHERE categoria_id = OLD.id)
                BEGIN
                    SELECT RAISE(ABORT, 'No se puede eliminar una categoria en uso por Productos.');
                END;

                CREATE TRIGGER IF NOT EXISTS trg_marcas_delete_restrict
                BEFORE DELETE ON Marcas
                FOR EACH ROW
                WHEN EXISTS (SELECT 1 FROM Productos WHERE marca_id = OLD.id)
                BEGIN
                    SELECT RAISE(ABORT, 'No se puede eliminar una marca en uso por Productos.');
                END;
                """
            )

            brand_map = {
                row[1]: row[0]
                for row in cursor.execute(
                    "SELECT id, nombre FROM Marcas ORDER BY nombre"
                ).fetchall()
            }
            category_map = {
                row[1]: row[0]
                for row in cursor.execute(
                    "SELECT id, nombre FROM Categorias ORDER BY nombre"
                ).fetchall()
            }

            missing_brand_rows = cursor.execute(
                """
                SELECT p.id
                FROM Productos p
                LEFT JOIN Marcas m
                    ON m.id = p.marca_id
                WHERE p.marca_id IS NOT NULL
                  AND m.id IS NULL
                """
            ).fetchall()
            if missing_brand_rows:
                broken_ids = ", ".join(str(row[0]) for row in missing_brand_rows[:10])
                raise sqlite3.IntegrityError(
                    f"Existen productos con marca_id invalido antes de migrar: {broken_ids}"
                )

            missing_category_rows = cursor.execute(
                """
                SELECT p.id
                FROM Productos p
                LEFT JOIN Categorias c
                    ON c.id = p.categoria_id
                WHERE p.categoria_id IS NOT NULL
                  AND c.id IS NULL
                """
            ).fetchall()
            if missing_category_rows:
                broken_ids = ", ".join(str(row[0]) for row in missing_category_rows[:10])
                raise sqlite3.IntegrityError(
                    f"Existen productos con categoria_id invalido antes de migrar: {broken_ids}"
                )

            generic_brand_id = brand_map["Generica"]
            other_category_id = category_map["Otros"]

            rows = cursor.execute(
                """
                SELECT id, nombre, COALESCE(descripcion, ''), marca_id, categoria_id
                FROM Productos
                ORDER BY id
                """
            ).fetchall()

            for product_id, product_name, description, current_brand_id, current_category_id in rows:
                updates = []
                params = []

                should_set_brand = (
                    current_brand_id is None
                    or current_brand_id == generic_brand_id
                    or not assign_only_missing
                )
                if should_set_brand:
                    inferred_brand_name = self.infer_brand_name(product_name, description)
                    next_brand_id = brand_map.get(inferred_brand_name, generic_brand_id)
                    if next_brand_id != current_brand_id:
                        updates.append("marca_id = ?")
                        params.append(next_brand_id)
                        report["products_updated_brand"] += 1

                should_set_category = (
                    current_category_id is None
                    or current_category_id == other_category_id
                    or not assign_only_missing
                )
                if should_set_category:
                    inferred_category_name = self.infer_category_name(product_name, description)
                    next_category_id = category_map.get(inferred_category_name, other_category_id)
                    if next_category_id != current_category_id:
                        updates.append("categoria_id = ?")
                        params.append(next_category_id)
                        report["products_updated_category"] += 1

                if updates:
                    params.append(product_id)
                    cursor.execute(
                        f"UPDATE Productos SET {', '.join(updates)} WHERE id = ?",
                        tuple(params),
                    )

            report["generic_products"] = cursor.execute(
                """
                SELECT p.id, p.nombre
                FROM Productos p
                INNER JOIN Marcas m
                    ON m.id = p.marca_id
                WHERE m.nombre = 'Generica'
                ORDER BY p.id
                """
            ).fetchall()

            report["other_products"] = cursor.execute(
                """
                SELECT p.id, p.nombre
                FROM Productos p
                INNER JOIN Categorias c
                    ON c.id = p.categoria_id
                WHERE c.nombre = 'Otros'
                ORDER BY p.id
                """
            ).fetchall()

        return report

    def write_product_taxonomy_summary(self, report, output_path=None):
        """Genera un resumen legible de la migración de Marcas/Categorias en archivo .mb."""
        output_file = Path(output_path or self.db_path.with_name("resumen_categorias_marcas.mb"))
        lines = [
            "# Resumen de migracion de catalogo",
            "",
            f"Base de datos: {self.db_path}",
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Modo seguro (solo NULL): {'Si' if report.get('assign_only_missing', True) else 'No'}",
            "",
            "## Tablas creadas",
        ]

        tables_created = report.get("tables_created", [])
        if tables_created:
            lines.extend(f"- {table_name}" for table_name in tables_created)
        else:
            lines.append("- Ninguna")

        lines.extend(["", "## Columnas agregadas"])
        columns_added = report.get("columns_added", [])
        if columns_added:
            lines.extend(f"- {column_name}" for column_name in columns_added)
        else:
            lines.append("- Ninguna")

        lines.extend(
            [
                "",
                "## Marcas insertadas",
                f"- Total: {len(report.get('brands_inserted', []))}",
            ]
        )
        if report.get("brands_inserted"):
            lines.extend(f"- {brand_name}" for brand_name in report["brands_inserted"])

        lines.extend(
            [
                "",
                "## Categorias insertadas",
                f"- Total: {len(report.get('categories_inserted', []))}",
            ]
        )
        if report.get("categories_inserted"):
            lines.extend(f"- {category_name}" for category_name in report["categories_inserted"])

        lines.extend(
            [
                "",
                "## Productos actualizados",
                f"- Con marca asignada/actualizada: {int(report.get('products_updated_brand', 0))}",
                f"- Con categoria asignada/actualizada: {int(report.get('products_updated_category', 0))}",
                "",
                "## Productos clasificados como Generica",
                f"- Total: {len(report.get('generic_products', []))}",
            ]
        )
        if report.get("generic_products"):
            lines.extend(
                f"- [{product_id}] {product_name}"
                for product_id, product_name in report["generic_products"]
            )

        lines.extend(
            [
                "",
                "## Productos clasificados como Otros",
                f"- Total: {len(report.get('other_products', []))}",
            ]
        )
        if report.get("other_products"):
            lines.extend(
                f"- [{product_id}] {product_name}"
                for product_id, product_name in report["other_products"]
            )

        output_file.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return output_file

    def ensure_product_taxonomy(self, assign_only_missing=True, summary_path=None):
        """Ejecuta la migración de taxonomía y opcionalmente escribe un resumen en .mb."""
        report = self._ensure_product_taxonomy(assign_only_missing=assign_only_missing)
        self.last_product_taxonomy_report = report
        if summary_path:
            self.write_product_taxonomy_summary(report, summary_path)
        return report

    def _ensure_sales_indexes(self):
        """Asegura indices utiles para ventas y registro."""
        self.cursor.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_ventas_fecha
                ON Ventas(fecha);

            CREATE INDEX IF NOT EXISTS idx_ventas_cliente
                ON Ventas(id_cliente);

            CREATE INDEX IF NOT EXISTS idx_detalle_venta_id
                ON DetalleVenta(venta_id);

            CREATE INDEX IF NOT EXISTS idx_detalle_producto_id
                ON DetalleVenta(producto_id);
            """
        )

    def _ensure_bootstrap_state(self):
        """Evita recrear el admin por defecto en bases ya existentes."""
        current_value = self.get_config(self.BOOTSTRAP_COMPLETED_KEY, None)
        if current_value is not None:
            return

        bootstrap_completed = "0" if self.is_new_database else "1"
        self.cursor.execute(
            "INSERT INTO Configuracion (clave, valor) VALUES (?, ?)",
            (self.BOOTSTRAP_COMPLETED_KEY, bootstrap_completed),
        )

    def _ensure_stock_guards(self):
        """Refuerza stock y detalle de venta desde la base de datos."""
        self.cursor.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS trg_productos_stock_insert
            BEFORE INSERT ON Productos
            FOR EACH ROW
            WHEN NEW.stock < 0
            BEGIN
                SELECT RAISE(ABORT, 'El stock no puede ser negativo.');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_productos_stock_update
            BEFORE UPDATE OF stock ON Productos
            FOR EACH ROW
            WHEN NEW.stock < 0
            BEGIN
                SELECT RAISE(ABORT, 'El stock no puede ser negativo.');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_detalle_venta_insert
            BEFORE INSERT ON DetalleVenta
            FOR EACH ROW
            WHEN NEW.cantidad <= 0
                 OR NEW.precio_unitario < 0
                 OR COALESCE(NEW.descuento, 0) < 0
                 OR COALESCE(NEW.subtotal, 0) < 0
            BEGIN
                SELECT RAISE(ABORT, 'El detalle de venta contiene valores invalidos.');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_detalle_venta_update
            BEFORE UPDATE ON DetalleVenta
            FOR EACH ROW
            WHEN NEW.cantidad <= 0
                 OR NEW.precio_unitario < 0
                 OR COALESCE(NEW.descuento, 0) < 0
                 OR COALESCE(NEW.subtotal, 0) < 0
            BEGIN
                SELECT RAISE(ABORT, 'El detalle de venta contiene valores invalidos.');
            END;
            """
        )

    def _ensure_sales_schema_integrity(self):
        """Migra tablas legacy para agregar claves foraneas faltantes."""
        ventas_fk = {
            row[3]: row[2]
            for row in self.fetch("PRAGMA foreign_key_list(Ventas)")
        }
        detalle_fk = {
            row[3]: row[2]
            for row in self.fetch("PRAGMA foreign_key_list(DetalleVenta)")
        }

        if ventas_fk.get("usuario_id") != "Usuarios" or ventas_fk.get("id_cliente") != "Clientes":
            self._rebuild_ventas_table()

        if detalle_fk.get("venta_id") != "Ventas" or detalle_fk.get("producto_id") != "Productos":
            self._rebuild_detalle_venta_table()

        self._ensure_sales_indexes()

    @contextmanager
    def _schema_migration(self):
        """Ejecuta una migracion estructural con foreign keys desactivadas temporalmente."""
        fk_enabled = self.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        try:
            self.conn.commit()
            self.conn.execute("PRAGMA foreign_keys = OFF")
            self.cursor.execute("BEGIN")
            yield
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            self.conn.execute(f"PRAGMA foreign_keys = {'ON' if fk_enabled else 'OFF'}")

    def _rebuild_ventas_table(self):
        """Reconstruye Ventas para agregar FKs reales y sanear referencias huerfanas."""
        with self._schema_migration():
            self.cursor.execute("ALTER TABLE Ventas RENAME TO Ventas_legacy_migration")
            self.cursor.execute(
                """
                CREATE TABLE Ventas (
                    id TEXT PRIMARY KEY,
                    fecha TEXT NOT NULL,
                    total REAL NOT NULL CHECK (total >= 0),
                    monto_pagado REAL,
                    vuelto REAL,
                    metodo_pago TEXT DEFAULT 'NO_DEFINIDO' CHECK (
                        metodo_pago IN (
                            'EFECTIVO',
                            'TARJETA',
                            'TRANSFERENCIA',
                            'QR',
                            'CREDITO',
                            'NO_DEFINIDO'
                        )
                    ),
                    usuario_id INTEGER,
                    id_cliente INTEGER,
                    tipo_recibo TEXT,
                    FOREIGN KEY (usuario_id) REFERENCES Usuarios(id)
                        ON UPDATE CASCADE
                        ON DELETE SET NULL,
                    FOREIGN KEY (id_cliente) REFERENCES Clientes(id)
                        ON UPDATE CASCADE
                        ON DELETE SET NULL
                )
                """
            )
            self.cursor.execute(
                """
                INSERT INTO Ventas (
                    id,
                    fecha,
                    total,
                    monto_pagado,
                    vuelto,
                    metodo_pago,
                    usuario_id,
                    id_cliente,
                    tipo_recibo
                )
                SELECT
                    v.id,
                    COALESCE(v.fecha, CURRENT_TIMESTAMP),
                    COALESCE(v.total, 0),
                    COALESCE(v.monto_pagado, 0),
                    COALESCE(v.vuelto, 0),
                    CASE
                        WHEN UPPER(COALESCE(v.metodo_pago, 'NO_DEFINIDO')) IN (
                            'EFECTIVO',
                            'TARJETA',
                            'TRANSFERENCIA',
                            'QR',
                            'CREDITO',
                            'NO_DEFINIDO'
                        ) THEN UPPER(COALESCE(v.metodo_pago, 'NO_DEFINIDO'))
                        ELSE 'NO_DEFINIDO'
                    END,
                    CASE WHEN u.id IS NULL THEN NULL ELSE v.usuario_id END,
                    CASE WHEN c.id IS NULL THEN NULL ELSE v.id_cliente END,
                    v.tipo_recibo
                FROM Ventas_legacy_migration v
                LEFT JOIN Usuarios u
                    ON u.id = v.usuario_id
                LEFT JOIN Clientes c
                    ON c.id = v.id_cliente
                """
            )
            self.cursor.execute("DROP TABLE Ventas_legacy_migration")

    def _rebuild_detalle_venta_table(self):
        """Reconstruye DetalleVenta para agregar FK real a Productos y checks basicos."""
        with self._schema_migration():
            self.cursor.execute("ALTER TABLE DetalleVenta RENAME TO DetalleVenta_legacy_migration")
            self.cursor.execute(
                """
                CREATE TABLE DetalleVenta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venta_id TEXT NOT NULL,
                    producto_id INTEGER,
                    nombre_producto TEXT,
                    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
                    precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
                    descuento REAL DEFAULT 0 CHECK (descuento >= 0),
                    subtotal REAL NOT NULL CHECK (subtotal >= 0),
                    FOREIGN KEY (venta_id) REFERENCES Ventas(id)
                        ON UPDATE CASCADE
                        ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES Productos(id)
                        ON UPDATE CASCADE
                        ON DELETE SET NULL
                )
                """
            )
            self.cursor.execute(
                """
                INSERT INTO DetalleVenta (
                    id,
                    venta_id,
                    producto_id,
                    nombre_producto,
                    cantidad,
                    precio_unitario,
                    descuento,
                    subtotal
                )
                SELECT
                    dv.id,
                    dv.venta_id,
                    CASE WHEN p.id IS NULL THEN NULL ELSE dv.producto_id END,
                    COALESCE(dv.nombre_producto, p.nombre, 'Producto sin nombre'),
                    CASE
                        WHEN CAST(COALESCE(dv.cantidad, 0) AS INTEGER) <= 0 THEN 1
                        ELSE CAST(dv.cantidad AS INTEGER)
                    END,
                    COALESCE(dv.precio_unitario, 0),
                    CASE
                        WHEN COALESCE(dv.descuento, 0) < 0 THEN 0
                        ELSE COALESCE(dv.descuento, 0)
                    END,
                    CASE
                        WHEN COALESCE(dv.subtotal, 0) < 0 THEN 0
                        ELSE COALESCE(dv.subtotal, 0)
                    END
                FROM DetalleVenta_legacy_migration dv
                INNER JOIN Ventas v
                    ON v.id = dv.venta_id
                LEFT JOIN Productos p
                    ON p.id = dv.producto_id
                """
            )
            self.cursor.execute("DROP TABLE DetalleVenta_legacy_migration")

    @classmethod
    def is_password_hashed(cls, stored_password):
        """Indica si la contrasena ya fue migrada a hash PBKDF2."""
        return str(stored_password or "").startswith(f"{cls.PASSWORD_SCHEME}$")

    @classmethod
    def hash_password(cls, plain_password, salt=None):
        """Genera un hash PBKDF2 con sal aleatoria."""
        plain_password = str(plain_password or "")
        salt = salt or os.urandom(16).hex()
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            cls.PASSWORD_ITERATIONS,
        ).hex()
        return f"{cls.PASSWORD_SCHEME}${cls.PASSWORD_ITERATIONS}${salt}${digest}"

    @classmethod
    def verify_password(cls, plain_password, stored_password):
        """Verifica contrasenas hash y retrocompatibilidad con texto plano."""
        plain_password = str(plain_password or "")
        stored_password = str(stored_password or "")

        if not cls.is_password_hashed(stored_password):
            return hmac.compare_digest(stored_password, plain_password)

        try:
            scheme, iterations, salt, digest = stored_password.split("$", 3)
            if scheme != cls.PASSWORD_SCHEME:
                return False
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
        except (TypeError, ValueError):
            return False

        return hmac.compare_digest(candidate, digest)

    def _migrate_password_storage(self):
        """Migra credenciales legacy en texto plano a hash PBKDF2."""
        rows = self.fetch("SELECT id, contrasena FROM Usuarios")
        updated = False

        for user_id, stored_password in rows:
            if self.is_password_hashed(stored_password):
                continue
            self.cursor.execute(
                "UPDATE Usuarios SET contrasena = ? WHERE id = ?",
                (self.hash_password(stored_password), user_id),
            )
            updated = True

        if updated:
            self.conn.commit()

    def has_users(self):
        """Indica si existe al menos un usuario configurado."""
        return bool(self.fetch("SELECT 1 FROM Usuarios LIMIT 1"))

    def authenticate_user(self, username, password):
        """Autentica usuarios y actualiza credenciales legacy si hace falta."""
        username = str(username or "").strip()
        if not username or password in (None, ""):
            return None

        rows = self.fetch(
            "SELECT id, nombre, rol, contrasena FROM Usuarios WHERE usuario = ? LIMIT 1",
            (username,),
        )
        if not rows:
            return None

        user_id, nombre, rol, stored_password = rows[0]
        if not self.verify_password(password, stored_password):
            return None

        if not self.is_password_hashed(stored_password):
            self.cursor.execute(
                "UPDATE Usuarios SET contrasena = ? WHERE id = ?",
                (self.hash_password(password), user_id),
            )
            self.conn.commit()

        return (user_id, nombre, rol)

    @contextmanager
    def transaction(self):
        """Agrupa varias sentencias en una transaccion atomica."""
        try:
            self.last_error = None
            self._explicit_transaction_depth += 1
            self.cursor.execute("BEGIN IMMEDIATE")
            yield self.cursor
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            if isinstance(exc, sqlite3.Error):
                self.last_error = exc
            raise
        finally:
            self._explicit_transaction_depth = max(0, self._explicit_transaction_depth - 1)

    def create_ventas_diarias_table(self):
        """Crea la tabla legacy ventas_diarias y migra historial desde Ventas."""

        self.cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS ventas_diarias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                monto_total NUMERIC(12,2) NOT NULL CHECK (monto_total >= 0),
                metodo_pago TEXT NOT NULL CHECK (
                    metodo_pago IN (
                        'EFECTIVO',
                        'TARJETA',
                        'TRANSFERENCIA',
                        'QR',
                        'CREDITO',
                        'NO_DEFINIDO'
                    )
                ),
                fecha_registro TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
                referencia TEXT NOT NULL UNIQUE,
                producto_id INTEGER NULL,
                legacy_venta_id TEXT UNIQUE,
                FOREIGN KEY (producto_id) REFERENCES Productos(id)
                    ON UPDATE CASCADE
                    ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ventas_diarias_fecha
                ON ventas_diarias(fecha_registro);

            CREATE INDEX IF NOT EXISTS idx_ventas_diarias_producto
                ON ventas_diarias(producto_id);

            CREATE INDEX IF NOT EXISTS idx_ventas_fecha
                ON Ventas(fecha);

            CREATE INDEX IF NOT EXISTS idx_ventas_cliente
                ON Ventas(id_cliente);

            CREATE INDEX IF NOT EXISTS idx_detalle_venta_id
                ON DetalleVenta(venta_id);

            CREATE INDEX IF NOT EXISTS idx_detalle_producto_id
                ON DetalleVenta(producto_id);

            INSERT INTO ventas_diarias (
                monto_total,
                metodo_pago,
                fecha_registro,
                referencia,
                producto_id,
                legacy_venta_id
            )
            SELECT
                v.total AS monto_total,
                'NO_DEFINIDO' AS metodo_pago,
                COALESCE(v.fecha, CURRENT_TIMESTAMP) AS fecha_registro,
                'LEG-' || v.id AS referencia,
                CASE
                    WHEN COUNT(DISTINCT dv.producto_id) = 1 THEN MIN(dv.producto_id)
                    ELSE NULL
                END AS producto_id,
                v.id AS legacy_venta_id
            FROM Ventas v
            LEFT JOIN DetalleVenta dv
                ON dv.venta_id = v.id
            WHERE NOT EXISTS (
                SELECT 1
                FROM ventas_diarias vd
                WHERE vd.legacy_venta_id = v.id
            )
            GROUP BY v.id, v.total, v.fecha;
            """
        )

    def insert_initial_data(self):
        """Inserta datos iniciales si las tablas están vacías."""

        # Usuario administrador por defecto
        bootstrap_completed = self.get_config(self.BOOTSTRAP_COMPLETED_KEY, "1")
        if not self.fetch("SELECT * FROM Usuarios") and bootstrap_completed == "0":
            self.execute(
                "INSERT INTO Usuarios (nombre, usuario, contrasena, rol) VALUES (?, ?, ?, ?)",
                ("Administrador", "admin", self.hash_password("1234"), "Administrador"),
            )
            self.set_config(self.BOOTSTRAP_COMPLETED_KEY, "1")

        # Proveedor de ejemplo
        if not self.fetch("SELECT * FROM Proveedores"):
            self.execute(
                "INSERT INTO Proveedores (nombre, contacto, telefono) VALUES (?, ?, ?)",
                ("Distribuidora Central", "Juan Pérez", "555-1234"),
            )

        # Descuentos predefinidos
        if not self.fetch("SELECT * FROM Descuentos"):
            self.execute(
                "INSERT INTO Descuentos (nombre, tipo, porcentaje) VALUES (?, ?, ?)",
                ("Docena 10%", "Docena", 0.10),
            )
            self.execute(
                "INSERT INTO Descuentos (nombre, tipo, porcentaje) VALUES (?, ?, ?)",
                ("Mayorista 15%", "Mayorista", 0.15),
            )

        # Plantilla de recibo por defecto
        if not self.fetch(
            "SELECT * FROM Configuracion WHERE clave = 'recibo_template'"
        ):
            self.set_config("recibo_template", self.default_receipt_template())

        # Productos de ejemplo
        if not self.fetch("SELECT * FROM Productos"):
            productos_ejemplo = [
                ('Monitor 27"', "Monitor 4K profesional", 6890.00, 15, 1),
                ("Teclado Mecánico", "Switches Blue, RGB", 1190.00, 105, 1),
                ("Mouse Gamer", "RGB, 16000 DPI", 850.00, 50, 1),
                ("Laptop HP", "i5, 8GB RAM, 256GB SSD", 18500.00, 8, 1),
            ]
            self.cursor.executemany(
                "INSERT INTO Productos (nombre, descripcion, precio, stock, proveedor_id) VALUES (?, ?, ?, ?, ?)",
                productos_ejemplo,
            )
            self.conn.commit()

        # Clientes de ejemplo
        if not self.fetch("SELECT * FROM Clientes"):
            from datetime import datetime

            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            clientes_ejemplo = [
                (
                    "Juan Carlos",
                    "Pérez González",
                    "0801199901234",
                    "9876-1234",
                    "juan.perez@email.com",
                    "Colonia Palmira, Tegucigalpa",
                    fecha_actual,
                    1,
                ),
                (
                    "María Elena",
                    "Rodríguez López",
                    "0801200005678",
                    "9965-4789",
                    "maria.rodriguez@email.com",
                    "Barrio La Granja, San Pedro Sula",
                    fecha_actual,
                    1,
                ),
                (
                    "José Antonio",
                    "Martínez Castro",
                    "0501199812345",
                    "9754-3261",
                    "jose.martinez@email.com",
                    "Centro, Comayagua",
                    fecha_actual,
                    1,
                ),
                (
                    "Ana Sofía",
                    "García Hernández",
                    "1801199909876",
                    "9843-7521",
                    "ana.garcia@email.com",
                    "Colonia Kennedy, La Ceiba",
                    fecha_actual,
                    1,
                ),
            ]
            self.cursor.executemany(
                "INSERT INTO Clientes (nombre, apellido, dni, telefono, email, direccion, fecha_registro, activo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                clientes_ejemplo,
            )
            self.conn.commit()

    def default_receipt_template(self):
        """Plantilla HTML por defecto para recibos."""
        return """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; font-size: 10pt; }
        .recibo { width: 300px; margin: 0 auto; border: 1px dashed #333; padding: 15px; }
        h1 { font-size: 16pt; text-align: center; margin: 0 0 10px 0; }
        .info { text-align: center; margin-bottom: 15px; font-size: 9pt; }
        .detail { margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px; }
        .item { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 9pt; }
        .total-section { margin-top: 15px; border-top: 2px solid #333; padding-top: 10px; }
        .total { font-weight: bold; font-size: 12pt; }
        .footer { margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px; text-align: center; font-size: 8pt; }
    </style>
</head>
<body>
    <div class="recibo">
        <h1>{{NOMBRE_NEGOCIO}}</h1>
        <div class="info">
            <p><strong>Venta ID:</strong> {{ID_VENTA}}</p>
            <p><strong>Fecha:</strong> {{FECHA}}</p>
        </div>
        
        <div class="detail">
            <div style="font-weight: bold; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 5px;" class="item">
                <span>Producto</span><span>Cant. / Subtotal</span>
            </div>
            <!-- ITEMS_PLACEHOLDER -->
        </div>

        <div class="total-section">
            <div class="item total"><span>TOTAL A PAGAR:</span><span>L {{TOTAL}}</span></div>
            <div class="item"><span>MONTO RECIBIDO:</span><span>L {{MONTO_PAGADO}}</span></div>
            <div class="item"><span>VUELTO:</span><span>L {{VUELTO}}</span></div>
        </div>

        <div class="footer">
            <p>¡Gracias por su compra!</p>
            <p>Vuelva pronto</p>
        </div>
    </div>
</body>
</html>"""

    def get_config(self, clave, default=None):
        """Obtiene un valor de configuración."""
        result = self.fetch("SELECT valor FROM Configuracion WHERE clave = ?", (clave,))
        return result[0][0] if result else default

    def set_config(self, clave, valor):
        """Establece o actualiza un valor de configuración."""
        self.execute(
            "INSERT OR REPLACE INTO Configuracion (clave, valor) VALUES (?, ?)",
            (clave, valor),
        )

    def create_pos_sale(
        self,
        sale_id,
        fecha,
        total,
        pagado,
        vuelto,
        metodo_pago,
        usuario_id,
        cliente_id,
        tipo_recibo,
        cart_data,
    ):
        """Registra una venta POS de forma atomica y con revalidacion de stock."""
        metodo_pago = (metodo_pago or "NO_DEFINIDO").strip().upper()
        if metodo_pago not in self.METODOS_PAGO_VALIDOS:
            raise ValueError("Metodo de pago no valido.")

        if not cart_data:
            raise ValueError("No hay productos para registrar en la venta.")

        if cliente_id in ("", None):
            cliente_id = None
        if usuario_id in ("", None):
            usuario_id = None

        with self.transaction() as cursor:
            cursor.execute(
                """
                INSERT INTO Ventas (
                    id, fecha, total, monto_pagado, vuelto, metodo_pago, usuario_id, id_cliente, tipo_recibo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sale_id,
                    fecha,
                    float(total or 0),
                    float(pagado or 0),
                    float(vuelto or 0),
                    metodo_pago,
                    usuario_id,
                    cliente_id,
                    tipo_recibo,
                ),
            )

            for raw_product_id, item in cart_data.items():
                product_id = int(raw_product_id)
                qty = int(item["cantidad"])
                price = float(item["precio_unitario"])
                pct = float(item.get("descuento_porcentaje", 0) or 0)
                discount_amount = (price * qty) * pct
                subtotal = (price * qty) - discount_amount

                if qty <= 0:
                    raise ValueError(f"Cantidad invalida para el producto {item['nombre']}.")

                product_row = cursor.execute(
                    "SELECT nombre, stock FROM Productos WHERE id = ?",
                    (product_id,),
                ).fetchone()
                if not product_row:
                    raise ValueError(f"El producto {product_id} ya no existe.")

                current_stock = int(product_row[1] or 0)
                if current_stock < qty:
                    raise ValueError(
                        f"Stock insuficiente para {item['nombre']}. Disponible: {current_stock}."
                    )

                cursor.execute(
                    "UPDATE Productos SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (qty, product_id, qty),
                )
                if cursor.rowcount != 1:
                    raise ValueError(
                        f"No se pudo actualizar el stock de {item['nombre']}. Intente refrescar el catalogo."
                    )

                cursor.execute(
                    """
                    INSERT INTO DetalleVenta (
                        venta_id, producto_id, nombre_producto, cantidad, precio_unitario, descuento, subtotal
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        product_id,
                        item.get("nombre") or product_row[0],
                        qty,
                        price,
                        discount_amount,
                        subtotal,
                    ),
                )

    def create_venta_diaria(self, monto_total, metodo_pago, referencia, producto_id=None):
        """Inserta una venta diaria y devuelve su ID."""
        metodo_pago = (metodo_pago or "").strip().upper()
        if metodo_pago not in self.METODOS_PAGO_VALIDOS:
            raise ValueError("Metodo de pago no válido.")

        if producto_id in ("", None):
            producto_id = None

        self.cursor.execute(
            """
            INSERT INTO ventas_diarias (monto_total, metodo_pago, referencia, producto_id)
            VALUES (?, ?, ?, ?)
            """,
            (monto_total, metodo_pago, referencia.strip(), producto_id),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def fetch_ventas_diarias(
        self, fecha_desde=None, fecha_hasta=None, transaccion_id=None
    ):
        """Obtiene ventas diarias con filtros opcionales."""
        query = """
            SELECT
                id,
                monto_total,
                metodo_pago,
                referencia,
                fecha_registro,
                producto_id,
                legacy_venta_id
            FROM ventas_diarias
            WHERE 1=1
        """
        params = []

        if fecha_desde:
            query += " AND date(fecha_registro) >= date(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            query += " AND date(fecha_registro) <= date(?)"
            params.append(fecha_hasta)

        if transaccion_id:
            token = transaccion_id.strip()
            if token.isdigit():
                query += " AND id = ?"
                params.append(int(token))
            else:
                # Permite buscar por referencia/legacy para trazabilidad histórica.
                query += " AND (referencia = ? OR legacy_venta_id = ?)"
                params.extend((token, token))

        query += " ORDER BY datetime(fecha_registro) DESC, id DESC"
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def fetch_filter_options(self):
        """Obtiene opciones disponibles para filtros de registro POS."""
        productos = self.fetch(
            """
            SELECT p.id, p.nombre
            FROM Productos p
            ORDER BY p.nombre
            """
        )
        clientes = self.fetch(
            """
            SELECT c.id, (c.nombre || ' ' || c.apellido) AS nombre_completo
            FROM Clientes c
            ORDER BY nombre_completo
            """
        )
        return {"productos": productos, "clientes": clientes}

    def fetch_sales_registry(self, filters=None):
        """Obtiene registros del POS desde Ventas/DetalleVenta, que son la fuente principal."""
        filters = filters or {}
        query = """
            SELECT
                v.id,
                v.fecha,
                v.total,
                COALESCE(v.monto_pagado, 0) AS monto_pagado,
                COALESCE(v.vuelto, 0) AS vuelto,
                COALESCE((c.nombre || ' ' || c.apellido), 'Cliente General') AS cliente_nombre,
                GROUP_CONCAT(DISTINCT COALESCE(p.nombre, dv.nombre_producto)) AS productos,
                COUNT(dv.id) AS lineas
            FROM Ventas v
            LEFT JOIN Clientes c
                ON c.id = v.id_cliente
            LEFT JOIN DetalleVenta dv
                ON dv.venta_id = v.id
            LEFT JOIN Productos p
                ON p.id = dv.producto_id
            WHERE 1=1
        """
        params = []

        fecha_desde = (filters.get("fecha_desde") or "").strip()
        fecha_hasta = (filters.get("fecha_hasta") or "").strip()
        if fecha_desde:
            query += " AND date(v.fecha) >= date(?)"
            params.append(fecha_desde)
        if fecha_hasta:
            query += " AND date(v.fecha) <= date(?)"
            params.append(fecha_hasta)

        mes = filters.get("mes")
        if mes not in (None, ""):
            try:
                month_token = f"{int(mes):02d}"
                query += " AND strftime('%m', v.fecha) = ?"
                params.append(month_token)
            except (TypeError, ValueError):
                pass

        anio = filters.get("anio")
        if anio not in (None, ""):
            try:
                year_token = str(int(anio))
                query += " AND strftime('%Y', v.fecha) = ?"
                params.append(year_token)
            except (TypeError, ValueError):
                pass

        venta_id = (filters.get("venta_id") or "").strip()
        if venta_id:
            query += " AND v.id = ?"
            params.append(venta_id)

        producto_id = filters.get("producto_id")
        if producto_id:
            query += """
                AND EXISTS (
                    SELECT 1
                    FROM DetalleVenta dvf
                    WHERE dvf.venta_id = v.id
                      AND dvf.producto_id = ?
                )
            """
            params.append(producto_id)

        cliente_id = filters.get("cliente_id")
        if cliente_id:
            query += " AND v.id_cliente = ?"
            params.append(cliente_id)

        query += """
            GROUP BY
                v.id,
                v.fecha,
                v.total,
                v.monto_pagado,
                v.vuelto,
                c.nombre,
                c.apellido
            ORDER BY datetime(v.fecha) DESC, v.id DESC
        """
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def fetch_sale_header(self, venta_id):
        """Obtiene cabecera de una venta POS para reimpresion."""
        rows = self.fetch(
            """
            SELECT
                v.id,
                v.fecha,
                v.total,
                COALESCE(v.monto_pagado, 0) AS monto_pagado,
                COALESCE(v.vuelto, 0) AS vuelto,
                COALESCE(v.metodo_pago, 'NO_DEFINIDO') AS metodo_pago,
                v.tipo_recibo,
                c.nombre,
                c.apellido,
                c.dni,
                c.telefono,
                c.direccion
            FROM Ventas v
            LEFT JOIN Clientes c
                ON c.id = v.id_cliente
            WHERE v.id = ?
            LIMIT 1
            """,
            (venta_id,),
        )
        if not rows:
            return None

        row = rows[0]
        return {
            "venta_id": row[0],
            "fecha": row[1],
            "total": float(row[2] or 0),
            "monto_pagado": float(row[3] or 0),
            "vuelto": float(row[4] or 0),
            "metodo_pago": row[5] or "NO_DEFINIDO",
            "tipo_recibo": row[6],
            "cliente": {
                "nombre": row[7] or "",
                "apellido": row[8] or "",
                "dni": row[9] or "",
                "telefono": row[10] or "",
                "direccion": row[11] or "",
            }
            if row[7] or row[8] or row[9] or row[10] or row[11]
            else None,
        }

    def fetch_sale_items(self, venta_id):
        """Obtiene detalle de productos de una venta POS."""
        rows = self.fetch(
            """
            SELECT
                dv.producto_id,
                COALESCE(p.nombre, dv.nombre_producto) AS nombre_producto,
                dv.cantidad,
                dv.precio_unitario,
                COALESCE(dv.descuento, 0) AS descuento_monto,
                dv.subtotal
            FROM DetalleVenta dv
            LEFT JOIN Productos p
                ON p.id = dv.producto_id
            WHERE dv.venta_id = ?
            ORDER BY dv.id
            """,
            (venta_id,),
        )
        return [
            {
                "producto_id": row[0],
                "nombre": row[1],
                "cantidad": float(row[2] or 0),
                "precio_unitario": float(row[3] or 0),
                "descuento_monto": float(row[4] or 0),
                "subtotal": float(row[5] or 0),
            }
            for row in rows
        ]

    def cleanup_legacy_sales_registry(self):
        """Depura ventas_diarias eliminando solo inconsistencias verificables."""
        report = {
            "antes_total": self.fetch("SELECT COUNT(*) FROM ventas_diarias")[0][0],
            "eliminados_huerfanos_venta": 0,
            "eliminados_huerfanos_producto": 0,
            "eliminados_duplicados_legacy": 0,
            "eliminados_duplicados_referencia": 0,
        }

        self.cursor.execute(
            """
            DELETE FROM ventas_diarias
            WHERE legacy_venta_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM Ventas v
                  WHERE v.id = ventas_diarias.legacy_venta_id
              )
            """
        )
        report["eliminados_huerfanos_venta"] = self.cursor.rowcount

        self.cursor.execute(
            """
            DELETE FROM ventas_diarias
            WHERE producto_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM Productos p
                  WHERE p.id = ventas_diarias.producto_id
              )
            """
        )
        report["eliminados_huerfanos_producto"] = self.cursor.rowcount

        self.cursor.execute(
            """
            DELETE FROM ventas_diarias
            WHERE legacy_venta_id IS NOT NULL
              AND id NOT IN (
                  SELECT MIN(id)
                  FROM ventas_diarias
                  WHERE legacy_venta_id IS NOT NULL
                  GROUP BY legacy_venta_id
              )
            """
        )
        report["eliminados_duplicados_legacy"] = self.cursor.rowcount

        self.cursor.execute(
            """
            DELETE FROM ventas_diarias
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM ventas_diarias
                GROUP BY referencia
            )
            """
        )
        report["eliminados_duplicados_referencia"] = self.cursor.rowcount

        self.conn.commit()
        report["despues_total"] = self.fetch("SELECT COUNT(*) FROM ventas_diarias")[0][0]
        report["total_eliminados"] = (
            report["eliminados_huerfanos_venta"]
            + report["eliminados_huerfanos_producto"]
            + report["eliminados_duplicados_legacy"]
            + report["eliminados_duplicados_referencia"]
        )
        return report

    def fetch(self, query, params=()):
        """Ejecuta una consulta SELECT y retorna los resultados."""
        try:
            self.last_error = None
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.last_error = e
            return []

    def execute(self, query, params=()):
        """Ejecuta una consulta INSERT/UPDATE/DELETE."""
        try:
            self.last_error = None
            self.cursor.execute(query, params)
            if self._explicit_transaction_depth == 0:
                self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            self.last_error = e
            return None

    def close(self):
        """Cierra la conexión a la base de datos."""
        self.conn.close()

