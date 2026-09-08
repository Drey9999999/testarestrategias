"""Experimento com tres janelas separadas, para o resultado significar algo.

  TREINO     2018-08-10 .. 2022-12-31   a cabeca aprende
  VALIDACAO  2023-01-01 .. 2024-12-31   escolhe-se a configuracao AQUI
  TESTE      2025-01-01 .. 2026-09-06   olhado uma unica vez, no fim

Os sinais de cada rodada ficam em cache no disco: rodar e caro, avaliar e
barato, e a maquina deste ambiente congela quando a sessao fica ociosa — o
cache torna o trabalho retomavel.

O foco do relatorio e o que o usuario pediu: quanto o conjunto de todas as
operacoes lucrou, e quanto sobra por operacao depois do custo.
"""

import json
import os
import statistics
import sys

from backtest.data import load
from backtest.deep_brain import rodar
from backtest.book_features import WARMUP
from backtest.engine import run_backtest, buy_and_hold

CAPITAL, FEE, SLIP = 10000.0, 0.001, 0.0005
FIM_TREINO = "2023-01-01"
FIM_VALID = "2025-01-01"
CACHE = "results/sinais_deep"

HORIZONTES = [5, 10, 20]
BANDAS = [0.00, 0.08]
HOLDS = [0]


def _grade():
    """Permite ampliar a grade pela linha de comando sem editar o arquivo."""
    import sys as _s
    h, b, hd = HORIZONTES, BANDAS, HOLDS
    for a in _s.argv[1:]:
        if a.startswith("--h="):
            h = [int(x) for x in a.split("=")[1].split(",")]
        if a.startswith("--b="):
            b = [float(x) for x in a.split("=")[1].split(",")]
        if a.startswith("--hold="):
            hd = [int(x) for x in a.split("=")[1].split(",")]
    return h, b, hd
SEMENTES = [0, 1, 2, 3, 4]


def limites(c):
    i_val = next(i for i, x in enumerate(c) if x.date >= FIM_TREINO)
    i_tes = next(i for i, x in enumerate(c) if x.date >= FIM_VALID)
    return i_val, i_tes


def sinais(inst, c, h, banda, semente, hold=0):
    suf = f"_hold{hold}" if hold else ""
    p = f"{CACHE}/{inst}_h{h}_b{int(banda*100)}{suf}_s{semente}.json"
    if os.path.exists(p):
        return json.load(open(p))
    sig, _ = rodar(c, WARMUP, horizonte=h, banda=banda, semente=semente,
                   hold_minimo=hold)
    json.dump(sig, open(p, "w"))
    return sig


def metricas(c, sig, ini, fim):
    """Resultado do conjunto de operacoes na fatia [ini, fim)."""
    r = run_backtest(c[ini:fim], sig[ini:fim], CAPITAL, FEE, SLIP)
    g = run_backtest(c[ini:fim], sig[ini:fim], CAPITAL, 0.0, 0.0)
    n = r.n_trades
    return {
        "ret": r.total_return, "bruto": g.total_return, "final": r.final_equity,
        "trades": n, "acerto": r.win_rate, "medio": r.avg_trade_pnl,
        "medio_pct": r.avg_trade_ret,
        "medio_bruto_pct": (g.avg_trade_ret if n else 0.0),
        "dd": r.max_drawdown,
        "lucro_total": r.final_equity - CAPITAL,
    }


def main():
    fase = "selecao"
    for a in sys.argv[1:]:
        if a.startswith("--fase="):
            fase = a.split("=")[1]
    insts = [a for a in sys.argv[1:] if "USDT" in a] or ["BTC-USDT", "ETH-USDT"]

    global HORIZONTES, BANDAS, HOLDS
    HORIZONTES, BANDAS, HOLDS = _grade()

    for inst in insts:
        c = load(inst)
        i_val, i_tes = limites(c)

        if fase == "teste":
            fase_teste(inst, c, i_val, i_tes)
            continue

        if fase == "selecao":
            print(f"\n{'='*88}\n{inst}  SELECAO (teste nao e olhado)\n{'='*88}")
            print(f"{'config':>14} {'treino':>10} {'valid':>10} {'val bruto':>11} "
                  f"{'trades':>7} {'medio/op':>10} {'bruto/op':>10}")
            bh_tr = buy_and_hold(c[WARMUP:i_val], start=0, capital=CAPITAL, fee=FEE, slippage=SLIP)
            bh_va = buy_and_hold(c[i_val-1:i_tes], start=0, capital=CAPITAL, fee=FEE, slippage=SLIP)
            for h in HORIZONTES:
              for hd in HOLDS:
                for b in BANDAS:
                    tr, va, vb, nt, mp, mb = [], [], [], [], [], []
                    for s in SEMENTES:
                        sg = sinais(inst, c, h, b, s, hd)
                        m1 = metricas(c, sg, WARMUP, i_val)
                        m2 = metricas(c, sg, i_val - 1, i_tes)
                        tr.append(m1["ret"]); va.append(m2["ret"]); vb.append(m2["bruto"])
                        nt.append(m2["trades"]); mp.append(m2["medio_pct"])
                        mb.append(m2["medio_bruto_pct"])
                    print(f"  h={h:<2} b={b:.2f} hold={hd:<2} {statistics.median(tr)*100:>9.1f}% "
                          f"{statistics.median(va)*100:>9.1f}% {statistics.median(vb)*100:>10.1f}% "
                          f"{statistics.median(nt):>7.0f} {statistics.median(mp)*100:>9.2f}% "
                          f"{statistics.median(mb)*100:>9.2f}%")
            print(f"  {'(comprado sempre)':<14} {bh_tr.total_return*100:>9.1f}% "
                  f"{bh_va.total_return*100:>9.1f}%   <- referencia: quanto rendia sem decidir nada")


def fase_teste(inst, c, i_val, i_tes):
    """Escolhe a configuracao pela VALIDACAO e so entao olha o teste, uma vez."""
    import random
    tabela = {}
    for h in HORIZONTES:
        for b in BANDAS:
            va = [metricas(c, sinais(inst, c, h, b, s), i_val - 1, i_tes)["ret"]
                  for s in SEMENTES]
            tabela[(h, b)] = statistics.median(va)
    h, b = max(tabela, key=tabela.get)
    print(f"\n{'='*88}\n{inst}  TESTE 2025/26  (config escolhida pela validacao: "
          f"h={h}, banda={b:.2f})\n{'='*88}")

    linhas = [metricas(c, sinais(inst, c, h, b, s), i_tes - 1, len(c)) for s in SEMENTES]
    lucro = [m["lucro_total"] for m in linhas]
    print(f"{'semente':>8} {'lucro total':>14} {'retorno':>9} {'bruto':>9} "
          f"{'trades':>7} {'acerto':>8} {'lucro/op':>10} {'dd':>8}")
    for s, m in zip(SEMENTES, linhas):
        print(f"{s:>8} {m['lucro_total']:>13,.0f} {m['ret']*100:>8.1f}% {m['bruto']*100:>8.1f}% "
              f"{m['trades']:>7} {m['acerto']*100:>7.1f}% {m['medio']:>9,.0f} {m['dd']*100:>7.1f}%")
    print(f"{'MEDIANA':>8} {statistics.median(lucro):>13,.0f} "
          f"{statistics.median([m['ret'] for m in linhas])*100:>8.1f}% "
          f"{statistics.median([m['bruto'] for m in linhas])*100:>8.1f}% "
          f"{statistics.median([m['trades'] for m in linhas]):>7.0f} "
          f"{statistics.median([m['acerto'] for m in linhas])*100:>7.1f}% "
          f"{statistics.median([m['medio'] for m in linhas]):>9,.0f} "
          f"{statistics.median([m['dd'] for m in linhas])*100:>7.1f}%")
    bh = buy_and_hold(c[i_tes-1:], start=0, capital=CAPITAL, fee=FEE, slippage=SLIP)
    print(f"  referencia comprado sempre: lucro {bh.final_equity-CAPITAL:,.0f} "
          f"({bh.total_return*100:+.1f}%)")

    # teste nulo: desloca o sinal contra os precos, preservando giro e suavidade
    print("\n  teste nulo (deslocamento circular do sinal):")
    for s in SEMENTES[:3]:
        sg = sinais(inst, c, h, b, s)[i_tes - 1:]
        real = metricas(c, sinais(inst, c, h, b, s), i_tes - 1, len(c))["ret"]
        nulos = []
        for k in range(10, len(sg) - 10):
            d = sg[k:] + sg[:k]
            nulos.append(run_backtest(c[i_tes-1:], d, CAPITAL, FEE, SLIP).total_return)
        pior = sum(1 for x in nulos if x >= real)
        print(f"    semente {s}: real {real*100:+7.1f}%  mediana nulo "
              f"{statistics.median(nulos)*100:+7.1f}%  p={pior/len(nulos):.3f}")


if __name__ == "__main__":
    main()
