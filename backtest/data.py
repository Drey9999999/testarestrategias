"""Coleta e cache de candles diarios reais (OKX spot, bar=1Dutc)."""

import json
import os
import time
import urllib.request

from .engine import Candle

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
BASE = "https://www.okx.com/api/v5/market/history-candles"


def _get(url, tries=5):
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def fetch(inst_id):
    """Baixa todo o historico diario disponivel na OKX para o par."""
    rows, after = {}, None
    while True:
        url = f"{BASE}?instId={inst_id}&bar=1Dutc&limit=100"
        if after:
            url += f"&after={after}"
        d = _get(url)
        if d.get("code") != "0" or not d.get("data"):
            break
        for c in d["data"]:
            rows[int(c[0])] = c
        oldest = min(int(c[0]) for c in d["data"])
        if after is not None and oldest >= after:
            break
        after = oldest
        time.sleep(0.15)
    return [rows[k] for k in sorted(rows)]


def load(inst_id, refresh=False):
    """Candles diarios fechados, do mais antigo ao mais recente."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, f"{inst_id}_1d.json")
    if refresh or not os.path.exists(path):
        raw = fetch(inst_id)
        with open(path, "w") as f:
            json.dump(raw, f)
    else:
        raw = json.load(open(path))

    candles = []
    for c in raw:
        if c[8] != "1":            # descarta o candle do dia corrente (nao fechado)
            continue
        candles.append(Candle(
            date=time.strftime("%Y-%m-%d", time.gmtime(int(c[0]) / 1000)),
            open=float(c[1]), high=float(c[2]), low=float(c[3]), close=float(c[4]),
        ))
    candles.sort(key=lambda x: x.date)
    return candles
