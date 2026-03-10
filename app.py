from __future__ import annotations

from calendar import monthrange
import sys
from datetime import date, timedelta
from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from codexiaauditor.audit_engine import generate_audit_report
from codexiaauditor.database import init_db
from codexiaauditor.invoice_parser import (
    parse_access_key_metadata,
    parse_emission_date_to_date,
    parse_invoice_file,
)
from codexiaauditor.repository import (
    add_category,
    add_item,
    add_movement,
    get_central_stock_report,
    get_balances,
    get_daily_movement_totals,
    get_item_theoretical_stock,
    get_laundry_billing_summary,
    get_laundry_period_item_report,
    list_categories,
    list_items,
    list_recent_movements,
    set_item_active,
    transfer_central_to_unit,
    update_item,
    upsert_inventory_count,
)

st.set_page_config(page_title="CODEXIAAUDITOR", layout="wide")
init_db()

MOVEMENT_LABELS = {
    "PURCHASE": "Compra de enxoval",
    "STOCK_IN": "Ajuste de entrada no estoque central",
    "STOCK_OUT": "Ajuste de saída no estoque central",
    "LAUNDRY_SENT": "Enviado para lavanderia (cobrado)",
    "LAUNDRY_RETURNED": "Retorno da lavanderia (cobrado)",
    "LAUNDRY_REWASH_SENT": "Relavagem: reenviado sem cobrança",
    "LAUNDRY_REWASH_RETURNED": "Relavagem: retorno sem cobrança",
    "IN_USE_ALLOCATED": "Transferido para estoque de uso",
    "IN_USE_RETURNED": "Retorno de uso para estoque central",
    "LOSS": "Perda / baixa por avaria ou extravio",
}
LABEL_TO_MOVEMENT = {v: k for k, v in MOVEMENT_LABELS.items()}

LAUNDRY_LABELS = {
    "Enviado para lavanderia (cobrado)": "LAUNDRY_SENT",
    "Retorno da lavanderia (cobrado)": "LAUNDRY_RETURNED",
    "Relavagem: reenviado sem cobrança": "LAUNDRY_REWASH_SENT",
    "Relavagem: retorno sem cobrança": "LAUNDRY_REWASH_RETURNED",
}
CENTRAL_STOCK_LABELS = {
    "Compra de enxoval": "PURCHASE",
    "Ajuste de entrada no estoque central": "STOCK_IN",
    "Ajuste de saída no estoque central": "STOCK_OUT",
    "Perda / baixa por avaria ou extravio": "LOSS",
}
UNIT_STOCK_LABELS = {
    "Ajuste de entrada no estoque da unidade": "STOCK_IN",
    "Ajuste de saída no estoque da unidade": "STOCK_OUT",
    "Transferir do estoque central para estoque de uso": "IN_USE_ALLOCATED",
    "Retornar do estoque de uso para estoque central": "IN_USE_RETURNED",
    "Perda / baixa por avaria ou extravio": "LOSS",
}


UNIT_OPTIONS = {"CENTRAL": "Estoque Central", "HOTEL": "Hotel", "CLUB": "Club"}


def _items_map(operation_unit: str) -> dict[str, int]:
    return {row["name"]: int(row["id"]) for row in list_items(operation_unit=operation_unit)}


def _period_bounds(period_mode: str, reference_date: date, custom_start: date, custom_end: date) -> tuple[date, date]:
    if period_mode == "Quinzenal":
        if reference_date.day <= 15:
            start = reference_date.replace(day=1)
            end = reference_date.replace(day=15)
        else:
            start = reference_date.replace(day=16)
            end = reference_date.replace(day=monthrange(reference_date.year, reference_date.month)[1])
        return start, end

    if period_mode == "Mensal":
        start = reference_date.replace(day=1)
        end = reference_date.replace(day=monthrange(reference_date.year, reference_date.month)[1])
        return start, end

    start = min(custom_start, custom_end)
    end = max(custom_start, custom_end)
    return start, end


def _norm_text(value: str) -> str:
    base = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", base).strip().upper()


st.sidebar.title("Menu")
selected_unit = st.sidebar.selectbox(
    "Unidade para auditoria",
    options=list(UNIT_OPTIONS.keys()),
    format_func=lambda x: UNIT_OPTIONS[x],
)
as_of_date = st.sidebar.date_input("Dados de referência de auditoria", value=date.today())
menu = st.sidebar.radio(
    "Módulos",
    options=[
        "Cadastro de Itens (Central)",
        "Estoque Central e de Uso",
        "Transferir Central -> Unidade",
        "Lançamentos Lavanderia",
        "Apuração Lavanderia (Planilha)",
        "Contagem Física",
        "Painel de Controle",
        "Auditoria IA",
    ],
)
st.sidebar.info("Dica: registre movimentos diariamente e faça contagem física no fechamento.")

st.title("AUDITOR CODEXIA")
st.caption(
    f"Unidade selecionada: **{UNIT_OPTIONS[selected_unit]}** | "
    "Auditoria inteligente de enxoval (compras, estoque, lavanderia e uso diário)"
)

if menu == "Cadastro de Itens (Central)":
    st.subheader("Cadastro mestre de itens (Estoque Central)")
    if selected_unit != "CENTRAL":
        st.info("O cadastro mestre é no estoque CENTRAL. A unidade selecionada no menu lateral não altera este módulo.")

    with st.popover("Criar categoria"):
        with st.form("form-create-category", clear_on_submit=True):
            new_category_name = st.text_input("Nome da categoria", placeholder="Ex: Roupa de Banho")
            save_category = st.form_submit_button("Salvar categoria")
            if save_category:
                try:
                    add_category(new_category_name)
                    st.success("Categoria criada.")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Não foi possível criar categoria: {exc}")

    categories = list_categories(active_only=True)
    category_names = [str(row["name"]) for row in categories]
    if not category_names:
        st.warning("Nenhuma categoria cadastrada. Crie ao menos uma categoria para cadastrar itens.")
    else:
        with st.form("form-item", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("Nome do item", placeholder="Ex: Lençol 180 fios")
            category = col2.selectbox("Categoria", options=category_names)
            par_level = col3.number_input("Nível mínimo (reserva)", min_value=0, step=1, value=0)
            submitted = st.form_submit_button("Salvar item")
            if submitted:
                if not name.strip():
                    st.error("Informe o nome do item.")
                else:
                    try:
                        add_item(
                            name=name,
                            category=category,
                            par_level=int(par_level),
                            laundry_unit_cost=0.0,
                            operation_unit="CENTRAL",
                        )
                        st.success("Item cadastrado com sucesso.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Não foi possível cadastrar: {exc}")

    items_df = pd.DataFrame(list_items(operation_unit="CENTRAL", active_only=False))
    if items_df.empty:
        st.warning("Nenhum item cadastrado ainda.")
    else:
        select_labels = [f"{int(row['id'])} - {row['name']}" for _, row in items_df.iterrows()]
        select_map = {label: int(label.split(" - ")[0]) for label in select_labels}

        a1, a2, a3, a4 = st.columns(4)
        selected_label = a1.selectbox("Item para ação", options=select_labels)
        selected_item_id = select_map[selected_label]

        if a2.button("Editar item"):
            st.session_state["central_edit_item_id"] = selected_item_id
        if a3.button("Ativar item"):
            set_item_active(selected_item_id, True)
            st.success("Item ativado.")
            st.rerun()
        if a4.button("Desativar item"):
            set_item_active(selected_item_id, False)
            st.success("Item desativado.")
            st.rerun()

        edit_item_id = st.session_state.get("central_edit_item_id")
        if edit_item_id is not None:
            edit_row = items_df[items_df["id"] == edit_item_id]
            if not edit_row.empty:
                current = edit_row.iloc[0]
                edit_categories = category_names.copy()
                current_category = str(current["category"])
                if current_category not in edit_categories:
                    edit_categories.append(current_category)

                with st.form("form-edit-item"):
                    st.markdown("**Editar item selecionado**")
                    e1, e2, e3, e4 = st.columns(4)
                    new_name = e1.text_input("Nome", value=str(current["name"]))
                    default_idx = edit_categories.index(current_category)
                    new_category = e2.selectbox("Categoria", options=edit_categories, index=default_idx)
                    new_par_level = e3.number_input(
                        "Nível mínimo (reserva)",
                        min_value=0,
                        step=1,
                        value=int(current["par_level"]),
                    )
                    new_active = e4.checkbox("Ativo", value=bool(current["active"]))
                    save_edit = st.form_submit_button("Salvar edição")
                    if save_edit:
                        try:
                            update_item(
                                item_id=int(current["id"]),
                                name=new_name,
                                category=new_category,
                                par_level=int(new_par_level),
                                laundry_unit_cost=float(current["laundry_unit_cost"] or 0.0),
                                active=bool(new_active),
                            )
                            st.success("Item atualizado com sucesso.")
                            st.session_state.pop("central_edit_item_id", None)
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Falha ao editar item: {exc}")

        st.dataframe(
            items_df[
                ["id", "name", "category", "par_level", "active"]
            ].rename(
                columns={
                    "id": "id",
                    "name": "item",
                    "category": "categoria",
                    "par_level": "nivel_minimo",
                    "active": "ativo",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

elif menu == "Transferir Central -> Unidade":
    st.subheader("Transferência do estoque CENTRAL para HOTEL/CLUB")
    central_items = pd.DataFrame(list_items(operation_unit="CENTRAL", active_only=True))
    if central_items.empty:
        st.warning("Cadastre itens no estoque CENTRAL antes de transferir.")
    else:
        saldo_base_date = st.date_input(
            "Data-base do saldo central",
            value=date.today(),
            help="Os saldos exibidos para transferência usam esta data-base.",
            key="transfer_saldo_base_date",
        )
        transfer_options = []
        transfer_map: dict[str, int] = {}
        for _, row in central_items.iterrows():
            stock = get_item_theoretical_stock(
                int(row["id"]),
                saldo_base_date,
                operation_unit="CENTRAL",
            )
            label = f"{row['name']} (saldo central em {saldo_base_date.strftime('%d/%m/%Y')}: {stock})"
            transfer_options.append(label)
            transfer_map[label] = int(row["id"])

        with st.form("form-transfer-central", clear_on_submit=True):
            t1, t2, t3, t4 = st.columns(4)
            selected_label = t1.selectbox("Item do CENTRAL", options=transfer_options)
            target_unit = t2.selectbox("Destino", options=["HOTEL", "CLUB"])
            qty = t3.number_input("Quantidade a transferir", min_value=1, step=1, value=1)
            transfer_date = t4.date_input("Data da transferência", value=saldo_base_date)
            x1, x2, x3 = st.columns(3)
            unit_laundry_cost = x1.number_input(
                "Valor da lavagem no destino (R$)",
                min_value=0.0,
                step=0.1,
                value=0.0,
                help="Se o item já existir na unidade e informar valor > 0, atualiza o valor.",
            )
            source_ref = x2.text_input("Referência", placeholder="NF, ordem interna")
            note = x3.text_input("Observação")
            transfer_submitted = st.form_submit_button("Transferir")
            if transfer_submitted:
                try:
                    central_item_id = transfer_map[selected_label]
                    result = transfer_central_to_unit(
                        central_item_id=central_item_id,
                        target_unit=target_unit,
                        quantity=int(qty),
                        movement_date=transfer_date,
                        laundry_unit_cost=float(unit_laundry_cost),
                        source_ref=source_ref,
                        note=note,
                    )
                    st.success(
                        f"Transferência concluída. Item CENTRAL #{result['central_item_id']} -> "
                        f"item {target_unit} #{result['target_item_id']} ({result['quantity']} un.)."
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha na transferência: {exc}")

elif menu == "Lançamentos Lavanderia":
    st.subheader(f"Lançamentos da lavanderia - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.warning("Lavanderia deve ser lançada em HOTEL ou CLUB. O CENTRAL não envia para lavanderia.")
        st.stop()
    st.info(
        "Use os tipos de relavagem quando o lote retorna mal lavado. "
        "Essas peças voltam para a lavanderia sem nova cobrança."
    )
    item_map = _items_map(selected_unit)
    if not item_map:
        st.warning("Cadastre pelo menos um item antes de lançar movimentações da lavanderia.")
    else:
        with st.form("form-laundry", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            movement_date = c1.date_input("Data do movimento", value=date.today())
            item_name = c2.selectbox("Item", options=sorted(item_map.keys()))
            movement_label = c3.selectbox("Tipo de movimento", options=list(LAUNDRY_LABELS.keys()))
            c4, c5, c6 = st.columns(3)
            quantity = c4.number_input("Quantidade", min_value=1, step=1, value=1)
            source_ref = c5.text_input("Referência", placeholder="NF, ordem interna, romaneio")
            note = c6.text_input("Observação")
            move_submitted = st.form_submit_button("Salvar movimento da lavanderia")
            if move_submitted:
                try:
                    add_movement(
                        item_id=item_map[item_name],
                        movement_type=LAUNDRY_LABELS[movement_label],
                        quantity=int(quantity),
                        movement_date=movement_date,
                        operation_unit=selected_unit,
                        source_ref=source_ref,
                        note=note,
                    )
                    st.success("Movimento registrado.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha ao salvar movimento: {exc}")

    summary = get_laundry_billing_summary(days=30, ref_date=as_of_date, operation_unit=selected_unit)
    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Lavagens enviadas (cobradas - 30d)", int(summary["billed_sent"]))
    l2.metric("Retornos cobrados (30d)", int(summary["billed_returned"]))
    l3.metric("Relavagens enviadas sem cobrança (30d)", int(summary["rewash_sent"]))
    l4.metric("Retornos de relavagem (30d)", int(summary["rewash_returned"]))

    recent_df = pd.DataFrame(list_recent_movements(limit=200, operation_unit=selected_unit))
    if not recent_df.empty:
        recent_df = recent_df[recent_df["movement_type"].isin(set(LAUNDRY_LABELS.values()))]
    if not recent_df.empty:
        recent_df["tipo"] = recent_df["movement_type"].map(MOVEMENT_LABELS)
        st.dataframe(
            recent_df[
                ["movement_date", "item_name", "tipo", "quantity", "source_ref", "note"]
            ].rename(
                columns={
                    "movement_date": "data",
                    "item_name": "item",
                    "quantity": "quantidade",
                    "source_ref": "referencia",
                    "note": "observacao",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

elif menu == "Estoque Central e de Uso":
    st.subheader(f"Estoque central e de uso - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.caption("Entrada de compras e ajustes do estoque central.")
        active_central_items = pd.DataFrame(list_items(operation_unit="CENTRAL", active_only=True))
        if active_central_items.empty:
            st.warning("Ative ao menos um item no cadastro central para lançar compras/movimentações.")
        else:
            central_item_map = {row["name"]: int(row["id"]) for _, row in active_central_items.iterrows()}
            central_form_labels = list(CENTRAL_STOCK_LABELS.keys())
            tab_manual, tab_import = st.tabs(["Lançamento manual", "Importar NF (PDF/XML/Chave)"])

            with tab_manual:
                with st.form("form-central-stock", clear_on_submit=True):
                    f1, f2, f3 = st.columns(3)
                    movement_date = f1.date_input("Data da compra/movimento", value=date.today(), key="central_movement_date")
                    item_name = f2.selectbox("Selecionar item", options=sorted(central_item_map.keys()))
                    movement_label = f3.selectbox("Tipo de movimento", options=central_form_labels)

                    f4, f5, f6 = st.columns(3)
                    quantity = f4.number_input("Quantidade", min_value=1, step=1, value=1, key="central_qty")
                    invoice_number = f5.text_input("Número da NF / chave", placeholder="Ex: 12345 ou chave de acesso")
                    unit_purchase_value = f6.number_input(
                        "Valor de compra unitário (R$)",
                        min_value=0.0,
                        step=0.01,
                        value=0.0,
                    )

                    auto_total = round(float(quantity) * float(unit_purchase_value), 2)
                    g1, g2 = st.columns(2)
                    g1.number_input(
                        "Valor total (R$) - automático",
                        min_value=0.0,
                        step=0.01,
                        value=float(auto_total),
                        disabled=True,
                    )
                    note = g2.text_input("Observação")

                    save_central_move = st.form_submit_button("Salvar movimentação de estoque central")
                    if save_central_move:
                        try:
                            movement_type = CENTRAL_STOCK_LABELS[movement_label]
                            if movement_type == "PURCHASE" and not invoice_number.strip():
                                st.error("Informe o número da NF/chave para lançamento de compra.")
                            else:
                                add_movement(
                                    item_id=central_item_map[item_name],
                                    movement_type=movement_type,
                                    quantity=int(quantity),
                                    movement_date=movement_date,
                                    operation_unit="CENTRAL",
                                    source_ref=invoice_number,
                                    movement_unit_cost=float(unit_purchase_value),
                                    movement_total_value=float(auto_total),
                                    note=note,
                                )
                                st.success("Movimentação central registrada.")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Falha ao salvar movimentação: {exc}")

            with tab_import:
                st.markdown("**Importar nota fiscal para alimentar estoque central**")
                up1, up2 = st.columns(2)
                uploaded_nf_file = up1.file_uploader("Enviar NF (XML ou PDF)", type=["xml", "pdf"])
                access_key_input = up2.text_input("Ou informar chave de acesso (44 dígitos)")
                extract_clicked = st.button("Extrair dados da NF", key="extract_invoice_button")

                if extract_clicked:
                    try:
                        if uploaded_nf_file is not None:
                            extracted = parse_invoice_file(uploaded_nf_file.name, uploaded_nf_file.getvalue())
                        elif access_key_input.strip():
                            extracted = parse_access_key_metadata(access_key_input)
                        else:
                            raise ValueError("Envie um arquivo XML/PDF ou informe uma chave de acesso.")
                        st.session_state["central_invoice_extract"] = extracted
                        st.success("Dados da nota extraídos.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Não foi possível extrair a nota: {exc}")

                extracted = st.session_state.get("central_invoice_extract")
                if extracted:
                    hdr1, hdr2, hdr3, hdr4 = st.columns(4)
                    hdr1.text_input("Número NF", value=str(extracted.get("invoice_number", "")), disabled=True)
                    hdr2.text_input("Série", value=str(extracted.get("series", "")), disabled=True)
                    hdr3.text_input("Data emissão", value=str(extracted.get("emission_date", "")), disabled=True)
                    hdr4.text_input("Chave acesso", value=str(extracted.get("access_key", "")), disabled=True)

                    extracted_items = extracted.get("items", [])
                    if not extracted_items:
                        st.info(
                            "Sem itens extraídos automaticamente. Para chave de acesso isolada, "
                            "a extração de itens depende de integração externa de consulta."
                        )
                    else:
                        st.markdown("**Itens extraídos da nota**")
                        central_names = sorted(central_item_map.keys())
                        normalized_name_map = {_norm_text(name): name for name in central_names}

                        with st.form("form-imported-items"):
                            launch_payload: list[dict[str, Any]] = []
                            for idx, ext_item in enumerate(extracted_items):
                                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
                                description = str(ext_item.get("description", "")).strip()
                                qty_default = float(ext_item.get("quantity", 0) or 0)
                                unit_default = float(ext_item.get("unit_value", 0) or 0)

                                desc_norm = _norm_text(description)
                                default_name = ""
                                if desc_norm in normalized_name_map:
                                    default_name = normalized_name_map[desc_norm]
                                else:
                                    for norm_name, original_name in normalized_name_map.items():
                                        if desc_norm and (desc_norm in norm_name or norm_name in desc_norm):
                                            default_name = original_name
                                            break

                                options = ["-- selecione item --"] + central_names
                                default_idx = options.index(default_name) if default_name in options else 0
                                selected_item_name = c1.selectbox(
                                    f"Item sistema #{idx + 1}",
                                    options=options,
                                    index=default_idx,
                                    key=f"import_item_{idx}",
                                )
                                qty = c2.number_input(
                                    f"Qtd #{idx + 1}",
                                    min_value=0.0,
                                    step=1.0,
                                    value=max(qty_default, 0.0),
                                    key=f"import_qty_{idx}",
                                )
                                unit_val = c3.number_input(
                                    f"Vlr unit #{idx + 1}",
                                    min_value=0.0,
                                    step=0.01,
                                    value=max(unit_default, 0.0),
                                    key=f"import_unit_{idx}",
                                )
                                c4.number_input(
                                    f"Vlr total #{idx + 1}",
                                    min_value=0.0,
                                    step=0.01,
                                    value=round(float(qty) * float(unit_val), 2),
                                    disabled=True,
                                    key=f"import_total_{idx}",
                                )
                                import_row = c5.checkbox(
                                    f"Importar #{idx + 1}",
                                    value=default_idx > 0,
                                    key=f"import_flag_{idx}",
                                )
                                st.caption(f"Descrição NF: {description}")

                                launch_payload.append(
                                    {
                                        "selected_item_name": selected_item_name,
                                        "description": description,
                                        "qty": float(qty),
                                        "unit_val": float(unit_val),
                                        "import_row": bool(import_row),
                                    }
                                )

                            launch_import = st.form_submit_button("Lançar itens importados no estoque central")
                            if launch_import:
                                imported_count = 0
                                emission_date = parse_emission_date_to_date(
                                    str(extracted.get("emission_date", "")),
                                    fallback=date.today(),
                                )
                                source_ref = str(extracted.get("invoice_number") or extracted.get("access_key") or "").strip()
                                for row in launch_payload:
                                    if not row["import_row"]:
                                        continue
                                    if row["selected_item_name"] == "-- selecione item --":
                                        continue
                                    if row["qty"] <= 0:
                                        continue
                                    item_id = central_item_map[row["selected_item_name"]]
                                    auto_total = round(row["qty"] * row["unit_val"], 2)
                                    add_movement(
                                        item_id=item_id,
                                        movement_type="PURCHASE",
                                        quantity=int(round(row["qty"])),
                                        movement_date=emission_date,
                                        operation_unit="CENTRAL",
                                        source_ref=source_ref,
                                        movement_unit_cost=row["unit_val"],
                                        movement_total_value=auto_total,
                                        note=f"Importado de NF - Item NF: {row['description']}",
                                    )
                                    imported_count += 1

                                if imported_count == 0:
                                    st.warning("Nenhum item foi importado. Marque itens válidos e selecione item do sistema.")
                                else:
                                    st.success(f"{imported_count} item(ns) importado(s) com sucesso para o estoque central.")

        stock_report = pd.DataFrame(get_central_stock_report(as_of_date=as_of_date))
        if stock_report.empty:
            st.info("Sem dados no relatório de estoque central.")
        else:
            stock_report["tipo_movimentacao"] = stock_report["last_movement_type"].map(MOVEMENT_LABELS).fillna(
                stock_report["last_movement_type"]
            )
            report_df = stock_report.rename(
                columns={
                    "last_purchase_date": "data_ultima_compra",
                    "name": "item",
                    "stock_qty": "quantidade_estoque",
                    "last_invoice": "numero_nf_ultima_compra",
                    "last_unit_cost": "valor_unitario_item",
                    "last_total_value": "valor_total_item",
                    "last_note": "observacao",
                }
            )
            st.markdown("**Relatório do estoque central**")
            st.dataframe(
                report_df[
                    [
                        "data_ultima_compra",
                        "item",
                        "tipo_movimentacao",
                        "quantidade_estoque",
                        "numero_nf_ultima_compra",
                        "valor_unitario_item",
                        "valor_total_item",
                        "observacao",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.caption(
            "Controle de estoque da unidade, estoque de uso (alocação/retorno) e perdas."
        )
        operational_labels = UNIT_STOCK_LABELS
        item_map = _items_map(selected_unit)
        if not item_map:
            st.warning("Cadastre pelo menos um item antes de registrar movimentos.")
        else:
            with st.form("form-operational", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                movement_date = c1.date_input("Data do movimento", value=date.today())
                item_name = c2.selectbox("Item", options=sorted(item_map.keys()))
                movement_label = c3.selectbox(
                    "Tipo de movimento",
                    options=list(operational_labels.keys()),
                    help="Use este módulo para ajustes de estoque e movimentação de uso diário.",
                )
                c4, c5, c6 = st.columns(3)
                quantity = c4.number_input("Quantidade", min_value=1, step=1, value=1)
                source_ref = c5.text_input("Referência", placeholder="NF, ordem interna")
                note = c6.text_input("Observação")
                move_submitted = st.form_submit_button("Salvar movimento")
                if move_submitted:
                    try:
                        add_movement(
                            item_id=item_map[item_name],
                            movement_type=operational_labels[movement_label],
                            quantity=int(quantity),
                            movement_date=movement_date,
                            operation_unit=selected_unit,
                            source_ref=source_ref,
                            note=note,
                        )
                        st.success("Movimento registrado.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Falha ao salvar movimento: {exc}")

        recent_df = pd.DataFrame(list_recent_movements(limit=150, operation_unit=selected_unit))
        if not recent_df.empty:
            recent_df = recent_df[recent_df["movement_type"].isin(set(operational_labels.values()))]
        if not recent_df.empty:
            recent_df["tipo"] = recent_df["movement_type"].map(MOVEMENT_LABELS)
            st.dataframe(
                recent_df[
                    ["movement_date", "item_name", "tipo", "quantity", "source_ref", "note"]
                ].rename(
                    columns={
                        "movement_date": "data",
                        "item_name": "item",
                        "quantity": "quantidade",
                        "source_ref": "referencia",
                        "note": "observacao",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

elif menu == "Apuração Lavanderia (Planilha)":
    st.subheader(f"Apuração de cobrança da lavanderia - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.warning("Apuração de lavanderia é exclusiva de HOTEL ou CLUB.")
        st.stop()
    st.caption(
        "Modelo de planilha com colunas diárias para validar cobrança quinzenal ou mensal, "
        "incluindo relave (sem cobrança) e perdas."
    )

    p1, p2, p3 = st.columns(3)
    period_mode = p1.selectbox("Modo de período", options=["Quinzenal", "Mensal", "Personalizado"])
    reference_date = p2.date_input("Data de referência", value=as_of_date)
    custom_start = p3.date_input("Início (personalizado)", value=as_of_date - timedelta(days=14))
    custom_end = st.date_input("Fim (personalizado)", value=as_of_date)

    start_date, end_date = _period_bounds(period_mode, reference_date, custom_start, custom_end)
    st.info(f"Período apurado: **{start_date.strftime('%d/%m/%Y')}** até **{end_date.strftime('%d/%m/%Y')}**")

    report_rows = get_laundry_period_item_report(
        start_date=start_date,
        end_date=end_date,
        operation_unit=selected_unit,
    )

    days = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    table_rows: list[dict[str, object]] = []

    for row in report_rows:
        line: dict[str, object] = {
            "ITENS": row["name"],
            "VALOR UNIT": float(row["laundry_unit_cost"]),
        }
        daily_map = row["daily_billed_qty"]
        for dt in days:
            line[f"{dt.day}º"] = int(daily_map.get(dt, 0))

        line["TOTAL"] = int(row["total_billed_qty"])
        line["VALOR TOTAL"] = float(row["total_billed_value"])
        line["RELAVE ENVIADO"] = int(row["rewash_sent_qty"])
        line["RELAVE RETORNADO"] = int(row["rewash_returned_qty"])
        line["PERDAS"] = int(row["loss_qty"])
        table_rows.append(line)

    if not table_rows:
        st.warning("Sem itens para apuração no período selecionado.")
    else:
        sheet_df = pd.DataFrame(table_rows)
        total_billed_qty = int(sheet_df["TOTAL"].sum())
        total_billed_value = float(sheet_df["VALOR TOTAL"].sum())
        total_rewash_sent = int(sheet_df["RELAVE ENVIADO"].sum())
        total_rewash_returned = int(sheet_df["RELAVE RETORNADO"].sum())
        total_losses = int(sheet_df["PERDAS"].sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Peças cobradas no período", total_billed_qty)
        m2.metric("Valor total cobrado (R$)", f"{total_billed_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        m3.metric("Relave enviado (sem cobrança)", total_rewash_sent)
        m4.metric("Relave pendente", total_rewash_sent - total_rewash_returned)
        st.metric("Perdas no período", total_losses)

        st.dataframe(sheet_df, use_container_width=True, hide_index=True)

        csv_data = sheet_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar apuração em CSV",
            data=csv_data,
            file_name=f"apuracao_lavanderia_{selected_unit.lower()}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )

elif menu == "Contagem Física":
    st.subheader("Contagem física (fechamento diário)")
    item_map = _items_map(selected_unit)
    if not item_map:
        st.warning("Cadastre itens antes de lançar contagem física.")
    else:
        with st.form("form-count", clear_on_submit=False):
            d1, d2, d3, d4 = st.columns(4)
            count_date = d1.date_input("Data da contagem", value=date.today())
            item_name = d2.selectbox("Item para contagem", options=sorted(item_map.keys()))
            counted_stock = d3.number_input("Estoque contado", min_value=0, step=1, value=0)
            counted_laundry = d4.number_input("Lavanderia contada", min_value=0, step=1, value=0)
            e1, e2 = st.columns(2)
            counted_in_use = e1.number_input("Em uso contado", min_value=0, step=1, value=0)
            note = e2.text_input("Observação da contagem")
            count_submitted = st.form_submit_button("Salvar contagem")
            if count_submitted:
                try:
                    upsert_inventory_count(
                        item_id=item_map[item_name],
                        count_date=count_date,
                        counted_stock=int(counted_stock),
                        counted_laundry=int(counted_laundry),
                        counted_in_use=int(counted_in_use),
                        operation_unit=selected_unit,
                        note=note,
                    )
                    st.success("Contagem registrada/atualizada.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Erro ao salvar contagem: {exc}")

elif menu == "Painel de Controle":
    st.subheader(f"Painel de controle - {UNIT_OPTIONS[selected_unit]}")
    balances = pd.DataFrame(get_balances(as_of_date, operation_unit=selected_unit))
    if balances.empty:
        st.info("Sem dados de saldo para a data selecionada.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total em estoque (teórico)", int(balances["stock_theoretical"].sum()))
        c2.metric("Total na lavanderia (teórico)", int(balances["laundry_theoretical"].sum()))
        c3.metric("Total em uso (teórico)", int(balances["in_use_theoretical"].sum()))

        critical_df = balances[balances["stock_theoretical"] <= balances["par_level"]].copy()
        if not critical_df.empty:
            st.error(
                f"ALERTA CRITICO: {len(critical_df)} item(ns) no nível mínimo ou abaixo."
            )
            st.dataframe(
                critical_df[
                    ["name", "stock_theoretical", "par_level"]
                ].rename(
                    columns={
                        "name": "item",
                        "stock_theoretical": "estoque_atual",
                        "par_level": "nivel_minimo",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        view_df = balances[
            [
                "name",
                "category",
                "stock_theoretical",
                "laundry_theoretical",
                "in_use_theoretical",
                "counted_stock",
                "counted_laundry",
                "counted_in_use",
            ]
        ].rename(
            columns={
                "name": "item",
                "category": "categoria",
                "stock_theoretical": "estoque_teorico",
                "laundry_theoretical": "lavanderia_teorica",
                "in_use_theoretical": "em_uso_teorico",
                "counted_stock": "estoque_contado",
                "counted_laundry": "lavanderia_contada",
                "counted_in_use": "em_uso_contado",
            }
        )
        st.dataframe(view_df, use_container_width=True, hide_index=True)

        chart_df = balances.melt(
            id_vars=["name"],
            value_vars=["stock_theoretical", "laundry_theoretical", "in_use_theoretical"],
            var_name="local",
            value_name="quantidade",
        )
        chart_df["local"] = chart_df["local"].map(
            {
                "stock_theoretical": "Estoque",
                "laundry_theoretical": "Lavanderia",
                "in_use_theoretical": "Em uso",
            }
        )
        fig = px.bar(chart_df, x="name", y="quantidade", color="local", barmode="group")
        fig.update_layout(xaxis_title="Item", yaxis_title="Quantidade")
        st.plotly_chart(fig, use_container_width=True)

        timeline_df = pd.DataFrame(
            get_daily_movement_totals(days=30, ref_date=as_of_date, operation_unit=selected_unit)
        )
        if not timeline_df.empty:
            st.markdown("**Últimos 30 dias de movimentações**")
            fig_line = px.line(
                timeline_df,
                x="movement_date",
                y=[
                    "purchased",
                    "laundry_sent",
                    "laundry_returned",
                    "rewash_sent",
                    "rewash_returned",
                    "allocated",
                    "returned_use",
                    "loss",
                ],
            )
            fig_line.update_layout(xaxis_title="Data", yaxis_title="Quantidade")
            st.plotly_chart(fig_line, use_container_width=True)

        summary = get_laundry_billing_summary(days=30, ref_date=as_of_date, operation_unit=selected_unit)
        st.markdown("**Resumo de lavanderia (30 dias)**")
        s1, s2 = st.columns(2)
        s1.metric("Lavagem cobrada enviada", int(summary["billed_sent"]))
        s2.metric("Relavagem sem cobrança enviada", int(summary["rewash_sent"]))

elif menu == "Auditoria IA":
    st.subheader(f"Auditoria IA de desfalque - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.warning("Auditoria IA operacional é exclusiva de HOTEL ou CLUB.")
        st.stop()
    report = generate_audit_report(as_of_date=as_of_date, operation_unit=selected_unit)
    f1, f2 = st.columns(2)
    f1.metric("Score geral de risco (0-100)", report["overall_risk_score"])
    f2.metric("Itens com alerta", report["items_with_alert"])

    l1, l2 = st.columns(2)
    l1.metric("Lavagens cobradas enviadas (30d)", int(report["laundry_summary_30d"]["billed_sent"]))
    l2.metric("Relavagens sem cobrança enviadas (30d)", int(report["laundry_summary_30d"]["rewash_sent"]))

    findings_df = pd.DataFrame(report["findings"])
    if findings_df.empty:
        st.success("Nenhum desvio crítico detectado para a data selecionada.")
    else:
        st.warning("Atenção: há indícios de falhas no fluxo do enxoval.")
        st.dataframe(
            findings_df.rename(
                columns={
                    "item": "item",
                    "severidade": "severidade",
                    "area": "area",
                    "descricao": "diagnostico_ia",
                    "acao": "acao_recomendada",
                    "risco_pontos": "pontos_risco",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        top_actions = findings_df["acao"].value_counts().head(3)
        st.markdown("**Prioridades sugeridas pela IA**")
        for idx, (action, count) in enumerate(top_actions.items(), start=1):
            st.write(f"{idx}. {action} (aparece em {count} alerta(s))")
