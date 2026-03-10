import streamlit as st
from database import (
    get_items, upsert_item, delete_item,
    get_all_central_balances, add_stock_entry, get_stock_entries, delete_stock_entry
)
from datetime import date
import pandas as pd


def render():
    st.header("Cadastro mestre de itens (Estoque Central)")

    with st.expander("ℹ️ Banco de dados do saldo central", expanded=False):
        st.caption(str(date.today()))

    tabs = st.tabs(["✏️ Cadastro / Edição", "📦 Entrada de Estoque", "📋 Listagem de Itens"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Cadastro / Edição
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[0]:
        items_all = get_items(active_only=False)
        item_options = {i["name"]: i for i in items_all}
        item_names = ["-- Novo item --"] + sorted(item_options.keys())

        selected_name = st.selectbox("Item para editar", item_names, key="item_edit_select")

        # FIX: ao trocar o item no selectbox, carregamos os valores corretos.
        # Usamos a key baseada no nome selecionado para forçar recriação dos widgets.
        selected_item = item_options.get(selected_name) if selected_name != "-- Novo item --" else None
        item_key = selected_item["id"] if selected_item else "new"

        # Valores padrão vindos do item selecionado
        default_nome     = selected_item["name"]              if selected_item else ""
        default_cat      = selected_item["category"]          if selected_item else ""
        default_par      = int(selected_item["par_level"])    if selected_item else 0
        default_preco    = float(selected_item.get("purchase_price", 0.0) or 0.0)    if selected_item else 0.0
        default_lav      = float(selected_item.get("laundry_unit_cost", 0.0) or 0.0) if selected_item else 0.0
        default_ativo    = bool(selected_item["active"])      if selected_item else True

        st.divider()
        col1, col2 = st.columns([3, 2])
        with col1:
            # key inclui item_key para que o widget seja recriado quando o item muda
            nome = st.text_input("Nome do item", value=default_nome, key=f"nome_{item_key}")
        with col2:
            categoria = st.text_input("Categoria (ex: SALÃO, COZINHA, ROUPA DE BANHO)",
                                      value=default_cat, key=f"cat_{item_key}")

        col3, col4, col5, col6 = st.columns(4)
        with col3:
            par_level = st.number_input(
                "Nível Par (qtd mínima)",
                min_value=0, step=1,
                value=default_par,
                key=f"par_{item_key}",
                help="Quantidade mínima desejada na unidade"
            )
        with col4:
            purchase_price = st.number_input(
                "Valor de Compra (R$) por peça",
                min_value=0.0, step=0.01, format="%.2f",
                value=default_preco,
                key=f"preco_{item_key}",
                help="Preço unitário pago na compra do item"
            )
        with col5:
            laundry_cost = st.number_input(
                "Custo Lavagem/Unidade (R$)",
                min_value=0.0, step=0.01, format="%.2f",
                value=default_lav,
                key=f"lav_{item_key}",
                help="Valor cobrado pela lavanderia por cada peça lavada"
            )
        with col6:
            st.write("")
            ativo = st.checkbox("Ativo", value=default_ativo, key=f"ativo_{item_key}")

        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            salvar = st.button("💾 Salvar edição", type="primary", key="btn_salvar_item")

        if salvar:
            if not nome.strip():
                st.error("❌ Nome é obrigatório.")
            else:
                upsert_item(
                    nome.strip().upper(),
                    categoria.strip().upper(),
                    par_level,
                    purchase_price,
                    laundry_cost,
                    1 if ativo else 0,
                    selected_item["id"] if selected_item else None
                )
                st.success(f"✅ Item **'{nome.upper()}'** salvo com sucesso!")
                st.rerun()

        # Desativar item
        itens_ativos = [i for i in items_all if i["active"] == 1]
        if itens_ativos:
            st.divider()
            with st.expander("⚠️ Desativar item"):
                del_name = st.selectbox("Selecione item para desativar",
                                        [i["name"] for i in itens_ativos], key="del_item_sel")
                if st.button("Desativar", type="secondary", key="btn_desativar"):
                    del_item_obj = next((i for i in itens_ativos if i["name"] == del_name), None)
                    if del_item_obj:
                        delete_item(del_item_obj["id"])
                        st.success(f"Item '{del_name}' desativado.")
                        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Entrada de Estoque
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[1]:
        st.subheader("📦 Registrar Entrada de Estoque no Central")
        st.info(
            "**Importante:** Cadastrar um item NÃO adiciona quantidade ao estoque. "
            "Após cada compra, registre a entrada aqui para que o saldo central seja atualizado."
        )

        items_active = get_items(active_only=True)
        if not items_active:
            st.warning("Nenhum item ativo. Cadastre itens primeiro.")
        else:
            col_e1, col_e2, col_e3 = st.columns([3, 1, 2])
            with col_e1:
                item_entry_name = st.selectbox(
                    "Item", [i["name"] for i in items_active], key="entry_item_sel"
                )
            with col_e2:
                qty_entry = st.number_input(
                    "Quantidade recebida", min_value=1, value=10, step=1, key="entry_qty"
                )
            with col_e3:
                date_entry = st.date_input("Data do recebimento", value=date.today(), key="entry_date")

            col_e4, col_e5 = st.columns([2, 3])
            with col_e4:
                ref_entry = st.text_input(
                    "Referência (NF / Pedido)", key="entry_ref",
                    placeholder="Ex: NF 001, Pedido 2026/03"
                )
            with col_e5:
                notes_entry = st.text_input("Observação", key="entry_notes")

            if st.button("✅ Registrar Entrada no Central", type="primary", key="btn_entrada"):
                item_obj = next((i for i in items_active if i["name"] == item_entry_name), None)
                if item_obj:
                    add_stock_entry(item_obj["id"], qty_entry, str(date_entry), ref_entry, notes_entry)
                    st.success(
                        f"✅ **{qty_entry}** unidade(s) de **'{item_entry_name}'** "
                        f"adicionada(s) ao estoque central!"
                    )
                    st.rerun()

            # Histórico de entradas
            st.divider()
            st.subheader("Histórico de Entradas")
            entries = get_stock_entries()
            if entries:
                df_e = pd.DataFrame(entries)[[
                    "id", "item_name", "quantity", "entry_date", "reference", "notes"
                ]]
                df_e.columns = ["ID", "Item", "Quantidade", "Data", "Referência", "Obs"]
                st.dataframe(df_e, use_container_width=True, hide_index=True)

                total_entries = sum(e["quantity"] for e in entries)
                st.metric("Total de peças recebidas no central", total_entries)

                with st.expander("⚠️ Remover entrada"):
                    del_entry_id = st.number_input(
                        "ID da entrada a remover", min_value=1, step=1, key="del_entry_id"
                    )
                    if st.button("Remover entrada", type="secondary", key="btn_del_entry"):
                        delete_stock_entry(del_entry_id)
                        st.success(f"Entrada #{del_entry_id} removida.")
                        st.rerun()
            else:
                st.info("Nenhuma entrada registrada ainda.")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Listagem completa
    # ══════════════════════════════════════════════════════════════════════════
    with tabs[2]:
        st.subheader("Todos os Itens — Saldo Central")
        balances = get_all_central_balances()
        if balances:
            df = pd.DataFrame(balances)
            # Adicionar purchase_price se existir
            cols = ["id", "name", "category", "par_level", "purchase_price",
                    "laundry_unit_cost", "central_balance", "total_received", "active"]
            available_cols = [c for c in cols if c in df.columns]
            df = df[available_cols]
            rename_map = {
                "id": "ID", "name": "Nome", "category": "Categoria",
                "par_level": "Nível Par", "purchase_price": "Valor Compra (R$)",
                "laundry_unit_cost": "Custo Lavagem (R$)",
                "central_balance": "Saldo Central", "total_received": "Total Recebido",
                "active": "Ativo"
            }
            df = df.rename(columns=rename_map)
            if "Ativo" in df.columns:
                df["Ativo"] = df["Ativo"].apply(lambda x: "✅" if x else "❌")

            def highlight_zero(row):
                if "Saldo Central" in row and row["Saldo Central"] == 0 and row.get("Total Recebido", 0) > 0:
                    return ["background-color: #fca5a5"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df.style.apply(highlight_zero, axis=1),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("Nenhum item cadastrado ainda.")
