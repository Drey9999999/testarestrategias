"""Trader autonomo baseado em um modelo de visao open-source rodando local.

O modelo (Qwen2-VL-2B-Instruct, licenca Apache 2.0) recebe SOMENTE a imagem do
grafico de candles ate o fechamento do dia e responde o que fazer no dia
seguinte. Nenhum indicador, preco numerico, ticker ou data e passado ao modelo.

Em vez de gerar texto, lemos as probabilidades dos tokens BUY / SELL / HOLD na
primeira posicao da resposta. E um unico forward (mais rapido) e evita que a
decodificacao gulosa colapse sempre na mesma palavra.

Decisao (sem nenhum ajuste com hindsight): a palavra mais provavel e a decisao.
  BUY  -> ficar comprado          (sinal +1 no motor)
  SELL -> ficar fora              (sinal -1 no motor)
  HOLD -> manter a posicao atual  (sinal  0 no motor)
"""

import csv
import os

MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"
WORDS = ["BUY", "SELL", "HOLD"]

PROMPT = (
    "This is a candlestick chart showing the last 60 trading days of an asset. "
    "Green candles closed up, red candles closed down. You are a technical trading analyst. "
    "Judging ONLY by the price action visible in this chart, what should be done with this asset "
    "at tomorrow's open? Answer with exactly one word: BUY, SELL, or HOLD."
)


class VisionTrader:
    def __init__(self, model_id=MODEL_ID, threads=4):
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText

        torch.set_num_threads(threads)
        self.torch = torch
        self.proc = AutoProcessor.from_pretrained(
            model_id, min_pixels=200 * 28 * 28, max_pixels=640 * 28 * 28)
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id, dtype=torch.float32).eval()
        tok = self.proc.tokenizer
        self.ids = [tok.encode(w, add_special_tokens=False)[0] for w in WORDS]
        msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": PROMPT}]}]
        self.text = self.proc.apply_chat_template(msgs, add_generation_prompt=True)

    def decide(self, image_path):
        """Retorna (decisao, p_buy, p_sell, p_hold) para uma foto do grafico."""
        from PIL import Image
        img = Image.open(image_path).convert("RGB")
        inp = self.proc(text=self.text, images=[img], return_tensors="pt")
        with self.torch.no_grad():
            logits = self.model(**inp).logits[0, -1].float()
        sub = self.torch.tensor([logits[i] for i in self.ids])
        p = self.torch.softmax(sub, 0).tolist()
        return WORDS[int(max(range(3), key=lambda k: p[k]))], p[0], p[1], p[2]


def score_series(chart_paths, cache_csv, log_every=25):
    """Roda o modelo em cada imagem, com cache em CSV para ser retomavel."""
    done = {}
    if os.path.exists(cache_csv):
        with open(cache_csv) as f:
            for row in csv.DictReader(f):
                done[int(row["i"])] = row

    faltam = [i for i in sorted(chart_paths) if i not in done]
    if faltam:
        trader = VisionTrader()
        novo = not os.path.exists(cache_csv)
        with open(cache_csv, "a", newline="") as f:
            w = csv.writer(f)
            if novo:
                w.writerow(["i", "date", "decision", "p_buy", "p_sell", "p_hold"])
            for n, i in enumerate(faltam, 1):
                path = chart_paths[i]
                date = os.path.basename(path).split("_")[1].replace(".png", "")
                d, pb, ps, ph = trader.decide(path)
                w.writerow([i, date, d, f"{pb:.6f}", f"{ps:.6f}", f"{ph:.6f}"])
                f.flush()
                done[i] = {"i": i, "date": date, "decision": d,
                           "p_buy": pb, "p_sell": ps, "p_hold": ph}
                if n % log_every == 0 or n == len(faltam):
                    print(f"  {n}/{len(faltam)} imagens ({date}) ultima decisao={d}", flush=True)
    return done


def decisions_to_signals(n_candles, decisions):
    """BUY -> +1, SELL -> -1, HOLD -> 0, na posicao do candle da decisao."""
    sig = [0] * n_candles
    for i, row in decisions.items():
        d = row["decision"]
        sig[i] = 1 if d == "BUY" else (-1 if d == "SELL" else 0)
    return sig
