"""Mais treino leva a algum lugar? A curva de aprendizado responde.

Compara duas coisas em funcao da quantidade de treino:

  - ACERTO DENTRO DA AMOSTRA: o modelo final aplicado aos dados em que ele
    treinou. Mede capacidade de memorizar.
  - ACERTO PREVENDO: o acerto direcional das decisoes tomadas no dia a dia,
    quando o rotulo ainda nao existia. Mede capacidade de prever.

Se o primeiro sobe e o segundo fica em 50%, mais treino nao esta aprendendo o
mercado — esta decorando ruido. Se os dois sobem juntos, ha o que aprender e
vale insistir.
"""

import json
import os
import statistics
import sys

from backtest.data import load
from backtest.deep_brain import rodar
from backtest.book_features import WARMUP
from backtest.engine import run_backtest

FIM_TREINO = "2023-01-01"
FIM_VALID = "2025-01-01"
H = 20
SEMENTES = [0, 1, 2]

# (passos_por_dia, epocas_profundas, intervalo) -> do nada ao exaustivo
INTENSIDADES = [
    ("nenhum",        0, 0, 0),
    ("minimo",        1, 0, 0),
    ("leve",          2, 2, 90),
    ("padrao",        4, 8, 60),
    ("pesado",        8, 20, 60),
    ("exaustivo",    16, 40, 30),
]


def main():
    inst = sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT"
    c = load(inst)
    i_val = next(i for i, x in enumerate(c) if x.date >= FIM_TREINO)
    i_tes = next(i for i, x in enumerate(c) if x.date >= FIM_VALID)

    print(f"\n{inst}  curva de aprendizado (horizonte {H} dias, {len(SEMENTES)} sementes)\n")
    print(f"{'treino':>11} {'epocas':>8} {'acerto DENTRO':>14} {'acerto PREVENDO':>17} "
          f"{'prevendo 25/26':>15} {'retorno 25/26':>14}")
    for nome, ppd, ep, iv in INTENSIDADES:
        dentro, prev, prev_t, ret = [], [], [], []
        eps = []
        for s in SEMENTES:
            cp = f"results/curva/{inst}_{nome}_s{s}.json"
            os.makedirs("results/curva", exist_ok=True)
            if os.path.exists(cp):
                g = json.load(open(cp))
                sig, info = g["sig"], g["info"]
            else:
                sig, info = rodar(c, WARMUP, horizonte=H, semente=s, passos_por_dia=ppd,
                                  epocas_profundas=ep, intervalo=iv)
                json.dump({"sig": sig, "info": info}, open(cp, "w"))
            d = info["diario"]
            dentro.append(info["acerto_dentro"] or 0.5)
            eps.append(info["epocas"])
            val = [x["acertou"] for x in d if x["acertou"] is not None]
            tes = [x["acertou"] for x in d
                   if x["acertou"] is not None and x["data"] >= FIM_VALID]
            prev.append(sum(val) / len(val))
            prev_t.append(sum(tes) / len(tes) if tes else 0.5)
            ret.append(run_backtest(c[i_tes-1:], sig[i_tes-1:], 10000, 0.001, 0.0005).total_return)
        print(f"{nome:>11} {statistics.median(eps):>8.0f} "
              f"{statistics.median(dentro)*100:>13.1f}% "
              f"{statistics.median(prev)*100:>16.1f}% "
              f"{statistics.median(prev_t)*100:>14.1f}% "
              f"{statistics.median(ret)*100:>13.1f}%")

    print("\n  acerto de 50% = moeda. 'DENTRO' mede memorizacao; "
          "'PREVENDO' mede previsao real.")


if __name__ == "__main__":
    main()
