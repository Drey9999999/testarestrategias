"""Carteira transversal em 54 ativos, com controles honestos.

Controles:
  - ESCOLHA ALEATORIA: mesma mecanica, ativos sorteados. Se o modelo nao
    superar o sorteio, a selecao dele nao vale nada.
  - CARTEIRA CHEIA: comprar os 54 e segurar, peso igual. E a deriva do setor.
"""

import random
import statistics
import sys

from backtest.portfolio import carregar, rodar_carteira, valor, preco

CUSTOS = [0.0015, 0.0005, 0.0002]
INICIO = "2025-01-01"


def aleatoria(por_data, opens, inicio, top_n, rebal, custo, semente, capital=10000.0):
    rng = random.Random(semente)
    datas = sorted(por_data)
    patr, cart = capital, {}
    for k, t in enumerate(datas):
        if k + 1 >= len(datas):
            break
        te = datas[k + 1]
        if k % rebal or t < inicio:
            continue
        patr = valor(patr, cart, opens, te)
        univ = [r["inst"] for r in por_data[t] if preco(opens, r["inst"], te)]
        esc = rng.sample(univ, min(top_n, len(univ)))
        giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1)
        patr *= (1 - custo * giro * 2)
        cart = {i: (patr / len(esc)) / preco(opens, i, te) for i in esc}
    return valor(patr, cart, opens, datas[-1])


def cheia(por_data, opens, inicio, custo, capital=10000.0):
    datas = sorted(por_data)
    i0 = next(k for k, t in enumerate(datas) if t >= inicio)
    te = datas[i0 + 1]
    univ = [r["inst"] for r in por_data[datas[i0]] if preco(opens, r["inst"], te)]
    patr = capital * (1 - custo)
    cart = {i: (patr / len(univ)) / preco(opens, i, te) for i in univ}
    return valor(patr, cart, opens, datas[-1]) * (1 - custo)


def main():
    por_data, opens = carregar()
    print(f"universo: {len(por_data[sorted(por_data)[-1]])} ativos hoje, "
          f"{len(por_data):,} datas")
    top_n = 5
    rebal = 10
    for custo in CUSTOS:
        print(f"\n{'='*74}\ncusto {custo*100:.2f}% por operacao   "
              f"(top {top_n}, rebalanceamento a cada {rebal} dias)\n{'='*74}")
        finais = []
        for s in range(5):
            r = rodar_carteira(por_data, opens, INICIO, top_n=top_n, rebal=rebal,
                               custo=custo, semente=s)
            finais.append(r["final"])
        al = [aleatoria(por_data, opens, INICIO, top_n, rebal, custo, 100 + k)
              for k in range(20)]
        ch = cheia(por_data, opens, INICIO, custo)
        med = statistics.median(finais)
        venceu = sum(1 for x in al if x >= med)
        print(f"  modelo (5 sementes) : R$ {med:>9,.0f}  ({med/100-100:+.1f}%)   "
              f"pior {min(finais):,.0f}  melhor {max(finais):,.0f}")
        print(f"  escolha aleatoria   : R$ {statistics.median(al):>9,.0f}  "
              f"({statistics.median(al)/100-100:+.1f}%)   "
              f"sorteios >= modelo: {venceu}/20")
        print(f"  carteira cheia (54) : R$ {ch:>9,.0f}  ({ch/100-100:+.1f}%)")


if __name__ == "__main__":
    main()
