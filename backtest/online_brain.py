"""Cabeca que continua treinando enquanto opera (walk-forward online).

Desenho temporal, que e onde esse tipo de teste costuma vazar futuro:

  - No fechamento do dia t a cabeca decide a posicao do intervalo
    [abertura de t+1, abertura de t+2].
  - O rotulo dessa decisao e r_t = open[t+2]/open[t+1] - 1, que so fica
    conhecido na abertura de t+2.
  - Logo, no fechamento de t o rotulo mais recente disponivel e o de t-2.
    O treino nunca toca em nada alem disso.

A normalizacao das features tambem e causal: media e desvio sao acumulados
por Welford apenas com amostras ja realizadas.
"""

import math

import torch
import torch.nn as nn

from .features import price_features, Memoria, PRICE_NAMES, MEMORY_NAMES, WARMUP, NAMES
from . import book_features


class Normalizador:
    """Media/desvio corridos, atualizados so com amostras do passado."""

    def __init__(self, dim):
        self.n = 0
        self.media = [0.0] * dim
        self.m2 = [0.0] * dim

    def atualizar(self, x):
        self.n += 1
        for j, v in enumerate(x):
            d = v - self.media[j]
            self.media[j] += d / self.n
            self.m2[j] += d * (v - self.media[j])

    def aplicar(self, x):
        if self.n < 2:
            return list(x)
        out = []
        for j, v in enumerate(x):
            sd = math.sqrt(self.m2[j] / (self.n - 1)) or 1.0
            out.append(max(-5.0, min(5.0, (v - self.media[j]) / sd)))
        return out


class Cabeca(nn.Module):
    def __init__(self, dim, oculto=16):
        super().__init__()
        self.rede = nn.Sequential(nn.Linear(dim, oculto), nn.Tanh(), nn.Linear(oculto, 1))

    def forward(self, x):
        return self.rede(x).squeeze(-1)


def conjunto_features(conjunto):
    """Nomes e warmup do conjunto escolhido.

    'basico' = 19 features genericas de preco. 'livro' = os 46 indicadores
    tirados do livro de analise tecnica. Em ambos os casos as 6 features de
    memoria sao concatenadas no fim.
    """
    if conjunto == "livro":
        return book_features.NAMES + MEMORY_NAMES, book_features.WARMUP
    return NAMES, WARMUP


def rodar(candles, ema_vals, inicio, congelar_em=None, usar_memoria=True,
          lr=0.01, oculto=16, passos_por_dia=2, lote=32, semente=0, limiar=0.5,
          conjunto="basico"):
    """Percorre a serie decidindo e (enquanto nao congelado) treinando.

    `congelar_em` e uma data: a partir dela os pesos param de mudar, mas a
    cabeca continua decidindo. E o braco "cerebro solido" da comparacao.

    Devolve (sinais, diario), onde `diario` traz, por dia, a norma dos pesos,
    o quanto eles se moveram e a importancia por feature — a instrumentacao
    que mostra a adaptacao acontecendo.
    """
    torch.manual_seed(semente)
    nomes, _ = conjunto_features(conjunto)
    pre = book_features.precalcular(candles) if conjunto == "livro" else None
    dim = len(nomes)
    modelo = Cabeca(dim, oculto)
    opt = torch.optim.Adam(modelo.parameters(), lr=lr)
    perda_fn = nn.BCEWithLogitsLoss()
    norm = Normalizador(dim)
    mem = Memoria()
    gen = torch.Generator().manual_seed(semente)

    n = len(candles)
    fim = n - 2                      # ultimo dia com rotulo possivel
    xs, pos = {}, {}
    # buffer pre-alocado: remontar o tensor todo dia sairia O(n^2)
    BX = torch.zeros(n, dim, dtype=torch.float32)
    BY = torch.zeros(n, dtype=torch.float32)
    nb = 0
    sinais = [0] * n
    diario = []
    congelado = False

    W = modelo.rede[0].weight
    anterior = W.detach().clone()

    for t in range(inicio, fim):
        if congelar_em is not None and candles[t].date >= congelar_em:
            congelado = True

        # 1) fecha o rotulo ja realizado (decisao de t-2) e treina com ele
        k = t - 2
        if k >= inicio:
            r_k = candles[k + 2].open / candles[k + 1].open - 1
            mem.registrar(r_k, pos[k] == 1)
            norm.atualizar(xs[k])
            BX[nb] = torch.tensor(norm.aplicar(xs[k]), dtype=torch.float32)
            BY[nb] = 1.0 if r_k > 0 else 0.0
            nb += 1

            if not congelado and nb >= lote:
                X, Y = BX[:nb], BY[:nb]
                for _ in range(passos_por_dia):
                    idx = torch.randint(0, nb, (lote,), generator=gen)
                    opt.zero_grad()
                    perda = perda_fn(modelo(X[idx]), Y[idx])
                    perda.backward()
                    opt.step()

        # 2) monta as features do dia (mercado + memoria do proprio desempenho)
        f = (book_features.features(candles, t, pre) if conjunto == "livro"
             else price_features(candles, t, ema_vals))
        m = mem.features() if usar_memoria else [0.0] * len(MEMORY_NAMES)
        x = f + m
        xs[t] = x

        # 3) decide
        with torch.no_grad():
            p = torch.sigmoid(modelo(torch.tensor([norm.aplicar(x)], dtype=torch.float32)))[0].item()
        pos[t] = 1 if p > limiar else 0
        mem.posicionado = pos[t]
        sinais[t] = 1 if pos[t] == 1 else -1

        atual = W.detach()
        delta = (atual - anterior).norm().item()
        anterior = atual.clone()
        imp = atual.abs().sum(dim=0)
        diario.append({
            "data": candles[t].date, "p": p, "posicao": pos[t],
            "norma_pesos": atual.norm().item(), "delta_pesos": delta,
            "congelado": int(congelado),
            "importancia": {nomes[j]: imp[j].item() for j in range(dim)},
        })

    return sinais, diario
