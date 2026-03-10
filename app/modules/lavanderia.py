import streamlit as st
from database import (
    get_items, get_laundry_records, add_laundry_record,
    register_laundry_return, delete_laundry, get_units
)
from datetime import date
import pandas as pd


def render(selected_unit="CENTRAL"):
    st.header("Lançamentos de Lavanderia")

    units = get_units()
    all_units = ["CENTRAL"] + units

    items = get_items(active_only=True)
    if not items:
        st.info("Nenhum item cadastrado.")
        return

    tabs = st.tabs(["Registrar Envio", "Registrar Retorno", "Histórico"])

    # ── Registrar Envio ────────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Enviar para Lavanderia")

        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            item_name = st.selectbox("Item", [i["name"] for i in items], key="laundry_item")
        with col2:
            unit_sel = st.selectbox("Unidade de origem", all_units, key="laundry_unit_send",
                                    index=all_units.index(selected_unit) if selected_unit in all_units else 0)
        with col3:
            qty_sent = st.number_input("Qtd enviada", min_value=1, value=1, step=1, key="laundry_qty_sent")

        col4, col5 = st.columns([3, 2])
        with col4:
            laundry_name = st.text_input("Nome da lavanderia", key="laundry_name", placeholder="Ex: Lavanderia Brilho")
        with col5:
            send_date = st.date_input("Data de envio", value=date.today(), key="laundry_send_date")

        notes_send = st.text_area("Observações", key="laundry_notes_send", height=60)

        if st.button("Registrar Envio", type="primary", key="btn_send_laundry"):
            item_obj = next((i for i in items if i["name"] == item_name), None)
            if item_obj:
                add_laundry_record(item_obj["id"], unit_sel, qty_sent, laundry_name, str(send_date), notes_send)
                st.success(f"✅ {qty_sent} unidade(s) de '{item_name}' enviadas para a lavanderia!")
                st.rerun()

    # ── Registrar Retorno ──────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Registrar Retorno da Lavanderia")
        pendentes = get_laundry_records(status="pendente") + get_laundry_records(status="parcial")
        if pendentes:
            options = {
                f"#{r['id']} - {r['item_name']} ({r['operation_unit']}) | Enviado:{r['quantity_sent']} Retornado:{r['quantity_returned']} | {r['send_date']}": r
                for r in pendentes
            }
            chosen_label = st.selectbox("Registro pendente", list(options.keys()), key="return_select")
            chosen = options[chosen_label]

            pending_qty = chosen["quantity_sent"] - chosen["quantity_returned"]
            col_r1, col_r2 = st.columns([1, 2])
            with col_r1:
                qty_ret = st.number_input(
                    f"Quantidade retornada (pendente: {pending_qty})",
                    min_value=1,
                    max_value=pending_qty,
                    value=pending_qty,
                    step=1,
                    key="laundry_ret_qty"
                )
            with col_r2:
                ret_date = st.date_input("Data do retorno", value=date.today(), key="laundry_ret_date")

            if st.button("Confirmar Retorno", type="primary", key="btn_return_laundry"):
                ok, msg = register_laundry_return(chosen["id"], qty_ret, str(ret_date))
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.info("Nenhum envio pendente de retorno.")

    # ── Histórico ──────────────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Histórico de Lavanderia")
        filtro_unit = st.selectbox("Filtrar por unidade", ["Todas"] + all_units, key="laundry_hist_unit")
        unit_filter = None if filtro_unit == "Todas" else filtro_unit

        records = get_laundry_records(operation_unit=unit_filter)
        if records:
            df = pd.DataFrame(records)[[
                "id", "item_name", "operation_unit", "quantity_sent",
                "quantity_returned", "laundry_name", "send_date", "return_date", "status"
            ]]
            df.columns = ["ID", "Item", "Unidade", "Enviado", "Retornado", "Lavanderia", "Envio", "Retorno", "Status"]

            def color_status(val):
                colors = {"pendente": "background-color: #fbbf24; color: black",
                          "parcial": "background-color: #60a5fa; color: black",
                          "completo": "background-color: #34d399; color: black"}
                return colors.get(val, "")

            st.dataframe(df.style.applymap(color_status, subset=["Status"]),
                         use_container_width=True, hide_index=True)

            diff_total = sum(r["quantity_sent"] - r["quantity_returned"] for r in records if r["status"] != "completo")
            if diff_total > 0:
                st.warning(f"⚠️ Total pendente de retorno: **{diff_total} peças**")

            with st.expander("⚠️ Remover registro"):
                del_id = st.number_input("ID do registro", min_value=1, step=1, key="del_laundry_id")
                if st.button("Remover", type="secondary", key="btn_del_laundry"):
                    delete_laundry(del_id)
                    st.success(f"Registro #{del_id} removido.")
                    st.rerun()
        else:
            st.info("Nenhum registro de lavanderia.")
