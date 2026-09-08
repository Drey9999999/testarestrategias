"""Item 13: a regra de menor volatilidade so funciona no ajuste exato em que
eu a testei, ou vale numa faixa larga?

Um p-valor obtido numa unica combinacao de parametros nao diz o que parece: se
o efeito some ao trocar 365 por 180 dias, ou 5 por 10 ativos, entao o que
sobreviveu foi uma coincidencia entre muitas tentativas, nao um efeito.

Aqui a mesma regra e testada em 12 combinacoes por janela, cada uma com o
proprio teste nulo contra carteiras sorteadas.
"""

import random
import statistics
import sys

from backtest.portfolio import carregar, valor, preco
import run_estatico as R

CUSTO = 0.0005
REBAL = 10
SORTEIOS = 200


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
    # sem OKB: o token da propria corretora ja distorceu um resultado antes
    opens = {k: v for k, v in opens.items() if k != "OKB-USDT"}
    por_data = {d: [r for r in v if r["inst"] != "OKB-USDT"] for d, v in por_data.items()}
    univ = sorted(opens)

    for inicio, fim, nome in [("2023-01-01", "2024-12-31", "validacao 2023-24"),
                              ("2025-01-01", None, "teste 2025/26")]:
        pdj = {d: v for d, v in por_data.items() if fim is None or d <= fim}
        print(f"\n{'='*72}\n{nome}   (53 ativos, custo 0,05%, {SORTEIOS} sorteios por celula)"
              f"\n{'='*72}")
        print(f"{'janela':>8} {'top_n':>6} {'carteira':>12} {'mediana sorteio':>17} {'p':>7}")
        sig = 0
        for janela in [60, 180, 365]:
            for n in [3, 5, 10, 20]:
                lc = R.ranking_por_volatilidade(opens, inicio, janela_dias=janela)[:n]
                real = segurar(lc, pdj, opens, inicio, fim)
                rng = random.Random(7)
                sort = sorted(segurar(rng.sample(univ, n), pdj, opens, inicio, fim)
                              for _ in range(SORTEIOS))
                p = sum(1 for x in sort if x >= real) / len(sort)
                sig += p < 0.05
                marca = " *" if p < 0.05 else "  "
                print(f"{janela:>8} {n:>6} R$ {real:>9,.0f} R$ {statistics.median(sort):>14,.0f} "
                      f"{p:>7.3f}{marca}")
        print(f"  significativas a 5%: {sig}/12")


if __name__ == "__main__":
    main()
