"""Download Yahoo daily data for every ticker that was ever in the S&P 500 since 1996
(point-in-time membership from github.com/fja05680/sp500). Delisted names are often missing
on Yahoo; the coverage is measured in scripts/sp500_pit_study.py.

Usage:  python scripts/sp500_pit_data.py   -> data/sp500_pit/raw/<ticker>.csv
"""
import os

import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "sp500_pit")
RAW = os.path.join(DIR, "raw")


def yahoo(t):
    return t.replace(".", "-")


def main():
    os.makedirs(RAW, exist_ok=True)
    hist = pd.read_csv(os.path.join(DIR, "sp500_historical.csv"))
    tickers = sorted({t for row in hist.tickers for t in row.split(",")})
    todo = [t for t in tickers if not os.path.exists(os.path.join(RAW, f"{t}.csv")) and
            not os.path.exists(os.path.join(RAW, f"{t}.missing"))]
    print(len(tickers), "tickers,", len(todo), "to download", flush=True)
    for k in range(0, len(todo), 40):
        batch = todo[k:k + 40]
        d = yf.download([yahoo(t) for t in batch], start="1994-01-01", interval="1d", progress=False,
                        auto_adjust=True, group_by="ticker", threads=True)
        for t in batch:
            try:
                x = d[yahoo(t)][["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            except Exception:
                x = pd.DataFrame()
            if len(x) > 50:
                x.to_csv(os.path.join(RAW, f"{t}.csv"))
            else:
                open(os.path.join(RAW, f"{t}.missing"), "w").close()
        got = len([f for f in os.listdir(RAW) if f.endswith(".csv")])
        print(f"  {k + len(batch)}/{len(todo)}  with data: {got}", flush=True)


if __name__ == "__main__":
    main()
