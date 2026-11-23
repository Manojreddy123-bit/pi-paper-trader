"""Compare Buy&Hold, MA crossover, LightGBM and Nifty on the same out-of-sample period."""
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from backtest import backtest, metrics
from config import CASH0, THRESH
from features import build_dataset
from train import walk_forward

ROOT = Path(__file__).resolve().parent.parent


def main():
    df = build_dataset()
    proba = walk_forward(df)
    opens = df.pivot(index="date", columns="ticker", values="open").dropna()
    closes = df.pivot(index="date", columns="ticker", values="close").dropna()
    cross = df.pivot(index="date", columns="ticker", values="sma_cross").reindex(closes.index)
    start = proba.index.min()
    opens, closes, cross = opens.loc[start:], closes.loc[start:], cross.loc[start:]
    proba = proba.reindex(index=closes.index, columns=closes.columns)
    n = closes.shape[1]
    ones = pd.DataFrame(1, index=closes.index, columns=closes.columns)

    runs = {
        "Buy & hold": backtest(opens, closes, ones, None, max_pos=n, max_w=1 / n, stop=None),
        "MA 20/50 crossover": backtest(opens, closes, (cross > 0).astype(int), cross),
        "LightGBM": backtest(opens, closes, (proba > THRESH).astype(int), proba),
    }
    conn = sqlite3.connect(ROOT / "data" / "prices.db")
    nifty = pd.read_sql("SELECT date, close FROM prices WHERE ticker='^NSEI'", conn,
                        parse_dates=["date"]).set_index("date")["close"]
    nifty = nifty.reindex(closes.index).ffill()

    curves = {k: v[0] for k, v in runs.items()}
    curves["Nifty 50"] = nifty / nifty.iloc[0] * CASH0
    table = pd.DataFrame({k: metrics(v) for k, v in curves.items()}).T
    table["Trades"] = [len(runs[k][1]) if k in runs else 0 for k in table.index]
    print(f"\nOut-of-sample period: {closes.index[0].date()} to {closes.index[-1].date()}\n")
    print(table.round(2).to_string())
    (ROOT / "docs").mkdir(exist_ok=True)
    table.round(2).to_csv(ROOT / "docs" / "results.csv")

    pd.DataFrame(curves).plot(figsize=(11, 5), title="Equity curves (start = Rs 1,00,000)")
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(ROOT / "docs" / "equity_curve.png", dpi=120)
    print("\nSaved docs/equity_curve.png and docs/results.csv")


if __name__ == "__main__":
    main()
