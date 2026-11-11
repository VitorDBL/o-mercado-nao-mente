"""Transforma os dados de data/ em números, gráficos e no relatório em docs/.

Cada capítulo responde uma pergunta. Os números do texto saem direto dos
dados, então o relatório se atualiza sozinho quando a coleta roda de novo.

Rode com: python src/analise.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DATA = RAIZ / "data"
DOCS = RAIZ / "docs"
IMG = DOCS / "img"

LARANJA = "#EB6A12"
GRAFITE = "#1A2230"
CINZA = "#9AA3B2"
CINZA_CLARO = "#DCE1E8"
AZUL = "#2F6FB3"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.edgecolor": CINZA_CLARO,
    "axes.labelcolor": GRAFITE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": "#5B6576",
    "ytick.color": "#5B6576",
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#EEF1F5",
    "grid.linewidth": 1,
    "figure.dpi": 100,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})


def pct(x: float, casas: int = 1) -> str:
    v = round(x * 100, casas)
    if v == 0:
        v = 0.0
    return f"{v:+.{casas}f}%".replace(".", ",")


def num(x: float, casas: int = 1) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def br(d: pd.Timestamp) -> str:
    return d.strftime("%d/%m/%Y")


@dataclass
class Dados:
    precos: pd.DataFrame
    selic: pd.Series
    ipca: pd.Series
    atualizado: str


def carregar() -> Dados:
    precos = pd.read_csv(DATA / "precos.csv", parse_dates=["data"], index_col="data")
    selic = pd.read_csv(DATA / "selic_meta.csv", parse_dates=["data"], index_col="data")["selic_meta"]
    ipca = pd.read_csv(DATA / "ipca_mensal.csv", parse_dates=["data"], index_col="data")["ipca_mensal"]
    atualizado = (DATA / "atualizado_em.txt").read_text().strip() if (DATA / "atualizado_em.txt").exists() else ""
    return Dados(precos, selic, ipca, atualizado)


def salvar(fig, nome: str) -> str:
    IMG.mkdir(parents=True, exist_ok=True)
    fig.savefig(IMG / nome)
    plt.close(fig)
    return f"img/{nome}"


def fmt_eixo_data(ax):
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


# ---------------------------------------------------------------- capítulo 1
def pandemia(d: Dados) -> dict:
    ibov = d.precos["Ibovespa"]
    antes = ibov["2020-01-01":"2020-03-01"]
    topo_data, topo = antes.idxmax(), antes.max()
    queda = ibov[topo_data:"2020-06-30"]
    fundo_data, fundo = queda.idxmin(), queda.min()
    depois = ibov[fundo_data:]
    recuperou = depois[depois >= topo]
    rec_data = recuperou.index[0] if len(recuperou) else None
    pregões_queda = len(ibov[topo_data:fundo_data]) - 1
    meses_rec = (rec_data - fundo_data).days / 30.44 if rec_data is not None else None

    janela = ibov["2019-07-01":"2021-12-31"]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.plot(janela.index, janela / 1000, color=GRAFITE, lw=1.6)
    ax.fill_between(ibov[topo_data:fundo_data].index, ibov[topo_data:fundo_data] / 1000,
                    topo / 1000, color=LARANJA, alpha=0.18, lw=0)
    ax.scatter([topo_data, fundo_data], [topo / 1000, fundo / 1000], color=LARANJA, zorder=3, s=30)
    ax.annotate(f"Topo: {num(topo / 1000, 0)} mil\n{br(topo_data)}", (topo_data, topo / 1000),
                xytext=(-120, 6), textcoords="offset points", fontsize=10, color=GRAFITE)
    ax.annotate(f"Fundo: {num(fundo / 1000, 0)} mil\n{br(fundo_data)}", (fundo_data, fundo / 1000),
                xytext=(12, -6), textcoords="offset points", fontsize=10, color=LARANJA, fontweight="bold")
    if rec_data is not None and rec_data <= janela.index.max():
        ax.axvline(rec_data, color=CINZA, lw=1, ls="--")
        ax.annotate(f"Recuperou o topo\n{br(rec_data)}", (rec_data, fundo / 1000),
                    xytext=(6, 4), textcoords="offset points", fontsize=10, color="#5B6576")
    ax.set_ylabel("Ibovespa (mil pontos)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
    img = salvar(fig, "1_pandemia.png")

    return {
        "topo": topo, "topo_data": topo_data, "fundo": fundo, "fundo_data": fundo_data,
        "queda": fundo / topo - 1, "pregoes": pregões_queda,
        "recuperacao_data": rec_data, "meses_recuperacao": meses_rec, "img": img,
    }


# ---------------------------------------------------------------- capítulo 2
def ciclos_selic(selic: pd.Series) -> dict:
    s = selic.resample("D").ffill()
    piso_data = s["2020-01-01":"2021-12-31"].idxmin()
    piso = s[piso_data]
    sobe = s[piso_data:]
    inicio_alta = sobe[sobe > piso].index[0]
    # fim da primeira alta: último aumento antes do primeiro corte
    depois = s[inicio_alta:]
    primeiro_corte = depois[depois.diff() < 0].index
    ate_corte = depois[:primeiro_corte[0]] if len(primeiro_corte) else depois
    teto1 = ate_corte.max()
    teto1_data = ate_corte[ate_corte == teto1].index[0]
    teto = depois.max()
    teto_data = depois[depois == teto].index[0]
    piso2 = s[teto1_data:teto_data].min() if teto_data > teto1_data else None
    piso2_data = s[teto1_data:teto_data].idxmin() if piso2 is not None else None
    if piso2 is not None:
        subida2 = s[piso2_data:teto_data]
        inicio_alta2 = subida2[subida2 > piso2].index[0]
    else:
        inicio_alta2 = None
    apos = s[teto_data:]
    cortes = apos[apos < teto]
    inicio_corte = cortes.index[0] if len(cortes) else None
    return {"piso": piso, "inicio_alta": inicio_alta, "teto1": teto1, "teto1_data": teto1_data,
            "piso2": piso2, "inicio_alta2": inicio_alta2, "teto": teto, "teto_data": teto_data,
            "inicio_corte": inicio_corte}


def juros(d: Dados) -> dict:
    c = ciclos_selic(d.selic)
    p = d.precos

    def ret(col, a, b):
        serie = p[col][a:b]
        return serie.iloc[-1] / serie.iloc[0] - 1

    alta = (c["inicio_alta"], c["teto1_data"])
    ativos = ["Ibovespa", "Itaú (ITUB4)", "Magazine Luiza (MGLU3)"]
    ret_alta = {a: ret(a, *alta) for a in ativos}

    fig, ax = plt.subplots(figsize=(10, 4.4))
    ibov = p["Ibovespa"]["2019-01-01":]
    ax.plot(ibov.index, ibov / 1000, color=GRAFITE, lw=1.4, label="Ibovespa (mil pontos)")
    ax.set_ylabel("Ibovespa (mil pontos)")
    ax.axvspan(*alta, color=LARANJA, alpha=0.10, lw=0)
    if c["inicio_alta2"] is not None:
        ax.axvspan(c["inicio_alta2"], c["teto_data"], color=LARANJA, alpha=0.10, lw=0)
    ax2 = ax.twinx()
    selic = d.selic.resample("D").ffill()["2019-01-01":]
    ax2.step(selic.index, selic, where="post", color=LARANJA, lw=2, label="Selic meta (% a.a.)")
    ax2.set_ylabel("Selic meta (% ao ano)", color=LARANJA)
    ax2.tick_params(axis="y", colors=LARANJA)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(CINZA_CLARO)
    fmt_eixo_data(ax)
    img1 = salvar(fig, "2_selic_ibovespa.png")

    base = p[ativos][alta[0]:alta[1]]
    base = base / base.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(10, 4.4))
    cores = {"Ibovespa": GRAFITE, "Itaú (ITUB4)": LARANJA, "Magazine Luiza (MGLU3)": AZUL}
    # posições dos rótulos no fim das linhas, afastadas para não encostarem
    finais = sorted(ativos, key=lambda a: base[a].iloc[-1])
    pos, ultimo = {}, None
    for a in finais:
        y = base[a].iloc[-1]
        if ultimo is not None and y - ultimo < 7:
            y = ultimo + 7
        pos[a] = ultimo = y
    for a in ativos:
        ax.plot(base.index, base[a], color=cores[a], lw=1.8)
        ax.annotate(f"{a.split(' (')[0]} {pct(ret_alta[a], 0)}", (base.index[-1], base[a].iloc[-1]),
                    xytext=(base.index[-1] + pd.Timedelta(days=10), pos[a]), textcoords="data", va="center", color=cores[a],
                    fontsize=10, fontweight="bold")
    ax.axhline(100, color=CINZA, lw=1, ls="--")
    ax.set_ylabel("Base 100 no início da alta")
    ax.set_xlim(right=base.index[-1] + (base.index[-1] - base.index[0]) * 0.16)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
    img2 = salvar(fig, "3_vencedores_perdedores.png")

    return {**c, "ret_alta": ret_alta, "img1": img1, "img2": img2}


# ---------------------------------------------------------------- capítulo 3
def eleicao(d: Dados) -> dict:
    p = d.precos
    datas = {"1º turno de 2022": "2022-10-03", "2º turno de 2022": "2022-10-31",
             "1º turno de 2026": "2026-10-05", "2º turno de 2026": "2026-10-26"}
    datas = {r: d_ for r, d_ in datas.items() if pd.Timestamp(d_) <= p.index.max()}
    ativos = ["Ibovespa", "Petrobras (PETR4)", "Itaú (ITUB4)", "Vale (VALE3)"]
    diarios = p[ativos].pct_change()
    tabela = {}
    for rotulo, dia in datas.items():
        dia = diarios.index[diarios.index.get_indexer([pd.Timestamp(dia)], method="bfill")[0]]
        tabela[rotulo] = {a: diarios.loc[dia, a] for a in ativos}

    anos = sorted({r[-4:] for r in tabela})
    vol_normal = {ano: diarios[f"{ano}-01-01":f"{ano}-09-30"].std() for ano in anos}

    # maior queda do Ibovespa num dia antes de cada pregão de eleição, para dar escala
    ibov = diarios["Ibovespa"]

    fig, eixos = plt.subplots(1, len(anos), figsize=(10, 4.4), sharey=True, squeeze=False)
    largura = 0.38
    xs = range(len(ativos))
    for ax, ano in zip(eixos[0], anos):
        turnos = [r for r in tabela if r.endswith(ano)]
        for k, (rotulo, cor) in enumerate(zip(turnos, [LARANJA, GRAFITE])):
            vals = [tabela[rotulo][a] * 100 for a in ativos]
            barras = ax.bar([x + (k - 0.5) * largura for x in xs], vals, largura, color=cor,
                            label=rotulo.split(" de ")[0])
            for b, v in zip(barras, vals):
                ax.annotate(f"{v:+.1f}%".replace(".", ","), (b.get_x() + b.get_width() / 2, v),
                            xytext=(0, 4 if v >= 0 else -13), textcoords="offset points",
                            ha="center", fontsize=8.5, color=GRAFITE)
        ax.axhline(0, color=GRAFITE, lw=0.8)
        ax.set_xticks(list(xs), [a.split(" (")[0] for a in ativos], fontsize=9)
        ax.set_title(f"Eleição de {ano}", fontsize=11, loc="left", color=GRAFITE)
    eixos[0][0].set_ylabel("Variação no pregão seguinte (%)")
    eixos[0][0].legend(frameon=False, loc="lower left")
    img = salvar(fig, "4_eleicao.png")

    pior = {}
    for rotulo, dia in datas.items():
        dia = diarios.index[diarios.index.get_indexer([pd.Timestamp(dia)], method="bfill")[0]]
        v = ibov.loc[dia]
        antes = ibov[:dia].iloc[:-1]
        pior_antes = antes[antes <= v]
        pior[rotulo] = pior_antes.index[-1] if (v < 0 and len(pior_antes)) else None

    return {"tabela": tabela, "vol_normal": vol_normal, "pior_desde": pior, "img": img}


# ---------------------------------------------------------------- capítulo 4
def acumulado(d: Dados) -> dict:
    p = d.precos
    ativos = [c for c in p.columns]
    inicio, fim = p.index.min(), p.index.max()
    retorno = {a: p[a].dropna().iloc[-1] / p[a].dropna().iloc[0] - 1 for a in ativos}
    ipca = d.ipca[inicio:fim]
    inflacao = (1 + ipca / 100).prod() - 1

    ordem = sorted(retorno, key=retorno.get)
    fig, ax = plt.subplots(figsize=(10, 4.6))
    vals = [1000 * (1 + retorno[a]) for a in ordem]
    cores = [LARANJA if v < 1000 * (1 + inflacao) else GRAFITE for v in vals]
    barras = ax.barh([a for a in ordem], vals, color=cores, height=0.6)
    for b, v in zip(barras, vals):
        ax.annotate(f"R$ {v:,.0f}".replace(",", "."), (v, b.get_y() + b.get_height() / 2),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=10, color=GRAFITE)
    ax.axvline(1000 * (1 + inflacao), color=CINZA, ls="--", lw=1.2)
    ax.text(1000 * (1 + inflacao), 1.01, f"inflação: R$ {1000 * (1 + inflacao):,.0f}".replace(",", "."),
            transform=ax.get_xaxis_transform(), ha="center", va="bottom", fontsize=9, color="#5B6576")
    ax.set_xlabel(f"Quanto viraram R$ 1.000 aplicados em {br(inicio)}")
    ax.grid(axis="y", visible=False)
    img = salvar(fig, "5_acumulado.png")

    return {"inicio": inicio, "fim": fim, "retorno": retorno, "inflacao": inflacao,
            "perderam": [a for a in ordem if retorno[a] < inflacao], "img": img}


# ---------------------------------------------------------------- relatório
ARTIGOS = {"Ibovespa": "o Ibovespa", "Petrobras": "a Petrobras", "Itaú": "o Itaú", "Vale": "a Vale",
           "Magazine Luiza": "a Magazine Luiza", "Dólar": "o dólar"}


def com_artigo(ativo: str) -> str:
    nome = ativo.split(" (")[0]
    return ARTIGOS.get(nome, nome)


def _mov(v: float) -> str:
    return f"{'subiu' if v > 0 else 'caiu'} {pct(abs(v)).lstrip('+')}"


def texto_eleicao(c3) -> str:
    tab, vol = c3["tabela"], c3["vol_normal"]
    paragrafos = []
    anos = list(vol)
    for i, ano in enumerate(anos):
        t1, t2 = (tab.get(f"1º turno de {ano}"), tab.get(f"2º turno de {ano}"))
        normal = vol[ano]
        frases = []
        if t1:
            ib = t1["Ibovespa"]
            m = max(t1, key=lambda a: abs(t1[a]))
            f = f"Em {ano}, no pregão depois do primeiro turno, o Ibovespa {_mov(ib)}"
            vezes = abs(ib) / normal["Ibovespa"]
            if vezes >= 2:
                f += f", umas {num(vezes, 0)} vezes a oscilação de um dia comum daquele ano"
            if m != "Ibovespa" and abs(t1[m]) > abs(ib):
                f += f", e {com_artigo(m)} {_mov(t1[m])}"
            f += "."
            if i > 0 and max(abs(v) for v in t1.values()) > max(abs(v) for v in tab[f"1º turno de {anos[0]}"].values()):
                f = f.replace(f"Em {ano}, no", f"Em {ano} os movimentos foram maiores. No", 1)
            frases.append(f)
        if t2:
            ib = t2["Ibovespa"]
            if abs(ib) >= 2 * normal["Ibovespa"]:
                f = f"Depois do segundo turno, o índice {_mov(ib)}"
                desde = c3["pior_desde"].get(f"2º turno de {ano}")
                if ib < 0 and desde is not None:
                    f += f", a maior queda num dia desde {br(desde)}"
                    if desde.year == 2020:
                        f += ", no começo da pandemia"
                f += "."
                if ib <= -0.10:
                    f += " Como passou de 10%, a queda acionou o circuit breaker da B3, que paralisa os negócios por meia hora."
            else:
                m = max(t2, key=lambda a: abs(t2[a]))
                if t1 and t1[m] * t2[m] < 0:
                    f = f"No segundo turno, {com_artigo(m)} fez o caminho contrário e {_mov(t2[m])}."
                else:
                    f = f"No segundo turno, o maior movimento foi d{com_artigo(m)}, que {_mov(t2[m])}."
            frases.append(f)
        if frases:
            paragrafos.append("<p>" + " ".join(frases) + "</p>")
    return "\n".join(paragrafos)


def relatorio(d: Dados, c1, c2, c3, c4) -> str:
    rec_txt = (f"A volta demorou bem mais. O índice só fechou acima do topo anterior em {br(c1['recuperacao_data'])}, "
               f"uns {num(c1['meses_recuperacao'], 0)} meses depois do fundo."
               if c1["recuperacao_data"] is not None else "Até a última atualização, o índice ainda não tinha voltado ao topo de antes da crise.")

    ra = c2["ret_alta"]
    itau, magalu = ra["Itaú (ITUB4)"], ra["Magazine Luiza (MGLU3)"]
    if itau > ra["Ibovespa"] > magalu:
        hipotese_txt = (f"Dessa vez a hipótese bateu. A distância entre os dois foi de {num(abs(itau - magalu) * 100, 0)} "
                        "pontos percentuais no mesmo intervalo, com a mesma taxa de juros valendo para os dois.")
    elif itau > magalu:
        hipotese_txt = (f"Só metade da hipótese bateu. A Magazine Luiza derreteu, mas o Itaú não se salvou e terminou "
                        f"um pouco abaixo do próprio Ibovespa. Uma explicação possível é que o juro alto deixa o crédito "
                        f"mais caro, mas também faz mais gente atrasar pagamento, e uma coisa compensou a outra.")
    else:
        hipotese_txt = ("Aqui a hipótese não se confirmou: a Magazine Luiza foi melhor que o Itaú no período. "
                        "Outros fatores pesaram mais que o juro.")

    eleicao_txt = texto_eleicao(c3)
    turnos = list(c3["tabela"])
    ativos_el = list(next(iter(c3["tabela"].values())))
    linhas_eleicao = "".join(
        f"<tr><td>{r.replace(' de ', ', ')}</td>" + "".join(f"<td>{pct(c3['tabela'][r][a])}</td>" for a in ativos_el) + "</tr>"
        for r in turnos
    )
    cab_eleicao = "".join(f"<th>{a.split(' (')[0]}</th>" for a in ativos_el)
    tipicos = {ano: pct(v["Ibovespa"]).lstrip("+") for ano, v in c3["vol_normal"].items()}
    if len(set(tipicos.values())) == 1:
        tipico = f"cerca de {next(iter(tipicos.values()))}" + (" nos dois anos" if len(tipicos) == 2 else "")
    else:
        tipico = " e ".join(f"{v} em {ano}" for ano, v in tipicos.items())

    perderam = [com_artigo(a) for a in c4["perderam"]]
    if not perderam:
        perderam_frase = "Todos os ativos que escolhi conseguiram."
    elif len(perderam) == 1:
        perderam_frase = f"Só {perderam[0]} não conseguiu."
    else:
        lista = ", ".join(perderam[:-1]) + " e " + perderam[-1]
        perderam_frase = lista[0].upper() + lista[1:] + " não conseguiram."

    selic_txt = f"Em {br(c2['inicio_alta'])} ele começou a subir de novo e chegou a {num(c2['teto1'], 2)}% em {br(c2['teto1_data'])}."
    if c2.get("piso2") is not None:
        selic_txt += (f" Depois de um tempo parada, a taxa caiu até {num(c2['piso2'], 2)}%, voltou a subir em "
                      f"{br(c2['inicio_alta2'])} e foi até {num(c2['teto'], 2)}%, em {br(c2['teto_data'])}.")
    if c2.get("inicio_corte") is not None:
        selic_txt += f" O corte seguinte só começou em {br(c2['inicio_corte'])}."
    atualizado = d.atualizado[:10]
    try:
        atualizado = br(pd.Timestamp(atualizado))
    except Exception:
        atualizado = br(c4["fim"])

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>O Mercado Não Mente | Vitor Del Bosque Lima</title>
<meta name="description" content="Análise de dados da bolsa brasileira: pandemia, juros e eleições contados pelos preços.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--ink:#1A2230;--muted:#5B6576;--line:#DCE1E8;--accent:#EB6A12;--bg:#FFFFFF;--soft:#F3F5F8}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'IBM Plex Sans',sans-serif;color:var(--ink);background:var(--bg);line-height:1.65;font-size:18px}}
main{{max-width:760px;margin:0 auto;padding:64px 24px 96px}}
.kicker{{color:var(--accent);font-weight:600;font-size:.95rem}}
h1{{font-family:'Bricolage Grotesque',sans-serif;font-size:clamp(2.4rem,6vw,3.6rem);line-height:1;letter-spacing:-.03em;margin:10px 0 18px}}
h2{{font-family:'Bricolage Grotesque',sans-serif;font-size:1.7rem;line-height:1.15;letter-spacing:-.02em;margin:64px 0 14px}}
.lede{{font-size:1.2rem;color:var(--muted)}}
p{{margin:0 0 16px}}
.num{{font-weight:600}}
figure{{margin:24px -12px 8px}}
figure img{{width:100%;height:auto;display:block}}
figcaption{{font-size:.85rem;color:var(--muted);padding:6px 12px 0}}
table{{width:100%;border-collapse:collapse;font-size:.95rem;margin:12px 0 20px}}
th,td{{text-align:right;padding:8px 10px;border-bottom:1px solid var(--line)}}
th:first-child,td:first-child{{text-align:left}}
th{{font-weight:600;color:var(--muted)}}
.meta{{font-size:.9rem;color:var(--muted);border-top:1px solid var(--line);margin-top:64px;padding-top:20px}}
a{{color:var(--accent)}}
</style>
</head>
<body><main>
<div class="kicker">Vitor Del Bosque Lima</div>
<h1>O Mercado Não Mente</h1>
<p class="lede">Quis ver nos números como a bolsa brasileira reagiu a alguns momentos que todo mundo lembra. Peguei os preços de {br(c4['inicio'])} a {br(c4['fim'])} e fui atrás de quatro perguntas.</p>

<h2>1. A pandemia tirou {pct(-c1['queda'], 0).lstrip('+')} do Ibovespa em {c1['pregoes']} pregões</h2>
<p>Em {br(c1['topo_data'])} o Ibovespa fechou em {num(c1['topo'] / 1000, 0)} mil pontos. Com a covid chegando ao Brasil, o índice caiu até {num(c1['fundo'] / 1000, 0)} mil em {br(c1['fundo_data'])}. Foram <span class="num">{pct(c1['queda'])}</span> em {(c1['fundo_data'] - c1['topo_data']).days} dias.</p>
<p>{rec_txt}</p>
<figure><img src="{c1['img']}" alt="Gráfico do Ibovespa entre 2019 e 2021 com a queda da pandemia destacada"><figcaption>Ibovespa no fechamento diário. Fonte: Yahoo Finance.</figcaption></figure>

<h2>2. O que aconteceu com a bolsa quando os juros subiram</h2>
<p>Na pandemia o Banco Central baixou a Selic até {num(c2['piso'], 2)}% ao ano, o menor nível desde que a taxa existe. {selic_txt}</p>
<figure><img src="{c2['img1']}" alt="Ibovespa e Selic meta desde 2019"><figcaption>Ibovespa (linha escura) e Selic meta (laranja). As faixas marcam os dois períodos de alta. Fontes: Yahoo Finance e Banco Central (série 432 do SGS).</figcaption></figure>
<p>Minha hipótese era simples. Com juro alto, comprar a prazo fica caro, então o varejo deveria sofrer, e banco tende a lucrar mais com crédito. Comparei o Ibovespa com o Itaú e a Magazine Luiza durante a primeira alta, de {num(c2['piso'], 2)}% para {num(c2['teto1'], 2)}%: o índice terminou em {pct(ra['Ibovespa'])}, o Itaú em <span class="num">{pct(ra['Itaú (ITUB4)'])}</span> e a Magazine Luiza em <span class="num">{pct(ra['Magazine Luiza (MGLU3)'])}</span>.</p>
<figure><img src="{c2['img2']}" alt="Itaú, Ibovespa e Magazine Luiza em base 100 no ciclo de alta da Selic"><figcaption>Base 100 no primeiro dia de alta da Selic.</figcaption></figure>
<p>{hipotese_txt}</p>

<h2>3. O dia seguinte às eleições de 2022 e 2026</h2>
{eleicao_txt}
<table><thead><tr><th>Pregão seguinte ao</th>{cab_eleicao}</tr></thead><tbody>{linhas_eleicao}</tbody></table>
<figure><img src="{c3['img']}" alt="Variação dos ativos nos pregões seguintes aos turnos das eleições de 2022 e 2026"><figcaption>Variação no pregão seguinte a cada turno. Num dia comum de janeiro a setembro, o Ibovespa oscilava {tipico} (desvio padrão dos retornos diários).</figcaption></figure>

<h2>4. Quem ganhou da inflação desde 2019</h2>
<p>No período, o IPCA acumulou {pct(c4['inflacao'])}. Então não basta o ativo subir, ele precisa subir mais que isso para o dinheiro valer mais do que no começo. {perderam_frase}</p>
<figure><img src="{c4['img']}" alt="Quanto viraram mil reais aplicados em cada ativo desde 2019"><figcaption>Preços ajustados por dividendos e desdobramentos. As barras em laranja ficaram abaixo da inflação. Fontes: Yahoo Finance e Banco Central (série 433 do SGS).</figcaption></figure>

<h2>De onde vêm os números</h2>
<p>Os preços vêm do Yahoo Finance pela biblioteca yfinance, e a Selic e o IPCA vêm da API do Banco Central. Tratei tudo em Python com pandas e fiz os gráficos com matplotlib. Os números do texto são calculados pelo próprio código, que roda de novo toda sexta pelo GitHub Actions, então esta página se atualiza sozinha.</p>
<p>Olhar o preço em volta de um fato não prova que foi ele que causou o movimento, porque muita coisa acontece ao mesmo tempo. E nada aqui é recomendação de investimento.</p>

<div class="meta">Dados atualizados em {atualizado}. Código em <a href="https://github.com/VitorDBL/o-mercado-nao-mente">github.com/VitorDBL/o-mercado-nao-mente</a> · <a href="https://vitordbl.github.io">vitordbl.github.io</a></div>
</main></body></html>
"""


def main() -> None:
    d = carregar()
    c1, c2, c3, c4 = pandemia(d), juros(d), eleicao(d), acumulado(d)
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(relatorio(d, c1, c2, c3, c4), encoding="utf-8")

    def limpar(o):
        if isinstance(o, dict):
            return {str(k): limpar(v) for k, v in o.items() if not str(k).startswith("img")}
        if isinstance(o, (pd.Timestamp,)):
            return o.date().isoformat()
        if isinstance(o, pd.Series):
            return {k: round(float(v), 6) for k, v in o.items()}
        if isinstance(o, list):
            return [limpar(v) for v in o]
        try:
            return round(float(o), 6)
        except (TypeError, ValueError):
            return o

    resumo = {"pandemia": c1, "juros": c2, "eleicao": c3, "acumulado": c4}
    (DATA / "resultados.json").write_text(json.dumps(limpar(resumo), ensure_ascii=False, indent=2))
    print("Relatório gerado em docs/index.html")


if __name__ == "__main__":
    main()
