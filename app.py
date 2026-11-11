"""Painel interativo para explorar os dados do projeto.

Rode com: streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path(__file__).parent / "data"

st.set_page_config(page_title="O Mercado Não Mente", page_icon="📈", layout="wide")
st.title("O Mercado Não Mente")
st.caption("Explore os preços da bolsa brasileira e a Selic desde 2019. O relatório completo está em vitordbl.github.io/o-mercado-nao-mente")


@st.cache_data
def carregar():
    precos = pd.read_csv(DATA / "precos.csv", parse_dates=["data"], index_col="data")
    selic = pd.read_csv(DATA / "selic_meta.csv", parse_dates=["data"], index_col="data")["selic_meta"]
    return precos, selic


precos, selic = carregar()

with st.sidebar:
    ativos = st.multiselect("Ativos", list(precos.columns), default=["Ibovespa", "Itaú (ITUB4)", "Magazine Luiza (MGLU3)"])
    inicio, fim = st.slider(
        "Período",
        min_value=precos.index.min().date(),
        max_value=precos.index.max().date(),
        value=(precos.index.min().date(), precos.index.max().date()),
        format="MM/YYYY",
    )

if not ativos:
    st.info("Escolha pelo menos um ativo na barra lateral.")
    st.stop()

janela = precos.loc[str(inicio):str(fim), ativos].dropna(how="all")
base100 = janela / janela.bfill().iloc[0] * 100

colunas = st.columns(len(ativos))
for col, ativo in zip(colunas, ativos):
    serie = janela[ativo].dropna()
    col.metric(ativo, f"{serie.iloc[-1]:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
               f"{(serie.iloc[-1] / serie.iloc[0] - 1) * 100:+.1f}% no período".replace(".", ","))

st.subheader("Desempenho comparado (base 100 no início do período)")
st.line_chart(base100)

st.subheader("Selic meta (% ao ano)")
st.line_chart(selic.resample("D").ffill().loc[str(inicio):str(fim)])

st.subheader("Maiores quedas em um dia")
diarios = janela.pct_change().dropna(how="all")
piores = (diarios.stack().sort_values().head(10) * 100).round(2).reset_index()
piores.columns = ["Data", "Ativo", "Variação (%)"]
piores["Data"] = piores["Data"].dt.strftime("%d/%m/%Y")
st.dataframe(piores, hide_index=True, width="stretch")
