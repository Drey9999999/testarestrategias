"""A AUC de 0,533 e sinal ou estrutura dos dados?

As amostras nao sao independentes: cada rotulo cobre 20 pregoes, entao dias
vizinhos se sobrepoem quase totalmente, e os 54 ativos sobem e descem juntos.
Um teste ingenuo trataria 37 mil amostras como 37 mil observacoes livres e
declararia qualquer coisa significativa.

Nulo correto: permutar os rotulos POR DATA, mantendo o vetor de rotulos de
cada dia intacto e apenas trocando a qual dia ele pertence. Isso preserva a
correlacao entre ativos e a sobreposicao temporal, e destroi so a ligacao
entre as features e o futuro.
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
ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
pred = [sum(c) / len(c) for c in zip(*ps)]
yva = [Yr[i].item() for i in va]
real = auc(yva, pred)

# agrupa a validacao por data, preservando o vetor de rotulos de cada dia
datas_va = defaultdict(list)
for pos, i in enumerate(va):
    datas_va[D[i]].append(pos)
chaves = sorted(datas_va)

rng = random.Random(5)
nulos = []
for _ in range(500):
    ordem = chaves[:]
    rng.shuffle(ordem)
    y2 = [0.0] * len(yva)
    for k_orig, k_novo in zip(chaves, ordem):
        orig, novo = datas_va[k_orig], datas_va[k_novo]
        for j, pos in enumerate(orig):
            y2[pos] = yva[novo[j % len(novo)]]
    nulos.append(auc(y2, pred))
nulos.sort()
acima = sum(1 for x in nulos if x >= real)

print(f"\nAUC real (ensemble de 5, alvo relativo): {real:.4f}")
print(f"nulo por permutacao de datas (500x): mediana {statistics.median(nulos):.4f}  "
      f"p5 {nulos[25]:.4f}  p95 {nulos[475]:.4f}  max {nulos[-1]:.4f}")
print(f"{acima}/500 permutacoes igualaram ou superaram  ->  p = {acima/500:.3f}")
