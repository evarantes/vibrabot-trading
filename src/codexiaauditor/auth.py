from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from .database import execute, get_connection

MASTER_EMAIL = "evarantes2@gmail.com"
MASTER_NAME = "Administrador Master"
MASTER_TEMP_PASSWORD = "123456"

ROLE_MASTER = "MASTER"
ROLE_ADMIN = "ADMIN"
ROLE_USER = "USER"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def hash_password(password: str, iterations: int = 200_000) -> str:
    if not password:
        raise ValueError("Senha não pode ser vazia.")
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${pwd_hash.hex()}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iter_str, salt_hex, hash_hex = encoded_hash.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iter_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(computed, expected)
    except Exception:  # noqa: BLE001
        return False


def ensure_master_user(all_module_keys: list[str]) -> None:
    email = normalize_email(MASTER_EMAIL)
    with get_connection() as conn:
        row = execute(
            conn,
            """
            SELECT id FROM users WHERE email = ?
            """,
            (email,),
        ).fetchone()
        if row is None:
            cursor = execute(
                conn,
                """
                INSERT INTO users (
                    email, full_name, role, password_hash, must_change_password, is_active
                )
                VALUES (?, ?, ?, ?, TRUE, TRUE)
                """,
                (
                    email,
                    MASTER_NAME,
                    ROLE_MASTER,
                    hash_password(MASTER_TEMP_PASSWORD),
                ),
            )
            master_id = int(cursor.lastrowid) if hasattr(cursor, "lastrowid") else None
            if master_id is None:
                ref = execute(conn, "SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                master_id = int(ref["id"])
        else:
            master_id = int(row["id"])
            execute(
                conn,
                """
                UPDATE users
                SET role = ?, is_active = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (ROLE_MASTER, master_id),
            )
    set_user_permissions(master_id, all_module_keys)


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    norm_email = normalize_email(email)
    with get_connection() as conn:
        row = execute(
            conn,
            """
            SELECT id, email, full_name, role, password_hash, must_change_password, is_active
            FROM users
            WHERE email = ?
            """,
            (norm_email,),
        ).fetchone()
    if row is None:
        return None
    user = dict(row)
    if not bool(user["is_active"]):
        return None
    if not verify_password(password, str(user["password_hash"])):
        return None
    user.pop("password_hash", None)
    return user


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = execute(
            conn,
            """
            SELECT id, email, full_name, role, must_change_password, is_active, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT id, email, full_name, role, must_change_password, is_active, created_at, updated_at
            FROM users
            ORDER BY role DESC, full_name, email
            """,
        ).fetchall()
    return [dict(row) for row in rows]


def create_user(
    email: str,
    full_name: str,
    role: str,
    password: str,
    must_change_password: bool,
    is_active: bool,
    module_keys: list[str],
) -> int:
    norm_email = normalize_email(email)
    if role not in {ROLE_ADMIN, ROLE_USER, ROLE_MASTER}:
        raise ValueError("Perfil inválido.")
    with get_connection() as conn:
        existing = execute(conn, "SELECT id FROM users WHERE email = ?", (norm_email,)).fetchone()
        if existing is not None:
            raise ValueError("Já existe usuário com este e-mail.")
        cursor = execute(
            conn,
            """
            INSERT INTO users (
                email, full_name, role, password_hash, must_change_password, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                norm_email,
                (full_name or "").strip(),
                role,
                hash_password(password),
                bool(must_change_password),
                bool(is_active),
            ),
        )
        user_id = int(cursor.lastrowid) if hasattr(cursor, "lastrowid") else None
        if user_id is None:
            row = execute(conn, "SELECT id FROM users WHERE email = ?", (norm_email,)).fetchone()
            user_id = int(row["id"])
    set_user_permissions(user_id, module_keys)
    return user_id


def update_user(
    user_id: int,
    full_name: str,
    role: str,
    is_active: bool,
    must_change_password: bool,
    module_keys: list[str],
    new_password: str = "",
) -> None:
    if role not in {ROLE_MASTER, ROLE_ADMIN, ROLE_USER}:
        raise ValueError("Perfil inválido.")
    with get_connection() as conn:
        execute(
            conn,
            """
            UPDATE users
            SET
                full_name = ?,
                role = ?,
                is_active = ?,
                must_change_password = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                (full_name or "").strip(),
                role,
                bool(is_active),
                bool(must_change_password),
                user_id,
            ),
        )
        if (new_password or "").strip():
            execute(
                conn,
                """
                UPDATE users
                SET password_hash = ?, must_change_password = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (hash_password(new_password.strip()), user_id),
            )
    set_user_permissions(user_id, module_keys)


def change_password(user_id: int, new_password: str) -> None:
    clean_password = (new_password or "").strip()
    if len(clean_password) < 6:
        raise ValueError("A senha deve ter ao menos 6 caracteres.")
    with get_connection() as conn:
        execute(
            conn,
            """
            UPDATE users
            SET password_hash = ?, must_change_password = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (hash_password(clean_password), user_id),
        )


def set_user_permissions(user_id: int, module_keys: list[str]) -> None:
    unique_keys = sorted(set((x or "").strip() for x in module_keys if (x or "").strip()))
    with get_connection() as conn:
        execute(conn, "DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        for module_key in unique_keys:
            execute(
                conn,
                """
                INSERT INTO user_permissions (user_id, module_key, allowed)
                VALUES (?, ?, TRUE)
                """,
                (user_id, module_key),
            )


def get_user_permissions(user_id: int) -> list[str]:
    user = get_user_by_id(user_id)
    if not user:
        return []
    if user["role"] == ROLE_MASTER:
        with get_connection() as conn:
            rows = execute(
                conn,
                """
                SELECT DISTINCT module_key
                FROM user_permissions
                ORDER BY module_key
                """,
            ).fetchall()
        return [str(row["module_key"]) for row in rows]

    with get_connection() as conn:
        rows = execute(
            conn,
            """
            SELECT module_key
            FROM user_permissions
            WHERE user_id = ? AND allowed = TRUE
            ORDER BY module_key
            """,
            (user_id,),
        ).fetchall()
    return [str(row["module_key"]) for row in rows]
