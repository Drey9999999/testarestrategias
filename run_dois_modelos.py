"""Dois modelos com papeis diferentes, porque um so nao da conta.

O alvo relativo responde QUAL ativo, e por construcao nunca responde SE vale a
pena estar comprado: metade dos ativos bate a mediana em qualquer cenario,
inclusive num desabamento.

Entao:
  - modelo RELATIVO escolhe os N melhores do dia
  - modelo ABSOLUTO ("este ativo sobe?"), com a media das probabilidades no
    universo inteiro, decide a exposicao: acima do limiar compra, abaixo fica
    em caixa

O limiar de exposicao e escolhido na VALIDACAO, nunca no teste.
"""

import random
import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, treinar, prever
from treino_cross import carregar_com_transversal
from backtest.portfolio import carregar, valor, preco
import run_estatico as R_est

REBAL, CUSTO, INICIO = 20, 0.0005, "2025-01-01"
EXCL = {"OKB-USDT"}


def treinar_dois():
    X, Yabs, D, A, R = carregar_com_transversal()
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
    Ya = torch.tensor(Yabs, dtype=torch.float32)

    saida = {}
    for nome, Yuse in [("rel", Yr), ("abs", Ya)]:
        mods = []
        for s in range(8):
            m, mu, sd, _ = treinar(Xt, Yuse, W, tr, va, dim, semente=s, oculto=128,
                                   camadas=3, lr=3e-4, epocas=80, parada=10)
            mods.append((m, mu, sd))
        for jan, idxs in [("va", va), ("te", te)]:
            ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
            pred = [sum(c)/len(c) for c in zip(*ps)]
            n = defaultdict(dict)
            for pos, i in enumerate(idxs):
                n[D[i]][A[i]] = pred[pos]
            saida[(nome, jan)] = n
    return saida


def operar(rel, absol, limiar, opens, datas, top_n, capital=10000.0):
    patr, cart, caixa = capital, {}, 0
    dec = 0
    for k in range(0, len(datas) - 1, REBAL):
        t, te_ = datas[k], datas[k + 1]
        dec += 1
        patr = valor(patr, cart, opens, te_)
        d_abs = [p for a, p in absol.get(t, {}).items() if a not in EXCL]
        exposto = (statistics.mean(d_abs) > limiar) if d_abs else False
        d_rel = {a: p for a, p in rel.get(t, {}).items() if a not in EXCL}
        esc = [a for a, _ in sorted(d_rel.items(), key=lambda x: -x[1])[:top_n]
               if preco(opens, a, te_)] if exposto else []
        giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1) if (esc or cart) else 0
        patr *= (1 - CUSTO * giro * 2)
        if not esc:
            cart = {}
            caixa += 1
            continue
        cart = {i: (patr / len(esc)) / preco(opens, i, te_) for i in esc}
    return valor(patr, cart, opens, datas[-1]), caixa, dec


def main():
    s = treinar_dois()
    por_data, opens_all = carregar()
    opens = {k: v for k, v in opens_all.items() if k not in EXCL}

    d_va = [d for d in sorted(por_data) if "2023-01-01" <= d < INICIO]
    d_te = [d for d in sorted(por_data) if d >= INICIO]

    print("\nescolha do limiar de exposicao na VALIDACAO 2023-24 (teste nao olhado)")
    melhor, mv = None, -1
    for lim in [0.0, 0.40, 0.45, 0.50, 0.55]:
        f, c, dec = operar(s[("rel", "va")], s[("abs", "va")], lim, opens, d_va, 3)
        print(f"  limiar {lim:.2f}: R$ {f:>9,.0f}   em caixa {c}/{dec}")
        if f > mv:
            melhor, mv = lim, f
    print(f"  -> limiar escolhido: {melhor:.2f}\n")

    print("TESTE 2025/26 (nunca olhado ate esta linha)")
    for n in [3, 5]:
        f, c, dec = operar(s[("rel", "te")], s[("abs", "te")], melhor, opens, d_te, n)
        f0, _, _ = operar(s[("rel", "te")], s[("abs", "te")], 0.0, opens, d_te, n)
        print(f"  top {n}: com filtro de exposicao R$ {f:>8,.0f} ({f/10000-1:+.1%})   "
              f"em caixa {c}/{dec}   |   sempre comprado R$ {f0:>8,.0f} ({f0/10000-1:+.1%})")
    lc = R_est.ranking_por_volatilidade(opens, INICIO, janela_dias=365)
    fv, _, _ = operar({d: {a: 1 for a in lc[:3]} for d in d_te},
                      s[("abs", "te")], 0.0, opens, d_te, 3)
    srt = []
    for k in range(30):
        r2 = random.Random(400 + k)
        univ = sorted(opens)
        fake = {d: {a: r2.random() for a in univ} for d in d_te}
        srt.append(operar(fake, s[("abs", "te")], 0.0, opens, d_te, 3)[0])
    print(f"\n  referencias: menor volatilidade R$ {fv:,.0f}   "
          f"sorteio (mediana de 30) R$ {statistics.median(srt):,.0f}")


if __name__ == "__main__":
    main()
