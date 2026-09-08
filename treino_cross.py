"""Features transversais: como este ativo se compara aos outros HOJE.

O alvo e relativo ("este bate a mediana do dia?"), mas o modelo so via cada
ativo isolado: RSI 62, MACD positivo, etc. Faltava a informacao comparativa —
RSI 62 e alto ou baixo em relacao ao que os outros 53 marcam hoje?

Para cada data e cada feature, calcula-se o percentil do ativo entre os ativos
daquela data. E causal por construcao: usa apenas dados do proprio dia.
"""

import json
import os
from collections import defaultdict


def carregar_com_transversal(dir_features="results/features", quais=None):
    """Devolve X com as features originais MAIS o percentil transversal delas."""
    brutos = {}
    for arq in sorted(os.listdir(dir_features)):
        d = json.load(open(f"{dir_features}/{arq}"))
        brutos[d["inst"]] = d

    por_data = defaultdict(list)
    for inst, d in brutos.items():
        for j, dt in enumerate(d["datas"]):
            por_data[dt].append((inst, j))

    n_feat = len(next(iter(brutos.values()))["X"][0])
    quais = list(range(n_feat)) if quais is None else quais

    X, Y, D, A, R = [], [], [], [], []
    for dt in sorted(por_data):
        membros = por_data[dt]
        if len(membros) < 5:
            continue
        linhas = [brutos[i]["X"][j] for i, j in membros]
        # percentil de cada feature entre os ativos do dia
        perc = [[0.0] * len(quais) for _ in membros]
        for c, f in enumerate(quais):
            col = sorted((linhas[k][f], k) for k in range(len(membros)))
            for posto, (_, k) in enumerate(col):
                perc[k][c] = posto / max(len(membros) - 1, 1) - 0.5
        for k, (inst, j) in enumerate(membros):
            X.append(linhas[k] + perc[k])
            R.append(brutos[inst]["ret"][j])
            Y.append(1.0 if brutos[inst]["ret"][j] > 0 else 0.0)
            D.append(dt)
            A.append(inst)
    return X, Y, D, A, R
