"""O mecanismo do livro: stop, alvo 1:2 ou mais, e 3% de risco por operacao.

Controle indispensavel: as MESMAS regras aplicadas a entradas ALEATORIAS, com
a mesma frequencia. Numa caminhada aleatoria o stop de 1R e atingido cerca de
duas vezes mais que o alvo de 2R, entao a expectativa do bracket sozinho e
zero. Se o modelo nao superar o sorteio, a vantagem nao vem dele.
"""

import json
import random
import statistics
import sys

from backtest.data import load
from backtest.bracket_engine import rodar_bracket
from backtest.book_features import WARMUP

DESDE = "2025-01-01"
SEMENTES = [0, 1, 2, 3, 4]
# configuracoes ditadas pelo livro: stop 20%+ para swing, alvo 2x ou 3x
CONFIGS = [(0.10, 2.0), (0.10, 3.0), (0.20, 2.0), (0.20, 3.0), (0.30, 2.0)]


def sinais_modelo(inst, s):
    return json.load(open(f"results/sinais_deep/{inst}_h20_b0_s{s}.json"))


def sinais_sempre_pronto(n):
    """Sempre disposto a entrar. Com saida so por stop/alvo, isso produz
    operacoes encadeadas e torna a comparacao por R medio justa: a metrica
    e por operacao, nao depende de quantas houve."""
    return [1] * n


def sinais_embaralhados(sig_modelo, rng):
    """Mesmas entradas do modelo, redistribuidas ao acaso no tempo."""
    corpo = sig_modelo[WARMUP:]
    emb = corpo[:]
    rng.shuffle(emb)
    return sig_modelo[:WARMUP] + emb


def resumo(r):
    return (f"{r.total_return*100:>8.1f}% {r.final:>10,.0f} {r.n_trades:>7} "
            f"{r.win_rate*100:>7.1f}% {r.r_medio:>+7.2f}R {r.ganho_medio:>+6.2f} "
            f"{r.perda_media:>+6.2f} {r.max_drawdown*100:>7.1f}%")


def main():
    insts = [a for a in sys.argv[1:] if "USDT" in a] or ["BTC-USDT", "ETH-USDT"]
    for inst in insts:
        c = load(inst)
        tudo = "--tudo" in sys.argv
        i0 = WARMUP if tudo else next(i for i, x in enumerate(c) if x.date >= DESDE) - 1
        janela = f"{c[i0].date} a {c[-1].date}"
        print(f"\n{'='*104}\n{inst}  {janela} com stop, alvo e 3% de risco "
              f"(regras do livro)\n{'='*104}")
        print(f"{'config':>16} {'retorno':>8} {'  final':>10} {'trades':>7} "
              f"{'acerto':>8} {'R medio':>8} {'ganho':>6} {'perda':>6} {'dd':>8}")
        for stop, rr in CONFIGS:
            rs = []
            for s in SEMENTES:
                sg = sinais_modelo(inst, s)
                rs.append(rodar_bracket(c[i0:], sg[i0:], 10000, 0.001, 0.0005,
                                        stop_pct=stop, rr=rr, sair_por_sinal=False))
            med = sorted(rs, key=lambda r: r.r_medio)[len(rs) // 2]
            print(f"  modelo {stop:.0%}/{rr:.0f}x {resumo(med)}")

            base = rodar_bracket(c[i0:], sinais_sempre_pronto(len(c))[i0:], 10000,
                                 0.001, 0.0005, stop_pct=stop, rr=rr,
                                 sair_por_sinal=False)
            print(f"  sempre pronto    {resumo(base)}")

            ra = []
            for k in range(20):
                rng = random.Random(1000 + k)
                sg = sinais_embaralhados(sinais_modelo(inst, SEMENTES[k % len(SEMENTES)]), rng)
                ra.append(rodar_bracket(c[i0:], sg[i0:], 10000, 0.001, 0.0005,
                                        stop_pct=stop, rr=rr, sair_por_sinal=False))
            mr = statistics.median(r.r_medio for r in ra)
            venceu = sum(1 for r in ra if r.r_medio >= med.r_medio)
            print(f"  entradas sorteadas {statistics.median(r.total_return for r in ra)*100:>6.1f}% "
                  f"{'':10} {statistics.median(r.n_trades for r in ra):>7.0f} "
                  f"{statistics.median(r.win_rate for r in ra)*100:>7.1f}% {mr:>+7.2f}R"
                  f"   <- sorteios >= modelo: {venceu}/20\n")


if __name__ == "__main__":
    main()
