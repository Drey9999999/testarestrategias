"""Banco de ensaios com um objetivo unico: aumentar o acerto da previsao.

Metrica principal: acerto direcional FORA DA AMOSTRA, com AUC ao lado. AUC
mede a capacidade de ordenar (o modelo poe os dias que sobem acima dos que
caem?) e nao depende do limiar, entao detecta melhora que o acerto bruto
esconde quando as classes estao desbalanceadas.

Protocolo fixo em todos os ensaios, para que a comparacao signifique algo:
  treino    ate 2022-12-31
  validacao 2023-01-01 a 2024-12-31   <- onde as decisoes sao tomadas
  teste     2025-01-01 em diante      <- so no fim, uma vez

O modelo preve a direcao do retorno de 20 pregoes. Como cada amostra so tem
rotulo 20 dias depois, o corte de treino desconta essa defasagem.
"""

import json
import os
import statistics

import torch
import torch.nn as nn

from backtest import book_features

H = 21                     # o rotulo usa abertura t+1 -> t+1+20
FIM_TREINO = "2023-01-01"
FIM_VALID = "2025-01-01"


def carregar_tudo(dir_features="results/features"):
    """Todas as amostras de todos os ativos, com data e rotulo."""
    X, Y, D, A, R = [], [], [], [], []
    for arq in sorted(os.listdir(dir_features)):
        d = json.load(open(f"{dir_features}/{arq}"))
        for j, dt in enumerate(d["datas"]):
            X.append(d["X"][j])
            R.append(d["ret"][j])
            Y.append(1.0 if d["ret"][j] > 0 else 0.0)
            D.append(dt)
            A.append(d["inst"])
    return X, Y, D, A, R


def fatiar(D, ativo_alvo=None, A=None):
    """Indices de treino, validacao e teste, com a defasagem do rotulo
    descontada: uma amostra so entra no treino se seu rotulo ja fechou antes
    do inicio da validacao."""
    import datetime as dt

    def menos(data, dias):
        d = dt.date.fromisoformat(data) - dt.timedelta(days=dias)
        return d.isoformat()

    corte_tr = menos(FIM_TREINO, 32)       # ~21 pregoes de folga
    corte_va = menos(FIM_VALID, 32)
    tr, va, te = [], [], []
    for i, data in enumerate(D):
        if ativo_alvo and A[i] != ativo_alvo:
            alvo = False
        else:
            alvo = True
        if data <= corte_tr:
            tr.append(i)
        elif FIM_TREINO <= data <= corte_va and alvo:
            va.append(i)
        elif data >= FIM_VALID and alvo:
            te.append(i)
    return tr, va, te


def auc(y, p):
    """Area sob a curva ROC, por contagem de pares concordantes."""
    pares = sorted(zip(p, y))
    pos = sum(y)
    neg = len(y) - pos
    if pos == 0 or neg == 0:
        return 0.5
    rank_soma, i = 0.0, 0
    while i < len(pares):
        j = i
        while j < len(pares) and pares[j][0] == pares[i][0]:
            j += 1
        rmed = (i + j + 1) / 2
        for k in range(i, j):
            if pares[k][1] == 1:
                rank_soma += rmed
        i = j
    return (rank_soma - pos * (pos + 1) / 2) / (pos * neg)


def avaliar(modelo, X, Y, idx, mu, sd):
    modelo.eval()
    with torch.no_grad():
        p = torch.sigmoid(modelo((X[idx] - mu) / sd)).tolist()
    y = [Y[i].item() for i in idx]
    acerto = sum(1 for a, b in zip(p, y) if (a > 0.5) == (b > 0.5)) / len(y)
    return acerto, auc(y, p), statistics.mean(y)


class Rede(nn.Module):
    def __init__(self, dim, oculto=64, camadas=2, dropout=0.3):
        super().__init__()
        cs, d = [], dim
        for _ in range(camadas):
            cs += [nn.Linear(d, oculto), nn.ReLU(), nn.Dropout(dropout)]
            d = oculto
        cs.append(nn.Linear(d, 1))
        self.r = nn.Sequential(*cs)

    def forward(self, x):
        return self.r(x).squeeze(-1)


def treinar(X, Y, W, tr, va, dim, semente=0, oculto=64, camadas=2, dropout=0.3,
            lr=1e-3, wd=1e-4, lote=512, epocas=40, parada=6, pesos=False):
    """Treina com parada antecipada pela AUC de validacao.

    `parada` = quantas epocas sem melhora na validacao antes de desistir. Sem
    isso, o modelo continua ajustando o treino muito depois de parar de
    melhorar a previsao — foi o que a curva de aprendizado mostrou antes.
    """
    torch.manual_seed(semente)
    gen = torch.Generator().manual_seed(semente)
    mu = X[tr].mean(0)
    sd = X[tr].std(0).clamp(min=1e-6)

    modelo = Rede(dim, oculto, camadas, dropout)
    opt = torch.optim.AdamW(modelo.parameters(), lr=lr, weight_decay=wd)
    perda_fn = nn.BCEWithLogitsLoss(reduction="none")

    Xtr, Ytr, Wtr = (X[tr] - mu) / sd, Y[tr], W[tr]
    melhor, melhor_estado, sem_melhora = -1.0, None, 0
    for ep in range(epocas):
        modelo.train()
        ordem = torch.randperm(len(tr), generator=gen)
        for i0 in range(0, len(tr) - lote + 1, lote):
            idx = ordem[i0:i0 + lote]
            opt.zero_grad()
            l = perda_fn(modelo(Xtr[idx]), Ytr[idx])
            l = (l * Wtr[idx]).mean() if pesos else l.mean()
            l.backward()
            opt.step()
        _, a, _ = avaliar(modelo, X, Y, va, mu, sd)
        if a > melhor + 1e-4:
            melhor, sem_melhora = a, 0
            melhor_estado = {k: v.clone() for k, v in modelo.state_dict().items()}
        else:
            sem_melhora += 1
            if sem_melhora >= parada:
                break
    if melhor_estado:
        modelo.load_state_dict(melhor_estado)
    return modelo, mu, sd, melhor


def prever(modelo, X, idx, mu, sd):
    modelo.eval()
    with torch.no_grad():
        return torch.sigmoid(modelo((X[idx] - mu) / sd)).tolist()
