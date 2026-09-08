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
python3 run_ema9.py                    # histórico completo, usa o cache em data/
python3 run_ema9.py --desde=2025-01-01 # recorta a janela (EMA aquecida com o histórico anterior)
python3 run_ema9.py --refresh          # rebaixa o histórico da OKX
python3 tests/test_engine.py           # testes de sanidade do motor
```

Com `--desde`, o histórico anterior à janela é usado apenas para aquecer a EMA, e o
candle imediatamente anterior serve de barra zero: se o preço já estava acima da EMA
naquele fechamento, a estratégia entra na janela já comprada, em vez de esperar um
novo cruzamento.

## Estrutura

- `backtest/engine.py` — EMA, geração de sinais, motor de execução, métricas.
- `backtest/data.py` — coleta e cache dos candles diários.
- `run_ema9.py` — roda o teste e imprime a tabela de resultados.
- `tests/test_engine.py` — verifica EMA, custos, execução no candle seguinte, drawdown.
- `results/` — resumo em JSON, lista de trades e curva de capital em CSV.

---

# Parte 2 — IA de visão, cérebro plástico e treino pesado

## O que foi testado, em ordem

1. **EMA 9** (histórico completo e 2025/26).
2. **IA de visão**: Qwen2-VL-2B local lendo 1.230 fotos de gráfico de candles.
3. **Cérebro plástico**: cabeça que nunca para de treinar, com features de
   memória do próprio desempenho, e o congelado como controle.
4. **Livro de análise técnica** definindo 46 indicadores (o que medir, não o
   que concluir).
5. **Treino pesado**: 376 épocas completas sobre todos os anos de gráfico por
   rodada, horizonte de alvo, dropout, weight decay.

## Disciplina de validação

- **Três janelas**: treino 2018-2022, validação 2023-2024, teste 2025/26
  tocado uma única vez, depois da configuração escolhida.
- **Causalidade provada por destruição do futuro**: embaralhados os candles a
  partir de uma data, nenhuma decisão anterior muda e as posteriores mudam
  (`tests/test_causalidade.py`, `tests/test_causalidade_deep.py`).
- **Teste nulo por deslocamento circular**, que preserva giro e suavidade do
  sinal — o teste por embaralhamento é permissivo demais (`validate_ai.py`).
- **Fração do tempo comprado** medida sempre, para flagrar degeneração em
  buy and hold disfarçado.

## Conclusão

Nenhuma variante produziu vantagem. A causa foi isolada: a vantagem bruta é de
~0,1% por operação contra 0,3% de custo. Forçar poucas operações com
permanência mínima elevou o lucro por operação, mas só porque o modelo passou
a ficar comprado 92-95% do tempo — virou buy and hold, não ficou melhor.

## Como rodar

```bash
python3 run_experimento.py --fase=selecao          # treino/validação
python3 run_experimento.py --fase=teste            # teste, uma vez
python3 run_experimento.py --fase=selecao --h=20 --b=0.05 --hold=20,40
python3 tests/test_causalidade_deep.py             # prova de causalidade
```
