"""Rotulos em varios horizontes, sobre as MESMAS features.

O horizonte muda quantas observacoes independentes existem: com alvo de 20
pregoes em dado diario, dias vizinhos se sobrepoem em 19/20 e sobram ~107
periodos independentes em 8 anos. Com 5 pregoes sobram ~430.

Isso importa mais para cronometrar o mercado (que tem so essas observacoes)
do que para escolher entre ativos (que as multiplica por 54).
"""

import json
import os
import time

HORIZONTES = [1, 2, 3, 5, 10, 20]


def main():
    dir_f = "results/features"
    for arq in sorted(os.listdir(dir_f)):
        d = json.load(open(f"{dir_f}/{arq}"))
        if all(f"ret{h}" in d for h in HORIZONTES):
            continue
        inst = d["inst"]
        raw = json.load(open(f"data/{inst}_1d.json"))
        opens, datas_all = {}, []
        for c in raw:
            dt = time.strftime("%Y-%m-%d", time.gmtime(int(c[0]) / 1000))
            opens[dt] = float(c[1])
            datas_all.append(dt)
        pos = {dt: k for k, dt in enumerate(datas_all)}
        for h in HORIZONTES:
            col = []
            for dt in d["datas"]:
                k = pos[dt]
                a, b = k + 1, k + 1 + h
                col.append(opens[datas_all[b]] / opens[datas_all[a]] - 1
                           if b < len(datas_all) else 0.0)
            d[f"ret{h}"] = col
        json.dump(d, open(f"{dir_f}/{arq}", "w"))
    print(f"rotulos gerados para horizontes {HORIZONTES} em {len(os.listdir(dir_f))} ativos")


if __name__ == "__main__":
    main()
