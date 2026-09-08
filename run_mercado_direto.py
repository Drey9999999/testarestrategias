"""Modelo dedicado a cronometrar o mercado: uma amostra por DATA.

O modelo anterior tinha uma amostra por (ativo, data) e aprendia sobretudo a
distinguir ativos entre si — habilidade transversal, que some ao agregar por
data. Aqui a unidade e a data: features do mercado inteiro, alvo = a mediana
dos retornos dos 54 ativos nos proximos 20 pregoes sobe?

Sao ~2.700 datas, nao 111 mil amostras. Menos dado, mas o alvo e exatamente o
que o filtro de exposicao precisa. As features incluem os niveis de mercado e
tambem suas VARIACOES: amplitude melhorando costuma valer mais que amplitude
alta.
"""

import random
import statistics
from collections import defaultdict

import torch

from treino_lab import auc, Rede
from treino_mercado import carregar_com_mercado, AGREGADOS

X, _, D, A, R = carregar_com_mercado()
n_merc = len(AGREGADOS)

por_data = defaultdict(list)
for i, d in enumerate(D):
    por_data[d].append(i)
datas = sorted(por_data)

# uma linha por data: os agregados de mercado (ultimas n_merc colunas)
base = {d: X[por_data[d][0]][-n_merc:] for d in datas}
alvo = {d: (1.0 if statistics.median(R[i] for i in por_data[d]) > 0 else 0.0)
        for d in datas}

# acrescenta variacoes de 5, 20 e 60 pregoes de cada agregado
linhas, ys, ds = [], [], []
for k, d in enumerate(datas):
    if k < 60:
        continue
    v = list(base[d])
    for lag in (5, 20, 60):
        ant = base[datas[k - lag]]
        v += [base[d][j] - ant[j] for j in range(n_merc)]
    linhas.append(v)
    ys.append(alvo[d])
    ds.append(d)

dim = len(linhas[0])
Xt = torch.tensor(linhas, dtype=torch.float32)
Yt = torch.tensor(ys, dtype=torch.float32)

FIM_TR, FIM_VA = "2022-12-01", "2024-12-01"     # folga para o rotulo de 20d
tr = [i for i, d in enumerate(ds) if d <= FIM_TR]
va = [i for i, d in enumerate(ds) if "2023-01-01" <= d <= FIM_VA]
te = [i for i, d in enumerate(ds) if d >= "2025-01-01"]
print(f"uma amostra por data: {len(linhas)} datas, {dim} features")
print(f"treino {len(tr)}  validacao {len(va)}  teste {len(te)}")

mu, sd = Xt[tr].mean(0), Xt[tr].std(0).clamp(min=1e-6)
Xn = (Xt - mu) / sd


def treinar_um(semente, oculto=32, camadas=2, dropout=0.4, lr=1e-3, epocas=200, parada=25):
    torch.manual_seed(semente)
    gen = torch.Generator().manual_seed(semente)
    m = Rede(dim, oculto, camadas, dropout)
    opt = torch.optim.AdamW(m.parameters(), lr=lr, weight_decay=1e-3)
    fn = torch.nn.BCEWithLogitsLoss()
    melhor, estado, sem = -1, None, 0
    for ep in range(epocas):
        m.train()
        ordem = torch.randperm(len(tr), generator=gen)
        for i0 in range(0, len(tr) - 32 + 1, 32):
            idx = [tr[j] for j in ordem[i0:i0 + 32]]
            opt.zero_grad()
            fn(m(Xn[idx]), Yt[idx]).backward()
            opt.step()
        m.eval()
        with torch.no_grad():
            p = torch.sigmoid(m(Xn[va])).tolist()
        a = auc([Yt[i].item() for i in va], p)
        if a > melhor + 1e-4:
            melhor, sem = a, 0
            estado = {k: v.clone() for k, v in m.state_dict().items()}
        else:
            sem += 1
            if sem >= parada:
                break
    if estado:
        m.load_state_dict(estado)
    return m, melhor


mods = [treinar_um(s)[0] for s in range(10)]
for rot, idx in [("VALIDACAO", va), ("TESTE 2025/26", te)]:
    with torch.no_grad():
        ps = [torch.sigmoid(m(Xn[idx])).tolist() for m in mods]
    pred = [sum(c)/len(c) for c in zip(*ps)]
    y = [Yt[i].item() for i in idx]
    a = auc(y, pred)
    rng = random.Random(53)
    n = len(y)
    nulos = sorted(auc(y, pred[k:] + pred[:k])
                   for k in [rng.randrange(20, n-20) for _ in range(1000)])
    acima = sum(1 for x in nulos if x >= a)
    print(f"\n{rot}: {n} datas, {statistics.mean(y)*100:.0f}% sobem")
    print(f"  AUC {a:.4f}   nulo mediana {statistics.median(nulos):.4f}  "
          f"p90 {nulos[900]:.4f}  ->  p = {acima/1000:.3f}")
