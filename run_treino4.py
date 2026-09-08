"""Refino sobre as features transversais: arquitetura, ensemble e recencia."""

import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, avaliar, auc, treinar, prever
from treino_cross import carregar_com_transversal

X, _, D, A, R = carregar_com_transversal()
tr, va, te = fatiar(D)
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)

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
Rt = torch.tensor(R, dtype=torch.float32)
W_mov = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)
# peso por recencia: amostras recentes valem mais, meia-vida de ~2 anos
ordem_data = {d: k for k, d in enumerate(sorted(set(D)))}
n_datas = len(ordem_data)
W_rec = torch.tensor([0.5 ** ((n_datas - ordem_data[d]) / 500) for d in D],
                     dtype=torch.float32)
W_rec = W_rec / W_rec.mean()
yva = [Yr[i].item() for i in va]

ENSAIOS = [
    ("128x3 (referencia)",        dict(oculto=128, camadas=3), W_mov, False),
    ("256x3",                     dict(oculto=256, camadas=3), W_mov, False),
    ("128x2",                     dict(oculto=128, camadas=2), W_mov, False),
    ("128x3 dropout 0,15",        dict(oculto=128, camadas=3, dropout=0.15), W_mov, False),
    ("128x3 lr 3e-4, 80 epocas",  dict(oculto=128, camadas=3, lr=3e-4, epocas=80,
                                       parada=10), W_mov, False),
    ("128x3 + peso por recencia", dict(oculto=128, camadas=3), W_rec, True),
]

melhor = (None, -1)
for nome, kw, Wu, usar in ENSAIOS:
    mods, aucs = [], []
    for s in range(5):
        m, mu, sd, _ = treinar(Xt, Yr, Wu, tr, va, dim, semente=s, pesos=usar, **kw)
        mods.append((m, mu, sd))
        aucs.append(avaliar(m, Xt, Yr, va, mu, sd)[1])
    ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
    med = [sum(c)/len(c) for c in zip(*ps)]
    a = auc(yva, med)
    acc = sum(1 for p, y in zip(med, yva) if (p > .5) == (y > .5))/len(yva)
    print(f"  {nome:<28} 1 semente AUC {statistics.median(aucs):.4f}  |  "
          f"ensemble de 5: acerto {acc*100:.1f}% AUC {a:.4f}")
    if a > melhor[1]:
        melhor = (nome, a)
print(f"\n  melhor na validacao: {melhor[0]}  AUC {melhor[1]:.4f}")
