import streamlit as st
from database import get_items, upsert_item, delete_item, get_all_central_balances, add_stock_entry
from datetime import date


def render():
    st.header("Cadastro mestre de itens (Estoque Central)")

    with st.expander("ℹ️ Banco de dados do saldo central", expanded=False):
        st.caption(str(date.today()))

    # ── Editar / Criar item ────────────────────────────────────────────────────
    items = get_items(active_only=False)
    item_options = {i["name"]: i for i in items}
    item_names = ["-- Novo item --"] + list(item_options.keys())

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        selected_name = st.selectbox("Item para editar", item_names)
    with col_btn:
        st.write("")
        st.write("")
        save_clicked = st.button("Salvar edição", type="primary")

    selected_item = item_options.get(selected_name) if selected_name != "-- Novo item --" else None

    col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
    with col1:
        nome = st.text_input("Nome", value=selected_item["name"] if selected_item else "")
    with col2:
        categoria = st.text_input("Categoria", value=selected_item["category"] if selected_item else "")

    # Par level com +/-
    col3a, col3b, col3c = col3.columns([1, 1, 1])
    par_val = selected_item["par_level"] if selected_item else 0
    if "par_level_val" not in st.session_state or selected_name != st.session_state.get("_last_item"):
        st.session_state["par_level_val"] = par_val
        st.session_state["_last_item"] = selected_name
    with col3a:
        st.write("")
        st.write("")
        if st.button("−", key="par_minus"):
            st.session_state["par_level_val"] = max(0, st.session_state["par_level_val"] - 1)
    with col3b:
        st.number_input("Nível Par", min_value=0, value=st.session_state["par_level_val"], key="_par_display", label_visibility="visible")
        st.session_state["par_level_val"] = st.session_state["_par_display"]
    with col3c:
        st.write("")
        st.write("")
        if st.button("+", key="par_plus"):
            st.session_state["par_level_val"] = st.session_state["par_level_val"] + 1

    # Laundry cost com +/-
    lc_val = selected_item["laundry_unit_cost"] if selected_item else 0.0
    if "lc_val" not in st.session_state or selected_name != st.session_state.get("_last_item2"):
        st.session_state["lc_val"] = lc_val
        st.session_state["_last_item2"] = selected_name

    col4a, col4b, col4c = col4.columns([1, 1, 1])
    with col4a:
        st.write("")
        st.write("")
        if st.button("−", key="lc_minus"):
            st.session_state["lc_val"] = max(0.0, st.session_state["lc_val"] - 1.0)
    with col4b:
        st.number_input("Unidade Valor. Lavagem (R$)", min_value=0.0, step=1.0, value=st.session_state["lc_val"], key="_lc_display", label_visibility="visible")
        st.session_state["lc_val"] = st.session_state["_lc_display"]
    with col4c:
        st.write("")
        st.write("")
        if st.button("+", key="lc_plus"):
            st.session_state["lc_val"] = st.session_state["lc_val"] + 1.0

    with col5:
        st.write("")
        st.write("")
        ativo = st.checkbox("Ativo", value=selected_item["active"] if selected_item else True)

    if save_clicked:
        if not nome.strip():
            st.error("Nome é obrigatório.")
        else:
            upsert_item(
                nome.strip().upper(),
                categoria.strip().upper(),
                st.session_state["par_level_val"],
                st.session_state["lc_val"],
                1 if ativo else 0,
                selected_item["id"] if selected_item else None
            )
            st.success(f"Item '{nome.upper()}' salvo com sucesso!")
            st.rerun()

    # ── Entrada de estoque ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("📦 Entrada de Estoque no Central")
    st.caption("Use esta seção para registrar compras ou recebimentos de enxoval no estoque central.")

    items_active = get_items(active_only=True)
    if items_active:
        col_e1, col_e2, col_e3, col_e4 = st.columns([3, 1, 2, 2])
        with col_e1:
            item_entry = st.selectbox("Item", [i["name"] for i in items_active], key="entry_item")
        with col_e2:
            qty_entry = st.number_input("Quantidade", min_value=1, value=10, step=1, key="entry_qty")
        with col_e3:
            date_entry = st.date_input("Data da entrada", value=date.today(), key="entry_date")
        with col_e4:
            ref_entry = st.text_input("Referência (NF, etc.)", key="entry_ref", placeholder="NF, ordem interna")

        if st.button("Registrar Entrada no Central", type="primary", key="btn_entry"):
            item_obj = next((i for i in items_active if i["name"] == item_entry), None)
            if item_obj:
                add_stock_entry(item_obj["id"], qty_entry, str(date_entry), ref_entry)
                st.success(f"✅ {qty_entry} unidade(s) de '{item_entry}' adicionada(s) ao estoque central!")
                st.rerun()
    else:
        st.info("Cadastre itens primeiro.")

    # ── Tabela de itens ────────────────────────────────────────────────────────
    st.divider()
    balances = get_all_central_balances()
    if balances:
        import pandas as pd
        df = pd.DataFrame(balances)[["id", "name", "category", "par_level", "laundry_unit_cost", "active", "central_balance", "total_received"]]
        df.columns = ["id", "name", "category", "par_level", "laundry_unit_cost", "active", "saldo_central", "total_recebido"]
        df["active"] = df["active"].apply(lambda x: "✅" if x else "❌")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum item cadastrado ainda.")

    # ── Deletar item ───────────────────────────────────────────────────────────
    active_items = [i for i in items if i["active"] == 1]
    if active_items:
        with st.expander("⚠️ Desativar item"):
            del_name = st.selectbox("Selecione item para desativar", [i["name"] for i in active_items], key="del_item")
            if st.button("Desativar item selecionado", type="secondary", key="btn_del"):
                del_item = next((i for i in active_items if i["name"] == del_name), None)
                if del_item:
                    delete_item(del_item["id"])
                    st.success(f"Item '{del_name}' desativado.")
                    st.rerun()
