"""Prova de que a carteira transversal nao enxerga o futuro."""
import sys, os, copy, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest.portfolio import carregar, rodar_carteira

CORTE = "2024-01-01"
por_data, opens = carregar()
r1 = rodar_carteira(por_data, opens, inicio="2021-01-01", semente=0)

# destroi o futuro: features e precos aleatorios a partir do corte
random.seed(3)
pd2 = {d: [dict(x) for x in v] for d, v in por_data.items()}
for d, linhas in pd2.items():
    if d >= CORTE:
        for r in linhas:
            r["x"] = [random.uniform(-3, 3) for _ in r["x"]]
            r["ret"] = random.uniform(-0.5, 0.5)
op2 = copy.deepcopy(opens)
for inst, o in op2.items():
    for d in o:
        if d >= CORTE:
            o[d] *= random.uniform(0.5, 2.0)
r2 = rodar_carteira(pd2, op2, inicio="2021-01-01", semente=0)

a1 = [h for h in r1["hist"] if h["data"] < CORTE]
a2 = [h for h in r2["hist"] if h["data"] < CORTE]
difs = [x["data"] for x, y in zip(a1, a2) if x["escolhidos"] != y["escolhidos"]]
dep = sum(1 for x, y in zip([h for h in r1["hist"] if h["data"] >= CORTE],
                            [h for h in r2["hist"] if h["data"] >= CORTE])
          if x["escolhidos"] != y["escolhidos"])
print(f"rebalanceamentos antes de {CORTE}: {len(a1)}")
print(f"escolhas que mudaram ao destruir o futuro: {len(difs)}")
print(f"escolhas posteriores que mudaram: {dep}")
assert not difs, f"VAZAMENTO em {difs[:5]}"
assert dep > 0, "teste cego"
print("\nSEM VAZAMENTO DE FUTURO")
