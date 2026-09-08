"""Item 16: o ganho da EMA 9 a custo zero e escolha de momento ou so exposicao?

A EMA 9 sem custo rende +0,7% no BTC contra -14,2% de comprar e segurar. Mas
ela passa boa parte do tempo FORA do mercado, e num periodo de queda ficar
fora ja e vantagem por si so.

O controle certo nao e "aleatorio", e "aleatorio que fica fora a MESMA fracao
do tempo, com o MESMO numero de trocas". Se empatar, a EMA nao escolheu
momento nenhum: so reduziu exposicao.
"""

import random
import statistics

from backtest.data import load
from backtest.engine import ema, ema_cross_signals, run_backtest, buy_and_hold


def posicoes(candles, sinais, w):
    """Serie 0/1 de estar comprado, dia a dia, na janela."""
    pos, atual = [], 0
    for i in range(w, len(candles)):
        s = sinais[i - 1] if i > 0 else 0
        if s == 1:
            atual = 1
        elif s == -1:
            atual = 0
        pos.append(atual)
    return pos


def sinais_de_posicoes(pos, n, w):
    sig = [0] * n
    ant = 0
    for j, p in enumerate(pos):
        i = w + j
        if p != ant and i - 1 >= 0:
            sig[i - 1] = 1 if p == 1 else -1
        ant = p
    return sig


def aleatorio_casado(pos_ref, rng):
    """Mesma fracao de tempo comprado e mesmo numero de trocas, em ordem
    aleatoria: blocos embaralhados."""
    n = len(pos_ref)
    dentro = sum(pos_ref)
    trocas = sum(1 for i in range(1, n) if pos_ref[i] != pos_ref[i - 1])
    blocos = max(trocas // 2 + 1, 1)
    # distribui `dentro` dias comprado em `blocos` blocos posicionados ao acaso
    pos = [0] * n
    restante, colocados = dentro, 0
    for b in range(blocos):
        tam = max(1, round(restante / (blocos - b)))
        ini = rng.randrange(0, max(n - tam, 1))
        for k in range(ini, min(ini + tam, n)):
            if pos[k] == 0 and colocados < dentro:
                pos[k] = 1
                colocados += 1
        restante = dentro - colocados
    return pos


def main():
    for inst in ["BTC-USDT", "ETH-USDT"]:
        c = load(inst)
        e = ema([x.close for x in c], 9)
        i0 = next(k for k, x in enumerate(c) if x.date >= "2025-01-01")
        w = i0 - 1
        se, _ = ema_cross_signals(c, 9)
        se = list(se)
        se[w] = 1 if (e[w] is not None and c[w].close > e[w]) else 0

        pos = posicoes(c, se, w)
        frac = sum(pos) / len(pos)
        trocas = sum(1 for i in range(1, len(pos)) if pos[i] != pos[i - 1])
        real = run_backtest(c[w:], se[w:], 10000, 0.0, 0.0).total_return
        bh = buy_and_hold(c[w:], start=0, capital=10000, fee=0.0, slippage=0.0).total_return

        rng = random.Random(11)
        nulos = []
        for _ in range(500):
            p2 = aleatorio_casado(pos, rng)
            s2 = sinais_de_posicoes(p2, len(c), w)
            nulos.append(run_backtest(c[w:], s2[w:], 10000, 0.0, 0.0).total_return)
        nulos.sort()
        acima = sum(1 for x in nulos if x >= real)

        print(f"\n{inst}  2025/26, custo zero")
        print(f"  EMA 9: {real*100:+.1f}%   comprar e segurar: {bh*100:+.1f}%")
        print(f"  tempo comprado: {frac*100:.1f}%   trocas de posicao: {trocas}")
        print(f"  500 aleatorios com a MESMA exposicao e MESMO numero de trocas:")
        print(f"    mediana {statistics.median(nulos)*100:+.1f}%   "
              f"p10 {nulos[50]*100:+.1f}%   p90 {nulos[450]*100:+.1f}%")
        print(f"    {acima}/500 igualaram ou superaram a EMA  ->  p = {acima/500:.3f}")


if __name__ == "__main__":
    main()
