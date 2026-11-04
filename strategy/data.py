"""Data loading (Yahoo Finance via yfinance, cached to CSV) and weekly resampling."""
from __future__ import annotations

import os
import time

import pandas as pd

from .universe import UNIVERSE, file_name

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")


def download(ticker: str, start: str = "1985-01-01") -> pd.DataFrame:
    import yfinance as yf

    last_err = None
    for attempt in range(4):
        try:
            d = yf.download(ticker, start=start, interval="1d", progress=False, auto_adjust=True)
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)
            d = d[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            os.makedirs(RAW_DIR, exist_ok=True)
            d.to_csv(os.path.join(RAW_DIR, file_name(ticker)))
            return d
        except Exception as e:  # network hiccups / rate limits
            last_err = e
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"download failed for {ticker}: {last_err}")


def load_daily(ticker: str, refresh: bool = False, drop_after: str | None = None) -> pd.DataFrame:
    """Daily OHLC from the clean start date. `drop_after` drops bars on/after a date
    (used to remove today's still-forming bar)."""
    path = os.path.join(RAW_DIR, file_name(ticker))
    if refresh or not os.path.exists(path):
        download(ticker)
    d = pd.read_csv(path, index_col=0, parse_dates=True)
    d = d[["Open", "High", "Low", "Close"]].astype(float).dropna()
    d = d[d.index >= UNIVERSE[ticker][2]]
    if drop_after is not None:
        d = d[d.index < drop_after]
    # sanitize: keep O/C inside [L, H]
    d["High"] = d[["High", "Open", "Close"]].max(axis=1)
    d["Low"] = d[["Low", "Open", "Close"]].min(axis=1)
    d = d[~d.index.duplicated(keep="last")].sort_index()
    return d


def to_weekly(d: pd.DataFrame) -> pd.DataFrame:
    """Weekly (Mon-Fri) candles. Index = the LAST trading date of each week, so a weekly
    signal maps to the daily bar on which it becomes known (the week's final close)."""
    wk = d.index.to_period("W-FRI")
    g = d.groupby(wk)
    w = pd.DataFrame({
        "Open": g["Open"].first(),
        "High": g["High"].max(),
        "Low": g["Low"].min(),
        "Close": g["Close"].last(),
        "last_date": g.apply(lambda x: x.index[-1], include_groups=False),
    })
    w = w.set_index("last_date")
    w.index.name = "Date"
    # the final week is still forming unless the data ends on a Friday
    if len(w) and d.index[-1].weekday() != 4:
        w = w.iloc[:-1]
    return w
