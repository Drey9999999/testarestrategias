"""Cronometragem com features de prazo curto, horizontes 1, 2 e 3.

Com h=1 nao ha sobreposicao alguma entre amostras: cada dia e uma observacao
independente, 594 na janela de teste contra 29 do h=20. E o maximo de poder
estatistico que estes dados permitem.
"""

import random
import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, auc, treinar, prever
from treino_mercado_curto import carregar_curto


def avaliar_h(h, sementes=8):
    X, Yl, D, A, R = carregar_curto(horizonte=h)
    tr, va, te = fatiar(D)
    dim = len(X[0])
    Xt = torch.tensor(X, dtype=torch.float32)
    Ya = torch.tensor(Yl, dtype=torch.float32)
    Rt = torch.tensor(R, dtype=torch.float32)
    W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)

    mods = [treinar(Xt, Ya, W, tr, va, dim, semente=s, oculto=128, camadas=3,
                    lr=3e-4, epocas=60, parada=8)[:3] for s in range(sementes)]

    saida = {}
    for jan, idxs in [("validacao", va), ("teste", te)]:
        ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
        pred = [sum(c)/len(c) for c in zip(*ps)]
        auc_ativo = auc([Ya[i].item() for i in idxs], pred)

        pd_, rd_ = defaultdict(list), defaultdict(list)
        for pos, i in enumerate(idxs):
            pd_[D[i]].append(pred[pos])
            rd_[D[i]].append(R[i])
        datas = sorted(pd_)
        pm = [statistics.mean(pd_[d]) for d in datas]
        ym = [1.0 if statistics.median(rd_[d]) > 0 else 0.0 for d in datas]
        a = auc(ym, pm)
        rng = random.Random(97)
        n = len(datas)
        nulos = sorted(auc(ym, pm[k:] + pm[:k])
                       for k in [rng.randrange(10, n-10) for _ in range(2000)])
        p = sum(1 for x in nulos if x >= a) / 2000
        saida[jan] = (auc_ativo, a, p, nulos[1900], n // max(h, 1))
    return saida


print(f"{'h':>3} {'janela':>10} {'indep.':>8} {'AUC ativo':>10} "
      f"{'AUC mercado':>12} {'nulo p95':>9} {'p':>7}")
for h in [1, 2, 3]:
    s = avaliar_h(h)
    for jan in ["validacao", "teste"]:
        aa, am, p, n95, ind = s[jan]
        marca = " *" if p < 0.05 else ""
        print(f"{h:>3} {jan:>10} {ind:>8} {aa:>10.4f} {am:>12.4f} "
              f"{n95:>9.4f} {p:>7.3f}{marca}")
