"""Carteira transversal: ranquear muitos ativos e comprar os melhores.

E onde vantagem minuscula por operacao pode virar resultado: 0,1% por
operacao e inutil em 2 ativos e util em 54, porque a decisao passa a ser
"quais destes 54 sao os melhores hoje", nao "o BTC sobe amanha?".

Causalidade: a amostra do ativo a na data d tem rotulo de 21 pregoes a frente,
conhecido so em d+21. No rebalanceamento da data t so entram no treino
amostras cujo rotulo ja fechou ate t.
"""

import json
import os

import torch
import torch.nn as nn

from backtest import book_features


def carregar(dir_features="results/features"):
    """Indexa as features por data, e os precos de abertura por ativo."""
    por_data = {}
    opens = {}
    for arq in sorted(os.listdir(dir_features)):
        d = json.load(open(f"{dir_features}/{arq}"))
        inst = d["inst"]
        datas, X = d["datas"], d["X"]
        raw = json.load(open(f"data/{inst}_1d.json"))
        import time as _t
        o = {}
        for c in raw:
            o[_t.strftime("%Y-%m-%d", _t.gmtime(int(c[0]) / 1000))] = float(c[1])
        opens[inst] = o
        for j, dt in enumerate(datas):
            rot = datas[j + 21] if j + 21 < len(datas) else None
            por_data.setdefault(dt, []).append(
                {"inst": inst, "x": X[j], "ret": d["ret"][j], "data_rotulo": rot})
    return por_data, opens


class Rede(nn.Module):
    def __init__(self, dim, oculto=64, dropout=0.2):
        super().__init__()
        self.r = nn.Sequential(
            nn.Linear(dim, oculto), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(oculto, oculto // 2), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(oculto // 2, 1))

    def forward(self, x):
        return self.r(x).squeeze(-1)


def rodar_carteira(por_data, opens, inicio, top_n=5, rebal=10, custo=0.0015,
                   epocas=3, lote=256, lr=0.001, semente=0, capital=10000.0,
                   retreinar_a_cada=60):
    """Walk-forward: treina no passado, ranqueia hoje, carrega os melhores."""
    torch.manual_seed(semente)
    gen = torch.Generator().manual_seed(semente)
    dim = len(book_features.NAMES)
    modelo = Rede(dim)
    opt = torch.optim.AdamW(modelo.parameters(), lr=lr, weight_decay=1e-4)
    perda_fn = nn.BCEWithLogitsLoss()

    datas = sorted(por_data)
    BX, BY = [], []
    usadas = set()
    patrimonio = capital
    carteira = {}
    curva = []
    hist = []
    ultimo_treino = -10**9

    for k, t in enumerate(datas):
        # 1) incorpora ao treino tudo cujo rotulo ja fechou ate hoje
        for dt in datas[:k + 1]:
            if dt in usadas:
                continue
            linhas = por_data[dt]
            if linhas[0]["data_rotulo"] is None or linhas[0]["data_rotulo"] > t:
                continue
            for r in linhas:
                BX.append(r["x"])
                BY.append(1.0 if r["ret"] > 0 else 0.0)
            usadas.add(dt)

        # execucao na abertura do dia SEGUINTE ao fechamento que gerou o sinal
        if k + 1 >= len(datas):
            break
        t_exec = datas[k + 1]

        if k % rebal or t < inicio or len(BX) < lote * 4:
            if t >= inicio:
                curva.append((t_exec, valor(patrimonio, carteira, opens, t_exec)))
            continue

        # 2) treino periodico sobre TODAS as amostras ja realizadas
        if k - ultimo_treino >= retreinar_a_cada:
            X = torch.tensor(BX, dtype=torch.float32)
            Y = torch.tensor(BY, dtype=torch.float32)
            mu, sd = X.mean(0), X.std(0).clamp(min=1e-6)
            modelo.train()
            for _ in range(epocas):
                ordem = torch.randperm(len(BX), generator=gen)
                for i0 in range(0, len(BX) - lote + 1, lote):
                    idx = ordem[i0:i0 + lote]
                    opt.zero_grad()
                    perda_fn(modelo((X[idx] - mu) / sd), Y[idx]).backward()
                    opt.step()
            modelo.eval()
            ultimo_treino = k
            rodar_carteira._norm = (mu, sd)

        mu, sd = getattr(rodar_carteira, "_norm", (None, None))
        if mu is None:
            continue

        # 3) ranqueia o universo de hoje e escolhe os melhores
        linhas = por_data[t]
        with torch.no_grad():
            xs = torch.tensor([r["x"] for r in linhas], dtype=torch.float32)
            p = torch.sigmoid(modelo((xs - mu) / sd)).tolist()
        ordenado = sorted(zip(p, [r["inst"] for r in linhas]), reverse=True)
        escolhidos = [i for _, i in ordenado[:top_n]]

        patrimonio = valor(patrimonio, carteira, opens, t_exec)
        antigos = set(carteira)
        giro = len(set(escolhidos) ^ antigos) / max(len(escolhidos) * 2, 1)
        patrimonio *= (1 - custo * giro * 2)
        validos = [i for i in escolhidos if preco(opens, i, t_exec)]
        if validos:
            carteira = {i: (patrimonio / len(validos)) / preco(opens, i, t_exec)
                        for i in validos}
        curva.append((t_exec, patrimonio))
        hist.append({"data": t, "execucao": t_exec, "escolhidos": escolhidos})

    final = valor(patrimonio, carteira, opens, datas[-1])
    return {"curva": curva, "final": final, "hist": hist, "capital": capital}


def preco(opens, inst, data):
    return opens.get(inst, {}).get(data)


def valor(patrimonio, carteira, opens, data):
    if not carteira:
        return patrimonio
    v = 0.0
    for i, q in carteira.items():
        px = preco(opens, i, data)
        v += q * px if px else 0.0
    return v or patrimonio
