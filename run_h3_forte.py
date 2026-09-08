"""Empurrar a cronometragem no horizonte de 3 pregoes, o mais testavel.

Com h=3 sobram ~198 periodos independentes na janela de teste, contra 29 do
h=20. Arquitetura e tamanho do ensemble escolhidos na VALIDACAO; o teste so e
olhado no fim.
"""

import json
import os
import random
import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, auc, treinar, prever
from treino_mercado import carregar_com_mercado

H = 3


def rotulos(h, dir_f="results/features"):
    brutos = {}
    for arq in sorted(os.listdir(dir_f)):
        d = json.load(open(f"{dir_f}/{arq}"))
        brutos[d["inst"]] = d
    por_data = defaultdict(list)
    for inst, d in brutos.items():
        for j, dt in enumerate(d["datas"]):
            por_data[dt].append((inst, j))
    saida = []
    for dt in sorted(por_data):
        m = por_data[dt]
        if len(m) >= 5:
            for inst, j in m:
                saida.append(brutos[inst][f"ret{h}"][j])
    return saida


X, _, D, A, _ = carregar_com_mercado()
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
tr, va, te = fatiar(D)
R = rotulos(H)
Ya = torch.tensor([1.0 if r > 0 else 0.0 for r in R], dtype=torch.float32)
Rt = torch.tensor(R, dtype=torch.float32)
W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)


def mercado(pred, idxs):
    pd_, rd_ = defaultdict(list), defaultdict(list)
    for pos, i in enumerate(idxs):
        pd_[D[i]].append(pred[pos])
        rd_[D[i]].append(R[i])
    datas = sorted(pd_)
    return (datas,
            [statistics.mean(pd_[d]) for d in datas],
            [1.0 if statistics.median(rd_[d]) > 0 else 0.0 for d in datas])


def testar(pred, idxs, semente=83):
    datas, pm, ym = mercado(pred, idxs)
    a = auc(ym, pm)
    rng = random.Random(semente)
    n = len(datas)
    nulos = sorted(auc(ym, pm[k:] + pm[:k])
                   for k in [rng.randrange(10, n - 10) for _ in range(2000)])
    return a, sum(1 for x in nulos if x >= a) / 2000


CFGS = [("128x3", dict(oculto=128, camadas=3)),
        ("64x2", dict(oculto=64, camadas=2)),
        ("256x2", dict(oculto=256, camadas=2)),
        ("128x3 dropout 0,45", dict(oculto=128, camadas=3, dropout=0.45))]

print("selecao na VALIDACAO (ensemble de 12)\n")
melhor, ma = None, -1
guard = {}
for nome, kw in CFGS:
    mods = [treinar(Xt, Ya, W, tr, va, dim, semente=s, lr=3e-4, epocas=60,
                    parada=8, **kw)[:3] for s in range(12)]
    ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
    pv = [sum(c)/len(c) for c in zip(*ps)]
    a, p = testar(pv, va)
    print(f"  {nome:<20} AUC {a:.4f}   p = {p:.3f}")
    guard[nome] = mods
    if a > ma:
        melhor, ma = nome, a
print(f"\n  -> escolhido pela validacao: {melhor}\n")

mods = guard[melhor]
ps = [prever(m, Xt, te, mu, sd) for m, mu, sd in mods]
pt = [sum(c)/len(c) for c in zip(*ps)]
a, p = testar(pt, te)
datas, pm, ym = mercado(pt, te)
print(f"TESTE 2025/26 ({len(datas)} datas, ~{len(datas)//H} periodos independentes)")
print(f"  AUC de cronometragem do mercado: {a:.4f}   p = {p:.3f}")
lim = statistics.median(pm)
acc = sum(1 for x, y in zip(pm, ym) if (x > lim) == (y > .5)) / len(ym)
print(f"  acerto no limiar mediano: {acc*100:.1f}%   "
      f"(mercado subiu em {statistics.mean(ym)*100:.0f}% das datas)")
