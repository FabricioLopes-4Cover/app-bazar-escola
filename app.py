import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Bazar 9º Ano 2027", page_icon="🛍️", layout="wide")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ITENS_HEADER = ["nome", "valor_unitario", "quantidade_cadastrada"]
VENDAS_HEADER = ["data_hora", "item", "quantidade_vendida", "valor_unitario", "valor_total", "forma_pagamento"]
FORMAS_PAGAMENTO = ["PIX", "Cartão", "Dinheiro"]


@st.cache_resource(show_spinner=False)
def conectar_planilha():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    cliente = gspread.authorize(creds)
    planilha = cliente.open_by_key(st.secrets["planilha_id"])

    try:
        aba_itens = planilha.worksheet("itens")
    except gspread.WorksheetNotFound:
        aba_itens = planilha.add_worksheet("itens", rows=1000, cols=len(ITENS_HEADER))
        aba_itens.append_row(ITENS_HEADER)

    try:
        aba_vendas = planilha.worksheet("vendas")
    except gspread.WorksheetNotFound:
        aba_vendas = planilha.add_worksheet("vendas", rows=1000, cols=len(VENDAS_HEADER))
        aba_vendas.append_row(VENDAS_HEADER)

    if aba_vendas.row_values(1) != VENDAS_HEADER:
        aba_vendas.update([VENDAS_HEADER], "A1")

    return aba_itens, aba_vendas


def carregar_itens(aba_itens):
    registros = aba_itens.get_all_records()
    df = pd.DataFrame(registros, columns=ITENS_HEADER)
    if df.empty:
        return df
    df["valor_unitario"] = pd.to_numeric(df["valor_unitario"], errors="coerce").fillna(0)
    df["quantidade_cadastrada"] = pd.to_numeric(df["quantidade_cadastrada"], errors="coerce").fillna(0).astype(int)
    return df


def carregar_vendas(aba_vendas):
    registros = aba_vendas.get_all_records()
    df = pd.DataFrame(registros, columns=VENDAS_HEADER)
    if df.empty:
        return df
    df["quantidade_vendida"] = pd.to_numeric(df["quantidade_vendida"], errors="coerce").fillna(0).astype(int)
    df["valor_unitario"] = pd.to_numeric(df["valor_unitario"], errors="coerce").fillna(0)
    df["valor_total"] = pd.to_numeric(df["valor_total"], errors="coerce").fillna(0)
    df["forma_pagamento"] = df["forma_pagamento"].replace("", "Não informado")
    return df


def quantidade_vendida_por_item(df_vendas, nome_item):
    if df_vendas.empty:
        return 0
    return int(df_vendas.loc[df_vendas["item"] == nome_item, "quantidade_vendida"].sum())


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def converter_valor_brl(texto):
    texto_limpo = texto.strip().replace("R$", "").strip()
    if not texto_limpo:
        return None
    if "," in texto_limpo:
        texto_limpo = texto_limpo.replace(".", "").replace(",", ".")
    try:
        return float(texto_limpo)
    except ValueError:
        return None


aba_itens, aba_vendas = conectar_planilha()

st.subheader("🛍️ Bazar 9º Ano 2027")
st.caption("Autora: Prof. Ana Hortência")

aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "➕ Cadastrar item", "📦 Estoque", "💰 Registrar venda", "📊 Vendas", "📈 Total vendido",
])

with aba1:
    st.subheader("Cadastrar novo item")
    with st.form("form_cadastro", clear_on_submit=True):
        nome = st.text_input("Nome do item (ex: Óculos de sol)")
        valor_texto = st.text_input("Valor unitário (R$)", placeholder="Ex: 2,50")
        quantidade = st.number_input("Quantidade cadastrada", min_value=1, step=1, value=1)
        enviado = st.form_submit_button("Cadastrar")

        if enviado:
            valor = converter_valor_brl(valor_texto)
            if not nome.strip():
                st.error("Informe o nome do item.")
            elif valor is None or valor <= 0:
                st.error("Informe um valor válido, por exemplo: 2,50")
            else:
                aba_itens.append_row([nome.strip(), valor, int(quantidade)])
                st.cache_resource.clear()
                st.success(f"Item '{nome.strip()}' cadastrado!")
                st.rerun()

with aba2:
    st.subheader("Itens cadastrados")
    df_itens = carregar_itens(aba_itens)
    df_vendas_all = carregar_vendas(aba_vendas)

    if df_itens.empty:
        st.info("Nenhum item cadastrado ainda.")
    else:
        df_itens["vendido"] = df_itens["nome"].apply(lambda n: quantidade_vendida_por_item(df_vendas_all, n))
        df_itens["disponivel"] = df_itens["quantidade_cadastrada"] - df_itens["vendido"]
        df_itens["valor_total"] = df_itens["valor_unitario"] * df_itens["quantidade_cadastrada"]

        df_exibicao = df_itens.copy()
        df_exibicao["valor_unitario"] = df_exibicao["valor_unitario"].apply(formatar_moeda)
        df_exibicao["valor_total"] = df_exibicao["valor_total"].apply(formatar_moeda)

        st.dataframe(
            df_exibicao.rename(columns={
                "nome": "Item",
                "valor_unitario": "Valor unitário",
                "quantidade_cadastrada": "Qtd. cadastrada",
                "vendido": "Qtd. vendida",
                "disponivel": "Disponível",
                "valor_total": "Valor total",
            }),
            use_container_width=True,
            hide_index=True,
        )

        col1, col2 = st.columns(2)
        col1.metric("Total de itens cadastrados", int(df_itens["quantidade_cadastrada"].sum()))
        col2.metric("Valor total do estoque", formatar_moeda(df_itens["valor_total"].sum()))

with aba3:
    st.subheader("Registrar venda")
    df_itens = carregar_itens(aba_itens)
    df_vendas_all = carregar_vendas(aba_vendas)

    if df_itens.empty:
        st.info("Cadastre algum item antes de registrar uma venda.")
    else:
        df_itens["vendido"] = df_itens["nome"].apply(lambda n: quantidade_vendida_por_item(df_vendas_all, n))
        df_itens["disponivel"] = df_itens["quantidade_cadastrada"] - df_itens["vendido"]
        itens_disponiveis = df_itens[df_itens["disponivel"] > 0]

        if itens_disponiveis.empty:
            st.warning("Não há itens disponíveis em estoque.")
        else:
            with st.form("form_venda", clear_on_submit=True):
                opcoes = itens_disponiveis["nome"].tolist()
                item_selecionado = st.selectbox("Item vendido", opcoes)
                disponivel = int(itens_disponiveis.loc[itens_disponiveis["nome"] == item_selecionado, "disponivel"].iloc[0])
                valor_unitario = float(itens_disponiveis.loc[itens_disponiveis["nome"] == item_selecionado, "valor_unitario"].iloc[0])
                st.caption(f"Disponível em estoque: {disponivel} | Valor unitário: {formatar_moeda(valor_unitario)}")

                qtd_vendida = st.number_input("Quantidade vendida", min_value=1, max_value=max(disponivel, 1), step=1, value=1)
                forma_pagamento = st.selectbox("Forma de pagamento", FORMAS_PAGAMENTO)
                confirmar = st.form_submit_button("Registrar venda")

                if confirmar:
                    if qtd_vendida > disponivel:
                        st.error("Quantidade maior que o disponível em estoque.")
                    else:
                        valor_total = qtd_vendida * valor_unitario
                        aba_vendas.append_row([
                            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            item_selecionado,
                            int(qtd_vendida),
                            valor_unitario,
                            valor_total,
                            forma_pagamento,
                        ])
                        st.cache_resource.clear()
                        st.success(f"Venda registrada: {qtd_vendida}x {item_selecionado} = {formatar_moeda(valor_total)}")
                        st.rerun()

with aba4:
    st.subheader("Histórico de vendas")
    df_vendas = carregar_vendas(aba_vendas)

    if df_vendas.empty:
        st.info("Nenhuma venda registrada ainda.")
    else:
        df_exibicao = df_vendas.copy()
        df_exibicao["_data_hora_ordenacao"] = pd.to_datetime(df_exibicao["data_hora"], format="%d/%m/%Y %H:%M:%S")
        df_exibicao = df_exibicao.sort_values("_data_hora_ordenacao", ascending=False).drop(columns="_data_hora_ordenacao")
        df_exibicao["valor_unitario"] = df_exibicao["valor_unitario"].apply(formatar_moeda)
        df_exibicao["valor_total"] = df_exibicao["valor_total"].apply(formatar_moeda)

        st.dataframe(
            df_exibicao.rename(columns={
                "data_hora": "Data/Hora",
                "item": "Item",
                "quantidade_vendida": "Quantidade",
                "valor_unitario": "Valor unitário",
                "valor_total": "Valor total",
                "forma_pagamento": "Pagamento",
            }),
            use_container_width=True,
            hide_index=True,
        )

        col1, col2 = st.columns(2)
        col1.metric("Quantidade total vendida", int(df_vendas["quantidade_vendida"].sum()))
        col2.metric("Valor total vendido", formatar_moeda(df_vendas["valor_total"].sum()))

with aba5:
    st.subheader("Total de itens vendidos")
    df_vendas_total = carregar_vendas(aba_vendas)

    if df_vendas_total.empty:
        st.info("Nenhuma venda registrada ainda.")
    else:
        st.markdown("**Por forma de pagamento**")
        resumo_pagamento = df_vendas_total.groupby("forma_pagamento", as_index=False).agg(
            quantidade_vendida=("quantidade_vendida", "sum"),
            valor_total=("valor_total", "sum"),
        )
        resumo_exibicao = resumo_pagamento.copy()
        resumo_exibicao["valor_total"] = resumo_exibicao["valor_total"].apply(formatar_moeda)
        st.dataframe(
            resumo_exibicao.rename(columns={
                "forma_pagamento": "Forma de pagamento",
                "quantidade_vendida": "Quantidade vendida",
                "valor_total": "Valor total",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        st.markdown("**Total geral**")
        col1, col2 = st.columns(2)
        col1.metric("Total de itens vendidos", int(df_vendas_total["quantidade_vendida"].sum()))
        col2.metric("Valor total vendido", formatar_moeda(df_vendas_total["valor_total"].sum()))
