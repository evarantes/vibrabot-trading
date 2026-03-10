import streamlit as st
from database import get_all_central_balances, get_transfers, get_unit_balance, get_units, get_items
import pandas as pd


def render():
    st.header("Estoque Central e de Uso")

    tabs = st.tabs(["Estoque Central", "Estoque por Unidade", "Visão Geral"])

    # ── Estoque Central ────────────────────────────────────────────────────────
    with tabs[0]:
        st.subheader("Saldo no Estoque Central")
        balances = get_all_central_balances()
        if balances:
            df = pd.DataFrame(balances)
            base_cols = ["id", "name", "category", "par_level", "total_received",
                         "total_transferred_out", "central_balance", "purchase_price", "laundry_unit_cost"]
            df = df[[c for c in base_cols if c in df.columns]]
            col_rename = {
                "id": "ID", "name": "Item", "category": "Categoria",
                "par_level": "Nível Par", "total_received": "Total Recebido",
                "total_transferred_out": "Transferido", "central_balance": "Saldo Central",
                "purchase_price": "Valor Compra (R$)", "laundry_unit_cost": "Custo Lav. (R$)"
            }
            df = df.rename(columns=col_rename)

            def highlight_low(row):
                if row["Saldo Central"] == 0:
                    return ["background-color: #fca5a5"] * len(row)
                elif row["Saldo Central"] < row["Nível Par"] * 0.2:
                    return ["background-color: #fde68a"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df.style.apply(highlight_low, axis=1),
                use_container_width=True, hide_index=True
            )

            total_central = sum(b["central_balance"] for b in balances)
            total_received = sum(b["total_received"] for b in balances)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Recebido", total_received)
            col2.metric("Total no Central", total_central)
            col3.metric("Total Transferido", total_received - total_central)
        else:
            st.info("Nenhum item com movimentação.")

    # ── Estoque por Unidade ────────────────────────────────────────────────────
    with tabs[1]:
        st.subheader("Saldo por Unidade Operacional")
        units = get_units()
        if not units:
            st.info("Nenhuma unidade cadastrada.")
        else:
            selected_unit = st.selectbox("Selecionar unidade", units, key="stock_unit_sel")
            items = get_items(active_only=True)
            rows = []
            for item in items:
                balance = get_unit_balance(item["id"], selected_unit)
                rows.append({
                    "ID": item["id"],
                    "Item": item["name"],
                    "Categoria": item["category"],
                    "Nível Par": item["par_level"],
                    "Saldo na Unidade": balance,
                    "Status": "✅ OK" if balance >= item["par_level"] else ("⚠️ Baixo" if balance > 0 else "❌ Zero")
                })
            if rows:
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)
                total = sum(r["Saldo na Unidade"] for r in rows)
                st.metric(f"Total em estoque na unidade {selected_unit}", total)
            else:
                st.info("Nenhum item.")

    # ── Visão Geral ────────────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader("Visão Geral — Todos os Estoques")
        balances = get_all_central_balances()
        units = get_units()
        items = get_items(active_only=True)

        if not items:
            st.info("Nenhum item.")
            return

        rows = []
        for item in items:
            central = item.get("central_balance", 0) if balances else 0
            unit_totals = {}
            for unit in units:
                unit_totals[unit] = get_unit_balance(item["id"], unit)

            rows.append({
                "Item": item["name"],
                "Categoria": item["category"],
                "Central": central,
                **unit_totals,
                "TOTAL": central + sum(unit_totals.values())
            })

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum dado disponível.")
