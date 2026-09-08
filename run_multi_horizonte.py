"""Ensemble ENTRE horizontes para cronometrar o mercado.

Os horizontes de 3, 10 e 20 pregoes dao previsoes parcialmente independentes:
erram em momentos diferentes. Combina-las tende a cancelar ruido e preservar
o que houver de sinal — e a mesma logica do ensemble de sementes, um nivel
acima.

Os pesos NAO sao ajustados: media simples das previsoes normalizadas.
"""

import json
import os
import random
import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, auc, treinar, prever
from treino_mercado import carregar_com_mercado

HORIZONTES = [3, 5, 10]
SEMENTES = 6


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
        if len(m) < 5:
            continue
        for inst, j in m:
            saida.append(brutos[inst][f"ret{h}"][j])
    return saida


X, _, D, A, _ = carregar_com_mercado()
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
tr, va, te = fatiar(D)

series = {}
for h in HORIZONTES:
    R = rotulos(h)
    Ya = torch.tensor([1.0 if r > 0 else 0.0 for r in R], dtype=torch.float32)
    Rt = torch.tensor(R, dtype=torch.float32)
    W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)
    mods = []
    for s in range(SEMENTES):
        m, mu, sd, _ = treinar(Xt, Ya, W, tr, va, dim, semente=s, oculto=128,
                               camadas=3, lr=3e-4, epocas=60, parada=8)
        mods.append((m, mu, sd))
    for jan, idxs in [("va", va), ("te", te)]:
        ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
        pred = [sum(c) / len(c) for c in zip(*ps)]
        pd_ = defaultdict(list)
        for pos, i in enumerate(idxs):
            pd_[D[i]].append(pred[pos])
        datas = sorted(pd_)
        vals = [statistics.mean(pd_[d]) for d in datas]
        mu_, sd_ = statistics.mean(vals), statistics.pstdev(vals) or 1.0
        series[(h, jan)] = (datas, [(v - mu_) / sd_ for v in vals])
    series[(h, "R")] = R
    print(f"  horizonte {h} treinado", flush=True)


def direcao(h, datas, idxs):
    R = series[(h, "R")]
    rd = defaultdict(list)
    for i in idxs:
        rd[D[i]].append(R[i])
    return [1.0 if statistics.median(rd[d]) > 0 else 0.0 for d in datas]


print()
for chave, rotulo, idxs in [("va", "VALIDACAO", va), ("te", "TESTE 2025/26", te)]:
    jan = chave
    datas = series[(HORIZONTES[0], jan)][0]
    comb = [statistics.mean(series[(h, jan)][1][k] for h in HORIZONTES)
            for k in range(len(datas))]
    for h in HORIZONTES + ["combinado"]:
        pred = comb if h == "combinado" else series[(h, jan)][1]
        # avaliado contra a direcao de mercado de 10 pregoes (prazo de operacao)
        y = direcao(10, datas, idxs)
        a = auc(y, pred)
        rng = random.Random(71)
        n = len(datas)
        nulos = sorted(auc(y, pred[k:] + pred[:k])
                       for k in [rng.randrange(10, n - 10) for _ in range(1000)])
        p = sum(1 for x in nulos if x >= a) / 1000
        rot = f"horizonte {h}" if h != "combinado" else "COMBINADO (3+5+10)"
        print(f"  {rotulo:<14} {rot:<20} AUC {a:.4f}   p = {p:.3f}")
    print()
