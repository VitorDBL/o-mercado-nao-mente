"""Coleta os dados brutos do projeto e salva em data/.

Fontes:
- Yahoo Finance (via yfinance): Ibovespa, ações e dólar, preços diários ajustados.
- Banco Central do Brasil, SGS: Selic meta (série 432) e IPCA mensal (série 433).

Rode com: python src/coleta.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

INICIO = "2019-01-01"
DATA = Path(__file__).resolve().parents[1] / "data"

ATIVOS = {
    "^BVSP": "Ibovespa",
    "PETR4.SA": "Petrobras (PETR4)",
    "VALE3.SA": "Vale (VALE3)",
    "ITUB4.SA": "Itaú (ITUB4)",
    "MGLU3.SA": "Magazine Luiza (MGLU3)",
    "USDBRL=X": "Dólar (USD/BRL)",
}

SERIES_BCB = {432: "selic_meta", 433: "ipca_mensal"}


def baixar_precos() -> pd.DataFrame:
    bruto = yf.download(list(ATIVOS), start=INICIO, auto_adjust=True, progress=False)
    fechamento = bruto["Close"].rename(columns=ATIVOS)
    fechamento.index = pd.to_datetime(fechamento.index).tz_localize(None)
    fechamento.index.name = "data"
    # O dólar negocia em dias em que a B3 está fechada; ficamos só com pregões da B3
    fechamento = fechamento.dropna(subset=["Ibovespa"]).ffill()
    return fechamento.round(4)


def baixar_bcb(codigo: int, nome: str) -> pd.DataFrame:
    # A API do SGS limita consultas diárias a 10 anos; nosso período cabe nisso
    inicio = pd.Timestamp(INICIO).strftime("%d/%m/%Y")
    url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
           f"?formato=json&dataInicial={inicio}")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    df["data"] = pd.to_datetime(df["data"], dayfirst=True)
    df[nome] = pd.to_numeric(df["valor"].str.replace(",", "."), errors="coerce")
    return df[["data", nome]].set_index("data")


def main() -> None:
    DATA.mkdir(exist_ok=True)
    precos = baixar_precos()
    precos.to_csv(DATA / "precos.csv")
    print(f"precos.csv: {len(precos)} pregões, de {precos.index.min():%d/%m/%Y} a {precos.index.max():%d/%m/%Y}")

    for codigo, nome in SERIES_BCB.items():
        serie = baixar_bcb(codigo, nome)
        serie.to_csv(DATA / f"{nome}.csv")
        print(f"{nome}.csv: {len(serie)} linhas")

    (DATA / "atualizado_em.txt").write_text(date.today().isoformat())


if __name__ == "__main__":
    main()
