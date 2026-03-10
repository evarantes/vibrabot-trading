from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .database import execute, get_connection

MOVEMENT_TYPES = {
    "PURCHASE",
    "STOCK_IN",
    "STOCK_OUT",
    "LAUNDRY_SENT",
    "LAUNDRY_RETURNED",
    "LAUNDRY_REWASH_SENT",
    "LAUNDRY_REWASH_RETURNED",
    "IN_USE_ALLOCATED",
    "IN_USE_RETURNED",
    "LOSS",
}
OPERATION_UNITS = {"HOTEL", "CLUB"}


def _normalize_unit(operation_unit: str) -> str:
    unit = operation_unit.strip().upper()
    if unit not in OPERATION_UNITS:
        raise ValueError(f"Unidade inválida: {operation_unit}. Use HOTEL ou CLUB.")
    return unit


def add_item(name: str, category: str, par_level: int = 0) -> None:
    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO items (name, category, par_level)
            VALUES (?, ?, ?)
            """,
            (name.strip(), category.strip(), max(par_level, 0)),
        )


def list_items(active_only: bool = True) -> list[dict[str, Any]]:
    query = "SELECT id, name, category, par_level, active FROM items"
    params: list[Any] = []
    if active_only:
        query += " WHERE active = TRUE"
    query += " ORDER BY name"

    with get_connection() as conn:
        rows = execute(conn, query, params).fetchall()
    return [dict(row) for row in rows]


def add_movement(
    item_id: int,
    movement_type: str,
    quantity: int,
    movement_date: date,
    operation_unit: str = "HOTEL",
    source_ref: str = "",
    note: str = "",
) -> None:
    if movement_type not in MOVEMENT_TYPES:
        raise ValueError(f"Tipo de movimento inválido: {movement_type}")
    if quantity <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")
    unit = _normalize_unit(operation_unit)

    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO movements (
                item_id,
                operation_unit,
                movement_type,
                quantity,
                movement_date,
                source_ref,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                unit,
                movement_type,
                quantity,
                movement_date.isoformat(),
                source_ref.strip(),
                note.strip(),
            ),
        )


def upsert_inventory_count(
    item_id: int,
    count_date: date,
    counted_stock: int,
    counted_laundry: int = 0,
    counted_in_use: int = 0,
    operation_unit: str = "HOTEL",
    note: str = "",
) -> None:
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        updated = execute(
            conn,
            """
            UPDATE inventory_counts
            SET
                counted_stock = ?,
                counted_laundry = ?,
                counted_in_use = ?,
                note = ?
            WHERE item_id = ?
              AND count_date = ?
              AND operation_unit = ?
            """,
            (
                max(counted_stock, 0),
                max(counted_laundry, 0),
                max(counted_in_use, 0),
                note.strip(),
                item_id,
                count_date.isoformat(),
                unit,
            ),
        )
        if updated.rowcount > 0:
            return

        execute(
            conn,
            """
            INSERT INTO inventory_counts (
                item_id,
                count_date,
                operation_unit,
                counted_stock,
                counted_laundry,
                counted_in_use,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                count_date.isoformat(),
                unit,
                max(counted_stock, 0),
                max(counted_laundry, 0),
                max(counted_in_use, 0),
                note.strip(),
            ),
        )


def get_balances(as_of_date: date, operation_unit: str = "HOTEL") -> list[dict[str, Any]]:
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            WITH move AS (
                SELECT
                    item_id,
                    SUM(
                        CASE movement_type
                            WHEN 'PURCHASE' THEN quantity
                            WHEN 'STOCK_IN' THEN quantity
                            WHEN 'STOCK_OUT' THEN -quantity
                            WHEN 'LAUNDRY_SENT' THEN -quantity
                            WHEN 'LAUNDRY_REWASH_SENT' THEN -quantity
                            WHEN 'LAUNDRY_RETURNED' THEN quantity
                            WHEN 'LAUNDRY_REWASH_RETURNED' THEN quantity
                            WHEN 'IN_USE_ALLOCATED' THEN -quantity
                            WHEN 'IN_USE_RETURNED' THEN quantity
                            WHEN 'LOSS' THEN -quantity
                            ELSE 0
                        END
                    ) AS stock_theoretical,
                    SUM(
                        CASE movement_type
                            WHEN 'LAUNDRY_SENT' THEN quantity
                            WHEN 'LAUNDRY_REWASH_SENT' THEN quantity
                            WHEN 'LAUNDRY_RETURNED' THEN -quantity
                            WHEN 'LAUNDRY_REWASH_RETURNED' THEN -quantity
                            ELSE 0
                        END
                    ) AS laundry_theoretical,
                    SUM(
                        CASE movement_type
                            WHEN 'IN_USE_ALLOCATED' THEN quantity
                            WHEN 'IN_USE_RETURNED' THEN -quantity
                            ELSE 0
                        END
                    ) AS in_use_theoretical,
                    SUM(
                        CASE movement_type
                            WHEN 'PURCHASE' THEN quantity
                            ELSE 0
                        END
                    ) AS total_purchased,
                    SUM(
                        CASE movement_type
                            WHEN 'LOSS' THEN quantity
                            ELSE 0
                        END
                    ) AS total_loss
                FROM movements
                WHERE movement_date <= ?
                  AND operation_unit = ?
                GROUP BY item_id
            ),
            latest_count AS (
                SELECT item_id, count_date, counted_stock, counted_laundry, counted_in_use
                FROM (
                    SELECT
                        ic.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY item_id
                            ORDER BY count_date DESC, id DESC
                        ) AS rn
                    FROM inventory_counts ic
                    WHERE count_date <= ?
                      AND operation_unit = ?
                ) x
                WHERE rn = 1
            )
            SELECT
                i.id,
                i.name,
                i.category,
                i.par_level,
                COALESCE(m.stock_theoretical, 0) AS stock_theoretical,
                COALESCE(m.laundry_theoretical, 0) AS laundry_theoretical,
                COALESCE(m.in_use_theoretical, 0) AS in_use_theoretical,
                COALESCE(m.total_purchased, 0) AS total_purchased,
                COALESCE(m.total_loss, 0) AS total_loss,
                lc.count_date AS latest_count_date,
                lc.counted_stock,
                lc.counted_laundry,
                lc.counted_in_use
            FROM items i
            LEFT JOIN move m ON m.item_id = i.id
            LEFT JOIN latest_count lc ON lc.item_id = i.id
            WHERE i.active = TRUE
            ORDER BY i.name
            """,
            (as_of_date.isoformat(), unit, as_of_date.isoformat(), unit),
        ).fetchall()
    return [dict(row) for row in rows]


def list_recent_movements(limit: int = 200, operation_unit: str = "HOTEL") -> list[dict[str, Any]]:
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT
                m.id,
                m.operation_unit,
                m.movement_date,
                m.movement_type,
                m.quantity,
                m.source_ref,
                m.note,
                i.name AS item_name
            FROM movements m
            JOIN items i ON i.id = m.item_id
            WHERE m.operation_unit = ?
            ORDER BY m.movement_date DESC, m.id DESC
            LIMIT ?
            """,
            (unit, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def get_daily_allocated_usage(
    item_id: int,
    days: int = 30,
    ref_date: date | None = None,
    operation_unit: str = "HOTEL",
) -> list[dict[str, Any]]:
    end_date = ref_date or date.today()
    start_date = end_date - timedelta(days=days - 1)
    unit = _normalize_unit(operation_unit)

    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT
                movement_date,
                SUM(
                    CASE movement_type
                        WHEN 'IN_USE_ALLOCATED' THEN quantity
                        WHEN 'IN_USE_RETURNED' THEN -quantity
                        ELSE 0
                    END
                ) AS net_use_delta
            FROM movements
            WHERE item_id = ?
              AND operation_unit = ?
              AND movement_date BETWEEN ? AND ?
            GROUP BY movement_date
            ORDER BY movement_date
            """,
            (item_id, unit, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return [dict(row) for row in rows]


def get_laundry_movements(item_id: int, as_of_date: date, operation_unit: str = "HOTEL") -> list[dict[str, Any]]:
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT movement_date, movement_type, quantity
            FROM movements
            WHERE item_id = ?
              AND operation_unit = ?
              AND movement_type IN (
                  'LAUNDRY_SENT',
                  'LAUNDRY_RETURNED',
                  'LAUNDRY_REWASH_SENT',
                  'LAUNDRY_REWASH_RETURNED'
              )
              AND movement_date <= ?
            ORDER BY movement_date, id
            """,
            (item_id, unit, as_of_date.isoformat()),
        ).fetchall()
    return [dict(row) for row in rows]


def get_loss_totals(days: int, ref_date: date | None = None, operation_unit: str = "HOTEL") -> dict[int, int]:
    end_date = ref_date or date.today()
    start_date = end_date - timedelta(days=days - 1)
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT item_id, SUM(quantity) AS total_loss
            FROM movements
            WHERE movement_type = 'LOSS'
              AND operation_unit = ?
              AND movement_date BETWEEN ? AND ?
            GROUP BY item_id
            """,
            (unit, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return {int(row["item_id"]): int(row["total_loss"]) for row in rows}


def get_daily_movement_totals(
    days: int = 30,
    ref_date: date | None = None,
    operation_unit: str = "HOTEL",
) -> list[dict[str, Any]]:
    end_date = ref_date or date.today()
    start_date = end_date - timedelta(days=days - 1)
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT
                movement_date,
                SUM(CASE WHEN movement_type = 'PURCHASE' THEN quantity ELSE 0 END) AS purchased,
                SUM(CASE WHEN movement_type = 'LAUNDRY_SENT' THEN quantity ELSE 0 END) AS laundry_sent,
                SUM(CASE WHEN movement_type = 'LAUNDRY_RETURNED' THEN quantity ELSE 0 END) AS laundry_returned,
                SUM(CASE WHEN movement_type = 'LAUNDRY_REWASH_SENT' THEN quantity ELSE 0 END) AS rewash_sent,
                SUM(CASE WHEN movement_type = 'LAUNDRY_REWASH_RETURNED' THEN quantity ELSE 0 END) AS rewash_returned,
                SUM(CASE WHEN movement_type = 'IN_USE_ALLOCATED' THEN quantity ELSE 0 END) AS allocated,
                SUM(CASE WHEN movement_type = 'IN_USE_RETURNED' THEN quantity ELSE 0 END) AS returned_use,
                SUM(CASE WHEN movement_type = 'LOSS' THEN quantity ELSE 0 END) AS loss
            FROM movements
            WHERE operation_unit = ?
              AND movement_date BETWEEN ? AND ?
            GROUP BY movement_date
            ORDER BY movement_date
            """,
            (unit, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()
    return [dict(row) for row in rows]


def get_laundry_billing_summary(
    days: int = 30,
    ref_date: date | None = None,
    operation_unit: str = "HOTEL",
) -> dict[str, int]:
    end_date = ref_date or date.today()
    start_date = end_date - timedelta(days=days - 1)
    unit = _normalize_unit(operation_unit)

    with get_connection() as conn:
        row = execute(
            conn,
            """
            SELECT
                COALESCE(SUM(CASE WHEN movement_type = 'LAUNDRY_SENT' THEN quantity ELSE 0 END), 0) AS billed_sent,
                COALESCE(SUM(CASE WHEN movement_type = 'LAUNDRY_RETURNED' THEN quantity ELSE 0 END), 0) AS billed_returned,
                COALESCE(SUM(CASE WHEN movement_type = 'LAUNDRY_REWASH_SENT' THEN quantity ELSE 0 END), 0) AS rewash_sent,
                COALESCE(SUM(CASE WHEN movement_type = 'LAUNDRY_REWASH_RETURNED' THEN quantity ELSE 0 END), 0) AS rewash_returned
            FROM movements
            WHERE operation_unit = ?
              AND movement_date BETWEEN ? AND ?
            """,
            (unit, start_date.isoformat(), end_date.isoformat()),
        ).fetchone()

    if row is None:
        return {"billed_sent": 0, "billed_returned": 0, "rewash_sent": 0, "rewash_returned": 0}
    return {
        "billed_sent": int(row["billed_sent"] or 0),
        "billed_returned": int(row["billed_returned"] or 0),
        "rewash_sent": int(row["rewash_sent"] or 0),
        "rewash_returned": int(row["rewash_returned"] or 0),
    }

