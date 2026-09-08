"""Cabeca treinada com afinco: muitas passagens sobre todos os anos de grafico.

Diferencas para `online_brain`:

- **Horizonte do alvo.** Prever a direcao de amanha e o alvo mais ruidoso que
  existe e forca centenas de operacoes. Aqui o alvo e o retorno de H dias, o
  que aumenta a razao sinal-ruido e derruba o giro naturalmente.
- **Treino profundo periodico.** A cada `intervalo` dias a cabeca faz varias
  epocas sobre TODO o historico ja realizado, nao apenas alguns passos no
  ultimo lote. E o "suar" pedido: ela reve os anos inteiros muitas vezes.
- **Regularizacao.** Dropout e weight decay, porque capacidade sem freio em
  serie ruidosa decora ruido.

Causalidade: no fechamento do dia t a decisao vale para [abertura t+1,
abertura t+1+H], e o rotulo so fecha na abertura de t+1+H. Portanto no dia t
o treino so pode usar amostras k com k + 1 + H <= t.
"""

import torch
import torch.nn as nn

from .features import Memoria, MEMORY_NAMES
from . import book_features


class Cabeca(nn.Module):
    def __init__(self, dim, oculto=32, dropout=0.2):
        super().__init__()
        self.rede = nn.Sequential(
            nn.Linear(dim, oculto), nn.Tanh(), nn.Dropout(dropout),
            nn.Linear(oculto, oculto // 2), nn.Tanh(), nn.Dropout(dropout),
            nn.Linear(oculto // 2, 1))

    def forward(self, x):
        return self.rede(x).squeeze(-1)


class Normalizador:
    def __init__(self, dim):
        self.n = 0
        self.media = [0.0] * dim
        self.m2 = [0.0] * dim

    def atualizar(self, x):
        self.n += 1
        for j, v in enumerate(x):
            d = v - self.media[j]
            self.media[j] += d / self.n
            self.m2[j] += d * (v - self.media[j])

    def aplicar(self, x):
        if self.n < 2:
            return list(x)
        out = []
        for j, v in enumerate(x):
            sd = (self.m2[j] / (self.n - 1)) ** 0.5 or 1.0
            out.append(max(-5.0, min(5.0, (v - self.media[j]) / sd)))
        return out


def rodar(candles, inicio, horizonte=10, congelar_em=None, usar_memoria=True,
          lr=0.003, oculto=32, dropout=0.2, weight_decay=1e-4,
          passos_por_dia=4, epocas_profundas=8, intervalo=60, lote=64,
          semente=0, limiar=0.5, banda=0.0, hold_minimo=0):
    """Percorre a serie decidindo e treinando com afinco.

    Devolve (sinais, diario). `sinais` alimenta o mesmo motor de backtest de
    sempre: +1 comprado, -1 fora, executado na abertura seguinte.
    """
    torch.manual_seed(semente)
    gen = torch.Generator().manual_seed(semente)
    nomes = book_features.NAMES + MEMORY_NAMES
    dim = len(nomes)
    pre = book_features.precalcular(candles)

    modelo = Cabeca(dim, oculto, dropout)
    opt = torch.optim.AdamW(modelo.parameters(), lr=lr, weight_decay=weight_decay)
    perda_fn = nn.BCEWithLogitsLoss()
    norm = Normalizador(dim)
    mem = Memoria()

    n = len(candles)
    fim = n - horizonte - 1
    BX = torch.zeros(n, dim, dtype=torch.float32)
    BY = torch.zeros(n, dtype=torch.float32)
    nb = 0
    xs, pos = {}, {}
    entrou_em = None            # dia da entrada, para o periodo minimo
    sinais = [0] * n
    diario = []
    congelado = False
    epocas_feitas = 0

    def treinar(epocas):
        """Varre o buffer inteiro `epocas` vezes."""
        nonlocal epocas_feitas
        if nb < lote:
            return
        X, Y = BX[:nb], BY[:nb]
        modelo.train()
        for _ in range(epocas):
            ordem = torch.randperm(nb, generator=gen)
            for i0 in range(0, nb - lote + 1, lote):
                idx = ordem[i0:i0 + lote]
                opt.zero_grad()
                perda_fn(modelo(X[idx]), Y[idx]).backward()
                opt.step()
            epocas_feitas += 1
        modelo.eval()

    for t in range(inicio, fim):
        if congelar_em is not None and candles[t].date >= congelar_em:
            congelado = True

        # 1) fecha rotulos ja realizados: amostra k so entra quando k+1+H <= t
        k = t - 1 - horizonte
        if k >= inicio:
            r_k = candles[k + 1 + horizonte].open / candles[k + 1].open - 1
            mem.registrar(r_k, pos[k] == 1)
            norm.atualizar(xs[k])
            BX[nb] = torch.tensor(norm.aplicar(xs[k]), dtype=torch.float32)
            BY[nb] = 1.0 if r_k > 0 else 0.0
            nb += 1
            if not congelado:
                if passos_por_dia:
                    modelo.train()
                    X, Y = BX[:nb], BY[:nb]
                    for _ in range(passos_por_dia):
                        idx = torch.randint(0, nb, (lote,), generator=gen)
                        opt.zero_grad()
                        perda_fn(modelo(X[idx]), Y[idx]).backward()
                        opt.step()
                    modelo.eval()
                # treino profundo periodico: revisita todos os anos de grafico
                if intervalo and (t - inicio) % intervalo == 0:
                    treinar(epocas_profundas)

        # 2) features do dia
        x = book_features.features(candles, t, pre) + (
            mem.features() if usar_memoria else [0.0] * len(MEMORY_NAMES))
        xs[t] = x

        # 3) decide com histerese
        with torch.no_grad():
            p = torch.sigmoid(modelo(
                torch.tensor([norm.aplicar(x)], dtype=torch.float32)))[0].item()
        ant = pos.get(t - 1, 0)
        novo = (1 if p > limiar + banda else 0) if ant == 0 else (0 if p < limiar - banda else 1)
        # periodo minimo de permanencia: entrou, segura ao menos `hold_minimo`
        # dias. E o que de fato corta o giro — horizonte do alvo sozinho nao
        # corta, porque a decisao continua sendo diaria.
        if hold_minimo and ant == 1 and entrou_em is not None and (t - entrou_em) < hold_minimo:
            novo = 1
        if novo == 1 and ant == 0:
            entrou_em = t
        pos[t] = novo
        mem.posicionado = pos[t]
        sinais[t] = 1 if pos[t] == 1 else -1
        diario.append({"data": candles[t].date, "p": p, "posicao": pos[t],
                       "acertou": None, "congelado": int(congelado),
                       "epocas": epocas_feitas})

    # marca, para cada previsao, se ela acertou a direcao do periodo seguinte.
    # E acerto genuinamente preditivo: no dia t o modelo nao tinha esse rotulo.
    for d in diario:
        pass
    por_data = {d["data"]: d for d in diario}
    for t in range(inicio, fim):
        if t + 1 + horizonte < n:
            r = candles[t + 1 + horizonte].open / candles[t + 1].open - 1
            d = por_data.get(candles[t].date)
            if d is not None:
                d["acertou"] = int((d["p"] > 0.5) == (r > 0))

    # acerto DENTRO da amostra: o modelo final aplicado ao que ele ja treinou
    dentro = None
    if nb >= lote:
        modelo.eval()
        with torch.no_grad():
            pr = torch.sigmoid(modelo(BX[:nb]))
        dentro = float(((pr > 0.5).float() == BY[:nb]).float().mean())

    return sinais, {"diario": diario, "acerto_dentro": dentro,
                    "epocas": epocas_feitas, "amostras": nb}
