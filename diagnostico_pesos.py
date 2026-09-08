"""Mostra os pesos se movendo enquanto a cabeca decide e aprende."""

import sys

from backtest.data import load
from backtest.engine import ema
from backtest.online_brain import rodar
from backtest.features import WARMUP, PRICE_NAMES, MEMORY_NAMES

inst = sys.argv[1] if len(sys.argv) > 1 else "BTC-USDT"
c = load(inst)
e = ema([x.close for x in c], 9)
sinais, diario = rodar(c, e, WARMUP, usar_memoria=True)

print(f"{inst}: {len(diario)} decisoes, de {diario[0]['data']} a {diario[-1]['data']}\n")
print("evolucao dos pesos da camada de entrada:")
print(f"{'decisao':>8} {'data':>12} {'norma':>8} {'passo':>9} {'p(subir)':>9} {'pos':>4}")
for k in [0, 1, 5, 10, 30, 50, 100, 200, 400, 800, 1600, len(diario)-1]:
    if k >= len(diario): continue
    d = diario[k]
    print(f"{k:>8} {d['data']:>12} {d['norma_pesos']:>8.3f} {d['delta_pesos']:>9.5f} "
          f"{d['p']:>9.3f} {d['posicao']:>4}")

# quanto os pesos se moveram no total
total = sum(d["delta_pesos"] for d in diario)
print(f"\ncaminho total percorrido pelos pesos: {total:.2f} "
      f"(norma inicial {diario[0]['norma_pesos']:.2f} -> final {diario[-1]['norma_pesos']:.2f})")

# importancia por feature: inicio vs fim
ini, fim = diario[0]["importancia"], diario[-1]["importancia"]
print("\nimportancia por feature (soma dos |pesos| de entrada), inicio -> fim:")
ordenado = sorted(fim, key=lambda k: -(fim[k] - ini[k]))
print("  MAIS aprendidas:")
for k in ordenado[:6]:
    tag = "[MEMORIA]" if k in MEMORY_NAMES else ""
    print(f"    {k:<24} {ini[k]:.3f} -> {fim[k]:.3f}  ({fim[k]-ini[k]:+.3f}) {tag}")
print("  MENOS usadas:")
for k in ordenado[-4:]:
    tag = "[MEMORIA]" if k in MEMORY_NAMES else ""
    print(f"    {k:<24} {ini[k]:.3f} -> {fim[k]:.3f}  ({fim[k]-ini[k]:+.3f}) {tag}")

pm_i = sum(ini[k] for k in MEMORY_NAMES); pm_f = sum(fim[k] for k in MEMORY_NAMES)
pp_i = sum(ini[k] for k in PRICE_NAMES);  pp_f = sum(fim[k] for k in PRICE_NAMES)
print(f"\n  peso total em features de MERCADO : {pp_i:.2f} -> {pp_f:.2f}")
print(f"  peso total em features de MEMORIA : {pm_i:.2f} -> {pm_f:.2f}")
print(f"  fatia da memoria: {pm_i/(pm_i+pp_i)*100:.1f}% -> {pm_f/(pm_f+pp_f)*100:.1f}%")
