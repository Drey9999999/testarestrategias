"""Item 17: as duas pecas que passaram em algum teste, juntas.

Carteira dos N ativos menos volateis (janela 365d), mas cada ativo so e
carregado quando esta acima da propria EMA 9. Custo de maker.

O controle correto NAO e a carteira sem filtro: o filtro reduz exposicao, e
reduzir exposicao ja ajuda sozinho num mercado de queda (item 16 provou isso).
O controle e a MESMA carteira com a mesma exposicao removida ao acaso.
"""

import random
import statistics

from backtest.data import load
from backtest.engine import ema
from backtest.portfolio import carregar, valor, preco
import run_estatico as R

CUSTO = 0.0002          # maker barato
REBAL = 10
TOP_N = 5
JANELA_VOL = 365


def emas_por_ativo(insts):
    """Serie 0/1 por ativo e data: 1 se o fechamento esta acima da EMA 9."""
    acima = {}
    for inst in insts:
        c = load(inst)
        e = ema([x.close for x in c], 9)
        acima[inst] = {c[i].date: (1 if (e[i] is not None and c[i].close > e[i]) else 0)
                       for i in range(len(c))}
    return acima


def rodar(lst, pd_, opens, inicio, fim, filtro=None, capital=10000.0):
    """filtro[inst][data] = 1 permite carregar, 0 mantem em caixa."""
    datas = [d for d in sorted(pd_) if fim is None or d <= fim]
    patr, cart = capital, {}
    dias_dentro = tot = 0
    for k, t in enumerate(datas):
        if k + 1 >= len(datas):
            break
        te = datas[k + 1]
        if t < inicio or k % REBAL:
            continue
        esc = [i for i in lst if preco(opens, i, te)]
        if filtro is not None:
            esc = [i for i in esc if filtro.get(i, {}).get(t, 0) == 1]
        patr = valor(patr, cart, opens, te)
        tot += 1
        dias_dentro += 1 if esc else 0
        if not esc:
            cart = {}
            continue
        giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1)
        patr *= (1 - CUSTO * giro * 2)
        cart = {i: (patr / len(esc)) / preco(opens, i, te) for i in esc}
    return valor(patr, cart, opens, datas[-1]), (dias_dentro / tot if tot else 0)


def main():
    por_data, opens = carregar()
    opens = {k: v for k, v in opens.items() if k != "OKB-USDT"}
    por_data = {d: [r for r in v if r["inst"] != "OKB-USDT"] for d, v in por_data.items()}

    for inicio, fim, nome in [("2023-01-01", "2024-12-31", "validacao 2023-24"),
                              ("2025-01-01", None, "teste 2025/26")]:
        pdj = {d: v for d, v in por_data.items() if fim is None or d <= fim}
        lst = R.ranking_por_volatilidade(opens, inicio, janela_dias=JANELA_VOL)[:TOP_N]
        filtro = emas_por_ativo(lst)

        sem, _ = rodar(lst, pdj, opens, inicio, fim)
        com, exposicao = rodar(lst, pdj, opens, inicio, fim, filtro=filtro)

        # controle: mesma exposicao removida ao acaso, por ativo e por data
        rng = random.Random(23)
        nulos = []
        for _ in range(200):
            falso = {}
            for i in lst:
                dias = sorted(filtro[i])
                p = sum(filtro[i].values()) / max(len(dias), 1)
                falso[i] = {d: (1 if rng.random() < p else 0) for d in dias}
            nulos.append(rodar(lst, pdj, opens, inicio, fim, filtro=falso)[0])
        nulos.sort()
        acima = sum(1 for x in nulos if x >= com)

        print(f"\n{nome}   carteira: {', '.join(x.replace('-USDT','') for x in lst)}")
        print(f"  sem filtro de EMA        R$ {sem:>9,.0f}")
        print(f"  COM filtro de EMA 9      R$ {com:>9,.0f}   "
              f"(carteira ocupada em {exposicao*100:.0f}% dos rebalanceamentos)")
        print(f"  200 filtros ALEATORIOS de mesma densidade: "
              f"mediana R$ {statistics.median(nulos):,.0f}")
        print(f"    {acima}/200 igualaram ou superaram  ->  p = {acima/200:.3f}")


if __name__ == "__main__":
    main()
