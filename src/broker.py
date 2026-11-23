"""Virtual account stored in SQLite: cash, positions, pending orders, trades, daily equity."""
import sqlite3
from pathlib import Path

from config import CASH0, COST, MAX_W, STOP

DB = Path(__file__).resolve().parent.parent / "data" / "paper.db"


class Broker:
    def __init__(self):
        DB.parent.mkdir(exist_ok=True)
        self.c = sqlite3.connect(DB)
        self.c.executescript("""
            CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE IF NOT EXISTS positions (ticker TEXT PRIMARY KEY, shares INTEGER, entry_price REAL, entry_date TEXT);
            CREATE TABLE IF NOT EXISTS orders (ticker TEXT, side TEXT, signal_date TEXT);
            CREATE TABLE IF NOT EXISTS trades (date TEXT, ticker TEXT, side TEXT, shares INTEGER, price REAL);
            CREATE TABLE IF NOT EXISTS equity (date TEXT PRIMARY KEY, value REAL, cash REAL);
        """)
        if self.get("cash") is None:
            self.set("cash", CASH0)

    def get(self, key):
        r = self.c.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
        return r[0] if r else None

    def set(self, key, value):
        self.c.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (key, str(value)))
        self.c.commit()

    @property
    def cash(self):
        return float(self.get("cash"))

    def holdings(self):
        rows = self.c.execute("SELECT ticker, shares, entry_price FROM positions").fetchall()
        return {t: (sh, ep) for t, sh, ep in rows}

    def last_equity(self):
        r = self.c.execute("SELECT value FROM equity ORDER BY date DESC LIMIT 1").fetchone()
        return r[0] if r else CASH0

    def execute_orders(self, day, opens):
        """Fill pending orders at today's open. Sells first, then buys."""
        orders = self.c.execute("SELECT ticker, side FROM orders ORDER BY rowid").fetchall()
        cash, pos, log = self.cash, self.holdings(), []
        for t, side in orders:
            px = opens.get(t)
            if side == "SELL" and t in pos and px is not None and px == px:
                sh, _ = pos.pop(t)
                cash += sh * px * (1 - COST)
                self.c.execute("DELETE FROM positions WHERE ticker=?", (t,))
                self.c.execute("INSERT INTO trades VALUES (?,?,?,?,?)", (day, t, "SELL", sh, float(px)))
                log.append(f"SELL {t} x{sh} @ {px:.2f}")
        equity_open = cash + sum(sh * opens.get(t, ep) for t, (sh, ep) in pos.items())
        for t, side in orders:
            px = opens.get(t)
            if side == "BUY" and t not in pos and px is not None and px == px:
                sh = int(min(equity_open * MAX_W, cash / (1 + COST)) // px)
                if sh < 1:
                    continue
                cash -= sh * px * (1 + COST)
                pos[t] = (sh, float(px))
                self.c.execute("INSERT INTO positions VALUES (?,?,?,?)", (t, sh, float(px), day))
                self.c.execute("INSERT INTO trades VALUES (?,?,?,?,?)", (day, t, "BUY", sh, float(px)))
                log.append(f"BUY {t} x{sh} @ {px:.2f}")
        self.c.execute("DELETE FROM orders")
        self.set("cash", cash)
        return log

    def stopped(self, closes):
        return {t for t, (sh, ep) in self.holdings().items()
                if closes.get(t) is not None and closes.get(t) < ep * (1 - STOP)}

    def mark(self, day, closes):
        eq = self.cash + sum(sh * closes.get(t, ep) for t, (sh, ep) in self.holdings().items())
        self.c.execute("INSERT OR REPLACE INTO equity VALUES (?,?,?)", (day, eq, self.cash))
        self.c.commit()
        return eq

    def set_orders(self, day, sells, buys):
        self.c.execute("DELETE FROM orders")
        for t in sells:
            self.c.execute("INSERT INTO orders VALUES (?,?,?)", (t, "SELL", day))
        for t in buys:
            self.c.execute("INSERT INTO orders VALUES (?,?,?)", (t, "BUY", day))
        self.c.commit()
