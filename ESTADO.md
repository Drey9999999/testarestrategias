# Fila de trabalho autonomo

A sessao congela quando fica ociosa, entao o trabalho avanca em ciclos: a cada
despertar, executar o proximo item, commitar, e reagendar.

## Fila

- [x] 1. Baixar historico diario: 54 pares USDT com >= 900 candles
- [x] 2. Treino AGRUPADO (melhor que por ativo): 111.691 amostras, 54 mercados
- [x] 3. Carteira transversal: top 5, rebalanceamento a cada 10 dias
- [x] 4. Sensibilidade a custo: 0,15% / 0,05% / 0,02%
- [x] 5. Teste nulo por deslocamento: p = 0,036 / 0,145 / 0,655 (inconsistente)
- [x] 6. Teste nulo da regra de volatilidade: p entre 0,000 e 0,006
- [x] 7. Controle da preferencia estatica: o FIXO VENCE o adaptativo
- [x] 8. Repetido na validacao 2023-24: mesmo resultado
- [x] 9. Sensibilidade ao top_n: estatico vence em 7 de 8 configuracoes
- [x] 11. Sem OKB: o ordenamento estatico > adaptativo SE MANTEM nas 8
       configuracoes; o ganho absoluto some (ambos passam a perder feio)
- [x] 12. Rebalanceamento 10/20/40/60: NAO ha tendencia. Minha previsao de
       que adaptar menos melhoraria progressivamente estava ERRADA
- [x] 10. Relatorio consolidado publicado (relatorio.html)

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

### Ciclo 3 — o achado sobrevive, mas minha explicacao para ele nao

Item 11 (sem OKB, 53 ativos): o ordenamento se mantem em todas as 8
configuracoes. Mas o retorno absoluto desaparece, como eu ja suspeitava —
em 2025/26 o estatico cai de R$ 7.664 para R$ 3.888 e passa a perder 61%.
O adaptativo perde 79%. Continua sendo "menos ruim", nao lucro.

| janela | rebal | adaptativo | menor volatilidade |
|---|---|---|---|
| validacao 23-24 | 10 | R$ 26.242 | R$ 67.638 |
| teste 2025/26   | 10 | R$  2.071 | R$  3.888 |

Item 12 REFUTOU minha hipotese. Eu previ que, se reescolher a cada 10 dias e
pior que nunca reescolher, entao 40 ou 60 dias deveria ficar progressivamente
melhor. Nao ficou:

  teste 2025/26 adaptativo, por ritmo: 3.812 / 3.192 / 3.226 / 2.900
  validacao 23-24 adaptativo, por ritmo: 26.242 / 27.073 / 20.073 / 26.673

Nao ha tendencia — e ruido. Logo, a desvantagem do modelo NAO vem da
frequencia de adaptacao. Vem da selecao em si: em qualquer ritmo, escolher
pelo modelo e pior que escolher pela volatilidade passada. Minha explicacao
anterior ("adaptar adiciona ruido") estava errada.

O que a volatilidade passada captura e um efeito defensivo conhecido: ativos
menos volateis caem menos nas quedas. Que ele tambem tenha vencido no bull
market de 2023-24 (R$ 67.638 contra R$ 26.242) e mais surpreendente e merece
o teste nulo do item 6.

### Ciclo 4 — a unica coisa que passou em teste nulo

A regra "compre os 5 menos volateis do ano anterior e nao mexa" contra 500
carteiras de 5 ativos sorteadas do mesmo universo, mesma mecanica e custo:

| universo | janela | regra | mediana dos sorteios | p |
|---|---|---|---|---|
| 54 ativos | validacao 23-24 | R$ 53.163 | R$ 23.873 | 0,006 |
| 54 ativos | teste 2025/26   | R$  7.664 | R$  1.801 | 0,002 |
| sem OKB   | validacao 23-24 | R$ 67.638 | R$ 23.270 | 0,000 |
| sem OKB   | teste 2025/26   | R$  3.888 | R$  1.776 | 0,004 |

Significativo nas quatro condicoes. E medir a volatilidade um ano antes da
data prevista tambem funciona (R$ 35.817 e R$ 9.164), o que reforca: e uma
propriedade persistente do ativo, nao um artefato de quando se mede.

TRES RESSALVAS QUE PRECISAM ANDAR JUNTO DESSE NUMERO:

1. VIES DE SOBREVIVENCIA, e aqui ele morde com forca. A OKX so lista pares
   vivos hoje, e 11 dos 65 candidatos foram descartados por historico curto.
   Ativos de baixa volatilidade sao justamente os mais propensos a sobreviver.
   Parte do efeito — talvez boa parte — pode ser so isso. Nao ha como medir
   com esta fonte.
2. Continua perdendo dinheiro: R$ 3.888 em 2025/26 e -61%.
3. Nao e descoberta. E a anomalia de baixa volatilidade, documentada em acoes
   desde os anos 1970. O projeto reencontrou algo conhecido, nao achou algo
   novo.

### Ciclo 4 (parte 2) — relatorio consolidado

Publicado em https://claude.ai/code/artifact/be247b3d-f718-45f3-bec2-a815c8187537
e versionado como relatorio.html.

Placar final de sete abordagens: uma sobreviveu a teste nulo (menor
volatilidade, p entre 0,000 e 0,006), uma ficou parcial (o metodo do livro
protege mas nao preve), cinco nao sobreviveram.

## Fila seguinte (proximos ciclos)

- [x] 13. Fragilidade: significativa em 14 de 24 combinacoes. Vale para
      carteiras de 3 a 10 ativos com medicao de 180+ dias; falha em 20
- [ ] 14. Tentar medir o vies de sobrevivencia: comparar o universo de hoje
      com a lista de pares que a OKX listava em 2021, se houver como obter
- [x] 15. Custo: separa as duas causas. A EMA 9 era pedagio; a rede nao.

### Ciclo 5 — a regra sobrevive qualificada, e o custo separa duas causas

Item 13 (fragilidade). A regra foi significativa a 5% em 14 de 24 combinacoes
de janela de medicao x tamanho de carteira — muito acima do 1,2 esperado por
acaso, mas longe de universal. O padrao e informativo:

  - falha SEMPRE com 20 ativos (p entre 0,065 e 0,320): diluir 20 de 53 nao
    deixa selecao nenhuma
  - a janela de 60 dias falha na validacao inteira (p 0,085 a 0,470) e passa
    no teste — depende do periodo
  - com 3 a 10 ativos e janela de 180 ou 365 dias, passa em 9 de 12 celulas

Conclusao: o efeito e real mas exige carteira concentrada e medicao longa. O
relatorio publicado foi corrigido para dizer isso; a afirmacao anterior ("nas
quatro condicoes") era verdadeira mas estreita demais para o que sugeria.

Item 15 (custo). Baixar o custo separa duas causas que pareciam a mesma:

| custo/op | EMA 9 (BTC) | cerebro plastico | comprar e segurar |
|---|---|---|---|
| 0,15% | -15,6% | -54,7% | -14,4% |
| 0,02% |  -1,7% | -35,5% | -14,2% |
| zero  |  +0,7% | -31,9% | -14,2% |

A EMA 9 vira positiva sem custo: o problema dela ERA o pedagio, e ela carrega
uma vantagem defensiva real, ainda que minuscula. A rede perde 31,9% mesmo sem
pagar nada — ali nunca foi custo, e sim ausencia de vantagem. Isso CORRIGE uma
leitura anterior deste projeto, que atribuia o prejuizo da rede ao giro.

## Fila seguinte

- [x] 16. O ganho da EMA a custo zero e exposicao reduzida, nao momento
      (p = 0,342 e 0,538 contra aleatorios de mesma exposicao)
- [ ] 14. Vies de sobrevivencia: obter lista historica de pares da OKX
- [x] 17. A combinacao nao agrega: filtro de EMA e indistinguivel de filtro
      aleatorio de mesma densidade (p = 0,335 e 0,480)

### Ciclo 6 — a EMA nao e um segundo achado, e a fila util esta perto do fim

Item 16. A EMA 9 a custo zero rende +0,7% no BTC contra -14,2% de comprar e
segurar, e passa 50,2% do tempo comprada. Contra 500 estrategias aleatorias
com a MESMA exposicao e o MESMO numero de trocas (117):

  BTC: EMA +0,7%  | mediana aleatoria -11,7% | 171/500 igualam -> p = 0,342
  ETH: EMA -19,7% | mediana aleatoria -15,8% | 269/500 igualam -> p = 0,538

Nao ha escolha de momento. O que a EMA faz e reduzir exposicao, e reduzir
exposicao ja e vantagem num mercado de queda. Nao e um achado independente da
regra de volatilidade: e o mesmo efeito defensivo visto de outro angulo.
Linha da EMA corrigida no relatorio publicado.

Item 17. Carteira de menor volatilidade filtrada pela EMA 9, custo de maker:

  validacao: sem filtro R$ 67.659 | com filtro R$ 65.586 (PIOR) | p = 0,335
  teste:     sem filtro R$  3.889 | com filtro R$  4.098        | p = 0,480

Filtros aleatorios de mesma densidade rendem o mesmo. Combinar as duas pecas
nao produz nada — coerente com o item 16.

## Situacao da fila

As avenidas produtivas estao praticamente esgotadas. Sobrou o item 14 (vies de
sobrevivencia), que depende de uma fonte de dados historicos de listagem que
talvez nao exista publicamente. Fora isso, o que resta sao variacoes de coisas
ja refutadas, e continuar gerando variacoes de hipoteses mortas seria produzir
volume, nao conhecimento.

- [x] 14. Vies de sobrevivencia: NAO ha fonte. 9 dos 65 candidatos morreram e
      seus dados sumiram junto. Direcao do vies reavaliada (ver Ciclo 7)
- [x] 18. Ciclos encerrados

### Ciclo 7 — fechamento

Item 14. Nao existe fonte para reconstruir o universo historico:

  - o endpoint de instrumentos devolve so pares vivos (1.416 de 1.416, nenhum
    suspenso ou expirado)
  - pares delistados respondem "instrumento nao existe" no history-candles:
    a serie de precos some junto com o par. Testados e confirmados mortos:
    FTT, SRM, HT, CEL, MIR, ANC
  - dos 11 candidatos que eu havia descartado, 9 estao MORTOS (EOS, FTM, MKR,
    WAVES, OMG, RUNE, KAVA, ANKR, REN) e 2 apenas tem historico curto
    (DASH, ZEC)

Logo: 9 de 65 candidatos (13,8%) desapareceram no periodo, e o universo de 54
e composto integralmente de sobreviventes. Nao da para medir o efeito.

CORRECAO IMPORTANTE. Eu vinha afirmando, em varios ciclos, que esse vies
inflava o resultado da regra de volatilidade. Para ESTE teste especifico
provavelmente e o contrario:

  carteira sorteada de 5 num universo de 63 com 9 mortos:
    55,0% de chance de conter ao menos um par que foi a zero
  a regra de menor volatilidade escolhe os grandes e estaveis, e quase nunca
  pegaria um deles

Incluir os mortos rebaixaria o CONTROLE mais que a regra, e o p-valor tenderia
a ficar menor, nao maior. Isso e raciocinio, nao medicao — depende de nenhum
dos 9 ter aparecido como baixa volatilidade em algum periodo, e sem os dados
deles nao da para verificar. O relatorio publicado foi corrigido.

## Encerramento

Sete ciclos autonomos. Placar: uma abordagem sobreviveu a teste nulo (selecao
por menor volatilidade, qualificada a carteiras de 3 a 10 ativos com medicao
de 180+ dias), uma ficou parcial (o metodo de risco do livro protege mas nao
preve), cinco nao sobreviveram. Cinco bugs proprios encontrados e corrigidos,
todos os quais inflariam resultado. Tres miragens interceptadas antes de virar
afirmacao.

Os ciclos param aqui. O que restaria seria variar parametros de hipoteses ja
refutadas, o que produz volume e nao conhecimento. As direcoes ainda abertas
exigem coisas que este ambiente nao tem: custo de execucao real de maker,
dados que nao sejam candle (livro de ofertas, funding, fluxo on-chain), ou um
universo que inclua os mortos.
