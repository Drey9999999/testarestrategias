"""Prova de que a cabeca online nao enxerga o futuro.

Metodo: rodo a serie normal, depois destruo todos os candles a partir de uma
data e rodo de novo. Se alguma decisao ANTERIOR a essa data mudar, ha
vazamento. Se nenhuma mudar, o passado nao depende do futuro.
"""

import copy
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.data import load
from backtest.engine import ema
from backtest.online_brain import rodar
from backtest.online_brain import conjunto_features

CORTE = "2023-01-01"

c = load("BTC-USDT")
e = ema([x.close for x in c], 9)
corte = next(i for i, x in enumerate(c) if x.date >= CORTE)

CONJ = sys.argv[1] if len(sys.argv) > 1 else "basico"
_, WARMUP = conjunto_features(CONJ)
print(f"conjunto de features: {CONJ}")
s1, d1 = rodar(c, e, WARMUP, usar_memoria=True, conjunto=CONJ)

# destroi o futuro: precos aleatorios a partir do corte
random.seed(1)
c2 = copy.deepcopy(c)
for i in range(corte, len(c2)):
    f = random.uniform(0.5, 2.0)
    c2[i].open *= f; c2[i].high *= f; c2[i].low *= f; c2[i].close *= f
e2 = ema([x.close for x in c2], 9)
s2, d2 = rodar(c2, e2, WARMUP, usar_memoria=True, conjunto=CONJ)

antes = [(a, b) for a, b in zip(d1, d2) if a["data"] < CORTE]
difs = [a["data"] for a, b in antes if a["posicao"] != b["posicao"] or abs(a["p"] - b["p"]) > 1e-12]

print(f"decisoes anteriores a {CORTE}: {len(antes)}")
print(f"decisoes que mudaram ao destruir o futuro: {len(difs)}")
depois = sum(1 for a, b in zip(d1, d2) if a["data"] >= CORTE and a["posicao"] != b["posicao"])
print(f"decisoes posteriores que mudaram (tem que ser > 0, senao o teste e cego): {depois}")

assert len(difs) == 0, f"VAZAMENTO DE FUTURO em {difs[:5]}"
assert depois > 0, "teste cego: destruir o futuro nao mudou nada depois do corte"
print("\nSEM VAZAMENTO DE FUTURO")
