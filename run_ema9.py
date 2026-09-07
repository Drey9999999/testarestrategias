"""Backtest da EMA 9 no diario, BTC-USDT e ETH-USDT, dados reais (OKX spot)."""

import json
import os
import sys

from backtest.data import load
from backtest.engine import ema_cross_signals, run_backtest, buy_and_hold

CAPITAL = 10000.0
FEE = 0.001        # 0,1% por operacao
SLIP = 0.0005      # 0,05% por operacao
PERIOD = 9
ASSETS = ["BTC-USDT", "ETH-USDT"]


def pct(x):
    return f"{x * 100:,.1f}%".replace(",", ".")


def money(x):
    return f"R$ {x:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def main():
    refresh = "--refresh" in sys.argv
    rows, extra = [], []
    for inst in ASSETS:
        candles = load(inst, refresh=refresh)
        sig, _ = ema_cross_signals(candles, PERIOD)
        strat = run_backtest(candles, sig, CAPITAL, FEE, SLIP)
        # buy and hold entra no mesmo candle em que a estrategia ja poderia operar
        bh = buy_and_hold(candles, start=PERIOD, capital=CAPITAL, fee=FEE, slippage=SLIP)

        inicio = candles[PERIOD + 1].date
        fim = candles[-1].date
        rows.append({
            "ativo": inst, "inicio": inicio, "fim": fim, "candles": len(candles),
            "ret_ema": strat.total_return, "final_ema": strat.final_equity,
            "ret_bh": bh.total_return, "final_bh": bh.final_equity,
            "mdd_ema": strat.max_drawdown, "mdd_bh": bh.max_drawdown,
            "trades": strat.n_trades, "win_rate": strat.win_rate,
            "avg_pnl": strat.avg_trade_pnl, "avg_ret": strat.avg_trade_ret,
            "vencedores": sum(1 for t in strat.trades if t.pnl > 0),
        })
        extra.append((inst, strat))

    print(f"\nCapital inicial: {money(CAPITAL)} | taxa {FEE*100:.1f}%/op | "
          f"slippage {SLIP*100:.2f}%/op | EMA {PERIOD} no fechamento diario | "
          f"execucao na abertura do candle seguinte\n")
    print("| Ativo | Período | Retorno EMA 9 | Retorno buy and hold | Máximo drawdown | Nº de trades |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['ativo']} | {r['inicio']} a {r['fim']} | {pct(r['ret_ema'])} "
              f"| {pct(r['ret_bh'])} | {pct(r['mdd_ema'])} | {r['trades']} |")

    print("\nDetalhe por ativo (custos ja descontados):")
    for r in rows:
        print(f"\n  {r['ativo']}  ({r['candles']} candles diarios)")
        print(f"    EMA 9        : {money(CAPITAL)} -> {money(r['final_ema'])}  "
              f"({pct(r['ret_ema'])}), drawdown maximo {pct(r['mdd_ema'])}")
        print(f"    Buy and hold : {money(CAPITAL)} -> {money(r['final_bh'])}  "
              f"({pct(r['ret_bh'])}), drawdown maximo {pct(r['mdd_bh'])}")
        print(f"    Trades       : {r['trades']}  |  vencedores {r['vencedores']}  "
              f"|  taxa de acerto {r['win_rate']*100:.1f}%")
        print(f"    Lucro medio por trade: {money(r['avg_pnl'])}  "
              f"({r['avg_ret']*100:+.2f}% por trade)")

    os.makedirs("results", exist_ok=True)
    with open("results/ema9_daily.json", "w") as f:
        json.dump(rows, f, indent=2)
    for inst, strat in extra:
        with open(f"results/trades_{inst}.csv", "w") as f:
            f.write("entrada,preco_entrada,saida,preco_saida,pnl,retorno\n")
            for t in strat.trades:
                f.write(f"{t.entry_date},{t.entry_price:.4f},{t.exit_date},"
                        f"{t.exit_price:.4f},{t.pnl:.2f},{t.ret:.6f}\n")
        with open(f"results/equity_{inst}.csv", "w") as f:
            f.write("data,patrimonio\n")
            for d, eq in strat.equity:
                f.write(f"{d},{eq:.2f}\n")


if __name__ == "__main__":
    main()
