import os
from datetime import date, timedelta

from codexiaauditor import database
from codexiaauditor.audit_engine import generate_audit_report
from codexiaauditor.repository import (
    add_item,
    add_movement,
    get_balances,
    get_laundry_billing_summary,
    list_items,
    upsert_inventory_count,
)


def _prepare_tmp_db(tmp_path):
    os.environ["CODEXIAAUDITOR_DB_ENGINE"] = "sqlite"
    os.environ["CODEXIAAUDITOR_SQLITE_PATH"] = str(tmp_path / "test_codexiaauditor.db")
    database.DB_PATH = tmp_path / "test_codexiaauditor.db"
    database.init_db()


def test_audit_detects_discrepancy_and_laundry_delay(tmp_path):
    _prepare_tmp_db(tmp_path)
    today = date.today()

    add_item("Lencol casal", "Roupa de cama", par_level=20)
    item_id = list_items()[0]["id"]

    add_movement(item_id, "PURCHASE", 100, today - timedelta(days=6))
    add_movement(item_id, "LAUNDRY_SENT", 30, today - timedelta(days=5))
    add_movement(item_id, "LAUNDRY_RETURNED", 10, today - timedelta(days=2))
    add_movement(item_id, "IN_USE_ALLOCATED", 15, today - timedelta(days=1))
    add_movement(item_id, "LOSS", 4, today - timedelta(days=1))

    upsert_inventory_count(
        item_id=item_id,
        count_date=today,
        counted_stock=55,
        counted_laundry=14,
        counted_in_use=19,
    )

    report = generate_audit_report(today)

    assert report["overall_risk_score"] > 0
    assert report["items_with_alert"] == 1
    assert any(row["area"] == "lavanderia" for row in report["findings"])
    assert any("Divergência no estoque físico" in row["descricao"] for row in report["findings"])


def test_audit_without_findings_when_balanced(tmp_path):
    _prepare_tmp_db(tmp_path)
    today = date.today()

    add_item("Toalha banho", "Banho", par_level=10)
    item_id = list_items()[0]["id"]

    add_movement(item_id, "PURCHASE", 50, today - timedelta(days=3))
    add_movement(item_id, "IN_USE_ALLOCATED", 12, today - timedelta(days=2))
    add_movement(item_id, "IN_USE_RETURNED", 12, today - timedelta(days=1))
    add_movement(item_id, "LAUNDRY_SENT", 8, today - timedelta(days=1))
    add_movement(item_id, "LAUNDRY_RETURNED", 8, today)

    upsert_inventory_count(
        item_id=item_id,
        count_date=today,
        counted_stock=50,
        counted_laundry=0,
        counted_in_use=0,
    )

    report = generate_audit_report(today)

    assert report["overall_risk_score"] == 0
    assert report["items_with_alert"] == 0
    assert report["findings"] == []


def test_separacao_por_unidade_hotel_e_club(tmp_path):
    _prepare_tmp_db(tmp_path)
    today = date.today()

    add_item("Fronha premium", "Roupa de cama", par_level=10)
    item_id = list_items()[0]["id"]

    add_movement(item_id, "PURCHASE", 40, today, operation_unit="HOTEL")
    add_movement(item_id, "PURCHASE", 15, today, operation_unit="CLUB")

    balance_hotel = get_balances(today, operation_unit="HOTEL")[0]
    balance_club = get_balances(today, operation_unit="CLUB")[0]

    assert int(balance_hotel["stock_theoretical"]) == 40
    assert int(balance_club["stock_theoretical"]) == 15


def test_relavagem_controlada_sem_cobranca(tmp_path):
    _prepare_tmp_db(tmp_path)
    today = date.today()

    add_item("Toalha piscina", "Banho", par_level=10)
    item_id = list_items()[0]["id"]

    add_movement(item_id, "LAUNDRY_SENT", 30, today - timedelta(days=2), operation_unit="CLUB")
    add_movement(item_id, "LAUNDRY_REWASH_SENT", 8, today - timedelta(days=1), operation_unit="CLUB")
    add_movement(item_id, "LAUNDRY_RETURNED", 25, today, operation_unit="CLUB")
    add_movement(item_id, "LAUNDRY_REWASH_RETURNED", 5, today, operation_unit="CLUB")

    summary = get_laundry_billing_summary(days=7, ref_date=today, operation_unit="CLUB")
    assert summary["billed_sent"] == 30
    assert summary["rewash_sent"] == 8
