"""TD Sequential (DeMark) buy-setup detection.

TD Buy Setup:
  * bearish price flip: close[t] < close[t-4] while close[t-1] >= close[t-5]  -> bar 1
  * nine *consecutive* bars with close < close 4 bars earlier -> "buy setup 9"
  * a close >= close[t-4] before bar 9 cancels the count.
  * perfected:  low of bar 8 or bar 9 <= min(low of bar 6, low of bar 7)
  * TDST (resistance) for a buy setup: the highest high of bars 1..9.

A completed buy setup marks seller exhaustion of a decline -> candidate for a
tactical long ("play the aggregate after the sell-off").
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def td_buy_setup_count(close: pd.Series) -> pd.Series:
    c = close.to_numpy()
    cnt = np.zeros(len(c), dtype=int)
    for t in range(4, len(c)):
        if c[t] < c[t - 4]:
            cnt[t] = cnt[t - 1] + 1
        else:
            cnt[t] = 0
    return pd.Series(cnt, index=close.index, name="buy_setup")


def td_sell_setup_count(close: pd.Series) -> pd.Series:
    c = close.to_numpy()
    cnt = np.zeros(len(c), dtype=int)
    for t in range(4, len(c)):
        cnt[t] = cnt[t - 1] + 1 if c[t] > c[t - 4] else 0
    return pd.Series(cnt, index=close.index, name="sell_setup")


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_c = df["Close"].shift(1)
    tr = pd.concat([df["High"] - df["Low"], (df["High"] - prev_c).abs(), (df["Low"] - prev_c).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()  # Wilder


def buy_setup_signals(df: pd.DataFrame, dd_lookback: int) -> pd.DataFrame:
    """One row per completed buy setup 9 (count == 9 exactly).

    Columns: high/low/close of the signal (9th) candle, ATR, perfected flag, TDST,
    drawdown of the close vs the rolling max close over `dd_lookback` bars (selloff depth),
    and the % decline across the setup itself.
    """
    cnt = td_buy_setup_count(df["Close"])
    a = atr(df)
    roll_max = df["Close"].rolling(dd_lookback, min_periods=max(20, dd_lookback // 4)).max()
    dd = df["Close"] / roll_max - 1.0
    idx = np.flatnonzero(cnt.to_numpy() == 9)
    rows = []
    H, L, C = df["High"].to_numpy(), df["Low"].to_numpy(), df["Close"].to_numpy()
    for i in idx:
        if i < 9:
            continue
        b = lambda k: i - 9 + k  # position of setup bar k (1..9)
        perfected = min(L[b(8)], L[b(9)]) <= min(L[b(6)], L[b(7)])
        rows.append({
            "date": df.index[i],
            "pos": i,
            "high": H[i],
            "low": L[i],
            "close": C[i],
            "atr": a.iloc[i],
            "perfected": bool(perfected),
            "tdst": H[b(1):i + 1].max(),
            "drawdown": dd.iloc[i],
            "setup_decline": C[i] / C[b(1) - 1] - 1.0,
        })
    return pd.DataFrame(rows)
