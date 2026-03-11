from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .database import execute, get_connection, get_db_engine

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
OPERATION_UNITS = {"CENTRAL", "HOTEL", "CLUB"}


def _normalize_unit(operation_unit: str) -> str:
    raw = operation_unit.strip().upper()
    aliases = {
        "LA_PLAGE": "HOTEL",
        "LA PLAGE": "HOTEL",
        "LAPLAGE": "HOTEL",
        "CLUBE": "CLUB",
    }
    unit = aliases.get(raw, raw)
    if unit not in OPERATION_UNITS:
        raise ValueError(f"Unidade inválida: {operation_unit}. Use CENTRAL, HOTEL ou CLUB.")
    return unit


def _to_date(raw_value: Any) -> date:
    if isinstance(raw_value, date):
        return raw_value
    return date.fromisoformat(str(raw_value))


def add_item(
    name: str,
    category: str,
    par_level: int = 0,
    laundry_unit_cost: float = 0.0,
    operation_unit: str = "HOTEL",
) -> None:
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO items (name, operation_unit, category, par_level, laundry_unit_cost)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name.strip(),
                unit,
                category.strip(),
                max(par_level, 0),
                max(float(laundry_unit_cost), 0.0),
            ),
        )


def add_category(name: str) -> None:
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Nome da categoria é obrigatório.")
    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO categories (name, active)
            VALUES (?, TRUE)
            """,
            (clean_name,),
        )


def list_categories(active_only: bool = True) -> list[dict[str, Any]]:
    query = "SELECT id, name, active FROM categories"
    params: list[Any] = []
    if active_only:
        query += " WHERE active = TRUE"
    query += " ORDER BY name"

    with get_connection() as conn:
        rows = execute(conn, query, params).fetchall()
    return [dict(row) for row in rows]


def update_item(
    item_id: int,
    name: str,
    category: str,
    par_level: int,
    laundry_unit_cost: float | None = None,
    active: bool = True,
) -> None:
    set_laundry = 0.0 if laundry_unit_cost is None else max(float(laundry_unit_cost), 0.0)
    with get_connection() as conn:
        execute(
            conn,
            """
            UPDATE items
            SET
                name = ?,
                category = ?,
                par_level = ?,
                laundry_unit_cost = ?,
                active = ?
            WHERE id = ?
            """,
            (
                name.strip(),
                category.strip(),
                max(par_level, 0),
                set_laundry,
                bool(active),
                item_id,
            ),
        )


def set_item_active(item_id: int, active: bool) -> None:
    with get_connection() as conn:
        execute(
            conn,
            """
            UPDATE items
            SET active = ?
            WHERE id = ?
            """,
            (bool(active), item_id),
        )


def get_item_by_id(item_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = execute(
            conn,
            """
            SELECT id, name, operation_unit, category, par_level, laundry_unit_cost, active
            FROM items
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()
    return dict(row) if row else None


def list_items(operation_unit: str = "HOTEL", active_only: bool = True) -> list[dict[str, Any]]:
    unit = _normalize_unit(operation_unit)
    query = (
        "SELECT id, name, operation_unit, category, par_level, laundry_unit_cost, active "
        "FROM items WHERE operation_unit = ?"
    )
    params: list[Any] = [unit]
    if active_only:
        query += " AND active = TRUE"
    query += " ORDER BY name"

    with get_connection() as conn:
        rows = execute(conn, query, params).fetchall()
    return [dict(row) for row in rows]


def get_item_theoretical_stock(
    item_id: int,
    as_of_date: date,
    operation_unit: str | None = None,
) -> int:
    with get_connection() as conn:
        if operation_unit is None:
            item = execute(conn, "SELECT operation_unit FROM items WHERE id = ?", (item_id,)).fetchone()
            if item is None:
                return 0
            unit = _normalize_unit(str(item["operation_unit"]))
        else:
            unit = _normalize_unit(operation_unit)

        row = execute(
            conn,
            """
            SELECT
                COALESCE(
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
                    ),
                    0
                ) AS stock_theoretical
            FROM movements
            WHERE item_id = ?
              AND operation_unit = ?
              AND movement_date <= ?
            """,
            (item_id, unit, as_of_date.isoformat()),
        ).fetchone()
    if row is None:
        return 0
    return int(row["stock_theoretical"] or 0)


def transfer_central_to_unit(
    central_item_id: int,
    target_unit: str,
    quantity: int,
    movement_date: date,
    laundry_unit_cost: float = 0.0,
    source_ref: str = "",
    note: str = "",
    revised_from_transfer_id: int | None = None,
) -> dict[str, int]:
    target = _normalize_unit(target_unit)
    if target == "CENTRAL":
        raise ValueError("A unidade de destino deve ser HOTEL ou CLUB.")
    if quantity <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")

    central_item = get_item_by_id(central_item_id)
    if not central_item:
        raise ValueError("Item central não encontrado.")
    if _normalize_unit(central_item["operation_unit"]) != "CENTRAL":
        raise ValueError("Selecione um item do estoque CENTRAL.")

    stock_available = get_item_theoretical_stock(central_item_id, movement_date, operation_unit="CENTRAL")
    if stock_available < quantity:
        raise ValueError(
            f"Estoque central insuficiente. Disponível={stock_available}, solicitado={quantity}."
        )

    with get_connection() as conn:
        target_item = execute(
            conn,
            """
            SELECT id, laundry_unit_cost
            FROM items
            WHERE name = ?
              AND operation_unit = ?
            """,
            (central_item["name"], target),
        ).fetchone()

        if target_item is None:
            execute(
                conn,
                """
                INSERT INTO items (name, operation_unit, category, par_level, laundry_unit_cost, active)
                VALUES (?, ?, ?, ?, ?, TRUE)
                """,
                (
                    central_item["name"],
                    target,
                    central_item["category"],
                    int(central_item["par_level"] or 0),
                    max(float(laundry_unit_cost), 0.0),
                ),
            )
            target_item = execute(
                conn,
                """
                SELECT id, laundry_unit_cost
                FROM items
                WHERE name = ?
                  AND operation_unit = ?
                """,
                (central_item["name"], target),
            ).fetchone()
        elif laundry_unit_cost > 0:
            execute(
                conn,
                """
                UPDATE items
                SET laundry_unit_cost = ?
                WHERE id = ?
                """,
                (max(float(laundry_unit_cost), 0.0), int(target_item["id"])),
            )

        transfer_note = note.strip() or "Transferência do estoque CENTRAL para unidade."
        db_engine = get_db_engine()
        if db_engine == "postgres":
            central_move = execute(
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
                VALUES (?, 'CENTRAL', 'STOCK_OUT', ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    central_item_id,
                    quantity,
                    movement_date.isoformat(),
                    source_ref.strip(),
                    f"{transfer_note} Destino: {target}.",
                ),
            ).fetchone()
            central_movement_id = int(central_move["id"])

            target_move = execute(
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
                VALUES (?, ?, 'STOCK_IN', ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    int(target_item["id"]),
                    target,
                    quantity,
                    movement_date.isoformat(),
                    source_ref.strip(),
                    "Transferência recebida do estoque CENTRAL.",
                ),
            ).fetchone()
            target_movement_id = int(target_move["id"])

            transfer_row = execute(
                conn,
                """
                INSERT INTO transfers (
                    central_item_id,
                    target_item_id,
                    target_unit,
                    quantity,
                    transfer_date,
                    source_ref,
                    note,
                    status,
                    central_movement_id,
                    target_movement_id,
                    revised_from_transfer_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                RETURNING id
                """,
                (
                    central_item_id,
                    int(target_item["id"]),
                    target,
                    quantity,
                    movement_date.isoformat(),
                    source_ref.strip(),
                    transfer_note,
                    central_movement_id,
                    target_movement_id,
                    revised_from_transfer_id,
                ),
            ).fetchone()
            transfer_id = int(transfer_row["id"])
        else:
            central_cursor = execute(
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
                VALUES (?, 'CENTRAL', 'STOCK_OUT', ?, ?, ?, ?)
                """,
                (
                    central_item_id,
                    quantity,
                    movement_date.isoformat(),
                    source_ref.strip(),
                    f"{transfer_note} Destino: {target}.",
                ),
            )
            central_movement_id = int(central_cursor.lastrowid)

            target_cursor = execute(
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
                VALUES (?, ?, 'STOCK_IN', ?, ?, ?, ?)
                """,
                (
                    int(target_item["id"]),
                    target,
                    quantity,
                    movement_date.isoformat(),
                    source_ref.strip(),
                    "Transferência recebida do estoque CENTRAL.",
                ),
            )
            target_movement_id = int(target_cursor.lastrowid)

            transfer_cursor = execute(
                conn,
                """
                INSERT INTO transfers (
                    central_item_id,
                    target_item_id,
                    target_unit,
                    quantity,
                    transfer_date,
                    source_ref,
                    note,
                    status,
                    central_movement_id,
                    target_movement_id,
                    revised_from_transfer_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)
                """,
                (
                    central_item_id,
                    int(target_item["id"]),
                    target,
                    quantity,
                    movement_date.isoformat(),
                    source_ref.strip(),
                    transfer_note,
                    central_movement_id,
                    target_movement_id,
                    revised_from_transfer_id,
                ),
            )
            transfer_id = int(transfer_cursor.lastrowid)

    return {
        "transfer_id": transfer_id,
        "central_item_id": int(central_item_id),
        "target_item_id": int(target_item["id"]),
        "quantity": int(quantity),
    }


def get_transfer_by_id(transfer_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = execute(
            conn,
            """
            SELECT
                t.*,
                ci.name AS central_item_name,
                ti.name AS target_item_name
            FROM transfers t
            JOIN items ci ON ci.id = t.central_item_id
            JOIN items ti ON ti.id = t.target_item_id
            WHERE t.id = ?
            """,
            (transfer_id,),
        ).fetchone()
    return dict(row) if row else None


def list_recent_transfers(limit: int = 100) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT
                t.id,
                t.transfer_date,
                t.target_unit,
                t.quantity,
                t.source_ref,
                t.note,
                t.status,
                t.cancel_reason,
                t.cancelled_at,
                t.created_at,
                ci.name AS central_item_name,
                ti.name AS target_item_name
            FROM transfers t
            JOIN items ci ON ci.id = t.central_item_id
            JOIN items ti ON ti.id = t.target_item_id
            ORDER BY t.transfer_date DESC, t.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def cancel_transfer(transfer_id: int, cancel_reason: str = "") -> None:
    transfer = get_transfer_by_id(transfer_id)
    if not transfer:
        raise ValueError("Transferência não encontrada.")
    if transfer["status"] != "ACTIVE":
        raise ValueError("Apenas transferências ativas podem ser anuladas.")

    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO movements (
                item_id, operation_unit, movement_type, quantity, movement_date, source_ref, note
            )
            VALUES (?, 'CENTRAL', 'STOCK_IN', ?, ?, ?, ?)
            """,
            (
                int(transfer["central_item_id"]),
                int(transfer["quantity"]),
                date.today().isoformat(),
                str(transfer["source_ref"] or "").strip(),
                f"Anulação transferência #{transfer_id}.",
            ),
        )
        execute(
            conn,
            """
            INSERT INTO movements (
                item_id, operation_unit, movement_type, quantity, movement_date, source_ref, note
            )
            VALUES (?, ?, 'STOCK_OUT', ?, ?, ?, ?)
            """,
            (
                int(transfer["target_item_id"]),
                str(transfer["target_unit"]),
                int(transfer["quantity"]),
                date.today().isoformat(),
                str(transfer["source_ref"] or "").strip(),
                f"Anulação transferência #{transfer_id}.",
            ),
        )
        execute(
            conn,
            """
            UPDATE transfers
            SET
                status = 'CANCELLED',
                cancelled_at = CURRENT_TIMESTAMP,
                cancel_reason = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (cancel_reason.strip(), transfer_id),
        )


def edit_transfer(
    transfer_id: int,
    target_unit: str,
    quantity: int,
    transfer_date: date,
    note: str = "",
) -> dict[str, int]:
    original = get_transfer_by_id(transfer_id)
    if not original:
        raise ValueError("Transferência não encontrada.")
    if original["status"] != "ACTIVE":
        raise ValueError("Apenas transferências ativas podem ser editadas.")

    cancel_transfer(transfer_id, cancel_reason="Transferência editada e substituída.")
    return transfer_central_to_unit(
        central_item_id=int(original["central_item_id"]),
        target_unit=target_unit,
        quantity=quantity,
        movement_date=transfer_date,
        laundry_unit_cost=0.0,
        source_ref=str(original["source_ref"] or "").strip(),
        note=note or str(original["note"] or ""),
        revised_from_transfer_id=transfer_id,
    )


def add_movement(
    item_id: int,
    movement_type: str,
    quantity: int,
    movement_date: date,
    operation_unit: str = "HOTEL",
    source_ref: str = "",
    movement_unit_cost: float | None = None,
    movement_total_value: float | None = None,
    note: str = "",
) -> None:
    if movement_type not in MOVEMENT_TYPES:
        raise ValueError(f"Tipo de movimento inválido: {movement_type}")
    if quantity <= 0:
        raise ValueError("Quantidade deve ser maior que zero.")
    unit = _normalize_unit(operation_unit)

    with get_connection() as conn:
        row = execute(
            conn,
            "SELECT id FROM items WHERE id = ? AND operation_unit = ?",
            (item_id, unit),
        ).fetchone()
        if row is None:
            raise ValueError("Item não pertence à unidade selecionada.")

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
                movement_unit_cost,
                movement_total_value,
                note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                unit,
                movement_type,
                quantity,
                movement_date.isoformat(),
                source_ref.strip(),
                movement_unit_cost if movement_unit_cost is None else max(float(movement_unit_cost), 0.0),
                movement_total_value if movement_total_value is None else max(float(movement_total_value), 0.0),
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
                i.laundry_unit_cost,
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
              AND i.operation_unit = ?
            ORDER BY i.name
            """,
            (as_of_date.isoformat(), unit, as_of_date.isoformat(), unit, unit),
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
                m.movement_unit_cost,
                m.movement_total_value,
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


def get_central_stock_report(as_of_date: date) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            WITH stock_pos AS (
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
                    ) AS stock_qty
                FROM movements
                WHERE operation_unit = 'CENTRAL'
                  AND movement_date <= ?
                GROUP BY item_id
            ),
            last_purchase AS (
                SELECT
                    item_id,
                    movement_date AS last_purchase_date,
                    source_ref AS last_invoice,
                    movement_unit_cost AS last_unit_cost,
                    movement_total_value AS last_total_value,
                    note AS last_note
                FROM (
                    SELECT
                        m.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY item_id
                            ORDER BY movement_date DESC, id DESC
                        ) AS rn
                    FROM movements m
                    WHERE m.operation_unit = 'CENTRAL'
                      AND m.movement_type = 'PURCHASE'
                      AND m.movement_date <= ?
                ) x
                WHERE rn = 1
            ),
            last_move AS (
                SELECT
                    item_id,
                    movement_type AS last_movement_type
                FROM (
                    SELECT
                        m.*,
                        ROW_NUMBER() OVER (
                            PARTITION BY item_id
                            ORDER BY movement_date DESC, id DESC
                        ) AS rn
                    FROM movements m
                    WHERE m.operation_unit = 'CENTRAL'
                      AND m.movement_date <= ?
                ) z
                WHERE rn = 1
            )
            SELECT
                i.id AS item_id,
                i.name,
                i.category,
                i.par_level,
                COALESCE(lm.last_movement_type, 'SEM_MOVIMENTO') AS last_movement_type,
                COALESCE(sp.stock_qty, 0) AS stock_qty,
                lp.last_purchase_date,
                lp.last_invoice,
                COALESCE(lp.last_unit_cost, 0) AS last_unit_cost,
                COALESCE(lp.last_total_value, 0) AS last_total_value,
                lp.last_note
            FROM items i
            LEFT JOIN stock_pos sp ON sp.item_id = i.id
            LEFT JOIN last_purchase lp ON lp.item_id = i.id
            LEFT JOIN last_move lm ON lm.item_id = i.id
            WHERE i.operation_unit = 'CENTRAL'
            ORDER BY i.name
            """,
            (as_of_date.isoformat(), as_of_date.isoformat(), as_of_date.isoformat()),
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


def get_laundry_period_item_report(
    start_date: date,
    end_date: date,
    operation_unit: str = "HOTEL",
) -> list[dict[str, Any]]:
    unit = _normalize_unit(operation_unit)
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT
                i.id AS item_id,
                i.name,
                i.laundry_unit_cost,
                m.movement_date,
                SUM(CASE WHEN m.movement_type = 'LAUNDRY_SENT' THEN m.quantity ELSE 0 END) AS billed_qty,
                SUM(CASE WHEN m.movement_type = 'LAUNDRY_REWASH_SENT' THEN m.quantity ELSE 0 END) AS rewash_sent_qty,
                SUM(CASE WHEN m.movement_type = 'LAUNDRY_REWASH_RETURNED' THEN m.quantity ELSE 0 END) AS rewash_returned_qty,
                SUM(CASE WHEN m.movement_type = 'LOSS' THEN m.quantity ELSE 0 END) AS loss_qty
            FROM items i
            LEFT JOIN movements m
                ON m.item_id = i.id
               AND m.operation_unit = ?
               AND m.movement_date BETWEEN ? AND ?
            WHERE i.active = TRUE
              AND i.operation_unit = ?
            GROUP BY i.id, i.name, i.laundry_unit_cost, m.movement_date
            ORDER BY i.name, m.movement_date
            """,
            (unit, start_date.isoformat(), end_date.isoformat(), unit),
        ).fetchall()

    report_map: dict[int, dict[str, Any]] = {}
    for row in rows:
        item_id = int(row["item_id"])
        current = report_map.setdefault(
            item_id,
            {
                "item_id": item_id,
                "name": row["name"],
                "laundry_unit_cost": float(row["laundry_unit_cost"] or 0.0),
                "daily_billed_qty": {},
                "total_billed_qty": 0,
                "total_billed_value": 0.0,
                "rewash_sent_qty": 0,
                "rewash_returned_qty": 0,
                "loss_qty": 0,
            },
        )

        raw_dt = row["movement_date"]
        billed_qty = int(row["billed_qty"] or 0)
        rewash_sent_qty = int(row["rewash_sent_qty"] or 0)
        rewash_returned_qty = int(row["rewash_returned_qty"] or 0)
        loss_qty = int(row["loss_qty"] or 0)

        if raw_dt is not None:
            dt = _to_date(raw_dt)
            current["daily_billed_qty"][dt] = current["daily_billed_qty"].get(dt, 0) + billed_qty

        current["total_billed_qty"] += billed_qty
        current["rewash_sent_qty"] += rewash_sent_qty
        current["rewash_returned_qty"] += rewash_returned_qty
        current["loss_qty"] += loss_qty

    for item in report_map.values():
        item["total_billed_value"] = round(item["total_billed_qty"] * item["laundry_unit_cost"], 2)

    return list(report_map.values())

