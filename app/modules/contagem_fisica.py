import streamlit as st
from database import (
    get_items, get_units, add_physical_count, get_physical_counts,
    get_central_balance, get_unit_balance
)
from datetime import date
import pandas as pd


def render(selected_unit="CENTRAL"):
    st.header("Contagem Física")
    st.caption("Registre a contagem manual dos itens e compare com o saldo do sistema.")

    units = get_units()
    all_units = ["CENTRAL"] + units
    items = get_items(active_only=True)

    if not items:
        st.info("Nenhum item cadastrado.")
        return

    # ── Formulário de contagem ─────────────────────────────────────────────────
    with st.form("physical_count_form"):
        st.subheader("Nova Contagem")
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            count_unit = st.selectbox("Unidade", all_units,
                                      index=all_units.index(selected_unit) if selected_unit in all_units else 0)
        with col2:
            count_date = st.date_input("Data da contagem", value=date.today())
        with col3:
            st.write("")

        # Tabela de contagem em lote
        st.write("**Preencha a quantidade física contada para cada item:**")
        count_data = {}
        for item in items:
            expected = get_central_balance(item["id"]) if count_unit == "CENTRAL" else get_unit_balance(item["id"], count_unit)
            col_name, col_expected, col_counted, col_diff_preview = st.columns([3, 1, 1, 1])
            with col_name:
                st.write(f"**{item['name']}**")
            with col_expected:
                st.metric("Esperado", expected, label_visibility="visible")
            with col_counted:
                counted = st.number_input(
                    f"Contado",
                    min_value=0,
                    value=expected,
                    step=1,
                    key=f"count_{item['id']}"
                )
                count_data[item["id"]] = {"counted": counted, "expected": expected, "name": item["name"]}
            with col_diff_preview:
                diff = counted - expected
                color = "normal" if diff == 0 else ("inverse" if diff < 0 else "normal")
                st.metric("Diferença", diff, delta=str(diff) if diff != 0 else "OK")

        notes = st.text_area("Observações gerais")
        submitted = st.form_submit_button("Salvar Contagem Física", type="primary")

        if submitted:
            for item_id, data in count_data.items():
                add_physical_count(item_id, count_unit, str(count_date), data["counted"], notes)
            st.success(f"✅ Contagem física de {len(count_data)} itens registrada para {count_unit} em {count_date}!")
            st.rerun()

    # ── Histórico de contagens ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Histórico de Contagens")

    unit_hist = st.selectbox("Filtrar por unidade", ["Todas"] + all_units, key="count_hist_unit")
    unit_filter = None if unit_hist == "Todas" else unit_hist

    counts = get_physical_counts(operation_unit=unit_filter)
    if counts:
        df = pd.DataFrame(counts)
        df["diferenca"] = df["counted_quantity"] - df["expected_quantity"]
        df = df[["id", "item_name", "operation_unit", "count_date",
                 "counted_quantity", "expected_quantity", "diferenca", "notes"]]
        df.columns = ["ID", "Item", "Unidade", "Data", "Contado", "Esperado", "Diferença", "Obs"]

        def highlight_diff(row):
            if row["Diferença"] < 0:
                return ["background-color: #fca5a5"] * len(row)
            elif row["Diferença"] > 0:
                return ["background-color: #bbf7d0"] * len(row)
            return [""] * len(row)

        st.dataframe(
            df.style.apply(highlight_diff, axis=1),
            use_container_width=True, hide_index=True
        )

        total_diff = df["Diferença"].sum()
        if total_diff < 0:
            st.error(f"⚠️ Diferença total acumulada: **{total_diff} peças** (desfalque)")
        elif total_diff > 0:
            st.info(f"ℹ️ Diferença total: +{total_diff} peças (excesso registrado)")
        else:
            st.success("✅ Sem diferenças acumuladas.")
    else:
        st.info("Nenhuma contagem registrada.")
