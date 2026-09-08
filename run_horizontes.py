"""Cronometrar o mercado fica possivel com horizonte mais curto?

Com alvo de 20 pregoes sobram ~107 periodos independentes em 8 anos, e ~29 na
janela de teste — pouco demais para detectar qualquer coisa. Com 3 ou 5
pregoes esse numero multiplica por 4 a 7.

Para cada horizonte, mede-se a AUC de cronometragem (previsao agregada por
data contra a direcao do mercado) com teste nulo por deslocamento circular.
"""

import json
import os
import random
import statistics
import sys
from collections import defaultdict

import torch

from treino_lab import fatiar, auc, treinar, prever, Rede
from treino_mercado import carregar_com_mercado

HORIZONTES = [3, 5, 10, 20]


def rotulos(h, dir_f="results/features"):
    """ret do horizonte h, na mesma ordem em que carregar_com_mercado monta X."""
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
        if len(m) < 5:
            continue
        for inst, j in m:
            saida.append(brutos[inst][f"ret{h}"][j])
    return saida


X, _, D, A, _ = carregar_com_mercado()
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)

print(f"{'horiz':>6} {'periodos indep.':>16} {'AUC ativo':>11} "
      f"{'AUC mercado':>12} {'nulo p90':>10} {'p':>7}")
for h in HORIZONTES:
    R = rotulos(h)
    tr, va, te = fatiar(D)
    Ya = torch.tensor([1.0 if r > 0 else 0.0 for r in R], dtype=torch.float32)
    Rt = torch.tensor(R, dtype=torch.float32)
    W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)

    mods = []
    for s in range(4):
        m, mu, sd, _ = treinar(Xt, Ya, W, tr, va, dim, semente=s, oculto=128,
                               camadas=3, lr=3e-4, epocas=60, parada=8)
        mods.append((m, mu, sd))
    ps = [prever(m, Xt, te, mu, sd) for m, mu, sd in mods]
    pred = [sum(c) / len(c) for c in zip(*ps)]
    y_ativo = [Ya[i].item() for i in te]
    auc_ativo = auc(y_ativo, pred)

    p_d, r_d = defaultdict(list), defaultdict(list)
    for pos, i in enumerate(te):
        p_d[D[i]].append(pred[pos])
        r_d[D[i]].append(R[i])
    datas = sorted(p_d)
    pm = [statistics.mean(p_d[d]) for d in datas]
    ym = [1.0 if statistics.median(r_d[d]) > 0 else 0.0 for d in datas]
    a_merc = auc(ym, pm)

    rng = random.Random(61)
    n = len(datas)
    nulos = sorted(auc(ym, pm[k:] + pm[:k])
                   for k in [rng.randrange(10, n - 10) for _ in range(1000)])
    acima = sum(1 for x in nulos if x >= a_merc)
    indep = n // h
    print(f"{h:>6} {indep:>16} {auc_ativo:>11.4f} {a_merc:>12.4f} "
          f"{nulos[900]:>10.4f} {acima/1000:>7.3f}")
