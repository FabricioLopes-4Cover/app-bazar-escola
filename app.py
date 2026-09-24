import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import unicodedata
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
# Azul = vendido, laranja = em estoque (cores testadas para daltonismo)
CORES_GRAFICO = {"claro": ["#2a78d6", "#eb6834"], "escuro": ["#3987e5", "#d95926"]}


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


def ler_registros(aba):
    # A planilha está em português e mostra "11,11"; lido como texto, o gspread
    # tira a vírgula e vira 1111. Por isso lemos o número puro, sem formatação.
    return aba.get_all_records(value_render_option="UNFORMATTED_VALUE", numericise_ignore=["all"])


def carregar_itens(aba_itens):
    registros = ler_registros(aba_itens)
    df = pd.DataFrame(registros, columns=ITENS_HEADER)
    if df.empty:
        return df
    df["valor_unitario"] = pd.to_numeric(df["valor_unitario"], errors="coerce").fillna(0)
    df["quantidade_cadastrada"] = pd.to_numeric(df["quantidade_cadastrada"], errors="coerce").fillna(0).astype(int)
    return df


def carregar_vendas(aba_vendas):
    registros = ler_registros(aba_vendas)
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


def formatar_percentual(fracao):
    return f"{fracao:.2%}".replace(".", ",")


def chave_alfabetica(texto):
    # Ignora maiúsculas e acentos, para "Óculos" ficar junto de "oculos"
    sem_acento = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return sem_acento.strip().lower()


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def converter_valor_brl(texto):
    texto_limpo = texto.strip().replace("R$", "").strip()
    if not texto_limpo:
        return None
    # Só números (ex: 110) são lidos como centavos: 110 -> 1,10
    if texto_limpo.isdigit():
        return int(texto_limpo) / 100
    if "," in texto_limpo:
        texto_limpo = texto_limpo.replace(".", "").replace(",", ".")
    try:
        return float(texto_limpo)
    except ValueError:
        return None


LABEL_VALOR = "Valor unitário (R$)"

# Máscara de moeda no campo de valor: o aluno digita só os números e a vírgula
# entra sozinha (1 -> 0,01, 11 -> 0,11, 110 -> 1,10).
MASCARA_VALOR_JS = """
<script>
const doc = window.parent.document;
const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, "value").set;

function formatar(texto) {
  const digitos = texto.replace(/\\D/g, "").replace(/^0+/, "").slice(0, 6);
  if (!digitos) return "";
  const completo = digitos.padStart(3, "0");
  return completo.slice(0, -2) + "," + completo.slice(-2);
}

function aplicar() {
  doc.querySelectorAll('input[aria-label="LABEL"]').forEach((campo) => {
    if (campo.dataset.mascara) return;
    campo.dataset.mascara = "1";
    campo.setAttribute("inputmode", "numeric");
    campo.addEventListener("input", () => {
      const novo = formatar(campo.value);
      if (novo !== campo.value) {
        setter.call(campo, novo);
        campo.dispatchEvent(new Event("input", { bubbles: true }));
      }
    });
  });
}

aplicar();
new MutationObserver(aplicar).observe(doc.body, { childList: true, subtree: true });
</script>
""".replace("LABEL", LABEL_VALOR)


def injetar_script(html):
    # st.iframe substitui components.html nas versões novas do Streamlit
    if hasattr(st, "iframe"):
        st.iframe(html, height=1)
    else:
        components.html(html, height=0)


aba_itens, aba_vendas = conectar_planilha()

st.subheader("🛍️ Bazar 9º Ano 2027")
st.caption("Autora: Prof. Ana Hortência")

aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "➕ Cadastrar item", "📦 Estoque", "💰 Registrar venda", "📊 Vendas", "📈 Total vendido", "⚖️ Estoque X Venda",
])

with aba1:
    st.subheader("Cadastrar novo item")
    with st.form("form_cadastro", clear_on_submit=True):
        nome = st.text_input("Nome do item (ex: Óculos de sol)")
        valor_texto = st.text_input(
            LABEL_VALOR,
            placeholder="0,00",
            help="Digite só os números. Ex: 250 vira 2,50",
        )
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

    injetar_script(MASCARA_VALOR_JS)

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

        df_exibicao = df_itens.sort_values("nome", key=lambda nomes: nomes.map(chave_alfabetica))
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

        if "venda_registrada" in st.session_state:
            st.success(st.session_state.pop("venda_registrada"))

        if itens_disponiveis.empty:
            st.warning("Não há itens disponíveis em estoque.")
        else:
            rodada = st.session_state.get("venda_rodada", 0)
            with st.container(border=True):
                # Itens sem estoque já ficaram de fora em itens_disponiveis
                opcoes = sorted(itens_disponiveis["nome"].tolist(), key=chave_alfabetica)
                item_selecionado = st.selectbox(
                    "Item vendido",
                    opcoes,
                    index=None,
                    placeholder="Digite para buscar o item",
                    key=f"venda_item_{rodada}",
                )

                if item_selecionado is None:
                    disponivel = 0
                    valor_unitario = 0.0
                else:
                    linha_item = itens_disponiveis.loc[itens_disponiveis["nome"] == item_selecionado].iloc[0]
                    disponivel = int(linha_item["disponivel"])
                    valor_unitario = float(linha_item["valor_unitario"])
                    st.caption(f"Disponível em estoque: {disponivel} | Valor unitário: {formatar_moeda(valor_unitario)}")

                # Sem max_value: acima do limite o Streamlit ignora o número digitado e venderia 1 sem avisar
                qtd_vendida = st.number_input(
                    "Quantidade vendida", min_value=1, step=1, value=1, key=f"venda_qtd_{rodada}",
                )
                forma_pagamento = st.selectbox("Forma de pagamento", FORMAS_PAGAMENTO, key=f"venda_pagamento_{rodada}")
                confirmar = st.button("Registrar venda")

                if confirmar:
                    if item_selecionado is None:
                        st.error("Escolha o item vendido.")
                    elif qtd_vendida > disponivel:
                        st.error(f"Quantidade maior que o disponível em estoque ({disponivel}). Nada foi registrado.")
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
                        st.session_state["venda_registrada"] = (
                            f"Venda registrada: {qtd_vendida}x {item_selecionado} = {formatar_moeda(valor_total)}"
                        )
                        # Campos com chave nova voltam em branco na próxima venda
                        st.session_state["venda_rodada"] = rodada + 1
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

with aba6:
    st.subheader("Estoque X Venda")
    df_itens = carregar_itens(aba_itens)
    df_vendas_resumo = carregar_vendas(aba_vendas)

    if df_itens.empty:
        st.info("Nenhum item cadastrado ainda.")
    else:
        df_itens["vendido"] = df_itens["nome"].apply(lambda n: quantidade_vendida_por_item(df_vendas_resumo, n))
        df_itens["disponivel"] = (df_itens["quantidade_cadastrada"] - df_itens["vendido"]).clip(lower=0)

        valor_em_estoque = float((df_itens["disponivel"] * df_itens["valor_unitario"]).sum())
        qtd_em_estoque = int(df_itens["disponivel"].sum())
        valor_vendido = float(df_vendas_resumo["valor_total"].sum()) if not df_vendas_resumo.empty else 0.0
        qtd_vendida = int(df_vendas_resumo["quantidade_vendida"].sum()) if not df_vendas_resumo.empty else 0
        valor_bazar = valor_em_estoque + valor_vendido

        col1, col2 = st.columns(2)
        with col1.container(border=True):
            st.metric("💰 Total de venda", formatar_moeda(valor_vendido))
            st.caption(f"{qtd_vendida} itens vendidos")
        with col2.container(border=True):
            st.metric("📦 Total em estoque", formatar_moeda(valor_em_estoque))
            st.caption(f"{qtd_em_estoque} itens para vender")

        parte_vendida = valor_vendido / valor_bazar if valor_bazar > 0 else 0.0
        st.markdown(f"**Já vendemos {formatar_percentual(parte_vendida)} do valor do bazar**")

        tema_escuro = getattr(getattr(getattr(st, "context", None), "theme", None), "type", None) == "dark"
        cor_vendido, cor_estoque = CORES_GRAFICO["escuro" if tema_escuro else "claro"]

        if valor_bazar > 0:
            partes = [
                ("Vendido", valor_vendido, parte_vendida, cor_vendido),
                ("Em estoque", valor_em_estoque, 1 - parte_vendida, cor_estoque),
            ]
            barra = "".join(
                f'<div style="flex:{valor};background:{cor};border-radius:4px"></div>'
                for _, valor, _, cor in partes if valor > 0
            )
            legenda = "".join(
                f'<div style="display:flex;align-items:center;gap:8px;margin-top:6px">'
                f'<span style="width:14px;height:14px;border-radius:3px;background:{cor};flex:none"></span>'
                f'{nome}: {formatar_moeda(valor)} ({formatar_percentual(fracao)})</div>'
                for nome, valor, fracao, cor in partes
            )
            st.markdown(
                f'<div style="display:flex;gap:2px;height:36px;margin:4px 0 8px">{barra}</div>{legenda}',
                unsafe_allow_html=True,
            )

        st.caption(f"Venda + estoque = {formatar_moeda(valor_bazar)}")

        st.divider()
        st.markdown("**Vendas por forma de pagamento**")
        if df_vendas_resumo.empty:
            por_pagamento = pd.Series(0.0, index=FORMAS_PAGAMENTO)
        else:
            por_pagamento = df_vendas_resumo.groupby("forma_pagamento")["valor_total"].sum()
            # PIX, Cartão e Dinheiro sempre aparecem, nessa ordem; outras (ex: "Não informado") vão no fim
            extras = [f for f in por_pagamento.index if f not in FORMAS_PAGAMENTO]
            por_pagamento = por_pagamento.reindex(FORMAS_PAGAMENTO + extras, fill_value=0.0)

        maior_valor = float(por_pagamento.max())
        linhas = "".join(
            f'<div style="display:flex;align-items:center;gap:10px;margin:8px 0">'
            f'<div style="width:110px;flex:none">{forma}</div>'
            f'<div style="flex:1;display:flex;align-items:center;gap:8px">'
            f'<div style="width:{(valor / maior_valor * 80) if maior_valor > 0 else 0:.1f}%;height:28px;'
            f'background:{cor_vendido};border-radius:0 4px 4px 0"></div>'
            f'<div style="white-space:nowrap">{formatar_moeda(valor)}</div>'
            f'</div></div>'
            for forma, valor in por_pagamento.items()
        )
        st.markdown(linhas, unsafe_allow_html=True)
