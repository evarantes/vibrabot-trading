import streamlit as st
from database import get_audit_data, save_audit_report, get_audit_reports, get_units
import json
from datetime import date
import os


def gerar_analise(dados, unidade):
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return _analise_openai(dados, unidade, api_key)
    return _analise_heuristica(dados, unidade)


def _analise_openai(dados, unidade, api_key):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        total_recebido = sum(d["total_received"] for d in dados)
        total_desfalque = sum(d["shortfall"] for d in dados)
        itens_criticos = sorted([d for d in dados if d["shortfall"] > 0], key=lambda x: x["shortfall"], reverse=True)

        prompt = f"""Você é auditor especialista em gestão de enxoval hoteleiro.
        
Unidade auditada: {unidade}
Data: {date.today().strftime('%d/%m/%Y')}

DADOS:
- Total recebido: {total_recebido} peças
- Total com desfalque: {total_desfalque} peças
- Percentual de desfalque: {round(total_desfalque/total_recebido*100, 1) if total_recebido > 0 else 0}%

Itens críticos (top 5):
{json.dumps(itens_criticos[:5], ensure_ascii=False, indent=2)}

Gere relatório com: diagnóstico, causas prováveis, recomendações e plano de ação. Em português."""

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[IA indisponível: {e}]\n\n" + _analise_heuristica(dados, unidade)


def _analise_heuristica(dados, unidade):
    total_recebido = sum(d["total_received"] for d in dados)
    total_desfalque = sum(d["shortfall"] for d in dados)
    pct = round(total_desfalque / total_recebido * 100, 1) if total_recebido > 0 else 0

    lines = [
        f"# RELATÓRIO DE AUDITORIA — {unidade}",
        f"\n**Data:** {date.today().strftime('%d/%m/%Y')}",
        "\n---",
        "\n## 1. DIAGNÓSTICO GERAL\n"
    ]

    if pct == 0:
        lines.append("✅ **EXCELENTE**: Nenhum desfalque detectado.")
    elif pct <= 2:
        lines.append(f"🟡 **ACEITÁVEL**: Desfalque de {pct}% dentro da margem tolerável.")
    elif pct <= 5:
        lines.append(f"🟠 **PREOCUPANTE**: Desfalque de {pct}% — investigação recomendada.")
    elif pct <= 10:
        lines.append(f"🔴 **CRÍTICO**: Desfalque de {pct}% — ação imediata necessária.")
    else:
        lines.append(f"⚠️ **ALERTA MÁXIMO**: Desfalque de {pct}% — possível desvio sistemático!")

    lines.append(f"\n- Total recebido: **{total_recebido} peças**")
    lines.append(f"- Desfalque: **{total_desfalque} peças ({pct}%)**")

    criticos = sorted([d for d in dados if d["shortfall"] > 0], key=lambda x: x["shortfall"], reverse=True)
    if criticos:
        lines.append("\n## 2. ITENS COM MAIOR DESFALQUE\n")
        for i, d in enumerate(criticos[:5], 1):
            p = round(d["shortfall"] / d["total_received"] * 100, 1) if d["total_received"] > 0 else 0
            lines.append(f"{i}. **{d['name']}**: -{d['shortfall']} peças ({p}%)")

    lines += [
        "\n## 3. CAUSAS PROVÁVEIS\n",
        "- Itens enviados para lavanderia sem retorno confirmado",
        "- Registros de transferência sem correspondência física",
        "- Perdas operacionais não lançadas no sistema",
        "- Furtos ou extravios não documentados",
        "\n## 4. RECOMENDAÇÕES\n",
        "1. Realizar inventário físico imediato",
        "2. Reconciliar todos os envios de lavanderia pendentes",
        "3. Verificar transferências sem confirmação de recebimento",
        "4. Implementar contagem diária por setor",
        "\n## 5. PLANO DE AÇÃO\n",
        "**24h:** Inventário físico completo",
        "**7 dias:** Reunião com equipe de governança",
        "**30 dias:** Ciclo de auditoria mensal",
        "\n---",
        "\n*Gerado pelo CodexiaAuditor — Sistema de Auditoria de Enxoval Hoteleiro*"
    ]
    return "\n".join(lines)


def render(selected_unit="GERAL"):
    st.header("Auditório IA — Análise de Desfalques")

    units = get_units()
    all_units_opt = ["GERAL (todos)", "CENTRAL"] + units

    col1, col2 = st.columns([3, 2])
    with col1:
        titulo = st.text_input("Título da auditoria",
                               value=f"Auditoria {date.today().strftime('%d/%m/%Y')} — {selected_unit}")
    with col2:
        unit_opt = st.selectbox("Unidade auditada", all_units_opt,
                                index=all_units_opt.index("CENTRAL") if "CENTRAL" in all_units_opt else 0,
                                key="audit_unit_sel")
        unit = None if unit_opt.startswith("GERAL") else unit_opt

    # Preview dos dados
    dados = get_audit_data(unit)
    if not dados:
        st.info("Nenhum dado disponível para auditoria.")
        return

    total_recebido = sum(d["total_received"] for d in dados)
    total_central = sum(d["central_balance"] for d in dados)
    total_lavanderia = sum(d["laundry_pending"] for d in dados)
    total_em_uso = sum(d["in_use"] for d in dados)
    total_desfalque = sum(d["shortfall"] for d in dados)
    pct_desf = round(total_desfalque / total_recebido * 100, 1) if total_recebido > 0 else 0

    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
    col_m1.metric("Total Recebido", total_recebido)
    col_m2.metric("Saldo Central", total_central)
    col_m3.metric("Na Lavanderia", total_lavanderia)
    col_m4.metric("Em Uso", total_em_uso)
    col_m5.metric("DESFALQUE", total_desfalque,
                  delta=f"{pct_desf}%" if total_desfalque > 0 else "0",
                  delta_color="inverse" if total_desfalque > 0 else "normal")

    # Tabela detalhada
    import pandas as pd
    df = pd.DataFrame(dados)[[
        "name", "category", "total_received", "central_balance",
        "laundry_pending", "in_use", "shortfall"
    ]]
    df.columns = ["Item", "Categoria", "Total Recebido", "Central", "Lavanderia", "Em Uso", "Desfalque"]

    def highlight_shortfall(row):
        pct = row["Desfalque"] / row["Total Recebido"] * 100 if row["Total Recebido"] > 0 else 0
        if row["Desfalque"] > 0 and pct > 10:
            return ["background-color: #fca5a5"] * len(row)
        elif row["Desfalque"] > 0:
            return ["background-color: #fde68a"] * len(row)
        return [""] * len(row)

    st.dataframe(df.style.apply(highlight_shortfall, axis=1), use_container_width=True, hide_index=True)

    st.divider()

    col_btn1, col_btn2 = st.columns([1, 2])
    with col_btn1:
        if st.button("🤖 Gerar Auditoria com IA", type="primary", key="btn_audit_gen"):
            with st.spinner("Analisando dados com IA..."):
                analise = gerar_analise(dados, unit_opt)
                report_json = json.dumps({"dados": dados, "totais": {
                    "total_recebido": total_recebido,
                    "total_central": total_central,
                    "total_lavanderia": total_lavanderia,
                    "total_em_uso": total_em_uso,
                    "total_desfalque": total_desfalque
                }}, ensure_ascii=False)
                save_audit_report(titulo, unit_opt, report_json, analise, {
                    "total_received": total_recebido,
                    "in_use": total_em_uso,
                    "laundry_pending": total_lavanderia,
                    "shortfall": total_desfalque
                })
                st.session_state["last_audit"] = analise
                st.rerun()

    if "last_audit" in st.session_state:
        st.markdown(st.session_state["last_audit"])
        if st.button("Limpar análise", key="clear_audit"):
            del st.session_state["last_audit"]
            st.rerun()

    # ── Histórico ──────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Histórico de Auditorias")
    reports = get_audit_reports()
    if reports:
        for r in reports:
            with st.expander(f"📋 {r['title']} — {r['created_at'][:10]} | Desfalque: {r['total_missing']} peças"):
                col_a, col_b, col_c, col_d = st.columns(4)
                col_a.metric("Recebido", r["total_purchased"])
                col_b.metric("Em Uso", r["total_in_use"])
                col_c.metric("Lavanderia", r["total_laundry"])
                col_d.metric("Desfalque", r["total_missing"])
                if r["ai_analysis"]:
                    st.markdown(r["ai_analysis"])
    else:
        st.info("Nenhuma auditoria salva ainda.")
