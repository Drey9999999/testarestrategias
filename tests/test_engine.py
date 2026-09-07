"""Testes de sanidade do motor: EMA, custos, execucao no candle seguinte."""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import Candle, ema, run_backtest, buy_and_hold, ema_cross_signals


def approx(a, b, tol=1e-9):
    assert abs(a - b) < tol, f"{a} != {b}"


def test_ema():
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    e = ema(v, 9)
    assert e[:8] == [None] * 8
    approx(e[8], 5.0)                       # SMA(1..9)
    approx(e[9], 10 * 0.2 + 5.0 * 0.8)      # k = 2/10
    print("ok ema")


def test_execucao_no_proximo_open_e_custos():
    c = [Candle("d1", 100, 100, 100, 100),
         Candle("d2", 200, 200, 200, 200),
         Candle("d3", 300, 300, 300, 300)]
    sig = [1, -1, 0]                        # compra sinalizada em d1, venda em d2
    r = run_backtest(c, sig, capital=10000, fee=0.001, slippage=0.0005)
    t = r.trades[0]
    approx(t.entry_date == "d2" and 1 or 0, 1)   # executou na abertura de d2
    approx(t.exit_date == "d3" and 1 or 0, 1)    # executou na abertura de d3
    approx(t.entry_price, 200 * 1.0005)
    approx(t.exit_price, 300 * 0.9995)
    gross_in = 10000 / 1.001                     # taxa 0,1% na entrada
    qty = gross_in / (200 * 1.0005)
    approx(t.qty, qty)
    saida = qty * 300 * 0.9995
    approx(r.final_equity, saida * 0.999)        # taxa 0,1% na saida
    approx(t.pnl, r.final_equity - 10000)
    print("ok execucao/custos")


def test_posicao_aberta_liquidada_no_fim():
    c = [Candle("d1", 100, 100, 100, 100),
         Candle("d2", 100, 100, 100, 100),
         Candle("d3", 150, 150, 150, 150)]
    r = run_backtest(c, [1, 0, 0], capital=10000)
    assert r.n_trades == 1 and r.trades[0].exit_date == "d3"
    approx(r.final_equity, r.equity[-1][1])
    print("ok liquidacao final")


def test_drawdown():
    c = [Candle("d1", 100, 100, 100, 100),
         Candle("d2", 100, 100, 100, 100),
         Candle("d3", 100, 100, 100, 50),
         Candle("d4", 50, 50, 50, 100)]
    r = run_backtest(c, [1, 0, 0, 0], capital=10000, fee=0, slippage=0)
    approx(r.max_drawdown, -0.5)             # 100 -> 50 no meio do caminho
    print("ok drawdown")


def test_buy_and_hold_bate_com_precos():
    c = [Candle("d1", 100, 100, 100, 100),
         Candle("d2", 100, 100, 100, 100),
         Candle("d3", 200, 200, 200, 200)]
    r = buy_and_hold(c, start=0, capital=10000, fee=0, slippage=0)
    approx(r.final_equity, 20000.0)          # entrou em d2 a 100, saiu a 200
    print("ok buy and hold")


def test_sinais_de_cruzamento():
    closes = [10, 10, 10, 10, 10, 10, 10, 10, 10, 20, 5]
    c = [Candle(f"d{i}", x, x, x, x) for i, x in enumerate(closes)]
    sig, e = ema_cross_signals(c, 9)
    approx(e[8], 10.0)
    assert sig[9] == 1, sig                  # fecha acima da EMA vindo de <=
    assert sig[10] == -1, sig                # fecha abaixo vindo de >=
    print("ok sinais")


for fn in [test_ema, test_execucao_no_proximo_open_e_custos,
           test_posicao_aberta_liquidada_no_fim, test_drawdown,
           test_buy_and_hold_bate_com_precos, test_sinais_de_cruzamento]:
    fn()
print("\nTODOS OS TESTES PASSARAM")
