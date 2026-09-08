"""Features causais: tudo que entra no dia t vem de dados ate o fechamento de t.

Dois blocos separados de proposito:

- `price_features`: o que o mercado fez. Depende so dos candles.
- `memory_features`: o que a propria estrategia fez. Depende do estado da
  simulacao naquele instante — quanto ela ja perdeu, ha quantos dias erra
  seguido, se esta posicionada. E a "consciencia" do modelo sobre o proprio
  historico, e por construcao nao pode olhar o futuro: no dia t ela so conhece
  resultados ja realizados.
"""

import math

PRICE_NAMES = [
    "ret1", "ret2", "ret3", "ret5", "ret10", "ret20",
    "vol10", "vol20", "vol_ratio",
    "sma5", "sma10", "sma20", "sma60", "ema9",
    "range20", "range60",
    "corpo", "sombra", "candles_verdes10",
]

MEMORY_NAMES = [
    "posicionado", "resultado_ultimo_trade", "acerto10",
    "pnl20", "drawdown_atual", "sequencia_erros",
]

NAMES = PRICE_NAMES + MEMORY_NAMES
WARMUP = 61          # candles necessarios antes da primeira feature valida


def _ret(c, i, n):
    if i - n < 0 or c[i - n].close <= 0:
        return 0.0
    return math.log(c[i].close / c[i - n].close)


def _vol(c, i, n):
    if i - n < 0:
        return 0.0
    r = [_ret(c, k, 1) for k in range(i - n + 1, i + 1)]
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / len(r))


def _sma(c, i, n):
    if i - n + 1 < 0:
        return 0.0
    s = sum(x.close for x in c[i - n + 1:i + 1]) / n
    return math.log(c[i].close / s) if s > 0 else 0.0


def price_features(c, i, ema_vals):
    """Vetor de features de mercado no fechamento do candle i."""
    v10, v20 = _vol(c, i, 10), _vol(c, i, 20)
    hi20 = max(x.high for x in c[i - 19:i + 1])
    lo20 = min(x.low for x in c[i - 19:i + 1])
    hi60 = max(x.high for x in c[i - 59:i + 1])
    lo60 = min(x.low for x in c[i - 59:i + 1])
    rng = c[i].high - c[i].low
    e = ema_vals[i]
    return [
        _ret(c, i, 1), _ret(c, i, 2), _ret(c, i, 3),
        _ret(c, i, 5), _ret(c, i, 10), _ret(c, i, 20),
        v10 * 100, v20 * 100, (v10 / v20 - 1) if v20 > 0 else 0.0,
        _sma(c, i, 5), _sma(c, i, 10), _sma(c, i, 20), _sma(c, i, 60),
        math.log(c[i].close / e) if e else 0.0,
        (c[i].close - lo20) / (hi20 - lo20) - 0.5 if hi20 > lo20 else 0.0,
        (c[i].close - lo60) / (hi60 - lo60) - 0.5 if hi60 > lo60 else 0.0,
        (c[i].close - c[i].open) / rng if rng > 0 else 0.0,
        (rng / c[i].close) * 100 if c[i].close > 0 else 0.0,
        sum(1 for x in c[i - 9:i + 1] if x.close >= x.open) / 10 - 0.5,
    ]


class Memoria:
    """Estado que a estrategia carrega sobre si mesma.

    Atualizada apenas com resultados ja realizados, entao no dia t ela reflete
    o passado e nada alem dele.
    """

    def __init__(self):
        self.resultados = []      # retorno de cada decisao ja realizada
        self.pico = 1.0
        self.equity = 1.0
        self.posicionado = 0

    def features(self):
        ult = self.resultados[-1] if self.resultados else 0.0
        u10 = self.resultados[-10:]
        acerto = (sum(1 for x in u10 if x > 0) / len(u10) - 0.5) if u10 else 0.0
        u20 = self.resultados[-20:]
        pnl = sum(u20) * 10 if u20 else 0.0
        dd = self.equity / self.pico - 1 if self.pico > 0 else 0.0
        seq = 0
        for x in reversed(self.resultados):
            if x < 0:
                seq += 1
            else:
                break
        return [float(self.posicionado), ult * 50, acerto, pnl,
                dd * 5, min(seq, 10) / 10]

    def registrar(self, retorno_realizado, estava_posicionado):
        """Fecha o resultado de uma decisao ja liquidada."""
        self.resultados.append(retorno_realizado if estava_posicionado else 0.0)
        if estava_posicionado:
            self.equity *= (1 + retorno_realizado)
            self.pico = max(self.pico, self.equity)
