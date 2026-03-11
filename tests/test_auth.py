import os

from codexiaauditor import database
from codexiaauditor.auth import (
    MASTER_EMAIL,
    MASTER_TEMP_PASSWORD,
    ROLE_ADMIN,
    authenticate_user,
    change_password,
    create_user,
    ensure_master_user,
    get_user_permissions,
    list_users,
)


def _prepare_tmp_db(tmp_path):
    os.environ["CODEXIAAUDITOR_DB_ENGINE"] = "sqlite"
    os.environ["CODEXIAAUDITOR_SQLITE_PATH"] = str(tmp_path / "test_auth.db")
    database.DB_PATH = tmp_path / "test_auth.db"
    database.init_db()


def test_master_user_primeiro_login(tmp_path):
    _prepare_tmp_db(tmp_path)
    modules = ["items", "stock", "users"]
    ensure_master_user(modules)

    user = authenticate_user(MASTER_EMAIL, MASTER_TEMP_PASSWORD)
    assert user is not None
    assert user["role"] == "MASTER"
    assert bool(user["must_change_password"]) is True

    change_password(int(user["id"]), "nova_senha_123")
    user_after = authenticate_user(MASTER_EMAIL, "nova_senha_123")
    assert user_after is not None
    assert bool(user_after["must_change_password"]) is False


def test_create_user_with_permissions(tmp_path):
    _prepare_tmp_db(tmp_path)
    ensure_master_user(["items", "stock", "users", "audit"])

    user_id = create_user(
        email="operador@example.com",
        full_name="Operador Teste",
        role=ROLE_ADMIN,
        password="abc12345",
        must_change_password=True,
        is_active=True,
        module_keys=["stock", "laundry"],
    )
    users = list_users()
    assert any(int(u["id"]) == int(user_id) for u in users)

    perms = get_user_permissions(user_id)
    assert sorted(perms) == ["laundry", "stock"]
