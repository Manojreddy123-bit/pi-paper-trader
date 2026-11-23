"""Technical features + labels. Every feature uses only data up to day t (no look-ahead)."""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

DB = Path(__file__).resolve().parent.parent / "data" / "prices.db"
FEATURES = ["ret_1", "ret_5", "ret_20", "sma_ratio_5", "sma_ratio_20", "sma_ratio_50",
            "sma_cross", "rsi_14", "macd", "macd_signal", "vol_20", "vol_chg"]


def add_features(g):
    g = g.sort_values("date").copy()
    c = g["close"]
    g["ret_1"] = c.pct_change()
    g["ret_5"] = c.pct_change(5)
    g["ret_20"] = c.pct_change(20)
    for n in (5, 20, 50):
        g[f"sma_ratio_{n}"] = c / c.rolling(n).mean() - 1
    g["sma_cross"] = c.rolling(20).mean() / c.rolling(50).mean() - 1
    delta = c.diff()
    up = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    g["rsi_14"] = 100 - 100 / (1 + up / dn)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    g["macd"] = (ema12 - ema26) / c
    g["macd_signal"] = g["macd"].ewm(span=9, adjust=False).mean()
    g["vol_20"] = g["ret_1"].rolling(20).std()
    g["vol_chg"] = g["volume"] / g["volume"].rolling(20).mean() - 1
    # Decide at close of day t, buy at open of t+1, outcome = open(t+2)/open(t+1)-1
    g["fwd_ret"] = g["open"].shift(-2) / g["open"].shift(-1) - 1
    g["target"] = np.where(g["fwd_ret"].isna(), np.nan, (g["fwd_ret"] > 0).astype(float))
    return g


def build_dataset():
    conn = sqlite3.connect(DB)
    px = pd.read_sql("SELECT * FROM prices WHERE ticker != '^NSEI'", conn, parse_dates=["date"])
    conn.close()
    df = pd.concat([add_features(g) for _, g in px.groupby("ticker")])
    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES)
    return df.reset_index(drop=True)


if __name__ == "__main__":
    d = build_dataset()
    print(d.shape)
    print(d[["ticker", "date"] + FEATURES + ["target"]].tail())
