"""Features de mercado desenhadas para prazo CURTO.

Os agregados anteriores mediam NIVEL: quantos ativos estao acima da media,
qual a forca mediana. Em prazo de 1 a 3 pregoes o que costuma informar e
outra coisa:

  - ACELERACAO da amplitude: amplitude alta e estavel nao diz nada; amplitude
    subindo rapido diz que o dinheiro esta entrando agora
  - REVERSAO de curtissimo prazo: depois de um dia muito ruim no mercado
    inteiro, o dia seguinte tende a repicar (e o efeito mais documentado em
    prazo curto)
  - PRESSAO de volume: volume acima do normal acompanhando alta ou queda
  - POSICAO NA BARRA: fechar perto da maxima do dia e sinal diferente de
    fechar perto da minima, mesmo com o mesmo retorno
"""

import json
import os
import statistics
from collections import defaultdict

from backtest import book_features as BF

IDX = {n: k for k, n in enumerate(BF.NAMES)}

CURTO = [
    "ret_mercado_1", "ret_mercado_3", "ret_mercado_5",
    "aceleracao_amplitude_3", "aceleracao_amplitude_10",
    "amplitude_sma20", "fracao_fecha_forte",
    "volume_surto", "volume_direcional",
    "dispersao_variacao", "rsi_mercado_variacao", "reversao_extremo",
]


def carregar_curto(dir_features="results/features", horizonte=3):
    brutos = {}
    for arq in sorted(os.listdir(dir_features)):
        d = json.load(open(f"{dir_features}/{arq}"))
        brutos[d["inst"]] = d

    por_data = defaultdict(list)
    for inst, d in brutos.items():
        for j, dt in enumerate(d["datas"]):
            por_data[dt].append((inst, j))
    datas = [d for d in sorted(por_data) if len(por_data[d]) >= 5]
    n_feat = len(next(iter(brutos.values()))["X"][0])

    # serie de agregados por data, para poder derivar variacoes
    agg = {}
    for dt in datas:
        L = [brutos[i]["X"][j] for i, j in por_data[dt]]
        agg[dt] = {
            "amp20": sum(1 for x in L if x[IDX["sma20"]] > 0) / len(L),
            "amp200": sum(1 for x in L if x[IDX["preco_acima_sma200"]] > 0.5) / len(L),
            "ret1": statistics.median(x[IDX["ret1"]] if "ret1" in IDX
                                      else x[IDX["corpo"]] for x in L),
            "corpo": statistics.median(x[IDX["corpo"]] for x in L),
            "forte": sum(1 for x in L if x[IDX["corpo"]] > 0.3) / len(L),
            "vol": statistics.median(x[IDX["vol_relativo"]] for x in L),
            "disp": statistics.pstdev([x[IDX["sma20"]] for x in L]),
            "rsi": statistics.median(x[IDX["rsi14"]] for x in L),
            "sma20": statistics.median(x[IDX["sma20"]] for x in L),
        }

    X, Y, D, A, R = [], [], [], [], []
    for k, dt in enumerate(datas):
        if k < 12:
            continue
        a = agg[dt]
        a1, a3, a5, a10 = (agg[datas[k - 1]], agg[datas[k - 3]],
                           agg[datas[k - 5]], agg[datas[k - 10]])
        mercado = [
            (a["sma20"] - a1["sma20"]) * 20,
            (a["sma20"] - a3["sma20"]) * 20,
            (a["sma20"] - a5["sma20"]) * 20,
            (a["amp20"] - a3["amp20"]) * 2,
            (a["amp20"] - a10["amp20"]) * 2,
            a["amp20"] - 0.5,
            a["forte"] - 0.5,
            a["vol"],
            a["vol"] * (1 if a["corpo"] > 0 else -1),
            (a["disp"] - a5["disp"]) * 20,
            (a["rsi"] - a3["rsi"]) * 2,
            # reversao: mercado muito esticado para baixo nos ultimos 3 dias
            -1.0 if (a["sma20"] - a3["sma20"]) * 20 < -0.5 else
            (1.0 if (a["sma20"] - a3["sma20"]) * 20 > 0.5 else 0.0),
        ]
        linhas = [brutos[i]["X"][j] for i, j in por_data[dt]]
        perc = [[0.0] * n_feat for _ in linhas]
        for f in range(n_feat):
            col = sorted((linhas[q][f], q) for q in range(len(linhas)))
            for posto, (_, q) in enumerate(col):
                perc[q][f] = posto / max(len(linhas) - 1, 1) - 0.5
        for q, (inst, j) in enumerate(por_data[dt]):
            X.append(linhas[q] + perc[q] + mercado)
            R.append(brutos[inst][f"ret{horizonte}"][j])
            Y.append(1.0 if R[-1] > 0 else 0.0)
            D.append(dt)
            A.append(inst)
    return X, Y, D, A, R
