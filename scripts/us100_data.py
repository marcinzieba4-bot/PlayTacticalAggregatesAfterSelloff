"""Download daily OHLC (dividend/split adjusted) for the US-100 universe -> data/us100/raw/."""
import os
import time

import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "us100", "raw")


def main():
    os.makedirs(RAW, exist_ok=True)
    uni = pd.read_csv(os.path.join(ROOT, "data", "us100", "universe.csv"))
    for t in uni.ticker:
        path = os.path.join(RAW, f"{t}.csv")
        if os.path.exists(path):
            continue
        for k in range(4):
            try:
                d = yf.download(t, start="1985-01-01", interval="1d", progress=False, auto_adjust=True)
                if isinstance(d.columns, pd.MultiIndex):
                    d.columns = d.columns.get_level_values(0)
                d[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"]).to_csv(path)
                print(t, d.index[0].date(), len(d), flush=True)
                break
            except Exception as e:
                print("retry", t, e)
                time.sleep(2 ** (k + 1))


if __name__ == "__main__":
    main()
