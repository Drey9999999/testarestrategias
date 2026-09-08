"""As features transversais melhoram a previsao?"""

import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, avaliar, auc, treinar, prever, carregar_tudo
from treino_cross import carregar_com_transversal


def alvo_relativo(R, D):
    por_data = defaultdict(list)
    for i, d in enumerate(D):
        por_data[d].append(i)
    Y = [0.0] * len(R)
    for d, idxs in por_data.items():
        if len(idxs) < 5:
            continue
        med = statistics.median(R[i] for i in idxs)
        for i in idxs:
            Y[i] = 1.0 if R[i] > med else 0.0
    return Y


for rot, carregador in [("SEM transversal (46 features)", carregar_tudo),
                        ("COM transversal (92 features)", carregar_com_transversal)]:
    X, _, D, A, R = carregador()
    tr, va, te = fatiar(D)
    dim = len(X[0])
    Xt = torch.tensor(X, dtype=torch.float32)
    Yr = torch.tensor(alvo_relativo(R, D), dtype=torch.float32)
    Rt = torch.tensor(R, dtype=torch.float32)
    W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)

    mods, aucs = [], []
    for s in range(5):
        m, mu, sd, _ = treinar(Xt, Yr, W, tr, va, dim, semente=s, oculto=128, camadas=3)
        mods.append((m, mu, sd))
        aucs.append(avaliar(m, Xt, Yr, va, mu, sd)[1])
    yva = [Yr[i].item() for i in va]
    ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
    med = [sum(c)/len(c) for c in zip(*ps)]
    a_ens = auc(yva, med)
    acc = sum(1 for p, y in zip(med, yva) if (p > .5) == (y > .5))/len(yva)
    print(f"\n{rot}   ({dim} entradas, {len(X):,} amostras)")
    print(f"  1 semente: AUC {statistics.median(aucs):.4f}")
    print(f"  ensemble de 5: acerto {acc*100:.1f}%   AUC {a_ens:.4f}")
