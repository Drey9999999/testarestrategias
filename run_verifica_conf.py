"""O acerto alto nas previsoes confiantes e real ou concentracao?

Tres formas de esse numero ser falso:
  1. as previsoes confiantes se amontoam em poucas datas (um mes bom)
  2. se amontoam em poucos ativos (o OKB de novo)
  3. sao apenas a preferencia estatica por ativo, ja conhecida

O teste nulo por permutacao de datas responde a 3: como permutar datas nao
destroi a preferencia por ativo, a mediana do nulo ja contem esse efeito.
"""

import random
import statistics
from collections import defaultdict, Counter

import torch

from treino_lab import fatiar, treinar, prever
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

ps = [prever(m, Xt, te, mu, sd) for m, mu, sd in mods]
pred = [sum(c)/len(c) for c in zip(*ps)]
y = [Yr[i].item() for i in te]
conf = sorted(range(len(y)), key=lambda k: -abs(pred[k] - 0.5))

for frac in [0.30, 0.10]:
    n = int(len(y) * frac)
    sub = conf[:n]
    acc = sum(1 for k in sub if (pred[k] > .5) == (y[k] > .5)) / n
    datas = Counter(D[te[k]] for k in sub)
    ativos = Counter(A[te[k]] for k in sub)
    n_datas_tot = len(set(D[i] for i in te))
    print(f"\n=== decil/faixa mais confiante: {frac*100:.0f}% ({n:,} previsoes) ===")
    print(f"  acerto {acc*100:.1f}%")
    print(f"  espalhamento: {len(datas)} datas de {n_datas_tot} possiveis, "
          f"{len(ativos)} ativos de {len(set(A[i] for i in te))}")
    print(f"  data mais frequente: {datas.most_common(1)[0][1]/n*100:.1f}% das previsoes")
    print(f"  ativo mais frequente: {ativos.most_common(1)[0][0]} "
          f"({ativos.most_common(1)[0][1]/n*100:.1f}%)")
    top3 = sum(v for _, v in ativos.most_common(3))/n
    print(f"  3 ativos mais frequentes concentram {top3*100:.1f}% das previsoes")

    # nulo por permutacao de datas, restrito a este subconjunto
    grupos = defaultdict(list)
    for pos in sub:
        grupos[D[te[pos]]].append(pos)
    chaves = sorted(grupos)
    rng = random.Random(31)
    nulos = []
    for _ in range(500):
        ordem = chaves[:]
        rng.shuffle(ordem)
        certos = 0
        for ko, kn in zip(chaves, ordem):
            o, nn_ = grupos[ko], grupos[kn]
            for j, pos in enumerate(o):
                yy = y[nn_[j % len(nn_)]]
                certos += (pred[pos] > .5) == (yy > .5)
        nulos.append(certos / n)
    nulos.sort()
    acima = sum(1 for x in nulos if x >= acc)
    print(f"  nulo por permutacao de datas: mediana {statistics.median(nulos)*100:.1f}%  "
          f"max {nulos[-1]*100:.1f}%  ->  p = {acima/500:.3f}")
