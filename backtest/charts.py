"""Renderiza a 'foto' do grafico de candles que a IA vai analisar.

Regra critica: a imagem do dia t contem apenas candles ate o fechamento de t.
Nenhuma informacao futura entra no quadro.

O eixo de precos e normalizado (ultimo fechamento = 100) e o grafico nao traz
ticker, datas nem indicadores. Isso evita que o modelo reconheca "BTC em 2025"
pela memoria do pre-treino e responda por lembranca em vez de leitura do
grafico.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

UP = "#26a69a"
DOWN = "#ef5350"


def render(candles, out_path, size_px=448, dpi=100):
    """Desenha os candles recebidos (ja recortados) em `out_path`."""
    closes = [c.close for c in candles]
    base = closes[-1] / 100.0
    o = [c.open / base for c in candles]
    h = [c.high / base for c in candles]
    l = [c.low / base for c in candles]
    cl = [c.close / base for c in candles]

    fig_in = size_px / dpi
    fig, ax = plt.subplots(figsize=(fig_in, fig_in), dpi=dpi)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")

    for i in range(len(candles)):
        color = UP if cl[i] >= o[i] else DOWN
        ax.plot([i, i], [l[i], h[i]], color=color, linewidth=0.7, solid_capstyle="butt")
        bottom, height = min(o[i], cl[i]), abs(cl[i] - o[i])
        if height < 1e-9:
            ax.plot([i - 0.35, i + 0.35], [cl[i], cl[i]], color=color, linewidth=0.9)
        else:
            ax.add_patch(Rectangle((i - 0.35, bottom), 0.7, height,
                                   facecolor=color, edgecolor=color, linewidth=0.4))

    ax.set_xlim(-1, len(candles))
    lo, hi = min(l), max(h)
    pad = (hi - lo) * 0.06
    ax.set_ylim(lo - pad, hi + pad)
    ax.grid(True, color="#e0e0e0", linewidth=0.5)
    ax.tick_params(labelsize=6, length=2)
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_color("#9e9e9e")
        s.set_linewidth(0.6)

    fig.tight_layout(pad=0.3)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig.savefig(out_path, facecolor="white")
    plt.close(fig)
    return out_path


def render_series(candles, indices, out_dir, lookback=60, size_px=448):
    """Uma imagem por dia de decisao, cada uma com os `lookback` candles ate ali."""
    paths = {}
    for i in indices:
        janela = candles[max(0, i - lookback + 1): i + 1]
        p = os.path.join(out_dir, f"{i:05d}_{candles[i].date}.png")
        if not os.path.exists(p):
            render(janela, p, size_px=size_px)
        paths[i] = p
    return paths
