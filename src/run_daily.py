"""Run after market close: refresh data, fill yesterday's orders at today's open,
mark portfolio, generate tomorrow's orders, send Telegram summary."""
import logging
from pathlib import Path

import joblib

from broker import Broker
from config import MAX_POS, THRESH
from data import refresh_all
from features import FEATURES, build_dataset
from notify import send

MODEL = Path(__file__).resolve().parent.parent / "models" / "lgbm.pkl"
log = logging.getLogger("daily")


def main():
    refresh_all()
    df = build_dataset()
    last = df["date"].max()
    day = last.strftime("%Y-%m-%d")
    today = df[df["date"] == last].set_index("ticker")

    b = Broker()
    if b.get("last_day") == day:
        log.info("Already processed %s (market holiday or rerun). Exiting.", day)
        print(f"Already processed {day}.")
        return

    prev_equity = b.last_equity()
    filled = b.execute_orders(day, today["open"].to_dict())
    stopped = b.stopped(today["close"].to_dict())
    equity = b.mark(day, today["close"].to_dict())

    model = joblib.load(MODEL)
    today = today.assign(proba=model.predict_proba(today[FEATURES])[:, 1])
    held = b.holdings()
    want = set(today.index[today["proba"] > THRESH])
    sells = [t for t in held if t not in want or t in stopped]
    ranked = today.sort_values("proba", ascending=False).index
    cand = [t for t in ranked if t in want and t not in held and t not in stopped]
    slots = max(MAX_POS - (len(held) - len(sells)), 0)
    buys = cand[:slots]
    b.set_orders(day, sells, buys)
    b.set("last_day", day)

    chg = (equity / prev_equity - 1) * 100
    send(f"Paper trader {day}\n"
         f"Value: Rs {equity:,.0f} ({chg:+.2f}% today)\n"
         f"Cash: Rs {b.cash:,.0f} | Holdings: {len(b.holdings())}\n"
         f"Filled today: {', '.join(filled) or 'none'}\n"
         f"Orders for next open: SELL {sells or 'none'} | BUY {buys or 'none'}\n"
         f"(paper trading only, not financial advice)")


if __name__ == "__main__":
    main()
