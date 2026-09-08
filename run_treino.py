"""Ensaios de treino, medidos por acerto e AUC de validacao."""

import statistics
import sys

import torch

from treino_lab import (carregar_tudo, fatiar, avaliar, auc, treinar, prever, Rede)

X, Y, D, A, R = carregar_tudo()
tr, va, te = fatiar(D)
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
Yt = torch.tensor(Y, dtype=torch.float32)
Rt = torch.tensor(R, dtype=torch.float32)
# peso por tamanho do movimento: dias de retorno minusculo sao ruido puro
W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)
yva = [Y[i] for i in va]

def linha(nome, accs, aucs):
    print(f"  {nome:<34} acerto {statistics.median(accs)*100:>5.1f}%   "
          f"AUC {statistics.median(aucs):>6.4f}")

print(f"\nvalidacao: {len(va):,} amostras, {statistics.mean(yva)*100:.1f}% sobem")
print(f"referencia: chutar sempre 'sobe' acerta {max(statistics.mean(yva),1-statistics.mean(yva))*100:.1f}%, AUC 0,5000\n")

ENSAIOS = [
    ("baseline (64x2, dropout 0,3)",      dict()),
    ("+ ponderar por tamanho do movimento", dict(pesos=True)),
    ("+ rede maior (128x3)",              dict(oculto=128, camadas=3)),
    ("+ rede menor (32x1)",               dict(oculto=32, camadas=1)),
    ("+ dropout alto (0,5)",              dict(dropout=0.5)),
    ("+ regularizacao forte (wd 1e-2)",   dict(wd=1e-2)),
]

resultados = {}
for nome, kw in ENSAIOS:
    accs, aucs, mods = [], [], []
    for s in range(3):
        m, mu, sd, best = treinar(Xt, Yt, W, tr, va, dim, semente=s, **kw)
        acc, a, _ = avaliar(m, Xt, Yt, va, mu, sd)
        accs.append(acc); aucs.append(a); mods.append((m, mu, sd))
    linha(nome, accs, aucs)
    resultados[nome] = (statistics.median(aucs), mods, kw)

    # ensemble: media das probabilidades das 3 sementes
    ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
    med = [sum(c)/len(c) for c in zip(*ps)]
    acc_e = sum(1 for p, y in zip(med, yva) if (p > 0.5) == (y > 0.5))/len(yva)
    print(f"  {'  -> ensemble de 3 sementes':<34} acerto {acc_e*100:>5.1f}%   "
          f"AUC {auc(yva, med):>6.4f}")
