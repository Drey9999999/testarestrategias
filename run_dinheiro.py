"""A previsao de 61,3% vira dinheiro?

Regras, casadas com o que o modelo preve:
  - o alvo e o retorno de 20 pregoes, entao a carteira e rebalanceada a cada
    20 pregoes: os periodos de posse nao se sobrepoem e cada decisao e
    avaliada exatamente no horizonte para o qual foi treinada
  - a cada rebalanceamento, o ensemble pontua os 54 ativos e compra os N mais
    bem pontuados, peso igual
  - features do fechamento de t, execucao na abertura de t+1
  - long-only, sem alavancagem

Comparacoes obrigatorias: escolha aleatoria de N ativos, carteira cheia dos 54,
e a regra estatica de menor volatilidade que sobreviveu antes.
"""

import random
import statistics
import sys
from collections import defaultdict

import torch

from treino_lab import fatiar, treinar, prever
from treino_cross import carregar_com_transversal
from backtest.portfolio import carregar, valor, preco
import run_estatico as R_est

REBAL = 20
INICIO = "2025-01-01"


def montar():
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
    pred = [sum(c) / len(c) for c in zip(*ps)]
    # nota do modelo por (data, ativo) na janela de teste
    nota = defaultdict(dict)
    for pos, i in enumerate(te):
        nota[D[i]][A[i]] = pred[pos]
    return nota


def operar(escolher, opens, datas, custo, top_n, capital=10000.0):
    patr, cart = capital, {}
    hist = []
    for k in range(0, len(datas) - 1, REBAL):
        t, te_ = datas[k], datas[k + 1]
        esc = [i for i in escolher(t, top_n) if preco(opens, i, te_)]
        if not esc:
            continue
        patr = valor(patr, cart, opens, te_)
        giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1)
        patr *= (1 - custo * giro * 2)
        cart = {i: (patr / len(esc)) / preco(opens, i, te_) for i in esc}
        hist.append({"data": t, "escolhidos": esc})
    return valor(patr, cart, opens, datas[-1]), hist


def main():
    nota = montar()
    por_data, opens = carregar()
    datas = [d for d in sorted(por_data) if d >= INICIO]
    universo = sorted(opens)

    def modelo(t, n):
        d = nota.get(t, {})
        return [a for a, _ in sorted(d.items(), key=lambda x: -x[1])[:n]]

    rng = random.Random(3)

    def sorteio(t, n):
        return rng.sample(universo, n)

    def tudo(t, n):
        return universo

    lc = R_est.ranking_por_volatilidade(opens, INICIO, janela_dias=365)

    print(f"\njanela {datas[0]} a {datas[-1]}   rebalanceamento a cada {REBAL} pregoes "
          f"({len(range(0, len(datas)-1, REBAL))} decisoes)\n")
    for custo in [0.0015, 0.0005, 0.0002]:
        print(f"custo {custo*100:.2f}% por operacao")
        for n in [3, 5, 10]:
            fm, hist = operar(modelo, opens, datas, custo, n)
            sorteios = []
            for k in range(30):
                r2 = random.Random(100 + k)
                sorteios.append(operar(lambda t, nn: r2.sample(universo, nn),
                                       opens, datas, custo, n)[0])
            fv = operar(lambda t, nn: lc[:nn], opens, datas, custo, n)[0]
            venceu = sum(1 for x in sorteios if x >= fm)
            print(f"   top {n:<2}  modelo R$ {fm:>8,.0f}   sorteio R$ "
                  f"{statistics.median(sorteios):>8,.0f} ({venceu}/30 >= modelo)"
                  f"   menor vol R$ {fv:>8,.0f}")
        fc = operar(tudo, opens, datas, custo, 54)[0]
        print(f"   carteira cheia (54)  R$ {fc:,.0f}\n")


if __name__ == "__main__":
    main()
