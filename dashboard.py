import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

root = Path(__file__).resolve().parent
st.set_page_config(page_title="Pi Paper Trader", layout="wide")
st.title("Pi paper trader (virtual money, not financial advice)")

pc = sqlite3.connect(root / "data" / "paper.db")
eq = pd.read_sql("SELECT * FROM equity ORDER BY date", pc, parse_dates=["date"]).set_index("date")
if eq.empty:
    st.info("No data yet. Run: python src/run_daily.py")
    st.stop()

prices = sqlite3.connect(root / "data" / "prices.db")
nifty = pd.read_sql("SELECT date, close FROM prices WHERE ticker='^NSEI'", prices,
                    parse_dates=["date"]).set_index("date")["close"]
nifty = nifty.reindex(eq.index).ffill()
nifty = nifty / nifty.iloc[0] * eq["value"].iloc[0]

start, now = eq["value"].iloc[0], eq["value"].iloc[-1]
dd = (eq["value"] / eq["value"].cummax() - 1).min() * 100
c1, c2, c3, c4 = st.columns(4)
c1.metric("Portfolio value", f"Rs {now:,.0f}")
c2.metric("Total return", f"{(now / start - 1) * 100:.2f}%")
c3.metric("Cash", f"Rs {eq['cash'].iloc[-1]:,.0f}")
c4.metric("Max drawdown", f"{dd:.2f}%")

st.subheader("Portfolio vs Nifty 50")
st.line_chart(pd.DataFrame({"Portfolio": eq["value"], "Nifty 50": nifty}))

left, right = st.columns(2)
left.subheader("Holdings")
left.dataframe(pd.read_sql("SELECT * FROM positions", pc))
right.subheader("Orders for next open")
right.dataframe(pd.read_sql("SELECT * FROM orders", pc))
st.subheader("Trade log (latest 50)")
st.dataframe(pd.read_sql("SELECT * FROM trades ORDER BY date DESC, rowid DESC LIMIT 50", pc))
