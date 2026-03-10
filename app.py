from __future__ import annotations

from calendar import monthrange
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from codexiaauditor.audit_engine import generate_audit_report
from codexiaauditor.database import init_db
from codexiaauditor.repository import (
    add_item,
    add_movement,
    get_balances,
    get_daily_movement_totals,
    get_laundry_billing_summary,
    get_laundry_period_item_report,
    list_items,
    list_recent_movements,
    update_item_laundry_cost,
    upsert_inventory_count,
)

st.set_page_config(page_title="CODEXIAAUDITOR", layout="wide")
init_db()

MOVEMENT_LABELS = {
    "PURCHASE": "Compra de enxoval",
    "STOCK_IN": "Entrada manual no estoque",
    "STOCK_OUT": "Saída manual do estoque",
    "LAUNDRY_SENT": "Enviado para lavanderia (cobrado)",
    "LAUNDRY_RETURNED": "Retorno da lavanderia (cobrado)",
    "LAUNDRY_REWASH_SENT": "Relavagem: reenviado sem cobrança",
    "LAUNDRY_REWASH_RETURNED": "Relavagem: retorno sem cobrança",
    "IN_USE_ALLOCATED": "Alocado para uso (operação)",
    "IN_USE_RETURNED": "Retorno de uso para estoque",
    "LOSS": "Perda / baixa por avaria ou extravio",
}
LABEL_TO_MOVEMENT = {v: k for k, v in MOVEMENT_LABELS.items()}
UNIT_OPTIONS = {"HOTEL": "Hotel", "CLUB": "Club"}

LAUNDRY_LABELS = {
    "Enviado para lavanderia (cobrado)": "LAUNDRY_SENT",
    "Retorno da lavanderia (cobrado)": "LAUNDRY_RETURNED",
    "Relavagem: reenviado sem cobrança": "LAUNDRY_REWASH_SENT",
    "Relavagem: retorno sem cobrança": "LAUNDRY_REWASH_RETURNED",
}
OPERATIONAL_LABELS = {
    "Compra de enxoval": "PURCHASE",
    "Entrada manual no estoque": "STOCK_IN",
    "Saída manual do estoque": "STOCK_OUT",
    "Alocado para uso (operação)": "IN_USE_ALLOCATED",
    "Retorno de uso para estoque": "IN_USE_RETURNED",
    "Perda / baixa por avaria ou extravio": "LOSS",
}


def _items_map() -> dict[str, int]:
    return {row["name"]: int(row["id"]) for row in list_items()}


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
        "Cadastro de Itens",
        "Lançamentos Lavanderia",
        "Lançamentos Operacionais",
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

if menu == "Cadastro de Itens":
    st.subheader("Cadastrar item de enxoval")
    with st.form("form-item", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns(4)
        name = col1.text_input("Nome do item", placeholder="Ex: Lençol solteiro 180 fios")
        category = col2.text_input("Categoria", value="Roupa de cama")
        par_level = col3.number_input("Nível mínimo (par level)", min_value=0, step=1, value=0)
        laundry_cost = col4.number_input("Valor unit. lavagem (R$)", min_value=0.0, step=0.1, value=0.0)
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
                        laundry_unit_cost=float(laundry_cost),
                    )
                    st.success("Item cadastrado com sucesso.")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Não foi possível cadastrar: {exc}")

    items_df = pd.DataFrame(list_items())
    if items_df.empty:
        st.warning("Nenhum item cadastrado ainda.")
    else:
        with st.form("form-update-laundry-cost"):
            c1, c2, c3 = st.columns(3)
            item_name = c1.selectbox("Atualizar valor de lavagem do item", options=items_df["name"].tolist())
            new_cost = c2.number_input("Novo valor unit. (R$)", min_value=0.0, step=0.1, value=0.0)
            update_submitted = c3.form_submit_button("Atualizar valor")
            if update_submitted:
                try:
                    item_id = int(items_df[items_df["name"] == item_name]["id"].iloc[0])
                    update_item_laundry_cost(item_id=item_id, laundry_unit_cost=float(new_cost))
                    st.success("Valor unitário de lavagem atualizado.")
                    items_df = pd.DataFrame(list_items())
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Não foi possível atualizar valor: {exc}")

        items_df["laundry_unit_cost"] = pd.to_numeric(items_df["laundry_unit_cost"], errors="coerce").fillna(0.0)
        st.dataframe(items_df, use_container_width=True, hide_index=True)

elif menu == "Lançamentos Lavanderia":
    st.subheader(f"Lançamentos da lavanderia - {UNIT_OPTIONS[selected_unit]}")
    st.info(
        "Use os tipos de relavagem quando o lote retorna mal lavado. "
        "Essas peças voltam para a lavanderia sem nova cobrança."
    )
    item_map = _items_map()
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

elif menu == "Lançamentos Operacionais":
    st.subheader(f"Lançamentos operacionais - {UNIT_OPTIONS[selected_unit]}")
    item_map = _items_map()
    if not item_map:
        st.warning("Cadastre pelo menos um item antes de registrar movimentos.")
    else:
        with st.form("form-operational", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            movement_date = c1.date_input("Data do movimento", value=date.today())
            item_name = c2.selectbox("Item", options=sorted(item_map.keys()))
            movement_label = c3.selectbox("Tipo de movimento", options=list(OPERATIONAL_LABELS.keys()))
            c4, c5, c6 = st.columns(3)
            quantity = c4.number_input("Quantidade", min_value=1, step=1, value=1)
            source_ref = c5.text_input("Referência", placeholder="NF, ordem interna")
            note = c6.text_input("Observação")
            move_submitted = st.form_submit_button("Salvar movimento")
            if move_submitted:
                try:
                    add_movement(
                        item_id=item_map[item_name],
                        movement_type=OPERATIONAL_LABELS[movement_label],
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
        recent_df = recent_df[recent_df["movement_type"].isin(set(OPERATIONAL_LABELS.values()))]
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
    item_map = _items_map()
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
