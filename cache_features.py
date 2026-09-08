"""Pre-calcula features do livro para todos os ativos, uma vez.

Treinar agrupando os ativos e a forma legitima de "treinar mais": em vez de
repetir epocas sobre 3.000 dias de um ativo, sao ~160 mil amostras vindas de
54 mercados diferentes. Mais dado, nao mais repeticao.
"""

import glob
import json
import os
import sys

from backtest.data import load
from backtest import book_features

SAIDA = "results/features"


def main():
    os.makedirs(SAIDA, exist_ok=True)
    arqs = sorted(glob.glob("data/*_1d.json"))
    insts = [os.path.basename(a).replace("_1d.json", "") for a in arqs]
    total = 0
    for inst in insts:
        p = f"{SAIDA}/{inst}.json"
        if os.path.exists(p):
            total += len(json.load(open(p))["X"])
            continue
        c = load(inst)
        if len(c) < book_features.WARMUP + 100:
            continue
        pre = book_features.precalcular(c)
        X, datas, ret = [], [], []
        for i in range(book_features.WARMUP, len(c) - 21):
            X.append([round(v, 6) for v in book_features.features(c, i, pre)])
            datas.append(c[i].date)
            # retorno do intervalo negociavel [abertura i+1, abertura i+21]
            ret.append(c[i + 21].open / c[i + 1].open - 1)
        json.dump({"inst": inst, "datas": datas, "X": X, "ret": ret}, open(p, "w"))
        total += len(X)
        print(f"  {inst}: {len(X)} amostras", flush=True)
    print(f"\ntotal de amostras: {total:,} em {len(os.listdir(SAIDA))} ativos")


if __name__ == "__main__":
    main()
