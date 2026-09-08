"""Perda por pares: otimizar diretamente o que a AUC mede.

A perda de classificacao pergunta "este ativo sobe?" ponto a ponto. A AUC
pergunta outra coisa: "dado um ativo que subiu e um que caiu, o modelo poe o
certo na frente?". A perda por pares treina exatamente isso — dentro de cada
dia, sorteia pares de ativos e penaliza quando o de retorno maior recebe nota
menor. E o alinhamento entre o que se treina e o que se mede.
"""

import random
import statistics
from collections import defaultdict

import torch
import torch.nn as nn

from treino_lab import fatiar, auc, prever, Rede
from treino_cross import carregar_com_transversal

X, _, D, A, R = carregar_com_transversal()
tr, va, te = fatiar(D)
dim = len(X[0])
Xt = torch.tensor(X, dtype=torch.float32)
Rt = torch.tensor(R, dtype=torch.float32)

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
yva = [Yr[i].item() for i in va]

tr_set = set(tr)
datas_tr = [d for d in sorted(por_data) if all(i in tr_set for i in por_data[d])
            and len(por_data[d]) >= 8]


def treinar_pares(semente, oculto=128, camadas=3, dropout=0.3, lr=1e-3,
                  epocas=60, parada=8, pares_por_dia=24):
    torch.manual_seed(semente)
    rng = random.Random(semente)
    mu = Xt[tr].mean(0)
    sd = Xt[tr].std(0).clamp(min=1e-6)
    modelo = Rede(dim, oculto, camadas, dropout)
    opt = torch.optim.AdamW(modelo.parameters(), lr=lr, weight_decay=1e-4)
    melhor, estado, sem = -1.0, None, 0

    for ep in range(epocas):
        modelo.train()
        rng.shuffle(datas_tr)
        for i0 in range(0, len(datas_tr), 16):
            bloco = datas_tr[i0:i0 + 16]
            ai, bj = [], []
            for d in bloco:
                idxs = por_data[d]
                for _ in range(pares_por_dia):
                    x, y = rng.sample(idxs, 2)
                    if R[x] == R[y]:
                        continue
                    if R[x] < R[y]:
                        x, y = y, x
                    ai.append(x); bj.append(y)      # ai deve pontuar acima de bj
            if len(ai) < 8:
                continue
            xa = (Xt[ai] - mu) / sd
            xb = (Xt[bj] - mu) / sd
            opt.zero_grad()
            dif = modelo(xa) - modelo(xb)
            nn.functional.binary_cross_entropy_with_logits(
                dif, torch.ones_like(dif)).backward()
            opt.step()
        modelo.eval()
        with torch.no_grad():
            p = torch.sigmoid(modelo((Xt[va] - mu) / sd)).tolist()
        a = auc(yva, p)
        if a > melhor + 1e-4:
            melhor, sem = a, 0
            estado = {k: v.clone() for k, v in modelo.state_dict().items()}
        else:
            sem += 1
            if sem >= parada:
                break
    if estado:
        modelo.load_state_dict(estado)
    return modelo, mu, sd, melhor


mods, aucs = [], []
for s in range(5):
    m, mu, sd, best = treinar_pares(s)
    mods.append((m, mu, sd)); aucs.append(best)
    print(f"  semente {s}: AUC {best:.4f}", flush=True)
ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
med = [sum(c)/len(c) for c in zip(*ps)]
acc = sum(1 for p, y in zip(med, yva) if (p > .5) == (y > .5))/len(yva)
print(f"\n  perda por pares, ensemble de 5: acerto {acc*100:.1f}%  AUC {auc(yva, med):.4f}")
print(f"  (referencia com perda de classificacao: AUC 0,5546)")
