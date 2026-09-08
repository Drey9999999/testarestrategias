"""As features de mercado melhoram a previsao de DIRECAO absoluta?"""

import statistics
import torch

from treino_lab import fatiar, avaliar, auc, treinar, prever, carregar_tudo
from treino_cross import carregar_com_transversal
from treino_mercado import carregar_com_mercado

for rot, carregador in [("46 features do ativo", carregar_tudo),
                        ("+ 46 transversais (92)", carregar_com_transversal),
                        ("+ 12 de mercado (104)", carregar_com_mercado)]:
    X, Yabs, D, A, R = carregador()
    tr, va, te = fatiar(D)
    dim = len(X[0])
    Xt = torch.tensor(X, dtype=torch.float32)
    Ya = torch.tensor(Yabs, dtype=torch.float32)
    Rt = torch.tensor(R, dtype=torch.float32)
    W = (Rt.abs() / Rt.abs().mean()).clamp(0.2, 5.0)
    yva = [Ya[i].item() for i in va]

    mods, aucs = [], []
    for s in range(5):
        m, mu, sd, _ = treinar(Xt, Ya, W, tr, va, dim, semente=s, oculto=128,
                               camadas=3, lr=3e-4, epocas=80, parada=10)
        mods.append((m, mu, sd)); aucs.append(avaliar(m, Xt, Ya, va, mu, sd)[1])
    ps = [prever(m, Xt, va, mu, sd) for m, mu, sd in mods]
    med = [sum(c)/len(c) for c in zip(*ps)]
    acc = sum(1 for p, y in zip(med, yva) if (p > .5) == (y > .5))/len(yva)
    print(f"  ALVO ABSOLUTO — {rot:<24} ({dim:>3} entradas)  "
          f"ensemble de 5: acerto {acc*100:.1f}%  AUC {auc(yva, med):.4f}")
