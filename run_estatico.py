"""Item 7: existe valor ADAPTATIVO, ou so preferencia por ativo?

O modelo adaptativo reescolhe os ativos a cada 10 dias. Se um ranking FIXO,
decidido apenas com dados anteriores a janela de teste e nunca mais revisto,
render o mesmo, entao a adaptacao nao esta agregando nada — o que o modelo
aprendeu foi "estes ativos sao melhores", nao "agora e a hora destes".

Tres controles estaticos, todos decididos so com dados ate 2024-12-31:

  A. top N por score MEDIO do modelo no periodo de treino (congela a escolha
     do proprio modelo)
  B. top N por retorno passado (momento, sem modelo nenhum)
  C. top N por menor volatilidade passada (qualidade, sem modelo nenhum)
"""

import statistics
import sys

import torch

from backtest.portfolio import (carregar, rodar_carteira, valor, preco, Rede)
from backtest import book_features

import sys as _s
INICIO = "2025-01-01"
FIM = None
for _a in _s.argv[1:]:
    if _a.startswith("--inicio="): INICIO = _a.split("=")[1]
    if _a.startswith("--fim="): FIM = _a.split("=")[1]
CUSTO = 0.0005
TOP_N = 5
REBAL = 10


def _ate(datas):
    return [d for d in datas if FIM is None or d <= FIM]


def segurar_fixos(escolhidos, por_data, opens, inicio, capital=10000.0):
    """Compra a lista fixa e rebalanceia para peso igual, mesmo custo e ritmo."""
    datas = _ate(sorted(por_data))
    patr, cart = capital, {}
    for k, t in enumerate(datas):
        if k + 1 >= len(datas):
            break
        te = datas[k + 1]
        if t < inicio or k % REBAL:
            continue
        esc = [i for i in escolhidos if preco(opens, i, te)]
        if not esc:
            continue
        patr = valor(patr, cart, opens, te)
        giro = len(set(esc) ^ set(cart)) / max(len(esc) * 2, 1)
        patr *= (1 - CUSTO * giro * 2)
        cart = {i: (patr / len(esc)) / preco(opens, i, te) for i in esc}
    return valor(patr, cart, opens, datas[-1])


def ranking_por_retorno(opens, por_data, ate, janela_dias=365):
    """Retorno passado de cada ativo, so com precos anteriores a `ate`."""
    r = {}
    for inst, o in opens.items():
        ds = sorted(d for d in o if d < ate)
        if len(ds) < janela_dias + 5:
            continue
        r[inst] = o[ds[-1]] / o[ds[-janela_dias]] - 1
    return sorted(r, key=r.get, reverse=True)


def ranking_por_volatilidade(opens, ate, janela_dias=365):
    r = {}
    for inst, o in opens.items():
        ds = sorted(d for d in o if d < ate)
        if len(ds) < janela_dias + 5:
            continue
        px = [o[d] for d in ds[-janela_dias:]]
        rets = [px[i] / px[i - 1] - 1 for i in range(1, len(px)) if px[i - 1] > 0]
        r[inst] = statistics.pstdev(rets) if rets else 9e9
    return sorted(r, key=r.get)


def ranking_pelo_modelo(por_data, opens, ate, semente):
    """Score medio que o modelo (treinado so no passado) da a cada ativo,
    calculado apenas sobre datas anteriores a `ate`."""
    r = rodar_carteira(por_data, opens, inicio="2021-01-01", top_n=TOP_N,
                       rebal=REBAL, custo=CUSTO, semente=semente)
    cont = {}
    for h in r["hist"]:
        if h["data"] >= ate:
            continue
        for i in h["escolhidos"]:
            cont[i] = cont.get(i, 0) + 1
    return sorted(cont, key=cont.get, reverse=True)


def main():
    por_data, opens = carregar()
    print(f"\n{'='*78}\nItem 7 — adaptativo x preferencia fixa   "
          f"(top {TOP_N}, custo {CUSTO*100:.2f}%, {INICIO} a {FIM or 'fim'})\n{'='*78}")

    pd_janela = {d: v for d, v in por_data.items() if FIM is None or d <= FIM}
    adapt = []
    for s in range(5):
        adapt.append(rodar_carteira(pd_janela, opens, INICIO, top_n=TOP_N,
                                    rebal=REBAL, custo=CUSTO, semente=s)["final"])
    print(f"  ADAPTATIVO (reescolhe a cada 10 dias)")
    print(f"    mediana R$ {statistics.median(adapt):,.0f}   "
          f"pior {min(adapt):,.0f}   melhor {max(adapt):,.0f}")

    ests = []
    for s in range(3):
        lst = ranking_pelo_modelo(pd_janela, opens, INICIO, s)[:TOP_N]
        f = segurar_fixos(lst, pd_janela, opens, INICIO)
        ests.append(f)
        print(f"    [A] preferidos do modelo no treino, semente {s}: "
              f"{', '.join(x.replace('-USDT','') for x in lst)} -> R$ {f:,.0f}")
    print(f"  ESTATICO A mediana R$ {statistics.median(ests):,.0f}")

    lb = ranking_por_retorno(opens, pd_janela, INICIO)[:TOP_N]
    fb = segurar_fixos(lb, pd_janela, opens, INICIO)
    print(f"  ESTATICO B (maior retorno passado): "
          f"{', '.join(x.replace('-USDT','') for x in lb)} -> R$ {fb:,.0f}")

    lc = ranking_por_volatilidade(opens, INICIO)[:TOP_N]
    fc = segurar_fixos(lc, pd_janela, opens, INICIO)
    print(f"  ESTATICO C (menor volatilidade): "
          f"{', '.join(x.replace('-USDT','') for x in lc)} -> R$ {fc:,.0f}")


if __name__ == "__main__":
    main()
