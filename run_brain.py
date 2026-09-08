"""Cerebro solido x cerebro plastico, com e sem memoria, em 2025/26.

Quatro bracos, todos partindo do mesmo treino em 2018-2024:

  A congelado  sem memoria   pesos param em 2025-01-01
  B congelado  com memoria
  C plastico   sem memoria   pesos seguem treinando por 2025/26
  D plastico   com memoria   <- a arquitetura que o usuario propos

Roda varias sementes: resultado de semente unica nao diz nada.
"""

import statistics
import sys

from backtest.data import load
from backtest.engine import ema, ema_cross_signals, run_backtest, buy_and_hold
from backtest.online_brain import rodar
from backtest.online_brain import conjunto_features

CAPITAL, FEE, SLIP = 10000.0, 0.001, 0.0005
DESDE = "2025-01-01"
SEMENTES = list(range(10))
BRACOS = [("A congelado s/ memoria", True, False),
          ("B congelado c/ memoria", True, True),
          ("C plastico   s/ memoria", False, False),
          ("D plastico   c/ memoria", False, True)]


def main():
    only = [a for a in sys.argv[1:] if "USDT" in a] or ["BTC-USDT", "ETH-USDT"]
    conjunto = "livro" if "--livro" in sys.argv else "basico"
    _, warmup = conjunto_features(conjunto)
    for inst in only:
        c = load(inst)
        e = ema([x.close for x in c], 9)
        idx = next(i for i, x in enumerate(c) if x.date >= DESDE)
        w = idx - 1

        print(f"\n{'='*74}\n{inst}  janela {c[idx].date} a {c[-1].date}  "
              f"({len(SEMENTES)} sementes, features: {conjunto})\n{'='*74}")

        se, _ = ema_cross_signals(c, 9)
        se = list(se)
        se[w] = 1 if (e[w] is not None and c[w].close > e[w]) else 0
        r_ema = run_backtest(c[w:], se[w:], CAPITAL, FEE, SLIP)
        r_bh = buy_and_hold(c[w:], start=0, capital=CAPITAL, fee=FEE, slippage=SLIP)

        print(f"{'braco':<26} {'liquido':>9} {'BRUTO':>9} {'pior':>9} {'melhor':>9} "
              f"{'>bh':>5} {'trades':>7}")
        for nome, congelar, memoria in BRACOS:
            rets, brutos, trades = [], [], []
            for s in SEMENTES:
                sig, _ = rodar(c, e, warmup, congelar_em=DESDE if congelar else None,
                               usar_memoria=memoria, semente=s, conjunto=conjunto)
                r = run_backtest(c[w:], sig[w:], CAPITAL, FEE, SLIP)
                g = run_backtest(c[w:], sig[w:], CAPITAL, 0.0, 0.0)
                rets.append(r.total_return)
                brutos.append(g.total_return)
                trades.append(r.n_trades)
            venceu = sum(1 for x in rets if x > r_bh.total_return)
            print(f"{nome:<26} {statistics.median(rets)*100:>8.1f}% "
                  f"{statistics.median(brutos)*100:>8.1f}% "
                  f"{min(rets)*100:>8.1f}% {max(rets)*100:>8.1f}% "
                  f"{venceu:>3}/10 {statistics.median(trades):>7.0f}")

        g_ema = run_backtest(c[w:], se[w:], CAPITAL, 0.0, 0.0)
        g_bh = buy_and_hold(c[w:], start=0, capital=CAPITAL, fee=0.0, slippage=0.0)
        print(f"{'EMA 9':<26} {r_ema.total_return*100:>8.1f}% {g_ema.total_return*100:>8.1f}%")
        print(f"{'Buy and hold':<26} {r_bh.total_return*100:>8.1f}% {g_bh.total_return*100:>8.1f}%")


if __name__ == "__main__":
    main()
