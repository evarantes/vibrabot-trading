import streamlit as st
from database import get_laundry_records, get_items, get_units
import pandas as pd
from datetime import date, timedelta


def render():
    st.header("Apuração da Lavanderia (Planilha)")

    units = get_units()
    all_units = ["CENTRAL"] + units

    col1, col2, col3 = st.columns([2, 2, 2])
    with col1:
        unit_filter = st.selectbox("Unidade", ["Todas"] + all_units, key="apur_unit")
    with col2:
        start_date = st.date_input("Data início", value=date.today() - timedelta(days=30), key="apur_start")
    with col3:
        end_date = st.date_input("Data fim", value=date.today(), key="apur_end")

    unit = None if unit_filter == "Todas" else unit_filter
    records = get_laundry_records(operation_unit=unit)

    # Filtrar por data
    records = [
        r for r in records
        if start_date.isoformat() <= r["send_date"][:10] <= end_date.isoformat()
    ]

    if not records:
        st.info("Nenhum registro no período selecionado.")
        return

    # ── Resumo por item ────────────────────────────────────────────────────────
    st.subheader("Resumo por Item")
    items_map = {}
    for r in records:
        key = r["item_name"]
        if key not in items_map:
            items_map[key] = {
                "Item": key,
                "Categoria": r["category"],
                "Total Enviado": 0,
                "Total Retornado": 0,
                "Pendente": 0,
                "Lotes": 0,
                "Custo Total (R$)": 0.0
            }
        items_map[key]["Total Enviado"] += r["quantity_sent"]
        items_map[key]["Total Retornado"] += r["quantity_returned"]
        items_map[key]["Pendente"] += r["quantity_sent"] - r["quantity_returned"]
        items_map[key]["Lotes"] += 1

    df_summary = pd.DataFrame(list(items_map.values()))

    def highlight_pending(row):
        if row["Pendente"] > 0:
            return ["background-color: #fde68a"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df_summary.style.apply(highlight_pending, axis=1),
        use_container_width=True, hide_index=True
    )

    # Métricas
    total_sent = sum(r["quantity_sent"] for r in records)
    total_returned = sum(r["quantity_returned"] for r in records)
    total_pending = total_sent - total_returned

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Enviado", total_sent)
    col_m2.metric("Total Retornado", total_returned)
    col_m3.metric("Pendente de Retorno", total_pending, delta=f"-{total_pending}" if total_pending > 0 else "0", delta_color="inverse")
    col_m4.metric("Lotes Totais", len(records))

    # ── Detalhamento completo ──────────────────────────────────────────────────
    st.divider()
    st.subheader("Detalhamento Completo")

    df_detail = pd.DataFrame(records)[[
        "id", "item_name", "operation_unit", "quantity_sent", "quantity_returned",
        "laundry_name", "send_date", "return_date", "status"
    ]]
    df_detail.columns = ["ID", "Item", "Unidade", "Enviado", "Retornado",
                         "Lavanderia", "Data Envio", "Data Retorno", "Status"]

    def color_status(val):
        if val == "pendente":
            return "background-color: #fbbf24; color: black"
        elif val == "parcial":
            return "background-color: #60a5fa; color: black"
        elif val == "completo":
            return "background-color: #34d399; color: black"
        return ""

    st.dataframe(
        df_detail.style.applymap(color_status, subset=["Status"]),
        use_container_width=True, hide_index=True
    )

    # Download CSV
    csv = df_detail.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Baixar planilha CSV",
        csv,
        f"apuracao_lavanderia_{start_date}_{end_date}.csv",
        "text/csv"
    )
