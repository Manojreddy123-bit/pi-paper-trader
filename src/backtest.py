"""Daily backtester. Signal at close of day t -> trade at OPEN of day t+1, with costs and risk rules."""
import numpy as np
import pandas as pd

from config import CASH0, COST, MAX_POS, MAX_W, STOP


def backtest(opens, closes, want, score=None, cash0=CASH0, max_pos=MAX_POS,
             max_w=MAX_W, stop=STOP, cost=COST):
    cols, dates = list(closes.columns), closes.index
    want = want.reindex(index=dates, columns=cols).fillna(0)
    if score is not None:
        score = score.reindex(index=dates, columns=cols).fillna(0)
    cash, pos, eq, trades = float(cash0), {}, [], []
    for i, d in enumerate(dates):
        if i > 0:
            prev, sig, stopped = dates[i - 1], want.loc[dates[i - 1]], set()
            for t in list(pos):
                sh, ep = pos[t]
                hit = stop is not None and closes.at[prev, t] < ep * (1 - stop)
                if sig[t] != 1 or hit:
                    px = opens.at[d, t]
                    cash += sh * px * (1 - cost)
                    trades.append((d, t, "SELL", sh, px))
                    del pos[t]
                    if hit:
                        stopped.add(t)
            equity_open = cash + sum(sh * opens.at[d, t] for t, (sh, _) in pos.items())
            cand = [t for t in cols if sig[t] == 1 and t not in pos and t not in stopped]
            if score is not None:
                cand.sort(key=lambda t: -score.at[prev, t])
            for t in cand:
                if len(pos) >= max_pos:
                    break
                px = opens.at[d, t]
                sh = int(min(equity_open * max_w, cash / (1 + cost)) // px)
                if sh < 1:
                    continue
                cash -= sh * px * (1 + cost)
                pos[t] = (sh, px)
                trades.append((d, t, "BUY", sh, px))
        eq.append(cash + sum(sh * closes.at[d, t] for t, (sh, _) in pos.items()))
    return pd.Series(eq, index=dates), pd.DataFrame(trades, columns=["date", "ticker", "side", "shares", "price"])


def metrics(eq):
    r = eq.pct_change().dropna()
    years = len(r) / 252
    return {
        "Total return %": (eq.iloc[-1] / eq.iloc[0] - 1) * 100,
        "CAGR %": ((eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1) * 100,
        "Sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else 0.0,
        "Max drawdown %": (eq / eq.cummax() - 1).min() * 100,
        "Final value": eq.iloc[-1],
    }
