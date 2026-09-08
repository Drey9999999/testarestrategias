"""Escolhe a banda de histerese SO com 2018-2024 e aplica cega em 2025/26.

A banda corta o giro, e giro e o que estava destruindo o liquido. Mas escolher
a banda olhando o resultado de 2025/26 seria ajustar ao gabarito. Aqui a
selecao acontece inteiramente dentro do periodo de treino, e a janela de teste
so e tocada uma vez, ja com a banda decidida.
"""

import statistics
import sys

from backtest.data import load
from backtest.engine import ema, run_backtest, buy_and_hold
from backtest.online_brain import rodar, conjunto_features

CAPITAL, FEE, SLIP = 10000.0, 0.001, 0.0005
DESDE = "2025-01-01"
BANDAS = [0.00, 0.03, 0.06, 0.10, 0.15]
SEMENTES = list(range(10))


def main():
    inst = sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT"
    c = load(inst)
    e = ema([x.close for x in c], 9)
    _, warmup = conjunto_features("livro")
    idx = next(i for i, x in enumerate(c) if x.date >= DESDE)
    w = idx - 1

    print(f"\n{inst}  selecao da banda usando SO 2018-2024\n")
    print(f"{'banda':>7} {'treino (2018-2024)':>20} {'trades treino':>14}")
    resultados = {}
    guardado = {}
    for b in BANDAS:
        tr, ntr = [], []
        for s in SEMENTES:
            sig, _ = rodar(c, e, warmup, usar_memoria=True, semente=s,
                           conjunto="livro", banda=b)
            guardado[(b, s)] = sig
            r = run_backtest(c[warmup:w + 1], sig[warmup:w + 1], CAPITAL, FEE, SLIP)
            tr.append(r.total_return)
            ntr.append(r.n_trades)
        resultados[b] = statistics.median(tr)
        print(f"{b:>7.2f} {statistics.median(tr)*100:>19.1f}% {statistics.median(ntr):>14.0f}")

    melhor = max(resultados, key=resultados.get)
    print(f"\n  banda escolhida pelo TREINO: {melhor:.2f}")
    print(f"  (a janela de teste ainda nao foi olhada ate esta linha)\n")

    te, ntr = [], []
    for s in SEMENTES:
        sig = guardado[(melhor, s)]
        r = run_backtest(c[w:], sig[w:], CAPITAL, FEE, SLIP)
        te.append(r.total_return)
        ntr.append(r.n_trades)
    r_bh = buy_and_hold(c[w:], start=0, capital=CAPITAL, fee=FEE, slippage=SLIP)
    print(f"  TESTE 2025/26 com banda {melhor:.2f}: mediana {statistics.median(te)*100:+.1f}%  "
          f"pior {min(te)*100:+.1f}%  melhor {max(te)*100:+.1f}%")
    print(f"    trades medianos {statistics.median(ntr):.0f}   "
          f"venceram o buy and hold: {sum(1 for x in te if x > r_bh.total_return)}/10")
    print(f"  buy and hold: {r_bh.total_return*100:+.1f}%")


if __name__ == "__main__":
    main()
