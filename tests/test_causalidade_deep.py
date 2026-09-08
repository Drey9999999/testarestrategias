"""Prova de que a cabeca de treino profundo nao enxerga o futuro."""

import copy, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.data import load
from backtest.deep_brain import rodar
from backtest.book_features import WARMUP

CORTE = "2023-01-01"
H = 10

c = load("BTC-USDT")
corte = next(i for i, x in enumerate(c) if x.date >= CORTE)
s1, d1 = rodar(c, WARMUP, horizonte=H, semente=0)

random.seed(7)
c2 = copy.deepcopy(c)
for i in range(corte, len(c2)):
    f = random.uniform(0.5, 2.0)
    c2[i].open *= f; c2[i].high *= f; c2[i].low *= f; c2[i].close *= f
    c2[i].volume *= random.uniform(0.3, 3.0)
s2, d2 = rodar(c2, WARMUP, horizonte=H, semente=0)

antes = [(a, b) for a, b in zip(d1, d2) if a["data"] < CORTE]
difs = [a["data"] for a, b in antes if a["posicao"] != b["posicao"] or abs(a["p"] - b["p"]) > 1e-12]
depois = sum(1 for a, b in zip(d1, d2) if a["data"] >= CORTE and a["posicao"] != b["posicao"])

print(f"horizonte H={H}")
print(f"decisoes anteriores a {CORTE}: {len(antes)}")
print(f"mudaram ao destruir o futuro: {len(difs)}")
print(f"decisoes posteriores que mudaram: {depois}")
assert len(difs) == 0, f"VAZAMENTO em {difs[:5]}"
assert depois > 0, "teste cego"
print("\nSEM VAZAMENTO DE FUTURO")
