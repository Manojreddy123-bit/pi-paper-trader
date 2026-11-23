import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

root = Path(__file__).resolve().parent.parent
conn = sqlite3.connect(root / "data" / "prices.db")
df = pd.read_sql("SELECT ticker, date, close FROM prices", conn, parse_dates=["date"])
px = df.pivot(index="date", columns="ticker", values="close")

pick = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "^NSEI"]
sub = px[pick].dropna()
norm = sub / sub.iloc[0] * 100

norm.plot(figsize=(11, 5), title="Price growth (start = 100)")
plt.ylabel("Indexed price")
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(root / "docs" / "prices.png", dpi=120)
print("Saved docs/prices.png")
