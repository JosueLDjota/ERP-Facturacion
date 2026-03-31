"""
database.py - Gestor de Base de Datos SQLite
Maneja todas las operaciones CRUD y estructura de la base de datos.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import logging
from pathlib import Path
import sqlite3
from typing import Iterator

from erp.domain.services.security import generate_temporary_password, hash_password


logger = logging.getLogger(__name__)


class DatabaseError(RuntimeError):
    """Error operativo o transaccional de SQLite."""


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

    def __init__(self, db_name="erp_profesional.db"):
        self.db_path = self._resolve_db_path(db_name)
        self._transaction_depth = 0
        self.bootstrap_admin_password = None
        self.last_error = None

        self.conn = sqlite3.connect(
            self.db_path,
            timeout=30,
            uri=str(self.db_path).startswith("file:"),
        )
        self.cursor = self.conn.cursor()
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.create_tables()

    def _resolve_db_path(self, db_name) -> str:
        raw_path = str(db_name or "erp_profesional.db")
        if raw_path == ":memory:" or raw_path.startswith("file:"):
            return raw_path

        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path

        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Cursor]:
        """Abre una transacción reutilizable con savepoints para anidación segura."""
        cursor = self.conn.cursor()
        savepoint_name = None
        try:
            self.last_error = None
            if self._transaction_depth == 0:
                cursor.execute("BEGIN IMMEDIATE")
            else:
                savepoint_name = f"sp_{self._transaction_depth}"
                cursor.execute(f"SAVEPOINT {savepoint_name}")

            self._transaction_depth += 1
            yield cursor

            self._transaction_depth -= 1
            if savepoint_name:
                cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            elif self._transaction_depth == 0:
                self.conn.commit()
        except sqlite3.Error as exc:
            self.last_error = exc
            logger.exception("Error de base de datos durante transacción.")
            if savepoint_name:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                self._transaction_depth = max(0, self._transaction_depth - 1)
            else:
                self._transaction_depth = 0
                self.conn.rollback()
            raise DatabaseError(str(exc)) from exc
        except Exception:
            if savepoint_name:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
                self._transaction_depth = max(0, self._transaction_depth - 1)
            else:
                self._transaction_depth = 0
                self.conn.rollback()
            raise

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

        # Tabla de Productos
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS Productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                precio REAL NOT NULL,
                stock INTEGER NOT NULL,
                stock_minimo INTEGER NOT NULL DEFAULT 5,
                proveedor_id INTEGER,
                FOREIGN KEY (proveedor_id) REFERENCES Proveedores(id)
            )
        """
        )
        self._ensure_column(
            "Productos",
            "stock_minimo",
            "INTEGER NOT NULL DEFAULT 5",
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
        self._ensure_column("Usuarios", "password_updated_at", "TEXT")

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
                total REAL NOT NULL,
                monto_pagado REAL,
                vuelto REAL,
                metodo_pago TEXT DEFAULT 'NO_DEFINIDO',
                usuario_id INTEGER,
                id_cliente INTEGER,
                tipo_recibo TEXT,
                FOREIGN KEY (id_cliente) REFERENCES Clientes(id)
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
                venta_id TEXT,
                producto_id INTEGER,
                nombre_producto TEXT,
                cantidad INTEGER,
                precio_unitario REAL,
                descuento REAL DEFAULT 0,
                subtotal REAL,
                FOREIGN KEY (venta_id) REFERENCES Ventas(id)
            )
        """
        )

        self.create_ventas_diarias_table()
        self.conn.commit()
        self.insert_initial_data()

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

    def create_ventas_diarias_table(self):
        """Crea tabla de ventas diarias y migra historial desde Ventas."""

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

        # Usuario administrador inicial seguro
        if not self.fetch("SELECT * FROM Usuarios"):
            temporary_password = generate_temporary_password()
            self.bootstrap_admin_password = temporary_password
            self.execute(
                """
                INSERT INTO Usuarios (nombre, usuario, contrasena, rol, password_updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    "Administrador",
                    "admin",
                    hash_password(temporary_password),
                    "Administrador",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            logger.warning(
                "Se creó un usuario administrador inicial. Usuario: admin | Contraseña temporal: %s",
                temporary_password,
            )

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
                    0,
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
                    0,
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
                    0,
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
                    0,
                ),
            ]
            self.cursor.executemany(
                """
                INSERT INTO Clientes (
                    nombre, apellido, dni, telefono, email, direccion, fecha_registro, activo, mayorista
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                clientes_ejemplo,
            )
            self.conn.commit()

    def default_receipt_template(self):
        """Plantilla HTML por defecto para recibos."""
        from receipt_builder import default_receipt_template

        return default_receipt_template()

    def get_config(self, clave, default=None):
        """Obtiene un valor de configuración."""
        result = self.fetch("SELECT valor FROM Configuracion WHERE clave = ?", (clave,))
        return result[0][0] if result else default

    def set_config(self, clave, valor):
        """Establece o actualiza un valor de configuración."""
        self.execute_checked(
            "INSERT OR REPLACE INTO Configuracion (clave, valor) VALUES (?, ?)",
            (clave, valor),
        )

    def create_venta_diaria(self, monto_total, metodo_pago, referencia, producto_id=None):
        """Inserta una venta diaria y devuelve su ID."""
        metodo_pago = (metodo_pago or "").strip().upper()
        if metodo_pago not in self.METODOS_PAGO_VALIDOS:
            raise ValueError("Metodo de pago no válido.")

        if producto_id in ("", None):
            producto_id = None

        return self.execute_checked(
            """
            INSERT INTO ventas_diarias (monto_total, metodo_pago, referencia, producto_id)
            VALUES (?, ?, ?, ?)
            """,
            (monto_total, metodo_pago, referencia.strip(), producto_id),
        )

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
        """Obtiene registros de ventas del POS en modo solo lectura."""
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
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            self.last_error = e
            logger.exception("Error ejecutando consulta SELECT.")
            return []

    def execute(self, query, params=()):
        """Ejecuta una consulta INSERT/UPDATE/DELETE."""
        try:
            self.last_error = None
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            if self._transaction_depth == 0:
                self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            self.last_error = e
            if self._transaction_depth == 0:
                self.conn.rollback()
            logger.exception("Error ejecutando sentencia SQL.")
            return None

    def fetch_one(self, query, params=()):
        rows = self.fetch(query, params)
        return rows[0] if rows else None

    def execute_checked(self, query, params=()):
        result = self.execute(query, params)
        if self.last_error is not None:
            raise DatabaseError(str(self.last_error))
        return result

    def close(self):
        """Cierra la conexión a la base de datos."""
        self.conn.close()

