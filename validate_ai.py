"""Testa se o resultado da IA e habilidade ou sorte.

Dois nulos, e a diferenca entre eles importa:

1. Embaralhamento: quebra a ordem dos scores. Destroi tambem a autocorrelacao
   do sinal, entao as versoes nulas trocam de posicao muito mais e sangram em
   taxa. O p-valor sai otimista porque o teste acaba medindo "o sinal e suave",
   nao "o sinal acerta".

2. Deslocamento circular: rotaciona a serie de scores contra a serie de precos.
   Preserva a autocorrelacao e a frequencia de operacao, e quebra apenas o
   alinhamento com as datas reais. E o teste honesto.
"""

import csv
import random
import statistics

from backtest.data import load
from backtest.engine import run_backtest

DESDE = "2025-01-01"
MIN_BASE = 20


def avalia(candles, w, indices, scores):
    sig = [0] * len(candles)
    passado = []
    for i, s in zip(indices, scores):
        sig[i] = (1 if s > statistics.median(passado) else -1) if len(passado) >= MIN_BASE else -1
        passado.append(s)
    r = run_backtest(candles[w:], sig[w:], 10000, 0.001, 0.0005)
    return r.total_return, r.n_trades


def main():
    random.seed(42)
    for inst in ["BTC-USDT", "ETH-USDT"]:
        c = load(inst)
        idx = next(i for i, x in enumerate(c) if x.date >= DESDE)
        w = idx - 1
        rows = {int(r["i"]): r for r in csv.DictReader(open(f"results/ai_scores_{inst}.csv"))}
        indices = sorted(rows)
        sc = [float(rows[i]["p_buy"]) - float(rows[i]["p_sell"]) for i in indices]
        real, ntr = avalia(c, w, indices, sc)
        print(f"\n{inst}: retorno real {real*100:+.1f}% com {ntr} trades")

        emb = []
        for _ in range(2000):
            s = sc[:]
            random.shuffle(s)
            emb.append(avalia(c, w, indices, s)[0])
        p_emb = sum(1 for x in emb if x >= real) / len(emb)
        print(f"  nulo embaralhado    : mediana {statistics.median(emb)*100:+7.1f}%  p={p_emb:.3f}")

        des = [avalia(c, w, indices, sc[k:] + sc[:k]) for k in range(10, len(sc) - 10)]
        rets = sorted(x[0] for x in des)
        p_des = sum(1 for x in rets if x >= real) / len(rets)
        print(f"  nulo deslocado      : mediana {statistics.median(rets)*100:+7.1f}%  "
              f"max {rets[-1]*100:+.1f}%  trades medianos {statistics.median(x[1] for x in des):.0f}  "
              f"p={p_des:.3f}")
        print(f"  -> {'NAO passa' if p_des > 0.05 else 'passa'} no teste honesto (5%)")


if __name__ == "__main__":
    main()
