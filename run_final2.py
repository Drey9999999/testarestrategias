"""Avaliacao final da melhor configuracao na janela de teste.

Escolhas feitas na validacao: features transversais, alvo relativo, 128x3,
lr 3e-4 com 80 epocas e paciencia 10, ensemble. A validacao esta otimista por
ter sido usada nessas escolhas; o teste nunca foi tocado.
"""

import random
import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, avaliar, auc, treinar, prever
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

N = 10
mods = []
for s in range(N):
    m, mu, sd, _ = treinar(Xt, Yr, W, tr, va, dim, semente=s, oculto=128,
                           camadas=3, lr=3e-4, epocas=80, parada=10)
    mods.append((m, mu, sd))
print(f"ensemble de {N} sementes\n")

for rot, idxs in [("VALIDACAO (usada nas escolhas — otimista)", va),
                  ("TESTE 2025/26 (nunca tocada)", te)]:
    ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
    pred = [sum(c)/len(c) for c in zip(*ps)]
    y = [Yr[i].item() for i in idxs]
    real = auc(y, pred)
    acc = sum(1 for p, v in zip(pred, y) if (p > .5) == (v > .5))/len(y)

    grupos = defaultdict(list)
    for pos, i in enumerate(idxs):
        grupos[D[i]].append(pos)
    chaves = sorted(grupos)
    rng = random.Random(17)
    nulos = []
    for _ in range(500):
        ordem = chaves[:]
        rng.shuffle(ordem)
        y2 = [0.0]*len(y)
        for ko, kn in zip(chaves, ordem):
            o, n = grupos[ko], grupos[kn]
            for j, pos in enumerate(o):
                y2[pos] = y[n[j % len(n)]]
        nulos.append(auc(y2, pred))
    nulos.sort()
    acima = sum(1 for x in nulos if x >= real)
    print(f"{rot}")
    print(f"  {len(y):,} amostras   acerto {acc*100:.1f}%   AUC {real:.4f}")
    print(f"  nulo: mediana {statistics.median(nulos):.4f}   max {nulos[-1]:.4f}   "
          f"p = {acima/500:.3f}\n")
