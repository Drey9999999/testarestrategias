"""As duas pecas juntas, com custo real.

  QUAL ativo  -> modelo transversal (alvo relativo, features transversais)
  SE  investir -> modelo de cronometragem no horizonte de 2 pregoes

A carteira mantem os N melhores ativos, revistos a cada 20 pregoes (horizonte
do modelo de selecao), e liga/desliga a exposicao a cada 2 pregoes (horizonte
do modelo de cronometragem). Fora do mercado, o dinheiro fica em caixa.

O limiar de exposicao e escolhido na VALIDACAO. O teste so e olhado depois.
"""

import random
import statistics
from collections import defaultdict

import torch

from treino_lab import fatiar, treinar, prever
from treino_cross import carregar_com_transversal
from treino_mercado_curto import carregar_curto
from backtest.portfolio import carregar, valor, preco
import run_estatico as R_est

EXCL = {"OKB-USDT"}
REBAL_SEL = 20
PASSO_EXP = 2


def treinar_selecao():
    X, _, D, A, R = carregar_com_transversal()
    tr, va, te = fatiar(D)
    dim = len(X[0])
    Xt = torch.tensor(X, dtype=torch.float32)
    Rt = torch.tensor(R, dtype=torch.float32)
    W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)
    pd_ = defaultdict(list)
    for i, d in enumerate(D):
        pd_[d].append(i)
    Yl = [0.0] * len(R)
    for d, idxs in pd_.items():
        if len(idxs) >= 5:
            med = statistics.median(R[i] for i in idxs)
            for i in idxs:
                Yl[i] = 1.0 if R[i] > med else 0.0
    Y = torch.tensor(Yl, dtype=torch.float32)
    mods = [treinar(Xt, Y, W, tr, va, dim, semente=s, oculto=128, camadas=3,
                    lr=3e-4, epocas=80, parada=10)[:3] for s in range(8)]
    out = {}
    for jan, idxs in [("va", va), ("te", te)]:
        ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
        pred = [sum(c) / len(c) for c in zip(*ps)]
        n = defaultdict(dict)
        for pos, i in enumerate(idxs):
            n[D[i]][A[i]] = pred[pos]
        out[jan] = n
    return out


def treinar_timing():
    X, Yl, D, A, R = carregar_curto(horizonte=2)
    tr, va, te = fatiar(D)
    dim = len(X[0])
    Xt = torch.tensor(X, dtype=torch.float32)
    Y = torch.tensor(Yl, dtype=torch.float32)
    Rt = torch.tensor(R, dtype=torch.float32)
    W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)
    mods = [treinar(Xt, Y, W, tr, va, dim, semente=s, oculto=128, camadas=3,
                    lr=3e-4, epocas=60, parada=8)[:3] for s in range(8)]
    out = {}
    for jan, idxs in [("va", va), ("te", te)]:
        ps = [prever(m, Xt, idxs, mu, sd) for m, mu, sd in mods]
        pred = [sum(c) / len(c) for c in zip(*ps)]
        pd_ = defaultdict(list)
        for pos, i in enumerate(idxs):
            pd_[D[i]].append(pred[pos])
        out[jan] = {d: statistics.mean(v) for d, v in pd_.items()}
    return out


def operar(sel, tim, limiar, opens, datas, top_n, custo, capital=10000.0):
    patr, cart, alvo = capital, {}, []
    dentro = fora = 0
    for k in range(len(datas) - 1):
        t, te_ = datas[k], datas[k + 1]
        if k % REBAL_SEL == 0:
            d = {a: p for a, p in sel.get(t, {}).items() if a not in EXCL}
            alvo = [a for a, _ in sorted(d.items(), key=lambda x: -x[1])[:top_n]]
        if k % PASSO_EXP:
            continue
        sinal = tim.get(t)
        exposto = (sinal is not None and sinal > limiar)
        esc = [a for a in alvo if preco(opens, a, te_)] if exposto else []
        patr = valor(patr, cart, opens, te_)
        if esc or cart:
            giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1) if esc else 1.0
            patr *= (1 - custo * giro * 2)
        cart = ({a: (patr / len(esc)) / preco(opens, a, te_) for a in esc}
                if esc else {})
        dentro += bool(esc)
        fora += (not esc)
    return valor(patr, cart, opens, datas[-1]), dentro, fora


def main():
    sel = treinar_selecao()
    tim = treinar_timing()
    por_data, opens_all = carregar()
    opens = {k: v for k, v in opens_all.items() if k not in EXCL}
    d_va = [d for d in sorted(por_data) if "2023-01-01" <= d < "2025-01-01"]
    d_te = [d for d in sorted(por_data) if d >= "2025-01-01"]

    vals = sorted(tim["va"].values())
    print("escolha do limiar de exposicao na VALIDACAO (custo 0,05%)\n")
    melhor, mv = None, -1
    for q in [0.0, 0.2, 0.35, 0.5]:
        lim = vals[int(q * (len(vals) - 1))] if q else -1
        f, dd, ff = operar(sel["va"], tim["va"], lim, opens, d_va, 5, 0.0005)
        print(f"  corta {q*100:>4.0f}% mais fracos: R$ {f:>9,.0f}   "
              f"exposto {dd}/{dd+ff}")
        if f > mv:
            melhor, mv, mq = lim, f, q
    print(f"\n  -> limiar escolhido: corta {mq*100:.0f}% mais fracos\n")

    print("TESTE 2025/26")
    for custo in [0.0005, 0.0002]:
        for n in [3, 5]:
            f, dd, ff = operar(sel["te"], tim["te"], melhor, opens, d_te, n, custo)
            f0, _, _ = operar(sel["te"], tim["te"], -1, opens, d_te, n, custo)
            print(f"  custo {custo*100:.2f}%  top {n}:  COM cronometragem R$ {f:>8,.0f} "
                  f"({f/10000-1:+6.1%})  exposto {dd}/{dd+ff}   |   "
                  f"sempre comprado R$ {f0:>8,.0f} ({f0/10000-1:+6.1%})")
    lc = R_est.ranking_por_volatilidade(opens, "2025-01-01", janela_dias=365)
    fv, _, _ = operar({d: {a: 1 for a in lc[:5]} for d in d_te}, tim["te"], -1,
                      opens, d_te, 5, 0.0005)
    print(f"\n  referencia menor volatilidade (sempre comprado): R$ {fv:,.0f}")


if __name__ == "__main__":
    main()
