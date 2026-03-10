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
        st.warning("⚠️ Nenhuma unidade cadastrada. Cadastre uma unidade abaixo.")
        with st.expander("➕ Adicionar Unidade", expanded=True):
            new_unit = st.text_input("Nome da unidade (ex: HOTEL, RESTAURANTE)", key="first_unit")
            if st.button("Adicionar Unidade", type="primary"):
                if new_unit.strip():
                    add_unit(new_unit.strip().upper())
                    st.success(f"Unidade '{new_unit.upper()}' adicionada!")
                    st.rerun()
        return

    items = get_items(active_only=True)
    if not items:
        st.info("Nenhum item cadastrado. Vá para 'Cadastro de Itens (Central)' primeiro.")
        return

    # ── Montar lista de itens com saldo central atualizado ────────────────────
    items_with_balance = []
    for item in items:
        balance = get_central_balance(item["id"])
        items_with_balance.append({**item, "central_balance": balance})

    # ── Formulário de transferência ───────────────────────────────────────────
    st.subheader("Nova Transferência")

    col1, col2 = st.columns([3, 2])
    with col1:
        # Dropdown mostra nome + saldo central claramente
        item_labels = [
            f"{i['name']}  |  Saldo central: {i['central_balance']}"
            for i in items_with_balance
        ]
        selected_label = st.selectbox(
            "Item para CENTRAL",
            item_labels,
            key="transfer_item_sel"
        )
        selected_idx = item_labels.index(selected_label)
        selected_item = items_with_balance[selected_idx]

    with col2:
        dest = st.selectbox("Destino", units, key="transfer_dest")

    # Alerta de saldo antes de preencher a quantidade
    available = selected_item["central_balance"]
    if available > 0:
        st.success(
            f"📦 Saldo disponível no central para **{selected_item['name']}**: "
            f"**{available} unidade(s)**"
        )
    else:
        st.error(
            f"⛔ Saldo ZERO no central para **{selected_item['name']}**. "
            f"Registre entradas em **Cadastro de Itens → Entrada de Estoque** antes de transferir."
        )

    col3, col4 = st.columns([1, 2])
    with col3:
        # FIX CRÍTICO: number_input com key único + max_value = saldo disponível
        # Impede digitar mais do que existe e garante leitura correta do valor
        qty = st.number_input(
            "Quantidade a transferir",
            min_value=1,
            max_value=max(1, available),   # evita max_value=0 que geraria erro de widget
            value=min(1, available) if available > 0 else 1,
            step=1,
            key="transfer_qty_input",
            disabled=(available == 0)
        )

    with col4:
        transfer_date = st.date_input(
            "Data da transferência", value=date.today(), key="transfer_date_input"
        )

    col5, col6, col7 = st.columns([1, 2, 2])
    with col5:
        # FIX: este é o custo da LAVANDERIA no destino, não o valor de compra
        laundry_cost = st.number_input(
            "Valor da lavagem no destino (R$/peça)",
            min_value=0.0, step=0.01, format="%.2f",
            value=float(selected_item.get("laundry_unit_cost") or 0.0),
            key="transfer_lav_cost",
            help="Valor cobrado pela lavanderia por cada peça lavada nesta unidade de destino"
        )
    with col6:
        reference = st.text_input(
            "Referência", placeholder="NF, ordem interna", key="transfer_ref_input"
        )
    with col7:
        notes = st.text_input("Observação", key="transfer_notes_input")

    # Resumo antes de confirmar
    if available > 0:
        valor_total_compra = qty * float(selected_item.get("purchase_price") or 0.0)
        st.info(
            f"**Resumo:** {qty} × {selected_item['name']} → {dest} | "
            f"Valor de compra total: R$ {valor_total_compra:.2f} | "
            f"Custo lavagem/peça: R$ {laundry_cost:.2f}"
        )

    # Botão de transferência
    if st.button("🔄 Transferir", type="primary", key="btn_do_transfer", disabled=(available == 0)):
        # LEITURA DIRETA do widget — sem usar session_state intermediário
        ok, msg = transfer_to_unit(
            item_id=selected_item["id"],
            to_unit=dest,
            quantity=int(qty),          # garante int puro, sem arredondamento
            laundry_cost=float(laundry_cost),
            transfer_date=str(transfer_date),
            reference=reference,
            notes=notes
        )
        if ok:
            st.success(f"✅ {msg}")
            st.rerun()
        else:
            st.error(f"❌ {msg}")

    # ── Gerenciar unidades ─────────────────────────────────────────────────────
    st.divider()
    with st.expander("⚙️ Gerenciar Unidades"):
        st.write("**Unidades cadastradas:**", " · ".join(units))
        col_u1, col_u2 = st.columns([3, 1])
        with col_u1:
            new_unit_name = st.text_input(
                "Nova unidade", placeholder="Ex: POUSADA, RESTAURANTE", key="new_unit_input"
            )
        with col_u2:
            st.write("")
            st.write("")
            if st.button("Adicionar", key="btn_add_unit_tr"):
                if new_unit_name.strip():
                    add_unit(new_unit_name.strip().upper())
                    st.success(f"Unidade '{new_unit_name.upper()}' adicionada!")
                    st.rerun()

    # ── Histórico de transferências ────────────────────────────────────────────
    st.divider()
    st.subheader("Histórico de Transferências")

    transfers = get_transfers()
    if transfers:
        df = pd.DataFrame(transfers)

        # Calcular valor de compra por transferência
        items_map = {i["id"]: i for i in items}
        df["valor_compra_total"] = df.apply(
            lambda row: row["quantity"] * (items_map.get(row["item_id"], {}).get("purchase_price") or 0.0),
            axis=1
        )

        df_show = df[[
            "id", "item_name", "to_unit", "quantity",
            "valor_compra_total", "laundry_cost",
            "transfer_date", "reference", "notes"
        ]].copy()
        df_show.columns = [
            "ID", "Item", "Para", "Qtd",
            "Valor Compra Total (R$)", "Custo Lav./peça (R$)",
            "Data", "Referência", "Obs"
        ]
        st.dataframe(df_show, use_container_width=True, hide_index=True)

        total_qtd = df["quantity"].sum()
        total_valor = df["valor_compra_total"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total peças transferidas", int(total_qtd))
        c2.metric("Valor total de compra transferido", f"R$ {total_valor:.2f}")

        with st.expander("⚠️ Remover transferência"):
            del_id = st.number_input(
                "ID da transferência", min_value=1, step=1, key="del_transfer_id_inp"
            )
            if st.button("Remover", type="secondary", key="btn_del_transfer"):
                delete_transfer(del_id)
                st.success(f"Transferência #{del_id} removida.")
                st.rerun()
    else:
        st.info("Nenhuma transferência registrada ainda.")
