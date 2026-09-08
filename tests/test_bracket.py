"""Testes do motor com stop, alvo e dimensionamento por risco."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.engine import Candle
from backtest.bracket_engine import rodar_bracket

def ap(a,b,tol=1e-6): assert abs(a-b)<tol, f"{a} != {b}"

def t_stop():
    # entra a 100, stop 20% = 80. Candle seguinte fura 80.
    c=[Candle("d1",100,100,100,100), Candle("d2",100,105,95,100),
       Candle("d3",100,100,70,75)]
    r=rodar_bracket(c,[1,0,0],10000,fee=0,slippage=0,stop_pct=0.20,rr=2,risco_por_trade=0.03)
    t=r.trades[0]
    assert t.motivo=="stop", t.motivo
    ap(t.preco_saida, 80.0)
    ap(t.r_multiplo, -1.0)          # perdeu exatamente 1R
    ap(t.pnl, -300.0)               # 3% de 10.000
    print("ok stop = -1R e perde 3% da conta")

def t_alvo():
    # stop 20% -> alvo 40% (rr=2). Candle seguinte atinge 140.
    c=[Candle("d1",100,100,100,100), Candle("d2",100,145,95,140)]
    r=rodar_bracket(c,[1,0],10000,fee=0,slippage=0,stop_pct=0.20,rr=2,risco_por_trade=0.03)
    t=r.trades[0]
    assert t.motivo=="alvo", t.motivo
    ap(t.preco_saida, 140.0)
    ap(t.r_multiplo, 2.0)           # ganhou 2R
    ap(t.pnl, 600.0)
    print("ok alvo = +2R e ganha 6% da conta")

def t_stop_no_dia_da_entrada():
    c=[Candle("d1",100,100,100,100), Candle("d2",100,101,70,75)]
    r=rodar_bracket(c,[1,0],10000,fee=0,slippage=0,stop_pct=0.20,rr=2)
    assert r.trades[0].motivo=="stop" and r.trades[0].saida=="d2"
    print("ok stop verificado no proprio candle da entrada")

def t_ambos_no_mesmo_candle_assume_stop():
    c=[Candle("d1",100,100,100,100), Candle("d2",100,150,70,120)]
    r=rodar_bracket(c,[1,0],10000,fee=0,slippage=0,stop_pct=0.20,rr=2)
    assert r.trades[0].motivo=="stop", "deve assumir a hipotese pessimista"
    print("ok stop e alvo no mesmo candle -> assume stop")

def t_sem_alavancagem():
    # stop pequeno pediria posicao maior que a conta; deve ser limitada
    # candles que NAO encostam no stop de 99 nem no alvo
    c=[Candle("d1",100,100,100,100), Candle("d2",100,100.5,99.6,100),
       Candle("d3",100,100.5,99.6,100)]
    r=rodar_bracket(c,[1,0,0],10000,fee=0,slippage=0,stop_pct=0.01,rr=2,risco_por_trade=0.03)
    # 3% de risco / stop de 1% pediria 3x a conta; sem alavancagem fica em 1x
    ap(r.equity[1][1], 10000.0)
    assert not any(t.motivo in ("stop","alvo") for t in r.trades)
    print("ok posicao limitada ao patrimonio (sem alavancagem)")

def t_contabilidade():
    c=[Candle("d1",100,100,100,100), Candle("d2",100,145,95,140)]
    r=rodar_bracket(c,[1,0],10000,fee=0.001,slippage=0.0005,stop_pct=0.20,rr=2)
    ap(r.final, r.capital + sum(t.pnl for t in r.trades))
    print("ok patrimonio final = capital + soma dos pnl")

for f in [t_stop,t_alvo,t_stop_no_dia_da_entrada,t_ambos_no_mesmo_candle_assume_stop,
          t_sem_alavancagem,t_contabilidade]:
    f()
print("\nTODOS OS TESTES DO MOTOR BRACKET PASSARAM")
