import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "codexia.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT DEFAULT 'hotel'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT DEFAULT '',
            par_level INTEGER DEFAULT 0,
            purchase_price REAL DEFAULT 0.0,
            laundry_unit_cost REAL DEFAULT 0.0,
            active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # Migração: adicionar coluna purchase_price se não existir (banco legado)
    try:
        c.execute("ALTER TABLE items ADD COLUMN purchase_price REAL DEFAULT 0.0")
        conn.commit()
    except Exception:
        pass

    # Entradas no estoque central (compras, doações, ajustes)
    c.execute("""
        CREATE TABLE IF NOT EXISTS stock_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            entry_date TEXT NOT NULL,
            reference TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    """)

    # Transferências do Central → Unidade
    c.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            to_unit TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            laundry_cost REAL DEFAULT 0.0,
            transfer_date TEXT NOT NULL,
            reference TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    """)

    # Lançamentos de lavanderia (por unidade)
    c.execute("""
        CREATE TABLE IF NOT EXISTS laundry_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            operation_unit TEXT NOT NULL,
            quantity_sent INTEGER DEFAULT 0,
            quantity_returned INTEGER DEFAULT 0,
            laundry_name TEXT DEFAULT '',
            send_date TEXT NOT NULL,
            return_date TEXT DEFAULT '',
            status TEXT DEFAULT 'pendente',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    """)

    # Contagem física
    c.execute("""
        CREATE TABLE IF NOT EXISTS physical_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            operation_unit TEXT NOT NULL,
            count_date TEXT NOT NULL,
            counted_quantity INTEGER NOT NULL,
            expected_quantity INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    """)

    # Relatórios de auditoria
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            operation_unit TEXT DEFAULT 'GERAL',
            period_start TEXT DEFAULT '',
            period_end TEXT DEFAULT '',
            report_data TEXT DEFAULT '{}',
            ai_analysis TEXT DEFAULT '',
            total_purchased INTEGER DEFAULT 0,
            total_in_use INTEGER DEFAULT 0,
            total_laundry INTEGER DEFAULT 0,
            total_missing INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


# ── Items ──────────────────────────────────────────────────────────────────────

def get_items(active_only=True):
    conn = get_conn()
    if active_only:
        rows = conn.execute("SELECT * FROM items WHERE active=1 ORDER BY name").fetchall()
    else:
        rows = conn.execute("SELECT * FROM items ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_item(item_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def upsert_item(name, category, par_level, purchase_price, laundry_unit_cost, active=1, item_id=None):
    conn = get_conn()
    if item_id:
        conn.execute("""
            UPDATE items SET name=?, category=?, par_level=?, purchase_price=?, laundry_unit_cost=?, active=?
            WHERE id=?
        """, (name, category, par_level, purchase_price, laundry_unit_cost, active, item_id))
    else:
        conn.execute("""
            INSERT INTO items (name, category, par_level, purchase_price, laundry_unit_cost, active)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, category, par_level, purchase_price, laundry_unit_cost, active))
    conn.commit()
    conn.close()


# ── Stock Central ──────────────────────────────────────────────────────────────

def add_stock_entry(item_id, quantity, entry_date, reference="", notes=""):
    """Registra entrada de estoque no central."""
    conn = get_conn()
    conn.execute("""
        INSERT INTO stock_entries (item_id, quantity, entry_date, reference, notes)
        VALUES (?, ?, ?, ?, ?)
    """, (item_id, quantity, entry_date, reference, notes))
    conn.commit()
    conn.close()


def get_central_balance(item_id):
    """Retorna saldo disponível no estoque central = entradas - transferências."""
    conn = get_conn()

    entradas = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM stock_entries WHERE item_id=?",
        (item_id,)
    ).fetchone()[0]

    saidas = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM transfers WHERE item_id=?",
        (item_id,)
    ).fetchone()[0]

    conn.close()
    return max(0, entradas - saidas)


def get_all_central_balances():
    """Retorna saldo de todos os itens no central."""
    conn = get_conn()
    items = conn.execute("SELECT * FROM items WHERE active=1 ORDER BY name").fetchall()

    result = []
    for item in items:
        iid = item["id"]
        entradas = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM stock_entries WHERE item_id=?", (iid,)
        ).fetchone()[0]
        saidas = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM transfers WHERE item_id=?", (iid,)
        ).fetchone()[0]
        result.append({
            **dict(item),
            "central_balance": max(0, entradas - saidas),
            "total_received": entradas,
            "total_transferred_out": saidas,
        })

    conn.close()
    return result


# ── Transfers ─────────────────────────────────────────────────────────────────

def transfer_to_unit(item_id, to_unit, quantity, laundry_cost, transfer_date, reference="", notes=""):
    """
    Transfere itens do Central para uma unidade.
    Verifica saldo disponível antes de transferir.
    Retorna (sucesso, mensagem).
    """
    available = get_central_balance(item_id)

    # BUG CORRIGIDO: quantity deve ser int e vem diretamente do formulário
    quantity = int(quantity)

    if quantity <= 0:
        return False, "Quantidade deve ser maior que zero."

    if available < quantity:
        return False, f"Estoque central insuficiente. Disponível={available}, solicitado={quantity}"

    conn = get_conn()
    conn.execute("""
        INSERT INTO transfers (item_id, to_unit, quantity, laundry_cost, transfer_date, reference, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (item_id, to_unit, quantity, laundry_cost, transfer_date, reference, notes))
    conn.commit()
    conn.close()
    return True, f"Transferência de {quantity} unidade(s) para {to_unit} realizada com sucesso!"


def get_transfers(item_id=None, to_unit=None):
    conn = get_conn()
    q = """
        SELECT t.*, i.name as item_name, i.category
        FROM transfers t JOIN items i ON t.item_id = i.id
        WHERE 1=1
    """
    params = []
    if item_id:
        q += " AND t.item_id=?"
        params.append(item_id)
    if to_unit:
        q += " AND t.to_unit=?"
        params.append(to_unit)
    q += " ORDER BY t.transfer_date DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unit_balance(item_id, unit):
    """Saldo de um item em uma unidade = transferências recebidas - lavanderia pendente."""
    conn = get_conn()

    recebido = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM transfers WHERE item_id=? AND to_unit=?",
        (item_id, unit)
    ).fetchone()[0]

    laundry_out = conn.execute(
        "SELECT COALESCE(SUM(quantity_sent - quantity_returned), 0) FROM laundry_records WHERE item_id=? AND operation_unit=? AND status IN ('pendente','parcial')",
        (item_id, unit)
    ).fetchone()[0]

    conn.close()
    return max(0, recebido - laundry_out)


# ── Laundry ────────────────────────────────────────────────────────────────────

def add_laundry_record(item_id, operation_unit, quantity_sent, laundry_name, send_date, notes=""):
    conn = get_conn()
    conn.execute("""
        INSERT INTO laundry_records (item_id, operation_unit, quantity_sent, laundry_name, send_date, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (item_id, operation_unit, quantity_sent, laundry_name, send_date, notes))
    conn.commit()
    conn.close()


def register_laundry_return(record_id, quantity_returned, return_date):
    conn = get_conn()
    rec = conn.execute("SELECT * FROM laundry_records WHERE id=?", (record_id,)).fetchone()
    if not rec:
        conn.close()
        return False, "Registro não encontrado"

    total_returned = rec["quantity_returned"] + quantity_returned
    status = "completo" if total_returned >= rec["quantity_sent"] else "parcial"

    conn.execute("""
        UPDATE laundry_records
        SET quantity_returned=?, return_date=?, status=?
        WHERE id=?
    """, (total_returned, return_date, status, record_id))
    conn.commit()
    conn.close()
    return True, f"Retorno de {quantity_returned} unidade(s) registrado."


def get_laundry_records(operation_unit=None, status=None):
    conn = get_conn()
    q = """
        SELECT l.*, i.name as item_name, i.category
        FROM laundry_records l JOIN items i ON l.item_id = i.id
        WHERE 1=1
    """
    params = []
    if operation_unit:
        q += " AND l.operation_unit=?"
        params.append(operation_unit)
    if status:
        q += " AND l.status=?"
        params.append(status)
    q += " ORDER BY l.send_date DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Physical Count ─────────────────────────────────────────────────────────────

def add_physical_count(item_id, operation_unit, count_date, counted_quantity, notes=""):
    conn = get_conn()
    expected = get_unit_balance(item_id, operation_unit) if operation_unit != "CENTRAL" else get_central_balance(item_id)
    conn.execute("""
        INSERT INTO physical_counts (item_id, operation_unit, count_date, counted_quantity, expected_quantity, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (item_id, operation_unit, count_date, counted_quantity, expected, notes))
    conn.commit()
    conn.close()


def get_physical_counts(operation_unit=None):
    conn = get_conn()
    q = """
        SELECT p.*, i.name as item_name, i.category
        FROM physical_counts p JOIN items i ON p.item_id = i.id
        WHERE 1=1
    """
    params = []
    if operation_unit:
        q += " AND p.operation_unit=?"
        params.append(operation_unit)
    q += " ORDER BY p.count_date DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Audit ──────────────────────────────────────────────────────────────────────

def get_audit_data(operation_unit=None):
    """Coleta dados para auditoria."""
    conn = get_conn()
    items = conn.execute("SELECT * FROM items WHERE active=1 ORDER BY name").fetchall()
    result = []

    for item in items:
        iid = item["id"]

        total_received = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM stock_entries WHERE item_id=?", (iid,)
        ).fetchone()[0]

        transferred_to_unit = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM transfers WHERE item_id=?" +
            (" AND to_unit=?" if operation_unit else ""),
            (iid, operation_unit) if operation_unit else (iid,)
        ).fetchone()[0]

        central_balance = get_central_balance(iid)

        laundry_pending = conn.execute(
            "SELECT COALESCE(SUM(quantity_sent - quantity_returned), 0) FROM laundry_records WHERE item_id=? AND status IN ('pendente','parcial')" +
            (" AND operation_unit=?" if operation_unit else ""),
            (iid, operation_unit) if operation_unit else (iid,)
        ).fetchone()[0]

        last_count = conn.execute(
            "SELECT counted_quantity, count_date FROM physical_counts WHERE item_id=?" +
            (" AND operation_unit=?" if operation_unit else "") +
            " ORDER BY count_date DESC LIMIT 1",
            (iid, operation_unit) if operation_unit else (iid,)
        ).fetchone()

        in_use = transferred_to_unit - laundry_pending if operation_unit else max(0, transferred_to_unit - central_balance)
        total_accounted = central_balance + (transferred_to_unit if operation_unit else 0) + laundry_pending
        shortfall = max(0, total_received - (central_balance + transferred_to_unit + laundry_pending)) if not operation_unit else max(0, transferred_to_unit - (in_use + laundry_pending))

        result.append({
            "id": iid,
            "name": item["name"],
            "category": item["category"],
            "par_level": item["par_level"],
            "total_received": total_received,
            "central_balance": central_balance,
            "transferred_to_units": transferred_to_unit,
            "laundry_pending": laundry_pending,
            "in_use": in_use,
            "shortfall": shortfall,
            "last_count_qty": last_count["counted_quantity"] if last_count else None,
            "last_count_date": last_count["count_date"] if last_count else None,
        })

    conn.close()
    return result


def save_audit_report(title, operation_unit, report_data_json, ai_analysis, totals):
    conn = get_conn()
    conn.execute("""
        INSERT INTO audit_reports (title, operation_unit, report_data, ai_analysis,
            total_purchased, total_in_use, total_laundry, total_missing)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, operation_unit, report_data_json, ai_analysis,
          totals.get("total_received", 0),
          totals.get("in_use", 0),
          totals.get("laundry_pending", 0),
          totals.get("shortfall", 0)))
    conn.commit()
    last_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return last_id


def get_audit_reports():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM audit_reports ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_units():
    conn = get_conn()
    rows = conn.execute("SELECT name FROM units ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]


def add_unit(name, utype="hotel"):
    conn = get_conn()
    try:
        conn.execute("INSERT INTO units (name, type) VALUES (?, ?)", (name, utype))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()


def delete_item(item_id):
    conn = get_conn()
    conn.execute("UPDATE items SET active=0 WHERE id=?", (item_id,))
    conn.commit()
    conn.close()


def delete_stock_entry(entry_id):
    conn = get_conn()
    conn.execute("DELETE FROM stock_entries WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()


def delete_transfer(transfer_id):
    conn = get_conn()
    conn.execute("DELETE FROM transfers WHERE id=?", (transfer_id,))
    conn.commit()
    conn.close()


def delete_laundry(record_id):
    conn = get_conn()
    conn.execute("DELETE FROM laundry_records WHERE id=?", (record_id,))
    conn.commit()
    conn.close()


def get_stock_entries(item_id=None):
    conn = get_conn()
    q = """
        SELECT s.*, i.name as item_name
        FROM stock_entries s JOIN items i ON s.item_id = i.id
        WHERE 1=1
    """
    params = []
    if item_id:
        q += " AND s.item_id=?"
        params.append(item_id)
    q += " ORDER BY s.entry_date DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
