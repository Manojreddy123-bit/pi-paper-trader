"""Download daily prices for NSE stocks into SQLite. Re-running only fetches new days."""
import logging
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "prices.db"
YEARS = 6
INDEX = "^NSEI"
TICKERS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "LT.NS", "BHARTIARTL.NS", "HINDUNILVR.NS",
    "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "WIPRO.NS",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("data")


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL, date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, volume REAL,
            PRIMARY KEY (ticker, date))""")
    conn.commit()


def last_date(conn, ticker):
    return conn.execute("SELECT MAX(date) FROM prices WHERE ticker = ?", (ticker,)).fetchone()[0]


def fetch(ticker, start=None, retries=3):
    for attempt in range(1, retries + 1):
        try:
            kwargs = {"start": start} if start else {"period": f"{YEARS}y"}
            df = yf.Ticker(ticker).history(auto_adjust=True, **kwargs)
            if df.empty:
                raise ValueError("no data returned")
            df = df.reset_index()
            df = df.rename(columns=str.lower)
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            return df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
        except Exception as e:
            log.warning("%s attempt %d/%d failed: %s", ticker, attempt, retries, e)
            time.sleep(2 * attempt)
    return None


def save(conn, ticker, df):
    rows = [(ticker, *r) for r in df.itertuples(index=False, name=None)]
    conn.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?)", rows)
    conn.commit()
    return len(rows)


def refresh_all():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)
    failed = []
    for t in TICKERS + [INDEX]:
        last = last_date(conn, t)
        start = (datetime.strptime(last, "%Y-%m-%d") - timedelta(days=5)).strftime("%Y-%m-%d") if last else None
        df = fetch(t, start)
        if df is None:
            failed.append(t)
            continue
        n = save(conn, t, df)
        log.info("%-14s saved %4d rows (latest %s)", t, n, df["date"].iloc[-1])
    conn.close()
    if failed:
        log.error("Failed tickers: %s", failed)
    else:
        log.info("All tickers updated.")


if __name__ == "__main__":
    refresh_all()
