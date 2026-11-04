"""Second pass for data/sp500_pit/raw: retry missing tickers one by one (batch downloads drop
some), then map well-known renamed tickers to their current Yahoo symbol (the old membership
period then uses the renamed company's history, which Yahoo keeps under the new symbol)."""
import os
import time

import pandas as pd
import yfinance as yf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "sp500_pit", "raw")
RENAMES = {  # old S&P ticker -> current Yahoo ticker of the same company
    "FB": "META", "ANTM": "ELV", "UTX": "RTX", "ABC": "COR", "FI": "FISV", "PKI": "RVTY", "WLTW": "WTW",
    "COG": "CTRA", "HCP": "DOC", "PEAK": "DOC", "CDAY": "DAY", "KORS": "CPRI", "SYMC": "GEN", "NLOK": "GEN",
    "CTL": "LUMN", "HFC": "DINO", "ADS": "BFH", "JEC": "J", "BLL": "BALL", "RE": "EG", "FBHS": "FBIN",
    "TMK": "GL", "BHGE": "BKR", "FLT": "CPAY", "PX": "LIN", "GPS": "GAP", "ARNC": "HWM", "DWDP": "DD",
    "WYND": "TNL", "VIAB": "PARA", "VIAC": "PARA", "CBS": "PARA", "DISCA": "WBD", "DISCK": "WBD",
    "TSS": "GPN", "LLL": "LHX", "HRS": "LHX", "XEC": "CTRA", "TWC": "CHTR", "ESV": "VAL", "SCG": "D",
    "ETFC": "MS", "DNB": "DNB", "TGNA": "TGNA", "IAC": "IAC", "ODP": "ODP", "X": "X", "AKS": "CLF",
    "PCP": "BRK-B", "ATVI": "MSFT", "WFM": "AMZN", "MON": "BAYRY", "GOOG": "GOOGL", "MYL": "VTRS",
    "CELG": "BMY", "AGN": "ABBV", "ESRX": "CI", "AET": "CVS", "RHT": "IBM", "COL": "RTX", "RTN": "RTX",
    "SNI": "WBD", "TWX": "WBD", "BRCM": "AVGO", "LLTC": "ADI", "XLNX": "AMD", "MXIM": "ADI", "ALXN": "AZN",
    "CXO": "COP", "NBL": "CVX", "PXD": "XOM", "HES": "CVX", "MRO": "COP", "WRK": "SW", "CTXS": "CTXS",
}
# Acquired companies mapped to their ACQUIRER are NOT the same stock: those are dropped again below.
ACQUIRER_MAPS = {"ETFC", "PCP", "ATVI", "WFM", "MON", "CELG", "AGN", "ESRX", "AET", "RHT", "COL", "RTN", "SNI",
                 "TWX", "BRCM", "LLTC", "XLNX", "MXIM", "ALXN", "CXO", "NBL", "PXD", "HES", "MRO", "TWC", "SCG", "TSS"}


def dl(sym):
    for k in range(3):
        try:
            d = yf.download(sym, start="1994-01-01", progress=False, auto_adjust=True)
            if isinstance(d.columns, pd.MultiIndex):
                d.columns = d.columns.get_level_values(0)
            d = d[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
            return d if len(d) > 50 else None
        except Exception:
            time.sleep(1 + k)
    return None


def main():
    missing = sorted(f[:-8] for f in os.listdir(RAW) if f.endswith(".missing"))
    got = 0
    for t in missing:
        d = dl(t.replace(".", "-"))
        if d is not None:
            d.to_csv(os.path.join(RAW, f"{t}.csv"))
            os.remove(os.path.join(RAW, f"{t}.missing"))
            got += 1
    print("retry recovered", got, "of", len(missing))
    mapped = 0
    for old, new in RENAMES.items():
        if old in ACQUIRER_MAPS or os.path.exists(os.path.join(RAW, f"{old}.csv")) or old == new:
            continue
        src = os.path.join(RAW, f"{new}.csv")
        d = pd.read_csv(src, index_col=0, parse_dates=True) if os.path.exists(src) else dl(new)
        if d is not None and len(d):
            d.to_csv(os.path.join(RAW, f"{old}.csv"))
            if os.path.exists(os.path.join(RAW, f"{old}.missing")):
                os.remove(os.path.join(RAW, f"{old}.missing"))
            mapped += 1
    print("renames mapped", mapped, "| tickers with data:", len([f for f in os.listdir(RAW) if f.endswith(".csv")]))


if __name__ == "__main__":
    main()
