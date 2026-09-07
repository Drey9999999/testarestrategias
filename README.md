# Teste da EMA 9 no diário — BTC-USDT e ETH-USDT

Backtest simples e sem otimização da EMA de 9 períodos no gráfico diário, com dados
históricos reais de mercado spot.

## Regras testadas

- Comprar quando o candle diário fechar **acima** da EMA 9, após o anterior ter fechado abaixo ou igual.
- Vender quando fechar **abaixo** da EMA 9, após o anterior ter fechado acima ou igual.
- Execução sempre na **abertura do candle seguinte** ao sinal.
- Capital inicial de 10.000, long-only, all-in, sem alavancagem.
- Taxa de 0,1% e slippage de 0,05% em **cada** operação (entrada e saída).
- Nenhum filtro adicional e nenhum parâmetro otimizado.

Buy and hold entra no mesmo candle em que a estratégia já poderia operar e paga os
mesmos custos, para que a comparação seja direta. Posição aberta no fim da série é
liquidada no último fechamento.

## Dados

Candles diários (`1Dutc`) da OKX spot, endpoint público `market/history-candles`,
todo o histórico disponível: 3.161 candles fechados por ativo, de 2018-01-11 a
2026-09-06, sem lacunas. Cache em `data/`.

A Binance está bloqueada por região neste ambiente, por isso a OKX foi usada como
fonte dos mesmos pares USDT. Os valores são cotados em USDT; o capital inicial é
tratado como 10.000 unidades da moeda de cotação (não há conversão para BRL).

## Como rodar

```bash
python3 run_ema9.py            # usa o cache em data/
python3 run_ema9.py --refresh  # rebaixa o histórico da OKX
python3 tests/test_engine.py   # testes de sanidade do motor
```

## Estrutura

- `backtest/engine.py` — EMA, geração de sinais, motor de execução, métricas.
- `backtest/data.py` — coleta e cache dos candles diários.
- `run_ema9.py` — roda o teste e imprime a tabela de resultados.
- `tests/test_engine.py` — verifica EMA, custos, execução no candle seguinte, drawdown.
- `results/` — resumo em JSON, lista de trades e curva de capital em CSV.
