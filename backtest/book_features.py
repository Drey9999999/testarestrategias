"""Features derivadas do livro de analise tecnica fornecido pelo usuario.

O papel do livro aqui e definir O QUE MEDIR, nunca o que concluir. Cada
indicador entra como observacao; se ele preve ou nao, quem decide sao os pesos
treinados nos dados — que podem zera-lo.

Os parametros sao os do proprio livro (RSI 14 com zonas 30/70 e 20/80 e cruza-
mento da linha central; MACD 12/26/9; Bollinger sobre media de 21; SMA 20, 50,
100 e 200; EMA 9, 12 e 26; estocastico 14/3; CCI 20; retracoes de Fibonacci).
Terem sido escritos por um terceiro, antes da janela de teste, e a melhor
protecao disponivel contra escolher numeros que funcionam em 2025.

Tudo e causal: no dia i so entram dados ate o fechamento de i.
"""

import math

NAMES = [
    # RSI (livro: 14 periodos, zonas 30/70, extremos 20/80, linha central 50)
    "rsi14", "rsi_sobrevenda", "rsi_sobrecompra", "rsi_extremo_baixo",
    "rsi_extremo_alto", "rsi_acima_50", "rsi_inclinacao",
    # MACD (livro: 12/26/9)
    "macd_hist", "macd_acima_sinal", "macd_acima_zero", "macd_cruz_alta", "macd_cruz_baixa",
    # Bandas de Bollinger (livro: media de 21, desvios padrao)
    "bb_posicao", "bb_largura", "bb_rompeu_cima", "bb_rompeu_baixo", "bb_aperto",
    # Medias moveis (livro: SMA 20/50/100/200, EMA 9/12/26)
    "sma20", "sma50", "sma100", "sma200",
    "cruz_50_200", "ema9_vs_26", "ema12_vs_26", "preco_acima_sma200",
    # Estocastico e CCI
    "stoch_k", "stoch_d", "stoch_cruz", "stoch_sobrevenda", "stoch_sobrecompra", "cci20",
    # Suporte, resistencia e Fibonacci
    "dist_topo20", "dist_fundo20", "dist_topo60", "dist_fundo60",
    "fib_382", "fib_500", "fib_618",
    # Volume (livro: capitulo de Wyckoff / poder do volume)
    "vol_relativo", "vol_em_alta", "obv_inclinacao",
    # Candlestick
    "corpo", "sombra_sup", "sombra_inf", "engolfo", "martelo",
]

WARMUP = 210          # SMA 200 precisa de 200 candles


def _sma(c, i, n):
    return sum(x.close for x in c[i - n + 1:i + 1]) / n


def _ema_serie(v, n):
    k = 2.0 / (n + 1)
    out = [None] * len(v)
    if len(v) < n:
        return out
    s = sum(v[:n]) / n
    out[n - 1] = s
    for j in range(n, len(v)):
        s = v[j] * k + s * (1 - k)
        out[j] = s
    return out


def precalcular(c):
    """Series que valem a pena calcular uma vez para toda a base."""
    closes = [x.close for x in c]
    n = len(c)

    # RSI 14 (Wilder)
    rsi = [None] * n
    ganhos = perdas = 0.0
    for i in range(1, n):
        d = closes[i] - closes[i - 1]
        g, p = max(d, 0.0), max(-d, 0.0)
        if i <= 14:
            ganhos += g; perdas += p
            if i == 14:
                ganhos /= 14; perdas /= 14
                rsi[i] = 100 - 100 / (1 + ganhos / perdas) if perdas > 0 else 100.0
        else:
            ganhos = (ganhos * 13 + g) / 14
            perdas = (perdas * 13 + p) / 14
            rsi[i] = 100 - 100 / (1 + ganhos / perdas) if perdas > 0 else 100.0

    e12, e26 = _ema_serie(closes, 12), _ema_serie(closes, 26)
    macd = [(e12[i] - e26[i]) if (e12[i] is not None and e26[i] is not None) else None
            for i in range(n)]
    validos = [x for x in macd if x is not None]
    sinal_v = _ema_serie(validos, 9)
    sinal = [None] * n
    desloc = n - len(validos)
    for j, v in enumerate(sinal_v):
        sinal[desloc + j] = v

    e9 = _ema_serie(closes, 9)

    obv = [0.0] * n
    for i in range(1, n):
        obv[i] = obv[i - 1] + (c[i].volume if closes[i] > closes[i - 1]
                               else -c[i].volume if closes[i] < closes[i - 1] else 0.0)

    # Bollinger (media 21) e estocastico 14: caros se recalculados por dia
    bb_m, bb_sd, bb_larg = [None]*n, [None]*n, [None]*n
    for i in range(20, n):
        m = sum(closes[i-20:i+1]) / 21
        sd = math.sqrt(sum((x - m) ** 2 for x in closes[i-20:i+1]) / 21)
        bb_m[i], bb_sd[i] = m, sd
        bb_larg[i] = (4 * sd) / m if m else 0.0

    stoch = [None] * n
    for i in range(13, n):
        hi = max(x.high for x in c[i-13:i+1])
        lo = min(x.low for x in c[i-13:i+1])
        stoch[i] = (closes[i] - lo) / (hi - lo) * 100 if hi > lo else 50.0

    return {"rsi": rsi, "macd": macd, "sinal": sinal, "e9": e9, "e12": e12,
            "e26": e26, "obv": obv, "bb_m": bb_m, "bb_sd": bb_sd,
            "bb_larg": bb_larg, "stoch": stoch}


def features(c, i, pre):
    """Vetor de indicadores do livro no fechamento do candle i."""
    px = c[i].close
    rsi = pre["rsi"][i] or 50.0
    rsi_ant = pre["rsi"][i - 1] or 50.0
    macd, sinal = pre["macd"][i] or 0.0, pre["sinal"][i] or 0.0
    macd_a, sinal_a = pre["macd"][i - 1] or 0.0, pre["sinal"][i - 1] or 0.0

    # Bollinger sobre media de 21 (series ja pre-calculadas)
    m21, sd = pre["bb_m"][i], pre["bb_sd"][i] or 1e-9
    sup, inf = m21 + 2 * sd, m21 - 2 * sd
    largura = pre["bb_larg"][i]
    aperto = 1.0 if largura <= min(pre["bb_larg"][i - 59:i + 1]) * 1.05 else 0.0

    s20, s50, s100, s200 = (_sma(c, i, 20), _sma(c, i, 50), _sma(c, i, 100), _sma(c, i, 200))

    # Estocastico 14/3 (serie ja pre-calculada)
    st = pre["stoch"]
    k_, k_ant = st[i], st[i - 1]
    d_ = sum(st[i - 2:i + 1]) / 3
    d_ant = sum(st[i - 3:i]) / 3

    # CCI 20
    tps = [(x.high + x.low + x.close) / 3 for x in c[i - 19:i + 1]]
    tp, mtp = tps[-1], sum(tps) / 20
    md = sum(abs(x - mtp) for x in tps) / 20 or 1e-9
    cci = (tp - mtp) / (0.015 * md)

    hi20 = max(x.high for x in c[i - 19:i + 1]); lo20 = min(x.low for x in c[i - 19:i + 1])
    hi60 = max(x.high for x in c[i - 59:i + 1]); lo60 = min(x.low for x in c[i - 59:i + 1])
    amp = (hi60 - lo60) or 1e-9
    retr = (hi60 - px) / amp          # 0 no topo, 1 no fundo do swing

    volm = sum(x.volume for x in c[i - 19:i + 1]) / 20 or 1e-9
    obv_incl = (pre["obv"][i] - pre["obv"][i - 20]) / (abs(pre["obv"][i - 20]) + 1e-9)

    rng = (c[i].high - c[i].low) or 1e-9
    corpo = (px - c[i].open) / rng
    topo_corpo, base_corpo = max(px, c[i].open), min(px, c[i].open)
    a = c[i - 1]
    engolfo = 1.0 if (px > c[i].open and a.close < a.open
                      and px >= a.open and c[i].open <= a.close) else 0.0
    martelo = 1.0 if ((base_corpo - c[i].low) / rng > 0.6 and abs(corpo) < 0.3) else 0.0

    return [
        rsi / 50 - 1, 1.0 if rsi < 30 else 0.0, 1.0 if rsi > 70 else 0.0,
        1.0 if rsi < 20 else 0.0, 1.0 if rsi > 80 else 0.0,
        1.0 if rsi > 50 else 0.0, (rsi - rsi_ant) / 10,
        (macd - sinal) / px * 100, 1.0 if macd > sinal else 0.0, 1.0 if macd > 0 else 0.0,
        1.0 if (macd > sinal and macd_a <= sinal_a) else 0.0,
        1.0 if (macd < sinal and macd_a >= sinal_a) else 0.0,
        (px - inf) / (sup - inf) - 0.5 if sup > inf else 0.0, largura * 10,
        1.0 if px > sup else 0.0, 1.0 if px < inf else 0.0, aperto,
        math.log(px / s20), math.log(px / s50), math.log(px / s100), math.log(px / s200),
        1.0 if s50 > s200 else 0.0,
        math.log(pre["e9"][i] / pre["e26"][i]) if pre["e26"][i] else 0.0,
        math.log(pre["e12"][i] / pre["e26"][i]) if pre["e26"][i] else 0.0,
        1.0 if px > s200 else 0.0,
        k_ / 50 - 1, d_ / 50 - 1, 1.0 if (k_ > d_ and k_ant <= d_ant) else 0.0,
        1.0 if k_ < 20 else 0.0, 1.0 if k_ > 80 else 0.0, cci / 100,
        (hi20 - px) / px * 10, (px - lo20) / px * 10,
        (hi60 - px) / px * 10, (px - lo60) / px * 10,
        1.0 if abs(retr - 0.382) < 0.03 else 0.0,
        1.0 if abs(retr - 0.500) < 0.03 else 0.0,
        1.0 if abs(retr - 0.618) < 0.03 else 0.0,
        c[i].volume / volm - 1,
        (c[i].volume / volm - 1) * (1 if px > c[i].open else -1),
        obv_incl,
        corpo, (c[i].high - topo_corpo) / rng, (base_corpo - c[i].low) / rng,
        engolfo, martelo,
    ]
