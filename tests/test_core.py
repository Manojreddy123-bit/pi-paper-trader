import numpy as np
import pandas as pd

from backtest import backtest
from features import FEATURES, add_features


def _prices(n=300):
    rng = np.random.default_rng(0)
    c = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    return pd.DataFrame({"date": pd.date_range("2022-01-01", periods=n), "open": c * 0.999,
                         "high": c * 1.01, "low": c * 0.99, "close": c,
                         "volume": rng.integers(1000, 5000, n).astype(float)})


def test_no_lookahead():
    g = _prices()
    full = add_features(g)
    part = add_features(g.iloc[:250])
    assert np.allclose(full.iloc[:250][FEATURES].values, part[FEATURES].values, equal_nan=True)


def test_rsi_bounds():
    rsi = add_features(_prices())["rsi_14"].dropna()
    assert rsi.between(0, 100).all()


def test_buy_and_hold_matches_manual():
    idx = pd.date_range("2024-01-01", periods=5)
    opens = pd.DataFrame({"A": [10, 11, 12, 13, 14.0]}, index=idx)
    closes = pd.DataFrame({"A": [10.5, 11.5, 12.5, 13.5, 14.5]}, index=idx)
    want = pd.DataFrame({"A": [1] * 5}, index=idx)
    eq, _ = backtest(opens, closes, want, None, cash0=1000, max_pos=1, max_w=1.0, stop=None, cost=0)
    shares = int(1000 // 11)
    assert abs(eq.iloc[-1] - (1000 - shares * 11 + shares * 14.5)) < 1e-6


def test_costs_reduce_returns():
    idx = pd.date_range("2024-01-01", periods=5)
    o = pd.DataFrame({"A": [10.0] * 5}, index=idx)
    w = pd.DataFrame({"A": [1] * 5}, index=idx)
    free, _ = backtest(o, o, w, None, cash0=1000, max_pos=1, max_w=1.0, stop=None, cost=0)
    paid, _ = backtest(o, o, w, None, cash0=1000, max_pos=1, max_w=1.0, stop=None, cost=0.01)
    assert paid.iloc[-1] < free.iloc[-1]


def test_buy_and_hold_matches_manual():
    idx = pd.date_range("2024-01-01", periods=5)
    opens = pd.DataFrame({"A": [10, 11, 12, 13, 14.0]}, index=idx)
    closes = pd.DataFrame({"A": [10.5, 11.5, 12.5, 13.5, 14.5]}, index=idx)
    want = pd.DataFrame({"A": [1] * 5}, index=idx)
    eq, _ = backtest(opens, closes, want, None, cash0=1000, max_pos=1, max_w=1.0, stop=None, cost=0)
    shares = int(1000 // 11)
    assert abs(eq.iloc[-1] - (1000 - shares * 11 + shares * 14.5)) < 1e-6


def test_costs_reduce_returns():
    idx = pd.date_range("2024-01-01", periods=5)
    o = pd.DataFrame({"A": [10.0] * 5}, index=idx)
    w = pd.DataFrame({"A": [1] * 5}, index=idx)
    free, _ = backtest(o, o, w, None, cash0=1000, max_pos=1, max_w=1.0, stop=None, cost=0)
    paid, _ = backtest(o, o, w, None, cash0=1000, max_pos=1, max_w=1.0, stop=None, cost=0.01)
    assert paid.iloc[-1] < free.iloc[-1]
