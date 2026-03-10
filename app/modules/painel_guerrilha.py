import streamlit as st
from database import (
    get_all_central_balances, get_units, get_laundry_records,
    get_items, get_unit_balance, get_physical_counts
)
import pandas as pd
from datetime import date, timedelta


def render():
    st.header("Painel de Guerrilha")
    st.caption("Visão rápida do status crítico do enxoval. Foco nos pontos de atenção.")

    balances = get_all_central_balances()
    units = get_units()
    items = get_items(active_only=True)

    if not items:
        st.warning("Nenhum item cadastrado.")
        return

    # ── Métricas de alerta ─────────────────────────────────────────────────────
    total_central = sum(b["central_balance"] for b in balances)
    total_received = sum(b["total_received"] for b in balances)
    items_zero = [b for b in balances if b["central_balance"] == 0 and b["total_received"] > 0]
    pendentes_lav = get_laundry_records(status="pendente") + get_laundry_records(status="parcial")
    total_pending_laundry = sum(r["quantity_sent"] - r["quantity_returned"] for r in pendentes_lav)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Recebido (Central)", total_received)
    col2.metric("Saldo Central Atual", total_central)
    col3.metric("Itens com Saldo Zero", len(items_zero),
                delta="⚠️ Atenção" if items_zero else "✅ OK",
                delta_color="off" if not items_zero else "inverse")
    col4.metric("Peças na Lavanderia", total_pending_laundry,
                delta="pendentes" if total_pending_laundry > 0 else "OK")

    # ── Alertas críticos ───────────────────────────────────────────────────────
    st.divider()
    alertas = []

    for b in balances:
        if b["total_received"] > 0 and b["central_balance"] == 0:
            alertas.append(("🔴 CRÍTICO", f"'{b['name']}': saldo zero no central ({b['total_received']} recebidos, {b['total_transferred_out']} transferidos)"))
        elif b["par_level"] > 0 and b["central_balance"] < b["par_level"] * 0.2:
            alertas.append(("🟠 BAIXO", f"'{b['name']}': saldo {b['central_balance']} (nível par: {b['par_level']})"))

    for r in pendentes_lav:
        diff = r["quantity_sent"] - r["quantity_returned"]
        if diff > 0:
            days_ago = (date.today() - date.fromisoformat(r["send_date"][:10])).days
            if days_ago > 7:
                alertas.append(("🟡 ATENÇÃO", f"Lavanderia: '{r['item_name']}' ({r['operation_unit']}) - {diff} peças há {days_ago} dias sem retorno"))

    if alertas:
        st.subheader("⚠️ Alertas")
        for nivel, msg in sorted(alertas, key=lambda x: x[0]):
            if "CRÍTICO" in nivel:
                st.error(f"**{nivel}** — {msg}")
            elif "BAIXO" in nivel:
                st.warning(f"**{nivel}** — {msg}")
            else:
                st.info(f"**{nivel}** — {msg}")
    else:
        st.success("✅ Nenhum alerta crítico no momento!")

    # ── Status por unidade ─────────────────────────────────────────────────────
    if units:
        st.divider()
        st.subheader("Status por Unidade")
        for unit in units:
            with st.expander(f"🏨 {unit}"):
                rows = []
                for item in items:
                    bal = get_unit_balance(item["id"], unit)
                    status = "✅ OK" if bal >= item["par_level"] else ("⚠️ Baixo" if bal > 0 else "❌ Zero")
                    rows.append({"Item": item["name"], "Saldo": bal, "Nível Par": item["par_level"], "Status": status})
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Última contagem física vs sistema ─────────────────────────────────────
    st.divider()
    st.subheader("Comparativo: Última Contagem Física vs Sistema")

    counts = get_physical_counts()
    if counts:
        # Pegar última contagem por item
        latest = {}
        for c in counts:
            key = (c["item_name"], c["operation_unit"])
            if key not in latest:
                latest[key] = c
        rows = [
            {
                "Item": v["item_name"],
                "Unidade": v["operation_unit"],
                "Data Contagem": v["count_date"][:10],
                "Contado": v["counted_quantity"],
                "Esperado": v["expected_quantity"],
                "Diferença": v["counted_quantity"] - v["expected_quantity"]
            }
            for v in latest.values()
        ]
        df = pd.DataFrame(rows)

        def highlight(row):
            if row["Diferença"] < 0:
                return ["background-color: #fca5a5"] * len(row)
            return [""] * len(row)

        st.dataframe(df.style.apply(highlight, axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma contagem física registrada ainda.")
