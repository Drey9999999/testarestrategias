# Fila de trabalho autonomo

A sessao congela quando fica ociosa, entao o trabalho avanca em ciclos: a cada
despertar, executar o proximo item, commitar, e reagendar.

## Fila

- [x] 1. Baixar historico diario: 54 pares USDT com >= 900 candles
- [x] 2. Treino AGRUPADO (melhor que por ativo): 111.691 amostras, 54 mercados
- [x] 3. Carteira transversal: top 5, rebalanceamento a cada 10 dias
- [x] 4. Sensibilidade a custo: 0,15% / 0,05% / 0,02%
- [x] 5. Teste nulo por deslocamento: p = 0,036 / 0,145 / 0,655 (inconsistente)
- [ ] 6. Mais sementes no teste nulo (3 e pouco para concluir)
- [ ] 7. Controle da preferencia estatica: ranking fixo escolhido no treino
       rende o mesmo? Se sim, nao ha valor adaptativo, so preferencia por ativo
- [ ] 8. Repetir a carteira na validacao 2023-24, fora da janela de teste
- [ ] 9. Sensibilidade ao top_n (3, 5, 10, 20)
- [ ] 10. Relatorio consolidado

## Vies conhecido a declarar no relatorio

A OKX so lista pares vivos hoje. Moedas que morreram estao fora da amostra,
o que enviesa qualquer resultado para o lado OTIMISTA. Nao ha como corrigir
com esta fonte; tem que constar no relatorio.

## Registro

### Ciclo 1
- 54 ativos baixados; 11 descartados por historico curto (EOS, FTM, MKR, DASH,
  ZEC, WAVES, OMG, RUNE, KAVA, ANKR, REN) — o proprio viés de sobrevivencia.
- Carteira transversal em 2025/26, custo 0,05%: modelo R$ 3.812 (-61,9%),
  escolha aleatoria R$ 1.450 (-85,5%), carteira cheia R$ 2.528 (-74,7%).
  Nenhum de 20 sorteios igualou o modelo.
- Escolhas usam os 54 ativos; BTC/ETH sao 8,1% delas (sorteio daria 3,7%),
  entao nao e apenas "fugir para o BTC".
- Teste nulo por deslocamento das escolhas no tempo: p = 0,036 / 0,145 / 0,655.
  Bate a escolha aleatoria de ativos, NAO bate as proprias escolhas deslocadas.
  Hipotese: aprendeu preferencia por ativo, nao momento. Item 7 testa isso.
- Corrigido no caminho: a carteira executava na abertura do MESMO dia do sinal
  (vazamento de um dia). Agora executa na abertura do dia seguinte, com prova
  de causalidade por destruicao do futuro em tests/test_portfolio.py.
