"""Build the 'biggest 100 US stocks' universe: S&P 500 constituents (Wikipedia) ranked by
current market cap (Yahoo Finance), one share class per company.

Usage:  python scripts/us100_universe.py   -> data/us100/universe.csv
Note: this is TODAY's top 100, so any backtest on it carries survivorship bias.
"""
import io
import os
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "us100")


def mcap(sym):
    for k in range(3):
        try:
            fi = yf.Ticker(sym).fast_info
            return sym, float(fi["market_cap"])
        except Exception:
            time.sleep(2 * (k + 1))
    return sym, float("nan")


def main():
    os.makedirs(OUT, exist_ok=True)
    html = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                        headers={"User-Agent": "Mozilla/5.0 (research script)"}, timeout=30).text
    sp = pd.read_html(io.StringIO(html))[0]
    sp["yf"] = sp["Symbol"].str.replace(".", "-", regex=False)
    with ThreadPoolExecutor(8) as ex:
        caps = dict(ex.map(mcap, sp["yf"]))
    sp["market_cap"] = sp["yf"].map(caps)
    sp = sp.dropna(subset=["market_cap"]).sort_values("market_cap", ascending=False)
    # one share class per company (GOOGL/GOOG, FOXA/FOX, NWSA/NWS, BRK-B)
    sp = sp.drop_duplicates(subset="CIK", keep="first")
    top = sp.head(100).reset_index(drop=True)
    top["rank"] = top.index + 1
    top["as_of"] = pd.Timestamp.today().date().isoformat()
    top[["rank", "yf", "Security", "GICS Sector", "market_cap", "Date added", "as_of"]].rename(
        columns={"yf": "ticker", "Security": "name", "GICS Sector": "sector", "Date added": "sp500_added"}
    ).to_csv(os.path.join(OUT, "universe.csv"), index=False)
    print(top[["rank", "yf", "Security", "market_cap"]].head(15).to_string())
    print("missing caps:", sp["market_cap"].isna().sum(), "| #100 cap:", round(top.market_cap.iloc[-1] / 1e9, 1), "bn")


if __name__ == "__main__":
    main()
