"""Features do MERCADO INTEIRO, para o alvo absoluto.

O alvo relativo melhorou quando o modelo passou a ver como o ativo se compara
aos outros hoje. O alvo absoluto pergunta outra coisa — "isto sobe?" — e a
resposta depende do estado do mercado como um todo, que o modelo nunca viu.

Cada data recebe agregados calculados sobre os 54 mercados daquele dia:
amplitude (quantos estao acima das medias), dispersao, forca mediana, pressao
de volume. Sao causais: usam so o proprio dia.
"""

import json
import os
import statistics
from collections import defaultdict

from backtest import book_features as BF

# indices das features do livro que interessam para agregar
IDX = {n: k for k, n in enumerate(BF.NAMES)}
AGREGADOS = [
    "amplitude_sma200",    # fracao dos ativos acima da SMA 200
    "amplitude_sma50",
    "amplitude_rsi50",     # fracao com RSI acima de 50
    "amplitude_macd",      # fracao com MACD acima do sinal
    "forca_mediana",       # mediana da distancia para a SMA 20
    "dispersao",           # desvio-padrao dessa distancia entre ativos
    "rsi_mediano",
    "vol_mediana",         # mediana da largura das bandas (volatilidade)
    "volume_mediano",
    "dist_topo60_mediana", # quao longe o mercado esta das maximas
    "aperto_fracao",       # fracao em aperto de Bollinger
    "bb_posicao_mediana",
]


def carregar_com_mercado(dir_features="results/features"):
    """X = 46 features do ativo + 46 percentis transversais + 12 do mercado."""
    brutos = {}
    for arq in sorted(os.listdir(dir_features)):
        d = json.load(open(f"{dir_features}/{arq}"))
        brutos[d["inst"]] = d

    por_data = defaultdict(list)
    for inst, d in brutos.items():
        for j, dt in enumerate(d["datas"]):
            por_data[dt].append((inst, j))

    n_feat = len(next(iter(brutos.values()))["X"][0])
    X, Y, D, A, R = [], [], [], [], []
    for dt in sorted(por_data):
        membros = por_data[dt]
        if len(membros) < 5:
            continue
        linhas = [brutos[i]["X"][j] for i, j in membros]

        perc = [[0.0] * n_feat for _ in membros]
        for f in range(n_feat):
            col = sorted((linhas[k][f], k) for k in range(len(membros)))
            for posto, (_, k) in enumerate(col):
                perc[k][f] = posto / max(len(membros) - 1, 1) - 0.5

        def frac(nome, limiar=0.5):
            return sum(1 for L in linhas if L[IDX[nome]] > limiar) / len(linhas) - 0.5

        def med(nome):
            return statistics.median(L[IDX[nome]] for L in linhas)

        sma20 = [L[IDX["sma20"]] for L in linhas]
        mercado = [
            frac("preco_acima_sma200"), frac("cruz_50_200"),
            frac("rsi_acima_50"), frac("macd_acima_sinal"),
            statistics.median(sma20) * 10,
            statistics.pstdev(sma20) * 10,
            med("rsi14"), med("bb_largura"), med("vol_relativo"),
            med("dist_topo60"), frac("bb_aperto"), med("bb_posicao"),
        ]

        for k, (inst, j) in enumerate(membros):
            X.append(linhas[k] + perc[k] + mercado)
            R.append(brutos[inst]["ret"][j])
            Y.append(1.0 if brutos[inst]["ret"][j] > 0 else 0.0)
            D.append(dt)
            A.append(inst)
    return X, Y, D, A, R
