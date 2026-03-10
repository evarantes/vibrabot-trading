import streamlit as st
from database import (
    get_items, get_central_balance, get_all_central_balances,
    transfer_to_unit, get_transfers, get_units, add_unit, delete_transfer
)
from datetime import date
import pandas as pd


def render():
    st.header("Transferir Central → Unidade")

    units = get_units()
    if not units:
        st.warning("Nenhuma unidade cadastrada. Cadastre uma unidade abaixo.")
        with st.form("add_unit_form"):
            new_unit = st.text_input("Nome da unidade (ex: HOTEL, RESTAURANTE)")
            if st.form_submit_button("Adicionar Unidade"):
                if new_unit.strip():
                    add_unit(new_unit.strip().upper())
                    st.success(f"Unidade '{new_unit.upper()}' adicionada!")
                    st.rerun()
        return

    items = get_items(active_only=True)
    if not items:
        st.info("Nenhum item cadastrado. Vá para 'Cadastro de Itens (Central)' primeiro.")
        return

    # Montar lista de itens com saldo central
    items_with_balance = []
    for item in items:
        balance = get_central_balance(item["id"])
        items_with_balance.append({**item, "balance": balance})

    item_labels = [f"{i['name']} (saldo central: {i['balance']})" for i in items_with_balance]

    st.subheader("Nova Transferência")

    col1, col2, col3, col4 = st.columns([3, 2, 1, 2])

    with col1:
        item_label = st.selectbox("Item para CENTRAL", item_labels)

    with col2:
        dest = st.selectbox("Destino", units)

    # ── CORREÇÃO DO BUG: usar st.number_input com key único ───────────────────
    # O bug anterior ocorria porque o widget usava um valor padrão incorreto
    # ou lia de um state desatualizado. Aqui garantimos leitura direta do widget.
    with col3:
        qty = st.number_input(
            "Quantidade a transferir",
            min_value=1,
            max_value=9999,
            value=1,
            step=1,
            key="transfer_qty"
        )

    with col4:
        transfer_date = st.date_input("Data da transferência", value=date.today(), key="transfer_date")

    col5, col6, col7 = st.columns([1, 2, 3])
    with col5:
        laundry_cost = st.number_input(
            "Valor da lavagem no destino (R$)",
            min_value=0.0,
            step=0.01,
            value=0.0,
            key="transfer_laundry_cost"
        )
    with col6:
        reference = st.text_input("Referência", placeholder="NF, ordem interna", key="transfer_ref")
    with col7:
        notes = st.text_input("Observação", key="transfer_notes")

    # Encontrar item selecionado
    selected_idx = item_labels.index(item_label)
    selected_item = items_with_balance[selected_idx]

    # Mostrar saldo disponível
    available = selected_item["balance"]
    if available > 0:
        st.info(f"📦 Saldo disponível no central para '{selected_item['name']}': **{available} unidades**")
    else:
        st.error(f"⚠️ Saldo ZERO no central para '{selected_item['name']}'. Registre entradas no módulo 'Cadastro de Itens'.")

    if st.button("Transferir", type="primary", key="btn_transfer"):
        # BUG CORRIGIDO: lemos diretamente o valor do widget (qty já é o valor atual)
        ok, msg = transfer_to_unit(
            item_id=selected_item["id"],
            to_unit=dest,
            quantity=qty,          # <-- valor lido corretamente do formulário
            laundry_cost=laundry_cost,
            transfer_date=str(transfer_date),
            reference=reference,
            notes=notes
        )
        if ok:
            st.success(f"✅ {msg}")
            st.rerun()
        else:
            st.error(f"❌ Falha na transferência: {msg}")

    # ── Gerenciar unidades ─────────────────────────────────────────────────────
    with st.expander("⚙️ Gerenciar Unidades"):
        col_u1, col_u2 = st.columns([3, 1])
        with col_u1:
            new_unit_name = st.text_input("Nova unidade", placeholder="Ex: POUSADA, RESTAURANTE", key="new_unit_name")
        with col_u2:
            st.write("")
            st.write("")
            if st.button("Adicionar", key="btn_add_unit"):
                if new_unit_name.strip():
                    add_unit(new_unit_name.strip().upper())
                    st.success(f"Unidade '{new_unit_name.upper()}' adicionada!")
                    st.rerun()
        st.write("Unidades cadastradas:", ", ".join(units))

    # ── Histórico de transferências ────────────────────────────────────────────
    st.divider()
    st.subheader("Histórico de Transferências")

    transfers = get_transfers()
    if transfers:
        df = pd.DataFrame(transfers)[[
            "id", "item_name", "to_unit", "quantity", "laundry_cost",
            "transfer_date", "reference", "notes"
        ]]
        df.columns = ["ID", "Item", "Para", "Qtd", "Custo Lav. (R$)", "Data", "Referência", "Obs"]
        st.dataframe(df, use_container_width=True, hide_index=True)

        with st.expander("⚠️ Remover transferência"):
            del_id = st.number_input("ID da transferência a remover", min_value=1, step=1, key="del_transfer_id")
            if st.button("Remover", type="secondary", key="btn_del_transfer"):
                delete_transfer(del_id)
                st.success(f"Transferência #{del_id} removida.")
                st.rerun()
    else:
        st.info("Nenhuma transferência registrada.")
