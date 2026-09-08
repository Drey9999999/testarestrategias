"""O modelo absoluto ja consegue cronometrar o MERCADO?

O filtro de exposicao nao precisa acertar ativo por ativo: precisa acertar se o
mercado como um todo sobe. Entao a metrica certa e outra — agregar a previsao
do modelo por data e comparar com a direcao do mercado naquela data (mediana
dos retornos dos 54 ativos).

Sao ~600 datas na janela de teste, nao 32 mil amostras: o numero e mais ruidoso
e o teste nulo tem que refletir isso.
"""

import random
import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, auc, treinar, prever
from treino_mercado import carregar_com_mercado

X, Yabs, D, A, R = carregar_com_mercado()
tr, va, te = fatiar(D)
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
Ya = torch.tensor(Yabs, dtype=torch.float32)
Rt = torch.tensor(R, dtype=torch.float32)
W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)

mods = []
for s in range(8):
    m, mu, sd, _ = treinar(Xt, Ya, W, tr, va, dim, semente=s, oculto=128,
                           camadas=3, lr=3e-4, epocas=80, parada=10)
    mods.append((m, mu, sd))

for rot, idxs in [("VALIDACAO 2023-24", va), ("TESTE 2025/26", te)]:
    ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
    pred = [sum(c)/len(c) for c in zip(*ps)]

    # agrega por data: previsao media do mercado x direcao real do mercado
    p_data, r_data = defaultdict(list), defaultdict(list)
    for pos, i in enumerate(idxs):
        p_data[D[i]].append(pred[pos])
        r_data[D[i]].append(R[i])
    datas = sorted(p_data)
    pm = [statistics.mean(p_data[d]) for d in datas]
    ym = [1.0 if statistics.median(r_data[d]) > 0 else 0.0 for d in datas]

    a = auc(ym, pm)
    lim = statistics.median(pm)
    acc = sum(1 for p, y in zip(pm, ym) if (p > lim) == (y > .5)) / len(ym)
    base = statistics.mean(ym)

    # nulo: embaralhar a serie de previsoes contra as datas, em blocos, para
    # preservar a forte autocorrelacao de ambas as series
    rng = random.Random(41)
    nulos = []
    n = len(datas)
    for _ in range(1000):
        k = rng.randrange(20, n - 20)
        desl = pm[k:] + pm[:k]              # deslocamento circular
        nulos.append(auc(ym, desl))
    nulos.sort()
    acima = sum(1 for x in nulos if x >= a)

    print(f"\n{rot}: {len(datas)} datas   "
          f"({base*100:.0f}% delas o mercado subiu)")
    print(f"  AUC de cronometragem do mercado: {a:.4f}   "
          f"acerto no limiar mediano: {acc*100:.1f}%")
    print(f"  nulo por deslocamento circular (1000x): mediana {statistics.median(nulos):.4f}"
          f"   p90 {nulos[900]:.4f}   ->  p = {acima/1000:.3f}")
