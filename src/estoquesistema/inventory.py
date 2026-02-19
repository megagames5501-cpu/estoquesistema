from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Consumption:
    batch_id: int
    quantity: float


class InventorySystem:
    """Sistema de estoque com suporte a entradas/saídas LIFO e rastreabilidade."""

    def __init__(self, db_path: str | Path = "estoque.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS destinations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT
                );

                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    unit TEXT NOT NULL,
                    category_id INTEGER NOT NULL,
                    min_stock REAL DEFAULT 0,
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                );

                CREATE TABLE IF NOT EXISTS batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    lot_code TEXT,
                    supplier TEXT,
                    quantity REAL NOT NULL,
                    remaining_quantity REAL NOT NULL,
                    unit_cost REAL,
                    received_at TEXT NOT NULL,
                    FOREIGN KEY (item_id) REFERENCES items(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id)
                );

                CREATE TABLE IF NOT EXISTS movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id INTEGER NOT NULL,
                    location_id INTEGER,
                    destination_id INTEGER,
                    movement_type TEXT NOT NULL CHECK (movement_type IN ('IN','OUT')),
                    quantity REAL NOT NULL,
                    movement_at TEXT NOT NULL,
                    notes TEXT,
                    FOREIGN KEY (item_id) REFERENCES items(id),
                    FOREIGN KEY (location_id) REFERENCES locations(id),
                    FOREIGN KEY (destination_id) REFERENCES destinations(id)
                );

                CREATE TABLE IF NOT EXISTS movement_batches (
                    movement_id INTEGER NOT NULL,
                    batch_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    FOREIGN KEY (movement_id) REFERENCES movements(id),
                    FOREIGN KEY (batch_id) REFERENCES batches(id)
                );
                """
            )

    def create_category(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO categories (name, description) VALUES (?, ?)",
                (name, description),
            )
            return int(cur.lastrowid)

    def create_location(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO locations (name, description) VALUES (?, ?)",
                (name, description),
            )
            return int(cur.lastrowid)

    def create_destination(self, name: str, description: str = "") -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO destinations (name, description) VALUES (?, ?)",
                (name, description),
            )
            return int(cur.lastrowid)

    def create_item(self, name: str, unit: str, category_id: int, min_stock: float = 0) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO items (name, unit, category_id, min_stock)
                VALUES (?, ?, ?, ?)
                """,
                (name, unit, category_id, min_stock),
            )
            return int(cur.lastrowid)

    def add_stock(
        self,
        item_id: int,
        location_id: int,
        quantity: float,
        lot_code: str = "",
        supplier: str = "",
        unit_cost: float | None = None,
        received_at: str | None = None,
        notes: str = "",
    ) -> int:
        if quantity <= 0:
            raise ValueError("A quantidade de entrada deve ser positiva.")

        movement_at = received_at or datetime.utcnow().isoformat()

        with self._connect() as conn:
            cur_batch = conn.execute(
                """
                INSERT INTO batches (
                    item_id, location_id, lot_code, supplier,
                    quantity, remaining_quantity, unit_cost, received_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item_id,
                    location_id,
                    lot_code,
                    supplier,
                    quantity,
                    quantity,
                    unit_cost,
                    movement_at,
                ),
            )
            batch_id = int(cur_batch.lastrowid)

            cur_movement = conn.execute(
                """
                INSERT INTO movements (
                    item_id, location_id, destination_id,
                    movement_type, quantity, movement_at, notes
                ) VALUES (?, ?, NULL, 'IN', ?, ?, ?)
                """,
                (item_id, location_id, quantity, movement_at, notes),
            )
            movement_id = int(cur_movement.lastrowid)

            conn.execute(
                "INSERT INTO movement_batches (movement_id, batch_id, quantity) VALUES (?, ?, ?)",
                (movement_id, batch_id, quantity),
            )

            return batch_id

    def remove_stock_lifo(
        self,
        item_id: int,
        quantity: float,
        destination_id: int,
        location_id: int | None = None,
        movement_at: str | None = None,
        notes: str = "",
    ) -> int:
        if quantity <= 0:
            raise ValueError("A quantidade de retirada deve ser positiva.")

        with self._connect() as conn:
            available = self._available_stock(conn, item_id, location_id)
            if available < quantity:
                raise ValueError(
                    f"Estoque insuficiente para item {item_id}. Disponível: {available}, solicitado: {quantity}."
                )

            batch_rows = conn.execute(
                """
                SELECT id, remaining_quantity
                FROM batches
                WHERE item_id = ?
                  AND remaining_quantity > 0
                  AND (? IS NULL OR location_id = ?)
                ORDER BY received_at DESC, id DESC
                """,
                (item_id, location_id, location_id),
            ).fetchall()

            consumption = self._consume_batches(batch_rows, quantity)
            movement_time = movement_at or datetime.utcnow().isoformat()

            cur_movement = conn.execute(
                """
                INSERT INTO movements (
                    item_id, location_id, destination_id,
                    movement_type, quantity, movement_at, notes
                ) VALUES (?, ?, ?, 'OUT', ?, ?, ?)
                """,
                (item_id, location_id, destination_id, quantity, movement_time, notes),
            )
            movement_id = int(cur_movement.lastrowid)

            for part in consumption:
                conn.execute(
                    "UPDATE batches SET remaining_quantity = remaining_quantity - ? WHERE id = ?",
                    (part.quantity, part.batch_id),
                )
                conn.execute(
                    "INSERT INTO movement_batches (movement_id, batch_id, quantity) VALUES (?, ?, ?)",
                    (movement_id, part.batch_id, part.quantity),
                )

            return movement_id

    def _consume_batches(self, rows: Iterable[sqlite3.Row], quantity: float) -> list[Consumption]:
        remaining = quantity
        used: list[Consumption] = []

        for row in rows:
            if remaining <= 0:
                break
            from_batch = min(remaining, float(row["remaining_quantity"]))
            used.append(Consumption(batch_id=int(row["id"]), quantity=from_batch))
            remaining -= from_batch

        if remaining > 0:
            raise ValueError("Não foi possível consumir os lotes necessários para a retirada.")
        return used

    def _available_stock(self, conn: sqlite3.Connection, item_id: int, location_id: int | None) -> float:
        row = conn.execute(
            """
            SELECT COALESCE(SUM(remaining_quantity), 0) AS total
            FROM batches
            WHERE item_id = ?
              AND (? IS NULL OR location_id = ?)
            """,
            (item_id, location_id, location_id),
        ).fetchone()
        return float(row["total"])

    def current_stock(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    i.id AS item_id,
                    i.name AS item,
                    c.name AS category,
                    l.name AS location,
                    i.unit,
                    i.min_stock,
                    COALESCE(SUM(b.remaining_quantity), 0) AS quantity
                FROM items i
                JOIN categories c ON c.id = i.category_id
                LEFT JOIN batches b ON b.item_id = i.id
                LEFT JOIN locations l ON l.id = b.location_id
                GROUP BY i.id, i.name, c.name, l.name, i.unit, i.min_stock
                ORDER BY i.name
                """
            ).fetchall()

    def movement_history(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            return conn.execute(
                """
                SELECT
                    m.id,
                    m.movement_type,
                    i.name AS item,
                    m.quantity,
                    l.name AS location,
                    d.name AS destination,
                    m.movement_at,
                    m.notes
                FROM movements m
                JOIN items i ON i.id = m.item_id
                LEFT JOIN locations l ON l.id = m.location_id
                LEFT JOIN destinations d ON d.id = m.destination_id
                ORDER BY m.movement_at DESC, m.id DESC
                """
            ).fetchall()
