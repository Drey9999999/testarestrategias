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
- [x] 7. Controle da preferencia estatica: o FIXO VENCE o adaptativo
- [x] 8. Repetido na validacao 2023-24: mesmo resultado
- [x] 9. Sensibilidade ao top_n: estatico vence em 7 de 8 configuracoes
- [ ] 11. Refazer excluindo OKB: o ganho da carteira top-3 em 2025/26 vem
       quase todo dele (+135,6%), e e o token da propria corretora cujos
       dados uso. Sem ele, sobra o que?
- [ ] 12. Rebalanceamento: variar de 10 dias para 20, 40, 60 — se adaptar
       menos e melhor, adaptar ainda menos deve ser melhor ainda
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

### Ciclo 2 — a adaptacao destroi valor

Item 7 respondido, e contra o modelo adaptativo. Congelar a escolha rende mais
que reescolher a cada 10 dias, nas DUAS janelas:

| janela | adaptativo | favoritos congelados | menor volatilidade (sem modelo) |
|---|---|---|---|
| teste 2025/26   | R$  3.812 | R$  8.933 | R$  7.664 |
| validacao 23-24 | R$ 30.657 | R$ 34.190 | R$ 53.163 |

Item 9: variando o numero de ativos (3, 5, 10, 20), o estatico vence em 7 das
8 configuracoes. A vantagem e maior quanto menor a carteira.

Uma regra de uma linha — "compre os N menos volateis do ano passado e nao mexa"
— bate a rede neural treinada em 111.691 amostras. O que o modelo tinha de
util era preferencia por ativo, e reescolher a cada 10 dias so adicionava
ruido e custo.

RESSALVA QUE INVALIDA O NUMERO DE MANCHETE: a carteira top-3 em 2025/26 rendeu
+20,9% num mercado de queda, mas isso vem quase todo do OKB (+135,6%). BTC caiu
14,2% e ETH 24,7% na mesma carteira. Alem da concentracao, OKB e o token da
propria OKX, de onde vem todo o dado deste projeto. Com top_n=20 o resultado
volta a -71%, alinhado ao universo. O achado que se sustenta e o ORDENAMENTO
(estatico > adaptativo), nao o retorno absoluto.
