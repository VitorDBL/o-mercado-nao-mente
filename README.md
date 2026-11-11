# O Mercado Não Mente

Projeto pessoal de análise de dados em que olho como a bolsa brasileira reagiu à pandemia, aos ciclos de alta da Selic e às eleições de 2022 e 2026, e quais ativos ganharam da inflação desde 2019.

O relatório com os gráficos e as conclusões está em https://vitordbl.github.io/o-mercado-nao-mente/

## Como está organizado

`src/coleta.py` baixa os preços ajustados do Yahoo Finance (Ibovespa, Petrobras, Vale, Itaú, Magazine Luiza e dólar) e as séries de Selic e IPCA da API do SGS do Banco Central. Tudo vai para a pasta `data/`.

`src/analise.py` faz as contas, gera os gráficos e escreve o relatório em `docs/`. Os números do texto saem do código, então se os dados mudam o texto muda junto.

`app.py` é um painel em Streamlit para quem quiser escolher outros ativos e períodos.

Um workflow do GitHub Actions roda a coleta e a análise toda sexta depois do fechamento e publica o resultado.

## Rodando na sua máquina

```bash
pip install -r requirements.txt
python src/coleta.py
python src/analise.py
streamlit run app.py
```

## Ressalvas

O relatório mostra o que os preços fizeram em volta de cada acontecimento, mas não separa o efeito de cada um, porque muita coisa acontece ao mesmo tempo. Não é recomendação de investimento.
