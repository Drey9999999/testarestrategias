"""Segunda rodada: alvo relativo, ensembles maiores e taxa de aprendizado.

A alavanca mais promissora e trocar o alvo. Prever "este ativo sobe?" mistura
duas coisas: para onde vai o mercado inteiro (quase imprevisivel) e se este
ativo vai melhor que os outros (mais aprendivel). O alvo relativo remove a
primeira: o rotulo passa a ser "este ativo bate a mediana do dia?".
"""

import statistics
from collections import defaultdict

import torch

from treino_lab import carregar_tudo, fatiar, avaliar, auc, treinar, prever

X, Y, D, A, R = carregar_tudo()
tr, va, te = fatiar(D)
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
Rt = torch.tensor(R, dtype=torch.float32)
W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)

# alvo relativo: bate a mediana dos ativos naquela mesma data?
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
Ya = torch.tensor(Y, dtype=torch.float32)

for nome, Yuse in [("ABSOLUTO (sobe?)", Ya), ("RELATIVO (bate a mediana do dia?)", Yr)]:
    yva = [Yuse[i].item() for i in va]
    print(f"\n{'='*66}\nalvo {nome}   —   {statistics.mean(yva)*100:.1f}% positivos na validacao\n{'='*66}")
    for cfg_nome, kw in [("64x2", dict()), ("128x3", dict(oculto=128, camadas=3)),
                         ("256x3 dropout 0,4", dict(oculto=256, camadas=3, dropout=0.4))]:
        mods, accs, aucs = [], [], []
        for s in range(5):
            m, mu, sd, _ = treinar(Xt, Yuse, W, tr, va, dim, semente=s, **kw)
            acc, a, _ = avaliar(m, Xt, Yuse, va, mu, sd)
            accs.append(acc); aucs.append(a); mods.append((m, mu, sd))
        ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
        med = [sum(c)/len(c) for c in zip(*ps)]
        acc_e = sum(1 for p, y in zip(med, yva) if (p > 0.5) == (y > 0.5))/len(yva)
        print(f"  {cfg_nome:<20} 1 semente: acerto {statistics.median(accs)*100:.1f}% "
              f"AUC {statistics.median(aucs):.4f}  |  ensemble de 5: acerto {acc_e*100:.1f}% "
              f"AUC {auc(yva, med):.4f}")
