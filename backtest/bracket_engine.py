"""Motor de execucao fiel ao que o livro ensina.

O motor anterior entrava com todo o capital e so saia quando o sinal virava.
Isso ignora o mecanismo central do livro: taxa de acerto perto de 50% vira
lucro quando o ganho medio e 2x ou mais a perda media.

Regras implementadas, com as palavras do livro:

  - "arrisque nao mais do que 3% do tamanho da sua conta em uma unica
    negociacao": o tamanho da posicao sai do risco, nao do capital total.
  - "seu stop loss deve ser muito maior, como 20% ou mais": stop percentual
    configuravel, dimensionado ao prazo do grafico.
  - "use uma taxa de recompensa de risco de 1:2 ou superior": alvo em
    stop x R.
  - Sem alavancagem: a posicao nunca passa do patrimonio disponivel.

Dentro do candle diario nao se sabe a ordem dos toques. Quando stop e alvo
sao atingidos no mesmo candle, assume-se o STOP — a hipotese pessimista, para
nao inventar lucro que o dado nao prova.
"""

from dataclasses import dataclass, field


@dataclass
class TradeB:
    entrada: str
    preco_entrada: float
    saida: str
    preco_saida: float
    motivo: str          # "alvo", "stop" ou "sinal"
    qty: float
    pnl: float
    r_multiplo: float    # resultado em multiplos do risco assumido


@dataclass
class ResultadoB:
    equity: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    final: float = 0.0
    capital: float = 10000.0

    @property
    def total_return(self):
        return self.final / self.capital - 1

    @property
    def max_drawdown(self):
        pico, mdd = float("-inf"), 0.0
        for _, eq in self.equity:
            pico = max(pico, eq)
            mdd = min(mdd, eq / pico - 1)
        return mdd

    @property
    def n_trades(self):
        return len(self.trades)

    @property
    def win_rate(self):
        return (sum(1 for t in self.trades if t.pnl > 0) / len(self.trades)
                if self.trades else 0.0)

    @property
    def r_medio(self):
        """Expectativa por operacao, em multiplos de risco. E o numero que
        decide se a estrategia se paga."""
        return (sum(t.r_multiplo for t in self.trades) / len(self.trades)
                if self.trades else 0.0)

    @property
    def ganho_medio(self):
        g = [t.r_multiplo for t in self.trades if t.pnl > 0]
        return sum(g) / len(g) if g else 0.0

    @property
    def perda_media(self):
        p = [t.r_multiplo for t in self.trades if t.pnl <= 0]
        return sum(p) / len(p) if p else 0.0


def rodar_bracket(candles, sinais, capital=10000.0, fee=0.001, slippage=0.0005,
                  stop_pct=0.20, rr=2.0, risco_por_trade=0.03,
                  sair_por_sinal=True):
    """Executa os sinais com stop, alvo e dimensionamento por risco.

    `sinais[i]` refere-se ao fechamento do candle i e executa na abertura de
    i+1. +1 abre posicao; -1 fecha por sinal.

    Com `sair_por_sinal=False` a operacao so termina no stop ou no alvo, que e
    como o livro descreve o metodo: entra-se no setup e deixa-se o bracket
    resolver. Com saida por sinal ligada, um modelo que troca de opiniao a cada
    poucos dias fecha tudo antes de o alvo ser tocado, e o mecanismo de
    risco-recompensa nunca chega a operar.
    """
    caixa = capital
    qty = 0.0
    entrada = preco_ent = stop = alvo = risco_moeda = 0.0
    patrimonio_antes = capital
    res = ResultadoB(capital=capital)

    def fechar(i, preco, motivo):
        nonlocal caixa, qty
        bruto = qty * preco
        taxa = bruto * fee
        caixa += bruto - taxa
        pnl = caixa - patrimonio_antes
        res.trades.append(TradeB(entrada, preco_ent, candles[i].date, preco,
                                 motivo, qty, pnl,
                                 pnl / risco_moeda if risco_moeda else 0.0))
        qty = 0.0

    for i, c in enumerate(candles):
        # 1) posicao aberta: stop e alvo valem DENTRO do candle
        if qty > 0.0:
            bateu_stop = c.low <= stop
            bateu_alvo = c.high >= alvo
            if bateu_stop:                      # pessimista quando ambos batem
                fechar(i, stop * (1 - slippage), "stop")
            elif bateu_alvo:
                fechar(i, alvo * (1 - slippage), "alvo")

        # 2) ordem gerada pelo candle anterior
        sig = sinais[i - 1] if i > 0 else 0

        if sig == -1 and qty > 0.0 and sair_por_sinal:
            fechar(i, c.open * (1 - slippage), "sinal")

        elif sig == 1 and qty == 0.0 and caixa > 0:
            patrimonio_antes = caixa
            abriu_agora = True
            px = c.open * (1 + slippage)
            stop = px * (1 - stop_pct)
            alvo = px * (1 + stop_pct * rr)
            risco_moeda = caixa * risco_por_trade
            # tamanho pelo risco; nunca acima do patrimonio (sem alavancagem)
            notional = min(risco_moeda / stop_pct, caixa / (1 + fee))
            qty = notional / px
            caixa -= notional + notional * fee
            entrada, preco_ent = c.date, px
            # o stop pode ser atingido no PROPRIO candle da entrada; ignorar
            # isso inventaria sobrevivencia que o dado nao da
            if c.low <= stop:
                fechar(i, stop * (1 - slippage), "stop")
            elif c.high >= alvo:
                fechar(i, alvo * (1 - slippage), "alvo")

        res.equity.append((c.date, caixa + qty * c.close))

    if qty > 0.0:
        fechar(len(candles) - 1, candles[-1].close * (1 - slippage), "fim")
        res.equity[-1] = (candles[-1].date, caixa)

    res.final = caixa
    return res
