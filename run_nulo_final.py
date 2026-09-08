"""Item 6: a regra de menor volatilidade passa em teste nulo?

Dois nulos, porque medem coisas diferentes:

  A. CARTEIRAS SORTEADAS: 500 carteiras de 5 ativos tiradas do mesmo universo,
     mesma mecanica e mesmo custo. Responde "escolher os menos volateis e
     melhor que escolher qualquer 5?".
  B. RANKING DESLOCADO: o mesmo criterio calculado numa data anterior, e a
     carteira resultante aplicada na janela. Responde "importa QUANDO se mede
     a volatilidade, ou qualquer medida antiga serve?".
"""

import random
import statistics
import sys

from backtest.portfolio import carregar, valor, preco
import run_estatico as R

CUSTO = 0.0005
TOP_N = 5
REBAL = 10


def segurar(lst, pd_, opens, inicio, fim, capital=10000.0):
    datas = [d for d in sorted(pd_) if fim is None or d <= fim]
    patr, cart = capital, {}
    for k, t in enumerate(datas):
        if k + 1 >= len(datas):
            break
        te = datas[k + 1]
        if t < inicio or k % REBAL:
            continue
        esc = [i for i in lst if preco(opens, i, te)]
        if not esc:
            continue
        patr = valor(patr, cart, opens, te)
        giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1)
        patr *= (1 - CUSTO * giro * 2)
        cart = {i: (patr / len(esc)) / preco(opens, i, te) for i in esc}
    return valor(patr, cart, opens, datas[-1])


def main():
    por_data, opens = carregar()
    sem_okb = {k: v for k, v in opens.items() if k != "OKB-USDT"}
    pd_sem = {d: [r for r in v if r["inst"] != "OKB-USDT"] for d, v in por_data.items()}

    for rot, pd_, op_ in [("universo completo (54)", por_data, opens),
                          ("sem OKB (53)", pd_sem, sem_okb)]:
        for inicio, fim, nome in [("2023-01-01", "2024-12-31", "validacao 2023-24"),
                                  ("2025-01-01", None, "teste 2025/26")]:
            pdj = {d: v for d, v in pd_.items() if fim is None or d <= fim}
            lc = R.ranking_por_volatilidade(op_, inicio)[:TOP_N]
            real = segurar(lc, pdj, op_, inicio, fim)

            univ = sorted(op_)
            rng = random.Random(42)
            sorteios = []
            for _ in range(500):
                sorteios.append(segurar(rng.sample(univ, TOP_N), pdj, op_, inicio, fim))
            sorteios.sort()
            acima = sum(1 for x in sorteios if x >= real)
            p = acima / len(sorteios)

            # nulo B: mesmo criterio medido 1 ano antes
            ant = "2022-01-01" if inicio == "2023-01-01" else "2024-01-01"
            lb = R.ranking_por_volatilidade(op_, ant)[:TOP_N]
            desl = segurar(lb, pdj, op_, inicio, fim)

            print(f"\n{rot} — {nome}")
            print(f"  menor volatilidade  R$ {real:>10,.0f}   "
                  f"({', '.join(x.replace('-USDT','') for x in lc)})")
            print(f"  500 sorteios        mediana R$ {statistics.median(sorteios):>8,.0f}   "
                  f"p10 R$ {sorteios[50]:,.0f}   p90 R$ {sorteios[450]:,.0f}")
            print(f"  sorteios >= real: {acima}/500  ->  p = {p:.3f}")
            print(f"  ranking medido 1 ano antes ({ant}): R$ {desl:>10,.0f}")


if __name__ == "__main__":
    main()
