"""A previsao sobrevive na janela de teste, nunca usada para nada?

A parada antecipada escolheu a epoca pela AUC de VALIDACAO, entao a AUC de
validacao esta otimista por construcao. A janela de teste (2025/26) nunca foi
usada para treinar, escolher arquitetura, parar epoca nem nada. E o unico
numero limpo.
"""

import random
import statistics
from collections import defaultdict

import torch

from treino_lab import carregar_tudo, fatiar, auc, treinar, prever

X, Y, D, A, R = carregar_tudo()
tr, va, te = fatiar(D)
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
Rt = torch.tensor(R, dtype=torch.float32)
W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)

por_data = defaultdict(list)
for i, d in enumerate(D):
    por_data[d].append(i)
Yrel = [0.0] * len(R)
for d, idxs in por_data.items():
    if len(idxs) < 5:
        continue
    med = statistics.median(R[i] for i in idxs)
    for i in idxs:
        Yrel[i] = 1.0 if R[i] > med else 0.0
Yr = torch.tensor(Yrel, dtype=torch.float32)

mods = []
for s in range(5):
    m, mu, sd, _ = treinar(Xt, Yr, W, tr, va, dim, semente=s, oculto=128, camadas=3)
    mods.append((m, mu, sd))

for rot, idxs in [("VALIDACAO (contaminada pela parada antecipada)", va),
                  ("TESTE 2025/26 (nunca tocada)", te)]:
    ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
    pred = [sum(c) / len(c) for c in zip(*ps)]
    y = [Yr[i].item() for i in idxs]
    real = auc(y, pred)
    acc = sum(1 for p, v in zip(pred, y) if (p > .5) == (v > .5)) / len(y)

    grupos = defaultdict(list)
    for pos, i in enumerate(idxs):
        grupos[D[i]].append(pos)
    chaves = sorted(grupos)
    rng = random.Random(9)
    nulos = []
    for _ in range(500):
        ordem = chaves[:]
        rng.shuffle(ordem)
        y2 = [0.0] * len(y)
        for ko, kn in zip(chaves, ordem):
            o, n = grupos[ko], grupos[kn]
            for j, pos in enumerate(o):
                y2[pos] = y[n[j % len(n)]]
        nulos.append(auc(y2, pred))
    nulos.sort()
    acima = sum(1 for x in nulos if x >= real)
    print(f"\n{rot}")
    print(f"  amostras {len(y):,}   acerto {acc*100:.1f}%   AUC {real:.4f}")
    print(f"  nulo por permutacao de datas: mediana {statistics.median(nulos):.4f}  "
          f"max {nulos[-1]:.4f}")
    print(f"  {acima}/500 permutacoes igualaram ou superaram  ->  p = {acima/500:.3f}")
