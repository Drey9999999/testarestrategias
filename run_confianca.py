"""Acerto por faixa de confianca.

O acerto medio mistura as previsoes em que o modelo esta seguro com aquelas em
que esta em cima do muro. Um sistema real so opera as primeiras. Aqui o acerto
e medido nas previsoes mais confiantes — as que mais se afastam de 0,5.
"""

import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, auc, treinar, prever
from treino_cross import carregar_com_transversal

X, _, D, A, R = carregar_com_transversal()
tr, va, te = fatiar(D)
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
Rt = torch.tensor(R, dtype=torch.float32)
W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)

por_data = defaultdict(list)
for i, d in enumerate(D):
    por_data[d].append(i)
Yl = [0.0] * len(R)
for d, idxs in por_data.items():
    if len(idxs) >= 5:
        med = statistics.median(R[i] for i in idxs)
        for i in idxs:
            Yl[i] = 1.0 if R[i] > med else 0.0
Yr = torch.tensor(Yl, dtype=torch.float32)

mods = []
for s in range(10):
    m, mu, sd, _ = treinar(Xt, Yr, W, tr, va, dim, semente=s, oculto=128,
                           camadas=3, lr=3e-4, epocas=80, parada=10)
    mods.append((m, mu, sd))

for rot, idxs in [("VALIDACAO", va), ("TESTE 2025/26", te)]:
    ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
    pred = [sum(c)/len(c) for c in zip(*ps)]
    y = [Yr[i].item() for i in idxs]
    conf = sorted(range(len(y)), key=lambda k: -abs(pred[k] - 0.5))
    print(f"\n{rot}  ({len(y):,} previsoes, AUC {auc(y, pred):.4f})")
    print(f"  {'fatia mais confiante':>22} {'previsoes':>10} {'acerto':>9}")
    for frac in [1.0, 0.5, 0.3, 0.2, 0.1, 0.05, 0.02]:
        n = max(int(len(y) * frac), 50)
        sub = conf[:n]
        acc = sum(1 for k in sub if (pred[k] > .5) == (y[k] > .5)) / n
        marca = "  <- 60%" if acc >= 0.60 else ""
        print(f"  {frac*100:>20.0f}% {n:>10,} {acc*100:>8.1f}%{marca}")
