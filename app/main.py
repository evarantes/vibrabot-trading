import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from database import init_db, get_units, add_unit
from datetime import date

st.set_page_config(
    page_title="CODEXIAAUDITOR",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar banco de dados
init_db()

# Garantir unidades padrão
units = get_units()
if not units:
    add_unit("HOTEL", "hotel")

# ── CSS customizado ────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; }
    [data-testid="stSidebar"] { background-color: #f8fafc; }
    h1 { font-size: 2rem !important; font-weight: 900 !important; letter-spacing: -0.5px; }
    .stButton > button[kind="primary"] { background-color: #4f46e5; border-color: #4f46e5; }
    .stButton > button[kind="primary"]:hover { background-color: #4338ca; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🏨 Menu")
    st.divider()

    st.write("**Unidade para auditórios**")
    units_all = ["Estoque Central"] + get_units()
    selected_unit_label = st.selectbox(
        "Unidade",
        units_all,
        label_visibility="collapsed",
        key="sidebar_unit"
    )
    selected_unit = "CENTRAL" if selected_unit_label == "Estoque Central" else selected_unit_label

    st.write("**Dados de referência de auditoria**")
    ref_date = st.date_input("Data ref", value=date.today(), label_visibility="collapsed")

    st.divider()
    st.write("**Módulos**")
    modulo = st.radio(
        "modulo_radio",
        options=[
            "Cadastro de Itens (Central)",
            "Transferir Central → Unidade",
            "Lançamentos Lavanderia",
            "Estoque Central e de Uso",
            "Apuração Lavanderia (Planilha)",
            "Contagem Física",
            "Painel de guerrilha",
            "Auditório IA",
        ],
        label_visibility="collapsed"
    )

    st.divider()
    st.caption("💡 Dica: registre movimentos diariamente e faça contagem física no fechamento.")

# ── Header ─────────────────────────────────────────────────────────────────────
st.title("AUDITOR CODEXIA")
st.caption(f"Unidade selecionada: **{selected_unit_label}** | Auditoria inteligente de enxoval (compras, estoque, lavanderia e uso diário)")

# ── Roteamento de módulos ──────────────────────────────────────────────────────
if modulo == "Cadastro de Itens (Central)":
    from modules.cadastro_itens import render
    render()

elif modulo == "Transferir Central → Unidade":
    from modules.transferencias import render
    render()

elif modulo == "Lançamentos Lavanderia":
    from modules.lavanderia import render
    render(selected_unit=selected_unit)

elif modulo == "Estoque Central e de Uso":
    from modules.estoque import render
    render()

elif modulo == "Apuração Lavanderia (Planilha)":
    from modules.apuracao_lavanderia import render
    render()

elif modulo == "Contagem Física":
    from modules.contagem_fisica import render
    render(selected_unit=selected_unit)

elif modulo == "Painel de guerrilha":
    from modules.painel_guerrilha import render
    render()

elif modulo == "Auditório IA":
    from modules.auditoria_ia import render
    render(selected_unit=selected_unit)
