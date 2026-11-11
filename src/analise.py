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
    teto = s[inicio_alta:].max()
    teto_data = s[inicio_alta:][s[inicio_alta:] == teto].index[0]
    apos = s[teto_data:]
    cortes = apos[apos < teto]
    inicio_corte = cortes.index[0] if len(cortes) else None
    return {"piso": piso, "inicio_alta": inicio_alta, "teto": teto, "teto_data": teto_data,
            "inicio_corte": inicio_corte}


def juros(d: Dados) -> dict:
    c = ciclos_selic(d.selic)
    p = d.precos

    def ret(col, a, b):
        serie = p[col][a:b]
        return serie.iloc[-1] / serie.iloc[0] - 1

    alta = (c["inicio_alta"], c["teto_data"])
    ativos = ["Ibovespa", "Itaú (ITUB4)", "Magazine Luiza (MGLU3)"]
    ret_alta = {a: ret(a, *alta) for a in ativos}

    fig, ax = plt.subplots(figsize=(10, 4.4))
    ibov = p["Ibovespa"]["2019-01-01":]
    ax.plot(ibov.index, ibov / 1000, color=GRAFITE, lw=1.4, label="Ibovespa (mil pontos)")
    ax.set_ylabel("Ibovespa (mil pontos)")
    ax.axvspan(*alta, color=LARANJA, alpha=0.10, lw=0)
    ax2 = ax.twinx()
    selic = d.selic.resample("D").ffill()["2019-01-01":]
    ax2.step(selic.index, selic, where="post", color=LARANJA, lw=2, label="Selic meta (% a.a.)")
    ax2.set_ylabel("Selic meta (% ao ano)", color=LARANJA)
    ax2.tick_params(axis="y", colors=LARANJA)
    ax2.grid(False)
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(CINZA_CLARO)
    ax.text(alta[0] + (alta[1] - alta[0]) / 2, ax.get_ylim()[1] * 0.98, "ciclo de alta",
            ha="center", va="top", color=LARANJA, fontsize=10)
    fmt_eixo_data(ax)
    img1 = salvar(fig, "2_selic_ibovespa.png")

    base = p[ativos][alta[0]:alta[1]]
    base = base / base.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(10, 4.4))
    cores = {"Ibovespa": GRAFITE, "Itaú (ITUB4)": LARANJA, "Magazine Luiza (MGLU3)": AZUL}
    for a in ativos:
        ax.plot(base.index, base[a], color=cores[a], lw=1.8)
        ax.annotate(f"{a.split(' (')[0]} {pct(ret_alta[a], 0)}", (base.index[-1], base[a].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", color=cores[a],
                    fontsize=10, fontweight="bold")
    ax.axhline(100, color=CINZA, lw=1, ls="--")
    ax.set_ylabel("Base 100 no início da alta")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b/%y"))
    img2 = salvar(fig, "3_vencedores_perdedores.png")

    return {**c, "ret_alta": ret_alta, "img1": img1, "img2": img2}


# ---------------------------------------------------------------- capítulo 3
def eleicao(d: Dados) -> dict:
    p = d.precos
    datas = {"1º turno (02/10/2022)": "2022-10-03", "2º turno (30/10/2022)": "2022-10-31"}
    ativos = ["Ibovespa", "Petrobras (PETR4)", "Itaú (ITUB4)", "Vale (VALE3)"]
    diarios = p[ativos].pct_change()
    tabela = {}
    for rotulo, dia in datas.items():
        dia = diarios.index[diarios.index.get_indexer([pd.Timestamp(dia)], method="bfill")[0]]
        tabela[rotulo] = {a: diarios.loc[dia, a] for a in ativos}

    vol_normal = diarios["2022-01-01":"2022-09-30"].std()

    fig, ax = plt.subplots(figsize=(10, 4.2))
    largura = 0.38
    xs = range(len(ativos))
    for k, (rotulo, cor) in enumerate(zip(tabela, [LARANJA, GRAFITE])):
        vals = [tabela[rotulo][a] * 100 for a in ativos]
        barras = ax.bar([x + (k - 0.5) * largura for x in xs], vals, largura, color=cor, label=rotulo)
        for b, v in zip(barras, vals):
            ax.annotate(f"{v:+.1f}%".replace(".", ","), (b.get_x() + b.get_width() / 2, v),
                        xytext=(0, 4 if v >= 0 else -14), textcoords="offset points",
                        ha="center", fontsize=9, color=GRAFITE)
    ax.axhline(0, color=GRAFITE, lw=0.8)
    ax.set_xticks(list(xs), [a.split(" (")[0] for a in ativos])
    ax.set_ylabel("Variação no pregão seguinte (%)")
    ax.legend(frameon=False, loc="lower left")
    img = salvar(fig, "4_eleicao.png")

    return {"tabela": tabela, "vol_normal": vol_normal, "img": img}


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
    ax.annotate(f"R$ 1.000 corrigidos pela\ninflação: R$ {1000 * (1 + inflacao):,.0f}".replace(",", "."),
                (1000 * (1 + inflacao), len(ordem) - 0.5), xytext=(6, 0), textcoords="offset points",
                fontsize=9, color="#5B6576", va="top")
    ax.set_xlabel(f"Quanto viraram R$ 1.000 aplicados em {br(inicio)}")
    ax.grid(axis="y", visible=False)
    img = salvar(fig, "5_acumulado.png")

    return {"inicio": inicio, "fim": fim, "retorno": retorno, "inflacao": inflacao,
            "perderam": [a for a in ordem if retorno[a] < inflacao], "img": img}


# ---------------------------------------------------------------- relatório
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
        hipotese_txt = ("A ordem foi a que eu esperava, com o Itaú na frente da Magazine Luiza, mas o Ibovespa não ficou no meio "
                        "do caminho, então não dá para dizer que o juro explica tudo.")
    else:
        hipotese_txt = ("Aqui a hipótese não se confirmou: a Magazine Luiza foi melhor que o Itaú no período. "
                        "Outros fatores pesaram mais que o juro.")

    linhas_eleicao = "".join(
        f"<tr><td>{a.split(' (')[0]}</td>" + "".join(f"<td>{pct(c3['tabela'][r][a])}</td>" for r in c3["tabela"]) +
        f"<td>{pct(c3['vol_normal'][a]).lstrip('+')}</td></tr>"
        for a in next(iter(c3["tabela"].values()))
    )
    primeiro = next(iter(c3["tabela"].values()))
    maior_mov = max(primeiro, key=lambda a: abs(primeiro[a]))
    vezes = abs(primeiro[maior_mov]) / c3["vol_normal"][maior_mov]
    comparacao_txt = (f", então o movimento foi umas {num(vezes, 0)} vezes maior que o normal." if vezes >= 2
                      else ". Ou seja, o dia foi agitado, mas dentro do que se via naquele ano.")

    perderam = [a.split(" (")[0] for a in c4["perderam"]]
    if not perderam:
        perderam_frase = "Todos os ativos que escolhi conseguiram."
    elif len(perderam) == 1:
        perderam_frase = f"Só {perderam[0]} não conseguiu."
    else:
        perderam_frase = ", ".join(perderam[:-1]) + " e " + perderam[-1] + " não conseguiram."

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>O Mercado Não Mente | Vitor Del Bosque Lima</title>
<meta name="description" content="Análise de dados da bolsa brasileira: pandemia, juros e eleição contados pelos preços.">
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
<p>Na pandemia o Banco Central baixou a Selic até {num(c2['piso'], 2)}% ao ano, o menor nível desde que a taxa existe. Em {br(c2['inicio_alta'])} ele começou a subir de novo e só parou em {num(c2['teto'], 2)}%, em {br(c2['teto_data'])}.</p>
<figure><img src="{c2['img1']}" alt="Ibovespa e Selic meta desde 2019"><figcaption>Ibovespa (linha escura) e Selic meta (laranja). A faixa marca o período de alta. Fontes: Yahoo Finance e Banco Central (série 432 do SGS).</figcaption></figure>
<p>Minha hipótese era simples. Com juro alto, comprar a prazo fica caro, então o varejo deveria sofrer, e banco tende a lucrar mais com crédito. Comparei o Ibovespa com o Itaú e a Magazine Luiza durante a alta: o índice terminou em {pct(ra['Ibovespa'])}, o Itaú em <span class="num">{pct(ra['Itaú (ITUB4)'])}</span> e a Magazine Luiza em <span class="num">{pct(ra['Magazine Luiza (MGLU3)'])}</span>.</p>
<figure><img src="{c2['img2']}" alt="Itaú, Ibovespa e Magazine Luiza em base 100 no ciclo de alta da Selic"><figcaption>Base 100 no primeiro dia de alta da Selic.</figcaption></figure>
<p>{hipotese_txt}</p>

<h2>3. O dia seguinte ao primeiro turno de 2022</h2>
<p>No pregão depois do primeiro turno, {maior_mov.split(' (')[0]} andou <span class="num">{pct(primeiro[maior_mov])}</span>. Num dia comum daquele ano, a oscilação típica era de {pct(c3['vol_normal'][maior_mov]).lstrip('+')}{comparacao_txt}</p>
<table><thead><tr><th>Ativo</th>{''.join(f'<th>{r}</th>' for r in c3['tabela'])}<th>Dia típico em 2022</th></tr></thead><tbody>{linhas_eleicao}</tbody></table>
<figure><img src="{c3['img']}" alt="Variação dos ativos nos pregões seguintes aos turnos da eleição de 2022"><figcaption>Variação no pregão seguinte a cada turno. O dia típico é o desvio padrão dos retornos diários de janeiro a setembro de 2022.</figcaption></figure>

<h2>4. Quem ganhou da inflação desde 2019</h2>
<p>No período, o IPCA acumulou {pct(c4['inflacao'])}. Então não basta o ativo subir, ele precisa subir mais que isso para o dinheiro valer mais do que no começo. {perderam_frase}</p>
<figure><img src="{c4['img']}" alt="Quanto viraram mil reais aplicados em cada ativo desde 2019"><figcaption>Preços ajustados por dividendos e desdobramentos. As barras em laranja ficaram abaixo da inflação. Fontes: Yahoo Finance e Banco Central (série 433 do SGS).</figcaption></figure>

<h2>De onde vêm os números</h2>
<p>Os preços vêm do Yahoo Finance pela biblioteca yfinance, e a Selic e o IPCA vêm da API do Banco Central. Tratei tudo em Python com pandas e fiz os gráficos com matplotlib. Os números do texto são calculados pelo próprio código, que roda de novo toda sexta pelo GitHub Actions, então esta página se atualiza sozinha.</p>
<p>Uma ressalva importante: olhar o preço em volta de um fato não prova que o fato causou o movimento, porque muita coisa acontece ao mesmo tempo. E nada aqui é recomendação de investimento.</p>

<div class="meta">Dados atualizados em {d.atualizado or br(c4['fim'])}. Código em <a href="https://github.com/VitorDBL/o-mercado-nao-mente">github.com/VitorDBL/o-mercado-nao-mente</a> · <a href="https://vitordbl.github.io">vitordbl.github.io</a></div>
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
