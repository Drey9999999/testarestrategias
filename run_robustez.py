"""Itens 11 e 12: o achado sobrevive sem o OKB, e adaptar menos e melhor?

Item 11 — o ganho da carteira pequena em 2025/26 vinha quase todo do OKB, que
e o token da propria corretora de onde vem o dado. Excluindo-o, o ordenamento
"estatico vence adaptativo" se mantem?

Item 12 — se reescolher a cada 10 dias e pior que nunca reescolher, entao
reescolher a cada 40 ou 60 dias deve ficar entre os dois. Se nao ficar, a
explicacao "adaptacao adiciona ruido" esta errada.
"""

import json
import os
import statistics
import sys

CACHE = "results/robustez.json"


def _cache():
    return json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def _grava(c):
    os.makedirs("results", exist_ok=True)
    json.dump(c, open(CACHE, "w"), indent=1)

from backtest.portfolio import carregar, rodar_carteira, valor, preco
import run_estatico as R

CUSTO = 0.0005
JANELAS = [("2023-01-01", "2024-12-31", "validacao 2023-24"),
           ("2025-01-01", None, "teste 2025/26")]


def sem(por_data, opens, excluir):
    pd2 = {d: [r for r in v if r["inst"] not in excluir] for d, v in por_data.items()}
    op2 = {k: v for k, v in opens.items() if k not in excluir}
    return {d: v for d, v in pd2.items() if v}, op2


def fixos(lst, pd_, opens, inicio, fim, rebal):
    datas = [d for d in sorted(pd_) if fim is None or d <= fim]
    patr, cart = 10000.0, {}
    for k, t in enumerate(datas):
        if k + 1 >= len(datas):
            break
        te = datas[k + 1]
        if t < inicio or k % rebal:
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
    base_pd, base_op = carregar()
    excluir = set(sys.argv[1:]) or {"OKB-USDT"}
    print(f"\nexcluindo do universo: {', '.join(sorted(excluir))}")

    for rotulo, (pd_, op_) in [("COM tudo", (base_pd, base_op)),
                               ("SEM os excluidos", sem(base_pd, base_op, excluir))]:
        print(f"\n{'='*80}\n{rotulo}   ({len(op_)} ativos)\n{'='*80}")
        for inicio, fim, nome in JANELAS:
            pdj = {d: v for d, v in pd_.items() if fim is None or d <= fim}
            print(f"\n  {nome}")
            print(f"  {'rebal':>7} {'adaptativo':>13} {'menor volatilidade':>20}")
            lc = R.ranking_por_volatilidade(op_, inicio)[:5]
            for rebal in [10, 20, 40, 60]:
                ch = _cache()
                ck = f"{rotulo}|{nome}|{rebal}"
                if ck in ch:
                    ad, fc = ch[ck]
                else:
                    ad = statistics.median(
                        rodar_carteira(pdj, op_, inicio, top_n=5, rebal=rebal,
                                       custo=CUSTO, semente=s)["final"] for s in range(3))
                    fc = fixos(lc, pdj, op_, inicio, fim, rebal)
                    ch[ck] = [ad, fc]
                    _grava(ch)
                print(f"  {rebal:>7} R$ {ad:>10,.0f} R$ {fc:>17,.0f}")
            print(f"    carteira fixa escolhida: "
                  f"{', '.join(x.replace('-USDT','') for x in lc)}")


if __name__ == "__main__":
    main()
