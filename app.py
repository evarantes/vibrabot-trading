from __future__ import annotations

from calendar import monthrange
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent / "src"))

from codexiaauditor.audit_engine import generate_audit_report
from codexiaauditor.auth import (
    ROLE_ADMIN,
    ROLE_MASTER,
    ROLE_USER,
    authenticate_user,
    change_password,
    create_user,
    ensure_master_user,
    get_user_by_id,
    get_user_permissions,
    list_users,
    update_user,
)
from codexiaauditor.database import init_db
from codexiaauditor.invoice_parser import (
    parse_access_key_metadata,
    parse_emission_date_to_date,
    parse_invoice_file,
)
from codexiaauditor.repository import (
    add_category,
    add_item,
    add_movement,
    cancel_transfer,
    edit_transfer,
    get_central_stock_report,
    get_balances,
    get_daily_movement_totals,
    get_item_theoretical_stock,
    get_laundry_billing_summary,
    get_laundry_period_item_report,
    get_transfer_by_id,
    list_item_laundry_rates,
    list_laundry_price_table,
    list_categories,
    list_items,
    list_recent_movements,
    list_recent_transfers,
    set_item_active,
    transfer_central_to_unit,
    upsert_laundry_rate,
    update_item,
    upsert_inventory_count,
)

st.set_page_config(page_title="CODEXIAAUDITOR", layout="wide")
init_db()

MOVEMENT_LABELS = {
    "PURCHASE": "Compra de enxoval",
    "STOCK_IN": "Ajuste de entrada no estoque central",
    "STOCK_OUT": "Ajuste de saída no estoque central",
    "LAUNDRY_SENT": "Enviado para lavanderia (cobrado)",
    "LAUNDRY_RETURNED": "Retorno da lavanderia (cobrado)",
    "LAUNDRY_REWASH_SENT": "Relavagem: reenviado sem cobrança",
    "LAUNDRY_REWASH_RETURNED": "Relavagem: retorno sem cobrança",
    "IN_USE_ALLOCATED": "Transferido para estoque de uso",
    "IN_USE_RETURNED": "Retorno de uso para estoque central",
    "LOSS": "Perda / baixa por avaria ou extravio",
}
LABEL_TO_MOVEMENT = {v: k for k, v in MOVEMENT_LABELS.items()}

LAUNDRY_LABELS = {
    "Enviado para lavanderia (cobrado)": "LAUNDRY_SENT",
    "Retorno da lavanderia (cobrado)": "LAUNDRY_RETURNED",
    "Relavagem: reenviado sem cobrança": "LAUNDRY_REWASH_SENT",
    "Relavagem: retorno sem cobrança": "LAUNDRY_REWASH_RETURNED",
}
CENTRAL_STOCK_LABELS = {
    "Compra de enxoval": "PURCHASE",
    "Ajuste de entrada no estoque central": "STOCK_IN",
    "Ajuste de saída no estoque central": "STOCK_OUT",
    "Perda / baixa por avaria ou extravio": "LOSS",
}
UNIT_STOCK_LABELS = {
    "Ajuste de entrada no estoque da unidade": "STOCK_IN",
    "Ajuste de saída no estoque da unidade": "STOCK_OUT",
    "Transferir do estoque central para estoque de uso": "IN_USE_ALLOCATED",
    "Retornar do estoque de uso para estoque central": "IN_USE_RETURNED",
    "Perda / baixa por avaria ou extravio": "LOSS",
}


UNIT_OPTIONS = {"CENTRAL": "Estoque Central", "HOTEL": "Hotel", "CLUB": "Club"}
UNIT_LABELS = {
    "CENTRAL": "🏬 Estoque Central",
    "HOTEL": "🏨 Hotel",
    "CLUB": "🏖 Club",
}

MENU_LABELS = {
    "items": "🏗 Cadastro de Itens (Central)",
    "stock": "📦 Estoque Central e de Uso",
    "prices": "💲 Tabela de Preços Lavanderia",
    "transfer": "🔁 Transferir Central -> Unidade",
    "laundry": "🧺 Lançamentos Lavanderia",
    "billing": "🧾 Apuração Lavanderia (Planilha)",
    "count": "🧮 Contagem Física",
    "dashboard": "📊 Painel de Controle",
    "audit": "🤖 Auditoria IA",
    "users": "👤 Gestão de Usuários",
}

MENU_TO_LEGACY = {
    "items": "Cadastro de Itens (Central)",
    "stock": "Estoque Central e de Uso",
    "prices": "Tabela de Preços Lavanderia",
    "transfer": "Transferir Central -> Unidade",
    "laundry": "Lançamentos Lavanderia",
    "billing": "Apuração Lavanderia (Planilha)",
    "count": "Contagem Física",
    "dashboard": "Painel de Controle",
    "audit": "Auditoria IA",
    "users": "Gestão de Usuários",
}


def _items_map(operation_unit: str) -> dict[str, int]:
    return {row["name"]: int(row["id"]) for row in list_items(operation_unit=operation_unit)}


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


def _norm_text(value: str) -> str:
    base = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", base).strip().upper()


def _format_brl(value: float | int) -> str:
    numeric = float(value or 0.0)
    return f"R$ {numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_decimal_br(value: float | int) -> str:
    numeric = float(value or 0.0)
    return f"{numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_decimal_br(value: object) -> float:
    if value is None:
        return 0.0
    raw = str(value).strip()
    if not raw:
        return 0.0
    normalized = raw.replace("R$", "").replace(" ", "")
    if "," in normalized and "." in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    else:
        normalized = normalized.replace(",", ".")
    try:
        return max(float(normalized), 0.0)
    except ValueError:
        raise ValueError(f"Valor inválido: {value}. Use formato 0,00.")


def _format_date_br(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    raw = str(value).strip()
    if not raw:
        return ""
    try:
        return date.fromisoformat(raw).strftime("%d/%m/%Y")
    except ValueError:
        pass
    for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%d/%m/%Y")
        except Exception:  # noqa: BLE001
            continue
    return raw


def _parse_date_br(value: object) -> date:
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Data vazia. Use DD/MM/AAAA.")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data inválida: {value}. Use DD/MM/AAAA.")


def _logout() -> None:
    st.session_state.pop("auth_user_id", None)
    st.session_state.pop("auth_user", None)
    st.rerun()


ensure_master_user(list(MENU_LABELS.keys()))

auth_user_id = st.session_state.get("auth_user_id")
auth_user = get_user_by_id(int(auth_user_id)) if auth_user_id else None
if auth_user and not bool(auth_user.get("is_active", True)):
    auth_user = None
    st.session_state.pop("auth_user_id", None)
    st.session_state.pop("auth_user", None)

if not auth_user:
    st.title("AUDITOR CODEXIA")
    st.subheader("Acesso ao sistema")
    with st.form("form-login"):
        c1, c2 = st.columns(2)
        login_email = c1.text_input("E-mail")
        login_password = c2.text_input("Senha", type="password")
        login_submit = st.form_submit_button("Entrar")
        if login_submit:
            user = authenticate_user(login_email, login_password)
            if not user:
                st.error("Credenciais inválidas.")
            else:
                st.session_state["auth_user_id"] = int(user["id"])
                st.rerun()
    st.stop()

st.session_state["auth_user"] = auth_user

if bool(auth_user.get("must_change_password", False)):
    st.title("AUDITOR CODEXIA")
    st.warning("Altere sua senha no primeiro acesso para continuar.")
    with st.form("form-change-password-first-login"):
        p1, p2 = st.columns(2)
        new_pass = p1.text_input("Nova senha", type="password")
        confirm_pass = p2.text_input("Confirmar nova senha", type="password")
        save_new_pass = st.form_submit_button("Salvar nova senha")
        if save_new_pass:
            if len(new_pass.strip()) < 6:
                st.error("A nova senha deve ter no mínimo 6 caracteres.")
            elif new_pass != confirm_pass:
                st.error("A confirmação da senha não confere.")
            else:
                try:
                    change_password(int(auth_user["id"]), new_pass.strip())
                    st.success("Senha alterada com sucesso. Faça login novamente.")
                    _logout()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha ao alterar senha: {exc}")
    st.stop()

if str(auth_user.get("role")) == ROLE_MASTER:
    allowed_menu_keys = list(MENU_LABELS.keys())
else:
    allowed_menu_keys = get_user_permissions(int(auth_user["id"]))
    allowed_menu_keys = [x for x in allowed_menu_keys if x in MENU_LABELS]

if not allowed_menu_keys:
    st.error("Seu usuário não possui permissões de acesso. Contate o administrador.")
    if st.button("Sair"):
        _logout()
    st.stop()

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f7fafc 0%, #eef3f9 100%);
    }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stDateInput label,
    [data-testid="stSidebar"] .stRadio > label {
        font-weight: 700;
        color: #27364a;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
        background: #ffffff;
        border: 1px solid #d7e2ef;
        border-radius: 10px;
        padding: 8px 10px;
        margin-bottom: 6px;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
        border-color: #8bb2e0;
        background: #f8fbff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("## Menu")
st.sidebar.caption(f"👤 {auth_user['full_name']} ({auth_user['role']})")
if st.sidebar.button("Sair"):
    _logout()
selected_unit = st.sidebar.selectbox(
    "Unidade para auditoria",
    options=list(UNIT_OPTIONS.keys()),
    format_func=lambda x: UNIT_LABELS[x],
)
as_of_date = st.sidebar.date_input("Dados de referência de auditoria", value=date.today())
menu_key = st.sidebar.radio(
    "Módulos",
    options=allowed_menu_keys,
    format_func=lambda x: MENU_LABELS[x],
)
menu = MENU_TO_LEGACY[menu_key]
st.sidebar.caption(
    f"Unidade ativa: **{UNIT_OPTIONS[selected_unit]}**\n\n"
    f"Módulo ativo: **{MENU_LABELS[menu_key]}**"
)
st.sidebar.info("Dica: registre movimentos diariamente e faça contagem física no fechamento.")

st.title("AUDITOR CODEXIA")
st.caption(
    f"Unidade selecionada: **{UNIT_OPTIONS[selected_unit]}** | "
    "Auditoria inteligente de enxoval (compras, estoque, lavanderia e uso diário)"
)

if menu == "Cadastro de Itens (Central)":
    st.subheader("Cadastro mestre de itens (Estoque Central)")
    if selected_unit != "CENTRAL":
        st.info("O cadastro mestre é no estoque CENTRAL. A unidade selecionada no menu lateral não altera este módulo.")

    with st.popover("Criar categoria"):
        with st.form("form-create-category", clear_on_submit=True):
            new_category_name = st.text_input("Nome da categoria", placeholder="Ex: Roupa de Banho")
            save_category = st.form_submit_button("Salvar categoria")
            if save_category:
                try:
                    add_category(new_category_name)
                    st.success("Categoria criada.")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Não foi possível criar categoria: {exc}")

    categories = list_categories(active_only=True)
    category_names = [str(row["name"]) for row in categories]
    if not category_names:
        st.warning("Nenhuma categoria cadastrada. Crie ao menos uma categoria para cadastrar itens.")
    else:
        with st.form("form-item", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            name = col1.text_input("Nome do item", placeholder="Ex: Lençol 180 fios")
            category = col2.selectbox("Categoria", options=category_names)
            par_level = col3.number_input("Nível mínimo (reserva)", min_value=0, step=1, value=0)
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
                            laundry_unit_cost=0.0,
                            operation_unit="CENTRAL",
                        )
                        st.success("Item cadastrado com sucesso.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Não foi possível cadastrar: {exc}")

    items_df = pd.DataFrame(list_items(operation_unit="CENTRAL", active_only=False))
    if items_df.empty:
        st.warning("Nenhum item cadastrado ainda.")
    else:
        select_labels = [f"{int(row['id'])} - {row['name']}" for _, row in items_df.iterrows()]
        select_map = {label: int(label.split(" - ")[0]) for label in select_labels}

        a1, a2, a3, a4 = st.columns(4)
        selected_label = a1.selectbox("Item para ação", options=select_labels)
        selected_item_id = select_map[selected_label]

        if a2.button("Editar item"):
            st.session_state["central_edit_item_id"] = selected_item_id
        if a3.button("Ativar item"):
            set_item_active(selected_item_id, True)
            st.success("Item ativado.")
            st.rerun()
        if a4.button("Desativar item"):
            set_item_active(selected_item_id, False)
            st.success("Item desativado.")
            st.rerun()

        edit_item_id = st.session_state.get("central_edit_item_id")
        if edit_item_id is not None:
            edit_row = items_df[items_df["id"] == edit_item_id]
            if not edit_row.empty:
                current = edit_row.iloc[0]
                edit_categories = category_names.copy()
                current_category = str(current["category"])
                if current_category not in edit_categories:
                    edit_categories.append(current_category)

                with st.form("form-edit-item"):
                    st.markdown("**Editar item selecionado**")
                    e1, e2, e3, e4 = st.columns(4)
                    new_name = e1.text_input("Nome", value=str(current["name"]))
                    default_idx = edit_categories.index(current_category)
                    new_category = e2.selectbox("Categoria", options=edit_categories, index=default_idx)
                    new_par_level = e3.number_input(
                        "Nível mínimo (reserva)",
                        min_value=0,
                        step=1,
                        value=int(current["par_level"]),
                    )
                    new_active = e4.checkbox("Ativo", value=bool(current["active"]))
                    save_edit = st.form_submit_button("Salvar edição")
                    if save_edit:
                        try:
                            update_item(
                                item_id=int(current["id"]),
                                name=new_name,
                                category=new_category,
                                par_level=int(new_par_level),
                                laundry_unit_cost=float(current["laundry_unit_cost"] or 0.0),
                                active=bool(new_active),
                            )
                            st.success("Item atualizado com sucesso.")
                            st.session_state.pop("central_edit_item_id", None)
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Falha ao editar item: {exc}")

        st.dataframe(
            items_df[
                ["id", "name", "category", "par_level", "active"]
            ].rename(
                columns={
                    "id": "id",
                    "name": "item",
                    "category": "categoria",
                    "par_level": "nivel_minimo",
                    "active": "ativo",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

elif menu == "Gestão de Usuários":
    st.subheader("Gestão de usuários e permissões")
    current_role = str(auth_user.get("role", ""))
    if current_role not in {ROLE_MASTER, ROLE_ADMIN}:
        st.error("Acesso negado.")
        st.stop()

    permission_keys = list(MENU_LABELS.keys())
    users_data = list_users()
    user_table_rows: list[dict[str, object]] = []
    for user in users_data:
        user_permissions = get_user_permissions(int(user["id"]))
        user_table_rows.append(
            {
                "id": int(user["id"]),
                "nome": user["full_name"],
                "email": user["email"],
                "perfil": user["role"],
                "ativo": bool(user["is_active"]),
                "troca_senha_primeiro_login": bool(user["must_change_password"]),
                "modulos": ", ".join(MENU_LABELS[k] for k in user_permissions if k in MENU_LABELS),
            }
        )
    st.dataframe(pd.DataFrame(user_table_rows), use_container_width=True, hide_index=True)

    st.markdown("### Criar novo usuário")
    with st.form("form-create-user"):
        c1, c2, c3 = st.columns(3)
        new_name = c1.text_input("Nome completo")
        new_email = c2.text_input("E-mail")
        new_role = c3.selectbox("Perfil", options=[ROLE_ADMIN, ROLE_USER])
        c4, c5, c6 = st.columns(3)
        new_password = c4.text_input("Senha inicial", type="password", value="123456")
        must_change = c5.checkbox("Forçar troca no primeiro login", value=True)
        new_active = c6.checkbox("Ativo", value=True)
        selected_modules = st.multiselect(
            "Módulos permitidos",
            options=permission_keys,
            format_func=lambda x: MENU_LABELS[x],
            default=[k for k in permission_keys if k != "users"] if new_role == ROLE_USER else permission_keys,
        )
        create_submit = st.form_submit_button("Criar usuário")
        if create_submit:
            try:
                if not new_name.strip() or not new_email.strip():
                    st.error("Nome e e-mail são obrigatórios.")
                elif len(new_password.strip()) < 6:
                    st.error("A senha inicial deve ter pelo menos 6 caracteres.")
                else:
                    create_user(
                        email=new_email,
                        full_name=new_name,
                        role=new_role,
                        password=new_password.strip(),
                        must_change_password=must_change,
                        is_active=new_active,
                        module_keys=selected_modules,
                    )
                    st.success("Usuário criado com sucesso.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha ao criar usuário: {exc}")

    st.markdown("### Editar usuário existente")
    if users_data:
        option_labels = [
            f"#{int(u['id'])} | {u['full_name']} | {u['email']} | {u['role']}"
            for u in users_data
        ]
        selected_user_label = st.selectbox("Selecione o usuário", options=option_labels, key="edit_user_select")
        selected_user_id = int(selected_user_label.split("|")[0].replace("#", "").strip())
        selected_user = next((u for u in users_data if int(u["id"]) == selected_user_id), None)
        if selected_user:
            selected_permissions = get_user_permissions(selected_user_id)
            with st.form("form-edit-user"):
                e1, e2, e3 = st.columns(3)
                edit_name = e1.text_input("Nome", value=str(selected_user["full_name"]))
                edit_role = e2.selectbox("Perfil", options=[ROLE_MASTER, ROLE_ADMIN, ROLE_USER], index=[ROLE_MASTER, ROLE_ADMIN, ROLE_USER].index(str(selected_user["role"])))
                edit_active = e3.checkbox("Ativo", value=bool(selected_user["is_active"]))
                e4, e5 = st.columns(2)
                edit_must_change = e4.checkbox(
                    "Exigir troca de senha no próximo login",
                    value=bool(selected_user["must_change_password"]),
                )
                reset_password = e5.text_input("Nova senha (opcional)", type="password")
                edit_modules = st.multiselect(
                    "Módulos permitidos",
                    options=permission_keys,
                    format_func=lambda x: MENU_LABELS[x],
                    default=selected_permissions,
                    key=f"edit_modules_{selected_user_id}",
                )
                save_edit_user = st.form_submit_button("Salvar alterações do usuário")
                if save_edit_user:
                    try:
                        if int(selected_user_id) == int(auth_user["id"]) and edit_role != ROLE_MASTER and current_role == ROLE_MASTER:
                            st.error("O usuário master logado não pode remover seu próprio perfil master.")
                        elif str(selected_user["email"]).lower() == "evarantes2@gmail.com" and not edit_active:
                            st.error("O usuário master principal não pode ser desativado.")
                        else:
                            update_user(
                                user_id=selected_user_id,
                                full_name=edit_name,
                                role=edit_role,
                                is_active=bool(edit_active),
                                must_change_password=bool(edit_must_change),
                                module_keys=edit_modules if edit_role != ROLE_MASTER else permission_keys,
                                new_password=reset_password.strip(),
                            )
                            st.success("Usuário atualizado com sucesso.")
                            st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Falha ao atualizar usuário: {exc}")

elif menu == "Transferir Central -> Unidade":
    st.subheader("Transferência do estoque CENTRAL para HOTEL/CLUB")
    central_items = pd.DataFrame(list_items(operation_unit="CENTRAL", active_only=True))
    if central_items.empty:
        st.warning("Cadastre itens no estoque CENTRAL antes de transferir.")
    else:
        transfer_options = []
        transfer_map: dict[str, int] = {}
        for _, row in central_items.iterrows():
            stock = get_item_theoretical_stock(
                int(row["id"]),
                date.today(),
                operation_unit="CENTRAL",
            )
            label = f"{row['name']} - disponível: {stock}"
            transfer_options.append(label)
            transfer_map[label] = int(row["id"])

        with st.form("form-transfer-central", clear_on_submit=True):
            t1, t2, t3, t4, t5 = st.columns(5)
            selected_label = t1.selectbox("Item do CENTRAL", options=transfer_options)
            target_unit = t2.selectbox("Destino", options=["HOTEL", "CLUB"])
            qty = t3.number_input("Quantidade a transferir", min_value=1, step=1, value=1)
            transfer_date = t4.date_input("Data da transferência", value=date.today())
            note = t5.text_input("Observação")
            transfer_submitted = st.form_submit_button("Transferir")
            if transfer_submitted:
                try:
                    central_item_id = transfer_map[selected_label]
                    result = transfer_central_to_unit(
                        central_item_id=central_item_id,
                        target_unit=target_unit,
                        quantity=int(qty),
                        movement_date=transfer_date,
                        laundry_unit_cost=0.0,
                        source_ref="",
                        note=note,
                    )
                    st.success(
                        f"Transferência #{result['transfer_id']} concluída: "
                        f"{result['quantity']} un. para {target_unit}."
                    )
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Falha na transferência: {exc}")

        st.markdown("**Histórico das últimas transferências**")
        transfers_df = pd.DataFrame(list_recent_transfers(limit=100))
        if transfers_df.empty:
            st.info("Ainda não há transferências registradas.")
        else:
            display_df = transfers_df.rename(
                columns={
                    "id": "id",
                    "transfer_date": "data_transferencia",
                    "central_item_name": "item_central",
                    "target_unit": "destino",
                    "quantity": "quantidade",
                    "status": "status",
                    "note": "observacao",
                    "cancel_reason": "motivo_anulacao",
                }
            )
            st.dataframe(
                display_df[
                    [
                        "id",
                        "data_transferencia",
                        "item_central",
                        "destino",
                        "quantidade",
                        "status",
                        "observacao",
                        "motivo_anulacao",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

            action_options = [
                f"#{int(row['id'])} | {row['central_item_name']} -> {row['target_unit']} | "
                f"qtd={int(row['quantity'])} | status={row['status']}"
                for _, row in transfers_df.iterrows()
            ]
            selected_action = st.selectbox("Transferência para ação", options=action_options)
            selected_transfer_id = int(selected_action.split("|")[0].replace("#", "").strip())
            selected_transfer = get_transfer_by_id(selected_transfer_id)

            if selected_transfer and selected_transfer["status"] == "ACTIVE":
                with st.expander("Editar transferência", expanded=False):
                    with st.form("form-edit-transfer"):
                        e1, e2, e3, e4 = st.columns(4)
                        new_target = e1.selectbox(
                            "Novo destino",
                            options=["HOTEL", "CLUB"],
                            index=0 if str(selected_transfer["target_unit"]) == "HOTEL" else 1,
                        )
                        new_qty = e2.number_input(
                            "Nova quantidade",
                            min_value=1,
                            step=1,
                            value=int(selected_transfer["quantity"]),
                        )
                        raw_date = selected_transfer["transfer_date"]
                        current_transfer_date = raw_date if isinstance(raw_date, date) else date.fromisoformat(str(raw_date))
                        new_date = e3.date_input("Nova data", value=current_transfer_date)
                        new_note = e4.text_input("Nova observação", value=str(selected_transfer.get("note") or ""))
                        submit_edit = st.form_submit_button("Salvar edição da transferência")
                        if submit_edit:
                            try:
                                new_transfer = edit_transfer(
                                    transfer_id=selected_transfer_id,
                                    target_unit=new_target,
                                    quantity=int(new_qty),
                                    transfer_date=new_date,
                                    note=new_note,
                                )
                                st.success(
                                    f"Transferência editada com sucesso. Nova transferência #{new_transfer['transfer_id']}."
                                )
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                st.error(f"Falha ao editar transferência: {exc}")

                with st.expander("Anular transferência", expanded=False):
                    cancel_reason = st.text_input("Motivo da anulação", key=f"cancel_reason_{selected_transfer_id}")
                    if st.button("Anular transferência selecionada", key=f"btn_cancel_transfer_{selected_transfer_id}"):
                        try:
                            cancel_transfer(selected_transfer_id, cancel_reason=cancel_reason)
                            st.success("Transferência anulada com sucesso.")
                            st.rerun()
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Falha ao anular transferência: {exc}")
            else:
                st.info("Esta transferência já está anulada. Se necessário, crie uma nova.")

elif menu == "Lançamentos Lavanderia":
    st.subheader(f"Lançamentos da lavanderia - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.warning("Lavanderia deve ser lançada em HOTEL ou CLUB. O CENTRAL não envia para lavanderia.")
        st.stop()
    st.info(
        "Use os tipos de relavagem quando o lote retorna mal lavado. "
        "Essas peças voltam para a lavanderia sem nova cobrança."
    )
    item_map = _items_map(selected_unit)
    if not item_map:
        st.warning("Cadastre pelo menos um item antes de lançar movimentações da lavanderia.")
    else:
        top1, top2, top3 = st.columns(3)
        laundry_date = top1.date_input("Data", value=date.today(), key=f"laundry_template_date_{selected_unit}")
        romaneio = top2.text_input("Romaneio", key=f"laundry_template_romaneio_{selected_unit}")
        note_general = top3.text_input("Observação geral", key=f"laundry_template_note_{selected_unit}")

        st.markdown("**Planilha de lançamento da lavanderia**")
        item_names = sorted(item_map.keys())
        template_rows = [
            {
                "ITENS": name,
                "Coleta": 0,
                "Entrega": 0,
                "Env. Relavagem": 0,
                "Dev. Relavagem": 0,
            }
            for name in item_names
        ]
        sheet_state_key = f"laundry_template_rows_{selected_unit}"
        if sheet_state_key not in st.session_state:
            st.session_state[sheet_state_key] = pd.DataFrame(template_rows)
        else:
            current_df = st.session_state[sheet_state_key]
            current_items = current_df["ITENS"].tolist() if "ITENS" in current_df.columns else []
            if current_items != item_names:
                st.session_state[sheet_state_key] = pd.DataFrame(template_rows)

        with st.form(f"form_laundry_template_{selected_unit}", clear_on_submit=False):
            laundry_sheet_df = st.data_editor(
                st.session_state[sheet_state_key],
                use_container_width=True,
                hide_index=True,
                num_rows="fixed",
                key=f"laundry_template_editor_{selected_unit}",
                disabled=["ITENS"],
                column_config={
                    "ITENS": st.column_config.TextColumn("ITENS"),
                    "Coleta": st.column_config.NumberColumn("Coleta", min_value=0, step=1),
                    "Entrega": st.column_config.NumberColumn("Entrega", min_value=0, step=1),
                    "Env. Relavagem": st.column_config.NumberColumn("Env. Relavagem", min_value=0, step=1),
                    "Dev. Relavagem": st.column_config.NumberColumn("Dev. Relavagem", min_value=0, step=1),
                },
            )
            save_template_submit = st.form_submit_button("Salvar romaneio da planilha")
        st.session_state[sheet_state_key] = laundry_sheet_df

        if save_template_submit:
            def _to_int_non_negative(value: object) -> int:
                try:
                    n = int(float(value or 0))
                    return max(n, 0)
                except Exception:  # noqa: BLE001
                    return 0

            movements_saved = 0
            for _, row in laundry_sheet_df.iterrows():
                item_name = str(row.get("ITENS") or "").strip()
                if not item_name or item_name not in item_map:
                    continue

                payload = [
                    ("LAUNDRY_SENT", _to_int_non_negative(row.get("Coleta"))),
                    ("LAUNDRY_RETURNED", _to_int_non_negative(row.get("Entrega"))),
                    ("LAUNDRY_REWASH_SENT", _to_int_non_negative(row.get("Env. Relavagem"))),
                    ("LAUNDRY_REWASH_RETURNED", _to_int_non_negative(row.get("Dev. Relavagem"))),
                ]
                for movement_type, qty in payload:
                    if qty <= 0:
                        continue
                    add_movement(
                        item_id=item_map[item_name],
                        movement_type=movement_type,
                        quantity=qty,
                        movement_date=laundry_date,
                        operation_unit=selected_unit,
                        source_ref=str(romaneio or "").strip(),
                        note=str(note_general or "").strip(),
                    )
                    movements_saved += 1

            if movements_saved == 0:
                st.warning("Nenhum valor lançado. Preencha a planilha e informe quantidades maiores que zero.")
            else:
                st.success(f"Romaneio salvo com sucesso. {movements_saved} movimentação(ões) registrada(s).")
                st.session_state[sheet_state_key] = pd.DataFrame(template_rows)

    summary = get_laundry_billing_summary(days=30, ref_date=as_of_date, operation_unit=selected_unit)
    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Peças enviadas (30d)", int(summary["billed_sent"]))
    l2.metric("Peças entregues/cobradas (30d)", int(summary.get("charged_qty", summary["billed_returned"])))
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

elif menu == "Estoque Central e de Uso":
    st.subheader(f"Estoque central e de uso - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.caption("Entrada de compras e ajustes do estoque central.")
        active_central_items = pd.DataFrame(list_items(operation_unit="CENTRAL", active_only=True))
        if active_central_items.empty:
            st.warning("Ative ao menos um item no cadastro central para lançar compras/movimentações.")
        else:
            central_item_map = {row["name"]: int(row["id"]) for _, row in active_central_items.iterrows()}
            central_form_labels = list(CENTRAL_STOCK_LABELS.keys())
            tab_manual, tab_import = st.tabs(["Lançamento manual", "Importar NF (PDF/XML/Chave)"])

            with tab_manual:
                with st.form("form-central-stock", clear_on_submit=True):
                    f1, f2, f3 = st.columns(3)
                    movement_date = f1.date_input("Data da compra/movimento", value=date.today(), key="central_movement_date")
                    item_name = f2.selectbox("Selecionar item", options=sorted(central_item_map.keys()))
                    movement_label = f3.selectbox("Tipo de movimento", options=central_form_labels)

                    f4, f5, f6 = st.columns(3)
                    quantity = f4.number_input("Quantidade", min_value=1, step=1, value=1, key="central_qty")
                    invoice_number = f5.text_input("Número da NF / chave", placeholder="Ex: 12345 ou chave de acesso")
                    unit_purchase_value = f6.number_input(
                        "Valor de compra unitário (R$)",
                        min_value=0.0,
                        step=0.01,
                        value=0.0,
                    )

                    auto_total = round(float(quantity) * float(unit_purchase_value), 2)
                    g1, g2 = st.columns(2)
                    g1.number_input(
                        "Valor total (R$) - automático",
                        min_value=0.0,
                        step=0.01,
                        value=float(auto_total),
                        disabled=True,
                    )
                    note = g2.text_input("Observação")

                    save_central_move = st.form_submit_button("Salvar movimentação de estoque central")
                    if save_central_move:
                        try:
                            movement_type = CENTRAL_STOCK_LABELS[movement_label]
                            if movement_type == "PURCHASE" and not invoice_number.strip():
                                st.error("Informe o número da NF/chave para lançamento de compra.")
                            else:
                                add_movement(
                                    item_id=central_item_map[item_name],
                                    movement_type=movement_type,
                                    quantity=int(quantity),
                                    movement_date=movement_date,
                                    operation_unit="CENTRAL",
                                    source_ref=invoice_number,
                                    movement_unit_cost=float(unit_purchase_value),
                                    movement_total_value=float(auto_total),
                                    note=note,
                                )
                                st.success("Movimentação central registrada.")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Falha ao salvar movimentação: {exc}")

            with tab_import:
                st.markdown("**Importar nota fiscal para alimentar estoque central**")
                up1, up2 = st.columns(2)
                uploaded_nf_file = up1.file_uploader("Enviar NF (XML ou PDF)", type=["xml", "pdf"])
                access_key_input = up2.text_input("Ou informar chave de acesso (44 dígitos)")
                extract_clicked = st.button("Extrair dados da NF", key="extract_invoice_button")

                if extract_clicked:
                    try:
                        if uploaded_nf_file is not None:
                            extracted = parse_invoice_file(uploaded_nf_file.name, uploaded_nf_file.getvalue())
                        elif access_key_input.strip():
                            extracted = parse_access_key_metadata(access_key_input)
                        else:
                            raise ValueError("Envie um arquivo XML/PDF ou informe uma chave de acesso.")
                        st.session_state["central_invoice_extract"] = extracted
                        st.success("Dados da nota extraídos.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Não foi possível extrair a nota: {exc}")

                extracted = st.session_state.get("central_invoice_extract")
                if extracted:
                    hdr1, hdr2, hdr3, hdr4 = st.columns(4)
                    hdr1.text_input("Número NF", value=str(extracted.get("invoice_number", "")), disabled=True)
                    hdr2.text_input("Série", value=str(extracted.get("series", "")), disabled=True)
                    hdr3.text_input("Data emissão", value=str(extracted.get("emission_date", "")), disabled=True)
                    hdr4.text_input("Chave acesso", value=str(extracted.get("access_key", "")), disabled=True)

                    extracted_items = extracted.get("items", [])
                    if not extracted_items:
                        st.info(
                            "Sem itens extraídos automaticamente. Para chave de acesso isolada, "
                            "a extração de itens depende de integração externa de consulta."
                        )
                    else:
                        st.markdown("**Itens extraídos da nota**")
                        central_names = sorted(central_item_map.keys())
                        normalized_name_map = {_norm_text(name): name for name in central_names}

                        with st.form("form-imported-items"):
                            launch_payload: list[dict[str, Any]] = []
                            for idx, ext_item in enumerate(extracted_items):
                                c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
                                description = str(ext_item.get("description", "")).strip()
                                qty_default = float(ext_item.get("quantity", 0) or 0)
                                unit_default = float(ext_item.get("unit_value", 0) or 0)

                                desc_norm = _norm_text(description)
                                default_name = ""
                                if desc_norm in normalized_name_map:
                                    default_name = normalized_name_map[desc_norm]
                                else:
                                    for norm_name, original_name in normalized_name_map.items():
                                        if desc_norm and (desc_norm in norm_name or norm_name in desc_norm):
                                            default_name = original_name
                                            break

                                options = ["-- selecione item --"] + central_names
                                default_idx = options.index(default_name) if default_name in options else 0
                                selected_item_name = c1.selectbox(
                                    f"Item sistema #{idx + 1}",
                                    options=options,
                                    index=default_idx,
                                    key=f"import_item_{idx}",
                                )
                                qty = c2.number_input(
                                    f"Qtd #{idx + 1}",
                                    min_value=0.0,
                                    step=1.0,
                                    value=max(qty_default, 0.0),
                                    key=f"import_qty_{idx}",
                                )
                                unit_val = c3.number_input(
                                    f"Vlr unit #{idx + 1}",
                                    min_value=0.0,
                                    step=0.01,
                                    value=max(unit_default, 0.0),
                                    key=f"import_unit_{idx}",
                                )
                                c4.number_input(
                                    f"Vlr total #{idx + 1}",
                                    min_value=0.0,
                                    step=0.01,
                                    value=round(float(qty) * float(unit_val), 2),
                                    disabled=True,
                                    key=f"import_total_{idx}",
                                )
                                import_row = c5.checkbox(
                                    f"Importar #{idx + 1}",
                                    value=default_idx > 0,
                                    key=f"import_flag_{idx}",
                                )
                                st.caption(f"Descrição NF: {description}")

                                launch_payload.append(
                                    {
                                        "selected_item_name": selected_item_name,
                                        "description": description,
                                        "qty": float(qty),
                                        "unit_val": float(unit_val),
                                        "import_row": bool(import_row),
                                    }
                                )

                            launch_import = st.form_submit_button("Lançar itens importados no estoque central")
                            if launch_import:
                                imported_count = 0
                                emission_date = parse_emission_date_to_date(
                                    str(extracted.get("emission_date", "")),
                                    fallback=date.today(),
                                )
                                source_ref = str(extracted.get("invoice_number") or extracted.get("access_key") or "").strip()
                                for row in launch_payload:
                                    if not row["import_row"]:
                                        continue
                                    if row["selected_item_name"] == "-- selecione item --":
                                        continue
                                    if row["qty"] <= 0:
                                        continue
                                    item_id = central_item_map[row["selected_item_name"]]
                                    auto_total = round(row["qty"] * row["unit_val"], 2)
                                    add_movement(
                                        item_id=item_id,
                                        movement_type="PURCHASE",
                                        quantity=int(round(row["qty"])),
                                        movement_date=emission_date,
                                        operation_unit="CENTRAL",
                                        source_ref=source_ref,
                                        movement_unit_cost=row["unit_val"],
                                        movement_total_value=auto_total,
                                        note=f"Importado de NF - Item NF: {row['description']}",
                                    )
                                    imported_count += 1

                                if imported_count == 0:
                                    st.warning("Nenhum item foi importado. Marque itens válidos e selecione item do sistema.")
                                else:
                                    st.success(f"{imported_count} item(ns) importado(s) com sucesso para o estoque central.")

        stock_report = pd.DataFrame(get_central_stock_report(as_of_date=as_of_date))
        if stock_report.empty:
            st.info("Sem dados no relatório de estoque central.")
        else:
            stock_report["tipo_movimentacao"] = stock_report["last_movement_type"].map(MOVEMENT_LABELS).fillna(
                stock_report["last_movement_type"]
            )
            report_df = stock_report.rename(
                columns={
                    "last_purchase_date": "data_ultima_compra",
                    "name": "item",
                    "stock_qty": "quantidade_estoque",
                    "last_invoice": "numero_nf_ultima_compra",
                    "last_unit_cost": "valor_unitario_item",
                    "last_total_value": "valor_total_item",
                    "last_note": "observacao",
                }
            )
            st.markdown("**Relatório do estoque central**")
            st.dataframe(
                report_df[
                    [
                        "data_ultima_compra",
                        "item",
                        "tipo_movimentacao",
                        "quantidade_estoque",
                        "numero_nf_ultima_compra",
                        "valor_unitario_item",
                        "valor_total_item",
                        "observacao",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.caption(
            "Controle de estoque da unidade, estoque de uso (alocação/retorno) e perdas."
        )
        operational_labels = UNIT_STOCK_LABELS
        item_map = _items_map(selected_unit)
        if not item_map:
            st.warning("Cadastre pelo menos um item antes de registrar movimentos.")
        else:
            with st.form("form-operational", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                movement_date = c1.date_input("Data do movimento", value=date.today())
                item_name = c2.selectbox("Item", options=sorted(item_map.keys()))
                movement_label = c3.selectbox(
                    "Tipo de movimento",
                    options=list(operational_labels.keys()),
                    help="Use este módulo para ajustes de estoque e movimentação de uso diário.",
                )
                c4, c5, c6 = st.columns(3)
                quantity = c4.number_input("Quantidade", min_value=1, step=1, value=1)
                source_ref = c5.text_input("Referência", placeholder="NF, ordem interna")
                note = c6.text_input("Observação")
                move_submitted = st.form_submit_button("Salvar movimento")
                if move_submitted:
                    try:
                        add_movement(
                            item_id=item_map[item_name],
                            movement_type=operational_labels[movement_label],
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
            recent_df = recent_df[recent_df["movement_type"].isin(set(operational_labels.values()))]
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

elif menu == "Tabela de Preços Lavanderia":
    st.subheader("Tabela de preços de lavanderia por item")
    st.caption(
        "Defina tarifa unitária por item com data de vigência. "
        "Se houver reajuste no meio da quinzena/mês, cadastre nova tarifa com nova data."
    )

    scope_col1, scope_col2 = st.columns(2)
    scope_unit = scope_col1.selectbox(
        "Escopo da tabela",
        options=["TODAS", "HOTEL", "CLUB", "CENTRAL"],
    )
    ref_rate_date = scope_col2.date_input("Tarifa vigente em", value=as_of_date, key="laundry_rate_ref_date")

    unit_param = None if scope_unit == "TODAS" else scope_unit
    price_rows = list_laundry_price_table(operation_unit=unit_param, ref_date=ref_rate_date, active_only=False)
    price_df = pd.DataFrame(price_rows)
    if price_df.empty:
        st.info("Sem itens para exibir na tabela de preços.")
    else:
        batch1, batch2, batch3, batch4 = st.columns(4)
        batch_rate = batch1.text_input("Nova tarifa para todos (0,00)", value="0,00")
        batch_date = batch2.date_input("Vigência global (DD/MM/AAAA)", value=ref_rate_date, key="batch_rate_date")
        batch_note = batch3.text_input("Observação global")
        apply_all = batch4.button("Aplicar a todos os itens filtrados")
        if apply_all:
            try:
                parsed_rate = _parse_decimal_br(batch_rate)
                for _, row in price_df.iterrows():
                    upsert_laundry_rate(
                        item_id=int(row["item_id"]),
                        effective_from=batch_date,
                        unit_price=parsed_rate,
                        note=batch_note,
                    )
                st.success("Tarifa global aplicada para todos os itens filtrados.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha ao aplicar tarifa global: {exc}")

        edit_df = pd.DataFrame(
            {
                "unidade": price_df["operation_unit"],
                "item": price_df["item_name"],
                "categoria": price_df["category"],
                "tarifa_atual (0,00)": price_df["current_unit_price"].apply(_format_decimal_br),
                "vigencia_atual (DD/MM/AAAA)": price_df["effective_from"].apply(_format_date_br),
                "nova_tarifa (0,00)": price_df["current_unit_price"].apply(_format_decimal_br),
                "nova_vigencia (DD/MM/AAAA)": [ref_rate_date.strftime("%d/%m/%Y")] * len(price_df),
                "aplicar": [False] * len(price_df),
            }
        )
        st.markdown("**Tabela editável de tarifas por item**")
        with st.form("form_laundry_rate_editor", clear_on_submit=False):
            edited_df = st.data_editor(
                edit_df,
                use_container_width=True,
                hide_index=True,
                key="laundry_rate_editor",
                disabled=["unidade", "item", "categoria", "tarifa_atual (0,00)", "vigencia_atual (DD/MM/AAAA)"],
                column_config={
                    "nova_tarifa (0,00)": st.column_config.TextColumn(help="Ex: 3,50"),
                    "nova_vigencia (DD/MM/AAAA)": st.column_config.TextColumn(help="Ex: 16/03/2026"),
                    "aplicar": st.column_config.CheckboxColumn(help="Marque para salvar a nova tarifa deste item"),
                },
            )
            save_rate_sheet_submit = st.form_submit_button("Salvar alterações da planilha de tarifas")

        if save_rate_sheet_submit:
            try:
                changed = 0
                for idx, row in edited_df.iterrows():
                    if not bool(row.get("aplicar", False)):
                        continue
                    item_id = int(price_df.iloc[idx]["item_id"])
                    parsed_rate = _parse_decimal_br(row.get("nova_tarifa (0,00)", "0,00"))
                    parsed_date = _parse_date_br(row.get("nova_vigencia (DD/MM/AAAA)", ""))
                    upsert_laundry_rate(
                        item_id=item_id,
                        effective_from=parsed_date,
                        unit_price=parsed_rate,
                        note="Atualizado via planilha de tarifas.",
                    )
                    changed += 1
                if changed == 0:
                    st.warning("Nenhum item marcado para aplicar.")
                else:
                    st.success(f"Tarifa atualizada para {changed} item(ns).")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Falha ao salvar alterações da planilha: {exc}")

        options = []
        item_index: dict[str, int] = {}
        for _, row in price_df.iterrows():
            label = (
                f"{row['operation_unit']} | {row['item_name']} | "
                f"tarifa atual: {_format_decimal_br(float(row['current_unit_price']))}"
            )
            options.append(label)
            item_index[label] = int(row["item_id"])

        selected_hist_label = st.selectbox("Histórico de tarifas por item", options=options, key="rate_history_select")
        hist_item_id = item_index[selected_hist_label]
        hist_df = pd.DataFrame(list_item_laundry_rates(hist_item_id))
        if hist_df.empty:
            st.info("Este item ainda não possui histórico de tarifas.")
        else:
            hist_df = hist_df.rename(
                columns={
                    "effective_from": "vigencia_desde",
                    "unit_price": "tarifa_unitaria",
                    "note": "observacao",
                    "created_at": "criado_em",
                }
            )
            hist_df["vigencia_desde"] = hist_df["vigencia_desde"].apply(_format_date_br)
            hist_df["tarifa_unitaria"] = hist_df["tarifa_unitaria"].apply(_format_decimal_br)
            st.dataframe(
                hist_df[["vigencia_desde", "tarifa_unitaria", "observacao", "criado_em"]],
                use_container_width=True,
                hide_index=True,
            )

elif menu == "Apuração Lavanderia (Planilha)":
    st.subheader(f"Apuração de cobrança da lavanderia - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.warning("Apuração de lavanderia é exclusiva de HOTEL ou CLUB.")
        st.stop()
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
        m2.metric("Valor total cobrado (R$)", _format_brl(total_billed_value))
        m3.metric("Relave enviado (sem cobrança)", total_rewash_sent)
        m4.metric("Relave pendente", total_rewash_sent - total_rewash_returned)
        st.metric("Perdas no período", total_losses)

        display_sheet_df = sheet_df.rename(
            columns={
                "VALOR UNIT": "valor p/ unid.",
                "VALOR TOTAL": "Valor Total",
                "TOTAL": "TOTAL PEÇAS",
            }
        ).copy()
        display_sheet_df["valor p/ unid."] = display_sheet_df["valor p/ unid."].apply(_format_brl)
        display_sheet_df["Valor Total"] = display_sheet_df["Valor Total"].apply(_format_brl)

        st.dataframe(display_sheet_df, use_container_width=True, hide_index=True)

        csv_data = display_sheet_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Baixar apuração em CSV",
            data=csv_data,
            file_name=f"apuracao_lavanderia_{selected_unit.lower()}_{start_date}_{end_date}.csv",
            mime="text/csv",
        )

elif menu == "Contagem Física":
    st.subheader("Contagem física (fechamento diário)")
    item_map = _items_map(selected_unit)
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

        critical_df = balances[balances["stock_theoretical"] <= balances["par_level"]].copy()
        if not critical_df.empty:
            st.error(
                f"ALERTA CRITICO: {len(critical_df)} item(ns) no nível mínimo ou abaixo."
            )
            st.dataframe(
                critical_df[
                    ["name", "stock_theoretical", "par_level"]
                ].rename(
                    columns={
                        "name": "item",
                        "stock_theoretical": "estoque_atual",
                        "par_level": "nivel_minimo",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

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
        s1.metric("Lavagem cobrada entregue", int(summary.get("charged_qty", summary["billed_returned"])))
        s2.metric("Relavagem sem cobrança enviada", int(summary["rewash_sent"]))

elif menu == "Auditoria IA":
    st.subheader(f"Auditoria IA de desfalque - {UNIT_OPTIONS[selected_unit]}")
    if selected_unit == "CENTRAL":
        st.warning("Auditoria IA operacional é exclusiva de HOTEL ou CLUB.")
        st.stop()
    report = generate_audit_report(as_of_date=as_of_date, operation_unit=selected_unit)
    f1, f2 = st.columns(2)
    f1.metric("Score geral de risco (0-100)", report["overall_risk_score"])
    f2.metric("Itens com alerta", report["items_with_alert"])

    l1, l2 = st.columns(2)
    l1.metric(
        "Lavagens cobradas entregues (30d)",
        int(report["laundry_summary_30d"].get("charged_qty", report["laundry_summary_30d"]["billed_returned"])),
    )
    l2.metric("Relavagens sem cobrança enviadas (30d)", int(report["laundry_summary_30d"]["rewash_sent"]))

    delay_summary = report.get("laundry_delay_summary", {})
    d1, d2 = st.columns(2)
    d1.metric(
        "Peças > 3 dias na lavanderia",
        int(delay_summary.get("laundry_over_3d_qty", 0)),
    )
    d2.metric(
        "Peças de relavagem > 3 dias",
        int(delay_summary.get("rewash_over_3d_qty", 0)),
    )
    if int(delay_summary.get("rewash_over_3d_qty", 0)) > 0:
        st.error(
            "ALERTA DE RELAVAGEM: há peças de relavagem paradas há mais de 3 dias na lavanderia."
        )
    if int(delay_summary.get("laundry_over_3d_qty", 0)) > 0:
        st.warning(
            "ALERTA DE PRAZO: há peças gerais de lavanderia com permanência acima de 3 dias."
        )

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
