"""LightGBM with walk-forward validation: train only on the past, test on the next year."""
from pathlib import Path

import joblib
import pandas as pd
from lightgbm import LGBMClassifier

from features import FEATURES, build_dataset

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "lgbm.pkl"


def make_model():
    return LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=15,
                          min_child_samples=100, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.8, random_state=42, verbose=-1)


def walk_forward(df):
    """Returns out-of-sample probabilities as a date x ticker table."""
    d = df.dropna(subset=["target"])
    years = d["date"].dt.year
    out = []
    for year in range(years.min() + 3, years.max() + 1):
        start, end = pd.Timestamp(f"{year}-01-01"), pd.Timestamp(f"{year + 1}-01-01")
        train = d[d["date"] < start - pd.Timedelta(days=7)]
        test = d[(d["date"] >= start) & (d["date"] < end)]
        if len(test) == 0:
            continue
        m = make_model().fit(train[FEATURES], train["target"])
        out.append(test.assign(proba=m.predict_proba(test[FEATURES])[:, 1])[["date", "ticker", "proba"]])
    return pd.concat(out).pivot(index="date", columns="ticker", values="proba")


def train_final(df):
    d = df.dropna(subset=["target"])
    m = make_model().fit(d[FEATURES], d["target"])
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(m, MODEL_PATH)
    print("Saved", MODEL_PATH)


if __name__ == "__main__":
    train_final(build_dataset())
