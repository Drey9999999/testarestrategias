"""E se a carteira puder ficar em CAIXA quando o modelo nao ve alta?

Ate agora a carteira era obrigada a estar sempre comprada, entao num mercado
que caiu 78% ela so podia escolher perder menos. O modelo ja produz uma
probabilidade; usar o proprio limiar dele (0,5) para decidir entre comprar e
ficar em caixa nao acrescenta parametro nenhum ajustado ao resultado.

Regra: entre os N melhores do dia, carrega apenas os que tem probabilidade
acima do limiar. Se nenhum tiver, fica 100% em caixa ate o proximo
rebalanceamento.
"""

import random
import statistics
from collections import defaultdict

from run_dinheiro import montar, REBAL, INICIO
from backtest.portfolio import carregar, valor, preco
import run_estatico as R_est

CUSTO = 0.0005


def operar(escolher, opens, datas, top_n, capital=10000.0):
    patr, cart = capital, {}
    em_caixa = 0
    decisoes = 0
    for k in range(0, len(datas) - 1, REBAL):
        t, te_ = datas[k], datas[k + 1]
        decisoes += 1
        esc = [i for i in escolher(t, top_n) if preco(opens, i, te_)]
        patr = valor(patr, cart, opens, te_)
        giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1) if (esc or cart) else 0
        patr *= (1 - CUSTO * giro * 2)
        if not esc:
            cart = {}
            em_caixa += 1
            continue
        cart = {i: (patr / len(esc)) / preco(opens, i, te_) for i in esc}
    return valor(patr, cart, opens, datas[-1]), em_caixa, decisoes


def main():
    nota = montar()
    por_data, opens_all = carregar()
    opens = {k: v for k, v in opens_all.items() if k != "OKB-USDT"}
    datas = [d for d in sorted(por_data) if d >= INICIO]
    univ = sorted(opens)
    excl = {"OKB-USDT"}

    def ordenado(t):
        d = {a: p for a, p in nota.get(t, {}).items() if a not in excl}
        return sorted(d.items(), key=lambda x: -x[1])

    print(f"\nsem OKB, {len(univ)} ativos, custo {CUSTO*100:.2f}%, "
          f"rebalanceamento a cada {REBAL} pregoes\n")
    for limiar in [0.0, 0.5, 0.55, 0.6]:
        for n in [3, 5]:
            def esc(t, nn, lim=limiar):
                return [a for a, p in ordenado(t)[:nn] if p > lim]
            f, caixa, dec = operar(esc, opens, datas, n)
            rot = "sem filtro" if limiar == 0 else f"p > {limiar:.2f}"
            print(f"  {rot:<12} top {n}:  R$ {f:>8,.0f}   "
                  f"({f/10000-1:+6.1%})   em caixa {caixa}/{dec} vezes")
    lc = R_est.ranking_por_volatilidade(opens, INICIO, janela_dias=365)
    fv, _, _ = operar(lambda t, nn: lc[:nn], opens, datas, 3)
    srt = []
    for k in range(30):
        r2 = random.Random(300 + k)
        srt.append(operar(lambda t, nn: r2.sample(univ, nn), opens, datas, 3)[0])
    print(f"\n  referencias: menor volatilidade top3 R$ {fv:,.0f}   "
          f"sorteio top3 (mediana) R$ {statistics.median(srt):,.0f}")


if __name__ == "__main__":
    main()
