import os
from datetime import date, timedelta

from codexiaauditor import database
from codexiaauditor.audit_engine import generate_audit_report
from codexiaauditor.repository import (
    add_category,
    add_item,
    add_movement,
    cancel_transfer,
    edit_transfer,
    get_central_stock_report,
    get_balances,
    get_laundry_billing_summary,
    get_laundry_period_item_report,
    get_item_theoretical_stock,
    list_recent_transfers,
    list_categories,
    list_items,
    set_item_active,
    transfer_central_to_unit,
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

    add_item("Fronha premium", "Roupa de cama", par_level=10, operation_unit="LA_PLAGE")
    add_item("Fronha premium", "Roupa de cama", par_level=10, operation_unit="CLUB")
    item_hotel_id = list_items(operation_unit="LA_PLAGE")[0]["id"]
    item_club_id = list_items(operation_unit="CLUB")[0]["id"]

    add_movement(item_hotel_id, "PURCHASE", 40, today, operation_unit="LA_PLAGE")
    add_movement(item_club_id, "PURCHASE", 15, today, operation_unit="CLUB")

    balance_hotel = get_balances(today, operation_unit="LA_PLAGE")[0]
    balance_club = get_balances(today, operation_unit="CLUB")[0]

    assert int(balance_hotel["stock_theoretical"]) == 40
    assert int(balance_club["stock_theoretical"]) == 15


def test_relavagem_controlada_sem_cobranca(tmp_path):
    _prepare_tmp_db(tmp_path)
    today = date.today()

    add_item("Toalha piscina", "Banho", par_level=10, operation_unit="CLUB")
    item_id = list_items(operation_unit="CLUB")[0]["id"]

    add_movement(item_id, "LAUNDRY_SENT", 30, today - timedelta(days=2), operation_unit="CLUB")
    add_movement(item_id, "LAUNDRY_REWASH_SENT", 8, today - timedelta(days=1), operation_unit="CLUB")
    add_movement(item_id, "LAUNDRY_RETURNED", 25, today, operation_unit="CLUB")
    add_movement(item_id, "LAUNDRY_REWASH_RETURNED", 5, today, operation_unit="CLUB")

    summary = get_laundry_billing_summary(days=7, ref_date=today, operation_unit="CLUB")
    assert summary["billed_sent"] == 30
    assert summary["rewash_sent"] == 8


def test_apuracao_planilha_por_periodo(tmp_path):
    _prepare_tmp_db(tmp_path)
    base_date = date(2026, 3, 15)

    add_item("Toalha de praia", "Banho", par_level=10, laundry_unit_cost=2.5)
    add_item("Toalha de praia", "Banho", par_level=10, laundry_unit_cost=3.0, operation_unit="CLUB")
    item_id = list_items()[0]["id"]
    item_id_club = list_items(operation_unit="CLUB")[0]["id"]

    add_movement(item_id, "LAUNDRY_SENT", 10, date(2026, 3, 1), operation_unit="HOTEL")
    add_movement(item_id, "LAUNDRY_SENT", 12, date(2026, 3, 2), operation_unit="HOTEL")
    add_movement(item_id, "LAUNDRY_REWASH_SENT", 3, date(2026, 3, 2), operation_unit="HOTEL")
    add_movement(item_id, "LAUNDRY_REWASH_RETURNED", 2, date(2026, 3, 3), operation_unit="HOTEL")
    add_movement(item_id, "LOSS", 1, date(2026, 3, 4), operation_unit="HOTEL")
    add_movement(item_id_club, "LAUNDRY_SENT", 7, date(2026, 3, 5), operation_unit="CLUB")

    report = get_laundry_period_item_report(
        start_date=date(2026, 3, 1),
        end_date=base_date,
        operation_unit="HOTEL",
    )

    assert len(report) == 1
    row = report[0]
    assert row["total_billed_qty"] == 22
    assert row["total_billed_value"] == 55.0
    assert row["rewash_sent_qty"] == 3
    assert row["rewash_returned_qty"] == 2
    assert row["loss_qty"] == 1


def test_fluxo_estoque_central_para_unidades(tmp_path):
    _prepare_tmp_db(tmp_path)
    today = date.today()

    add_item("Toalha de mesa", "Mesa", par_level=0, operation_unit="CENTRAL")
    central_item_id = list_items(operation_unit="CENTRAL")[0]["id"]
    add_movement(central_item_id, "PURCHASE", 200, today, operation_unit="CENTRAL")

    transfer_central_to_unit(
        central_item_id=central_item_id,
        target_unit="CLUB",
        quantity=100,
        movement_date=today,
        laundry_unit_cost=2.5,
    )
    transfer_central_to_unit(
        central_item_id=central_item_id,
        target_unit="HOTEL",
        quantity=50,
        movement_date=today,
        laundry_unit_cost=2.2,
    )

    central_stock = get_item_theoretical_stock(central_item_id, today)
    club_item = list_items(operation_unit="CLUB")[0]
    hotel_item = list_items(operation_unit="HOTEL")[0]

    assert central_stock == 50
    assert int(get_item_theoretical_stock(int(club_item["id"]), today)) == 100
    assert int(get_item_theoretical_stock(int(hotel_item["id"]), today)) == 50
    assert float(club_item["laundry_unit_cost"]) == 2.5
    assert float(hotel_item["laundry_unit_cost"]) == 2.2


def test_saldo_item_filtra_por_unidade(tmp_path):
    _prepare_tmp_db(tmp_path)
    today = date.today()

    add_item("Guardanapo premium", "Mesa", operation_unit="CENTRAL")
    central_item_id = list_items(operation_unit="CENTRAL")[0]["id"]
    add_movement(central_item_id, "PURCHASE", 100, today, operation_unit="CENTRAL")

    from codexiaauditor.database import execute, get_connection

    # Simula dado legado inconsistente (mesmo item_id em outra unidade).
    with get_connection() as conn:
        execute(
            conn,
            """
            INSERT INTO movements (item_id, operation_unit, movement_type, quantity, movement_date, source_ref, note)
            VALUES (?, 'HOTEL', 'STOCK_OUT', 80, ?, '', 'dado legado')
            """,
            (central_item_id, today.isoformat()),
        )

    assert get_item_theoretical_stock(central_item_id, today, operation_unit="CENTRAL") == 100


def test_categoria_e_ativacao_de_item(tmp_path):
    _prepare_tmp_db(tmp_path)
    add_category("Roupa de Cama")
    categories = list_categories()
    assert any(cat["name"] == "Roupa de Cama" for cat in categories)

    add_item("Lencol solteiro", "Roupa de Cama", operation_unit="CENTRAL")
    item = list_items(operation_unit="CENTRAL")[0]
    set_item_active(int(item["id"]), False)

    active_items = list_items(operation_unit="CENTRAL", active_only=True)
    assert all(int(x["id"]) != int(item["id"]) for x in active_items)


def test_relatorio_estoque_central_com_dados_compra(tmp_path):
    _prepare_tmp_db(tmp_path)
    ref = date(2026, 3, 10)

    add_item("Toalha de mesa", "Mesa", operation_unit="CENTRAL")
    item_id = list_items(operation_unit="CENTRAL")[0]["id"]
    add_movement(
        item_id=item_id,
        movement_type="PURCHASE",
        quantity=200,
        movement_date=ref,
        operation_unit="CENTRAL",
        source_ref="NF-999",
        movement_unit_cost=5.5,
        movement_total_value=1100.0,
        note="Compra fornecedor A",
    )
    add_movement(
        item_id=item_id,
        movement_type="STOCK_OUT",
        quantity=50,
        movement_date=ref,
        operation_unit="CENTRAL",
        note="Transferência para unidades",
    )

    report = get_central_stock_report(ref)
    row = report[0]
    assert int(row["stock_qty"]) == 150
    assert str(row["last_invoice"]) == "NF-999"
    assert float(row["last_unit_cost"]) == 5.5
    assert float(row["last_total_value"]) == 1100.0


def test_transferencia_com_historico_edicao_e_anulacao(tmp_path):
    _prepare_tmp_db(tmp_path)
    ref = date(2026, 3, 10)

    add_item("Guardanapo", "Mesa", operation_unit="CENTRAL")
    central_item_id = list_items(operation_unit="CENTRAL")[0]["id"]
    add_movement(central_item_id, "PURCHASE", 100, ref, operation_unit="CENTRAL")

    created = transfer_central_to_unit(
        central_item_id=central_item_id,
        target_unit="HOTEL",
        quantity=20,
        movement_date=ref,
        note="Primeira transferência",
    )
    transfer_id = int(created["transfer_id"])

    edited = edit_transfer(
        transfer_id=transfer_id,
        target_unit="CLUB",
        quantity=10,
        transfer_date=ref,
        note="Transferência editada",
    )
    new_transfer_id = int(edited["transfer_id"])

    cancel_transfer(new_transfer_id, cancel_reason="Teste anulação")
    history = list_recent_transfers(limit=5)

    assert any(int(row["id"]) == transfer_id and row["status"] == "CANCELLED" for row in history)
    assert any(int(row["id"]) == new_transfer_id and row["status"] == "CANCELLED" for row in history)
