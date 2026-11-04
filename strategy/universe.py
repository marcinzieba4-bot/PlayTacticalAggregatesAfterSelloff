"""Universe: developed-market (DM) equity indices + US sector ETFs (main sectors)."""

# ticker -> (name, group, first clean date)
# "first clean date" = first date from which Yahoo has real OHLC candles (before that,
# several indices only carry O=H=L=C closes, which makes candle-based stops meaningless).
UNIVERSE = {
    # --- DM indices ---
    "^GSPC":      ("S&P 500",            "DM index", "1990-01-01"),
    "^NDX":       ("Nasdaq 100",         "DM index", "1990-01-01"),
    "^DJI":       ("Dow Jones 30",       "DM index", "1992-03-01"),
    "^RUT":       ("Russell 2000",       "DM index", "1990-01-01"),
    "^GSPTSE":    ("S&P/TSX (Canada)",   "DM index", "1990-01-01"),
    "^STOXX50E":  ("Euro Stoxx 50",      "DM index", "2007-06-01"),
    "^GDAXI":     ("DAX (Germany)",      "DM index", "1994-01-01"),
    "^FTSE":      ("FTSE 100 (UK)",      "DM index", "1990-01-01"),
    "^FCHI":      ("CAC 40 (France)",    "DM index", "1990-06-01"),
    "^AEX":       ("AEX (Netherlands)",  "DM index", "1993-01-01"),
    "^IBEX":      ("IBEX 35 (Spain)",    "DM index", "1993-10-01"),
    "^SSMI":      ("SMI (Switzerland)",  "DM index", "1991-03-01"),
    "FTSEMIB.MI": ("FTSE MIB (Italy)",   "DM index", "2004-01-01"),
    "^N225":      ("Nikkei 225 (Japan)", "DM index", "1989-01-01"),
    "^AXJO":      ("ASX 200 (Australia)", "DM index", "2001-01-01"),
    "^HSI":       ("Hang Seng (HK)",     "DM index", "1990-01-01"),
    # --- US sectors (SPDR Select Sector ETFs, dividend-adjusted) ---
    "XLK":  ("Technology",             "US sector", "1999-03-01"),
    "XLF":  ("Financials",             "US sector", "1999-03-01"),
    "XLE":  ("Energy",                 "US sector", "1999-03-01"),
    "XLV":  ("Health Care",            "US sector", "1999-03-01"),
    "XLI":  ("Industrials",            "US sector", "1999-03-01"),
    "XLY":  ("Consumer Discretionary", "US sector", "1999-03-01"),
    "XLP":  ("Consumer Staples",       "US sector", "1999-03-01"),
    "XLU":  ("Utilities",              "US sector", "1999-03-01"),
    "XLB":  ("Materials",              "US sector", "1999-03-01"),
    "XLRE": ("Real Estate",            "US sector", "2016-06-01"),
    "XLC":  ("Communication Services", "US sector", "2018-09-01"),
}


def file_name(ticker: str) -> str:
    return ticker.replace("^", "") + ".csv"
