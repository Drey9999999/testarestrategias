"""Motor de backtest simples para estrategias long-only em candles diarios.

Execucao sempre na abertura do candle seguinte ao sinal, com taxa e slippage
aplicados sobre o preco de execucao.
"""

from dataclasses import dataclass, field


@dataclass
class Candle:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Trade:
    entry_date: str
    entry_price: float   # preco ja com slippage
    exit_date: str
    exit_price: float    # preco ja com slippage
    qty: float
    fee_paid: float
    pnl: float           # lucro liquido em moeda, ja descontados taxa e slippage
    ret: float           # retorno liquido do trade


@dataclass
class Result:
    equity: list = field(default_factory=list)      # (data, patrimonio marcado a mercado)
    trades: list = field(default_factory=list)
    final_equity: float = 0.0

    @property
    def total_return(self):
        return self.final_equity / self.equity[0][1] - 1 if self.equity else 0.0

    @property
    def max_drawdown(self):
        peak = float("-inf")
        mdd = 0.0
        for _, eq in self.equity:
            peak = max(peak, eq)
            mdd = min(mdd, eq / peak - 1)
        return mdd

    @property
    def n_trades(self):
        return len(self.trades)

    @property
    def win_rate(self):
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.pnl > 0) / len(self.trades)

    @property
    def avg_trade_pnl(self):
        if not self.trades:
            return 0.0
        return sum(t.pnl for t in self.trades) / len(self.trades)

    @property
    def avg_trade_ret(self):
        if not self.trades:
            return 0.0
        return sum(t.ret for t in self.trades) / len(self.trades)


def ema(values, period):
    """EMA classica, semeada com a media simples dos primeiros `period` valores.

    Retorna lista do mesmo tamanho, com None antes do periodo estar completo.
    """
    out = [None] * len(values)
    if len(values) < period:
        return out
    k = 2.0 / (period + 1)
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


def run_backtest(candles, signals, capital=10000.0, fee=0.001, slippage=0.0005):
    """Executa sinais long-only, all-in, sem alavancagem.

    `signals[i]` in {+1 comprar, -1 vender, 0 nada} referente ao FECHAMENTO do
    candle i; a ordem e executada na ABERTURA do candle i+1.
    Posicao aberta no final e liquidada no fechamento do ultimo candle.
    """
    cash = capital
    qty = 0.0
    entry_date = None
    entry_price = 0.0
    entry_fee = 0.0
    res = Result()

    for i, c in enumerate(candles):
        # ordem gerada pelo candle anterior executa nesta abertura
        sig = signals[i - 1] if i > 0 else 0

        if sig == 1 and qty == 0.0:
            px = c.open * (1 + slippage)          # slippage contra o comprador
            gross = cash / (1 + fee)              # taxa cobrada sobre o notional
            qty = gross / px
            fee_paid = gross * fee
            cash = 0.0
            entry_date, entry_price, entry_fee = c.date, px, fee_paid

        elif sig == -1 and qty > 0.0:
            px = c.open * (1 - slippage)          # slippage contra o vendedor
            gross = qty * px
            fee_paid = gross * fee
            cash = gross - fee_paid
            cost = entry_price * qty + entry_fee
            res.trades.append(Trade(entry_date, entry_price, c.date, px, qty,
                                    entry_fee + fee_paid, cash - cost, cash / cost - 1))
            qty = 0.0

        res.equity.append((c.date, cash + qty * c.close))

    # liquida posicao aberta no fechamento do ultimo candle
    if qty > 0.0:
        last = candles[-1]
        px = last.close * (1 - slippage)
        gross = qty * px
        fee_paid = gross * fee
        cash = gross - fee_paid
        cost = entry_price * qty + entry_fee
        res.trades.append(Trade(entry_date, entry_price, last.date, px, qty,
                                entry_fee + fee_paid, cash - cost, cash / cost - 1))
        qty = 0.0
        res.equity[-1] = (last.date, cash)

    res.final_equity = cash
    return res


def ema_cross_signals(candles, period=9):
    """+1 quando o fechamento cruza para cima da EMA (anterior <=),
    -1 quando cruza para baixo (anterior >=)."""
    closes = [c.close for c in candles]
    e = ema(closes, period)
    sig = [0] * len(candles)
    for i in range(1, len(candles)):
        if e[i] is None or e[i - 1] is None:
            continue
        if closes[i] > e[i] and closes[i - 1] <= e[i - 1]:
            sig[i] = 1
        elif closes[i] < e[i] and closes[i - 1] >= e[i - 1]:
            sig[i] = -1
    return sig, e


def buy_and_hold(candles, start=0, capital=10000.0, fee=0.001, slippage=0.0005):
    """Compra na abertura do candle `start`+1 e liquida no ultimo fechamento,
    pagando exatamente os mesmos custos da estrategia."""
    sig = [0] * len(candles)
    sig[start] = 1
    return run_backtest(candles, sig, capital, fee, slippage)
