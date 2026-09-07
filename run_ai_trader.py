"""Simula 2025/26 com um trader autonomo de IA que le a foto do grafico.

Compara, na mesma janela e com os mesmos custos:
  IA de visao (Qwen2-VL-2B local)  x  EMA 9  x  buy and hold
"""

import os
import sys

from backtest.data import load
from backtest.charts import render_series
from backtest.ai_trader import (score_series, decisions_to_signals,
                                decisions_to_signals_relative)
from backtest.engine import ema_cross_signals, run_backtest, buy_and_hold

CAPITAL, FEE, SLIP = 10000.0, 0.001, 0.0005
LOOKBACK = 60
DESDE = "2025-01-01"
ASSETS = ["BTC-USDT", "ETH-USDT"]


def money(x):
    return f"R$ {x:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def metricas(nome, r):
    return (f"    {nome:14s}: {money(CAPITAL)} -> {money(r.final_equity)}  "
            f"({r.total_return*100:+.1f}%), dd {r.max_drawdown*100:.1f}%, "
            f"{r.n_trades} trades, acerto {r.win_rate*100:.1f}%, "
            f"medio {money(r.avg_trade_pnl)} ({r.avg_trade_ret*100:+.2f}%)")


def main():
    only = [a for a in sys.argv[1:] if a in ASSETS] or ASSETS
    linhas = []
    for inst in only:
        candles = load(inst)
        idx = next(i for i, c in enumerate(candles) if c.date >= DESDE)
        w = idx - 1                       # barra zero: decide a entrada do 1o dia da janela
        indices = list(range(w, len(candles)))

        print(f"\n[{inst}] renderizando {len(indices)} graficos "
              f"({candles[w].date} .. {candles[-1].date})", flush=True)
        charts = render_series(candles, indices, f"charts/{inst}", lookback=LOOKBACK)

        print(f"[{inst}] rodando o modelo de visao em {len(charts)} imagens", flush=True)
        os.makedirs("results", exist_ok=True)
        dec = score_series(charts, f"results/ai_scores_{inst}.csv")

        sig_ia = decisions_to_signals(len(candles), dec)
        ia = run_backtest(candles[w:], sig_ia[w:], CAPITAL, FEE, SLIP)

        sig_rel = decisions_to_signals_relative(len(candles), dec)
        ia_rel = run_backtest(candles[w:], sig_rel[w:], CAPITAL, FEE, SLIP)

        sig_ema, e = ema_cross_signals(candles, 9)
        sig_ema = list(sig_ema)
        sig_ema[w] = 1 if (e[w] is not None and candles[w].close > e[w]) else 0
        ema = run_backtest(candles[w:], sig_ema[w:], CAPITAL, FEE, SLIP)

        bh = buy_and_hold(candles[w:], start=0, capital=CAPITAL, fee=FEE, slippage=SLIP)

        cont = {}
        for r in dec.values():
            cont[r["decision"]] = cont.get(r["decision"], 0) + 1
        linhas.append((inst, candles[w + 1].date, candles[-1].date, ia, ia_rel, ema, bh, cont))

        with open(f"results/equity_ia_{inst}.csv", "w") as f:
            f.write("data,patrimonio\n")
            for d, eq in ia.equity:
                f.write(f"{d},{eq:.2f}\n")

    print("\n| Ativo | Período | IA literal | IA relativa | EMA 9 | Buy and hold |")
    print("|---|---|---|---|---|---|")
    for inst, ini, fim, ia, ia_rel, ema, bh, _ in linhas:
        print(f"| {inst} | {ini} a {fim} | {ia.total_return*100:+.1f}% | {ia_rel.total_return*100:+.1f}% "
              f"| {ema.total_return*100:+.1f}% | {bh.total_return*100:+.1f}% |")

    print("\nDetalhe (custos ja descontados):")
    for inst, ini, fim, ia, ia_rel, ema, bh, cont in linhas:
        print(f"\n  {inst}  {ini} a {fim}")
        print(metricas("IA literal", ia))
        print(metricas("IA relativa", ia_rel))
        print(metricas("EMA 9", ema))
        print(metricas("Buy and hold", bh))
        tot = sum(cont.values())
        print("    respostas do modelo: " +
              ", ".join(f"{k}={v} ({v/tot*100:.0f}%)" for k, v in sorted(cont.items())))


if __name__ == "__main__":
    main()
