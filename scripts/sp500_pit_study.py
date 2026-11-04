"""MACD strategy on the 100 biggest S&P 500 members chosen POINT-IN-TIME (less survivorship bias).

Universe: S&P 500 membership on each date since 1996 (github.com/fja05680/sp500). Every month,
the 100 largest members by trailing 1-year average dollar volume (price x volume, a size proxy:
historical market caps are not freely available) form the tradable list for that month. A MACD
signal is taken only if the stock is in that list on the signal date. Positions are then
managed by the usual rules (MACD < 0 stop, 1-year exit, optional 1 % stop + re-entry);
a stock whose data ends mid-trade (delisted / acquired) is closed at its last price.

Remaining bias: Yahoo only has ~62 % of all historical members (mostly delisted names are
missing, e.g. bankruptcies and takeovers), so the tradable list is drawn from the members
that have data. Coverage per year is reported. Tickers re-used by a different company can
also map a membership period to the wrong price history.

Usage:  python scripts/sp500_pit_study.py   -> results/sp500_pit/
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import macd_variants_study as mv  # noqa: E402
from strategy.backtest import SPLIT_DATE  # noqa: E402
from strategy.data import to_weekly  # noqa: E402
from strategy.macd_engine import simulate_campaign as _sim  # noqa: E402

DIR = os.path.join(ROOT, "data", "sp500_pit")
OUT = os.path.join(ROOT, "results", "sp500_pit")
CUTOFF = pd.Timestamp(os.environ.get("DATA_CUTOFF", "2026-11-04"))
START = pd.Timestamp("1997-01-01")
TOP = 100


def load(t):
    d = pd.read_csv(os.path.join(DIR, "raw", f"{t}.csv"), index_col=0, parse_dates=True)
    d = d[["Open", "High", "Low", "Close", "Volume"]].astype(float)
    d = d[(d.index < CUTOFF) & (d[["Open", "High", "Low", "Close"]] > 0).all(axis=1)].dropna()
    d["High"] = d[["High", "Open", "Close"]].max(axis=1)
    d["Low"] = d[["Low", "Open", "Close"]].min(axis=1)
    return d[~d.index.duplicated()]


def membership(cal):
    h = pd.read_csv(os.path.join(DIR, "sp500_historical.csv"), parse_dates=["date"])
    h = h.set_index("date")["tickers"].str.split(",")
    rows = h.reindex(cal, method="ffill")
    return rows


def main():
    os.makedirs(OUT, exist_ok=True)
    tickers = sorted(f[:-4] for f in os.listdir(os.path.join(DIR, "raw")) if f.endswith(".csv"))
    data = {t: load(t) for t in tickers}
    data = {t: d for t, d in data.items() if len(d) > 300}
    cal = pd.DatetimeIndex(sorted(set().union(*[set(d.index) for d in data.values()])))
    cal = cal[(cal >= pd.Timestamp("1996-01-02"))]
    mem = membership(cal)
    # coverage: share of members that have price data on that day
    have = {t: set(d.index) for t, d in data.items()}
    cov_rows = []
    for y in range(1996, 2027):
        days = cal[(cal.year == y)]
        if len(days) == 0:
            continue
        dd = days[len(days) // 2]
        m = mem.loc[dd]
        cov_rows.append({"year": y, "members": len(m), "with_data": sum(1 for t in m if t in have and dd in have[t])})
    cov = pd.DataFrame(cov_rows)
    cov["coverage_%"] = 100 * cov.with_data / cov.members
    print(cov.to_string(index=False), flush=True)

    # monthly top-100 by trailing 1-year dollar volume among members with data
    dv = pd.DataFrame({t: (d["Close"] * d["Volume"]).rolling(252, min_periods=200).mean() for t, d in data.items()}).reindex(cal)
    month_starts = pd.DatetimeIndex(sorted(set(cal.to_series().groupby(cal.to_period("M")).min())))
    elig = pd.DataFrame(False, index=cal, columns=list(data))
    top_lists = {}
    for ms in month_starts:
        members = [t for t in mem.loc[ms] if t in data]
        v = dv.loc[ms, members].dropna().sort_values(ascending=False)
        top = list(v.index[:TOP])
        top_lists[ms] = top
        nxt = month_starts[month_starts > ms]
        end = nxt[0] if len(nxt) else cal[-1] + pd.Timedelta(days=1)
        elig.loc[(elig.index >= ms) & (elig.index < end), top] = True
    pd.Series({str(k.date()): ",".join(v) for k, v in top_lists.items()}).to_csv(os.path.join(OUT, "top100_by_month.csv"))

    # instruments + signals (fresh MACD up-phase, stock in that month's top 100)
    inst, rows = {}, []
    for t, d in data.items():
        w = to_weekly(d)
        macd = w["Close"].ewm(span=12, adjust=False).mean() - w["Close"].ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        on = (macd > 0) & (sig > 0)
        on.iloc[:35] = False
        fresh = (on & ~on.shift(1, fill_value=False)).reindex(d.index).fillna(False).to_numpy(dtype=bool)
        x = {"name": t, "dates": d.index.values, "idx": d.index, "O": d["Open"].to_numpy(), "H": d["High"].to_numpy(),
             "L": d["Low"].to_numpy(), "C": d["Close"].to_numpy(),
             "macd": macd.reindex(d.index, method="ffill").to_numpy(), "wk_close": d.index.isin(w.index),
             "strength": (macd / w["Close"]).reindex(d.index, method="ffill").to_numpy()}
        inst[t] = x
        el = elig[t].reindex(d.index).fillna(False).to_numpy(dtype=bool)
        for j in np.flatnonzero(fresh & el):
            if j + 1 < len(d) and d.index[j + 1] >= START:
                rows.append({"ticker": t, "e": int(j + 1), "entry_date": d.index[j + 1], "strength": x["strength"][j]})
    sig = pd.DataFrame(rows).sort_values(["entry_date", "strength"], ascending=[True, False]).reset_index(drop=True)
    last_day = cal[-1]

    def sim(x, e, **kw):  # a stock whose data ends early (delisted/acquired) is closed at its last price
        r = _sim(x, e, **kw)
        if r["reason"] == "open" and x["idx"][-1] < last_day - pd.Timedelta(days=7):
            r["reason"] = "delisted"
        return r
    mv.simulate_campaign = sim
    tcal = cal[cal >= START]
    print(f"{len(inst)} stocks with data, {len(sig)} signals from point-in-time top-{TOP}", flush=True)

    res_rows, keep = [], {}

    def go(label, kw, max_open, s=sig):
        mv.MAX_OPEN = max_open
        res, camps = mv.run(inst, s, tcal, kw, 365, None)
        st = mv.stats(res, camps)
        res_rows.append({"variant": label, "max_open": max_open, **st})
        keep[(label, max_open)] = (res, camps)
        print(f"{label:16s} max {max_open:2d} | CAGR {st['cagr_%']:6.2f} (IS {st['cagr_IS_%']:6.2f} / OOS {st['cagr_OOS_%']:6.2f}) "
              f"DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:4.0f}% camp {st['campaigns']} "
              f"win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}%", flush=True)

    for mo in [3, 5, 10, 20]:
        go("base", dict(mode="base"), mo)
    for mo in [3, 10, 20]:
        go("sl1_reentry", dict(mode="sl_reentry", sl=0.01), mo)
    for mo in [3, 10]:
        go("pyr_1pct_K5", dict(mode="pyramid", step=0.01, K=5), mo)
        go("ladder_mart_K5", dict(mode="ladder", step=0.01, K=5, sizing="mart"), mo)
    rng = np.random.default_rng(4)
    rnd = []
    for _ in range(20):
        s2 = sig.assign(strength=rng.random(len(sig))).sort_values(["entry_date", "strength"], ascending=[True, False])
        mv.MAX_OPEN = 3
        r_, c_ = mv.run(inst, s2.reset_index(drop=True), tcal, dict(mode="base"), 365, None)
        st = mv.stats(r_, c_)
        rnd.append({k: st[k] for k in ["cagr_%", "sharpe", "max_dd_%"]})
    rnd = pd.DataFrame(rnd)

    # benchmarks: equal-weight point-in-time top 100 (monthly), all members with data, S&P 500 TR
    rets = pd.DataFrame({t: d["Close"].pct_change() for t, d in data.items()}).reindex(tcal)
    el = elig.reindex(tcal).shift(1).fillna(False)  # hold this month's list from its first day's close
    ew_top = (1 + rets.where(el).mean(axis=1).fillna(0.0)).cumprod() * mv.CAPITAL
    memb_mask = pd.DataFrame(False, index=tcal, columns=rets.columns)
    for dday, m in mem.reindex(tcal).items():
        cols = [t for t in m if t in memb_mask.columns]
        memb_mask.loc[dday, cols] = True
    ew_all = (1 + rets.where(memb_mask.shift(1).fillna(False)).mean(axis=1).fillna(0.0)).cumprod() * mv.CAPITAL
    spx = pd.read_csv(os.path.join(ROOT, "data", "us100", "SP500TR.csv"), index_col=0, parse_dates=True)["Close"]
    spx = spx.reindex(tcal).ffill()
    spx = spx / spx.iloc[0] * mv.CAPITAL
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from us100_study import eq_stats
    bm = {"EW_top100_pit": {**eq_stats(ew_top), "label": "Equal-weight point-in-time top 100 (monthly)"},
          "EW_sp500_pit": {**eq_stats(ew_all), "label": "Equal-weight all S&P 500 members with data"},
          "SP500TR": {**eq_stats(spx), "label": "S&P 500 total return"}}
    for k, v in bm.items():
        print(k, {kk: round(vv, 2) for kk, vv in v.items() if kk != "label"})
    print("random pick max 3:", rnd.describe().round(2).to_dict())

    # same period, survivorship-biased universe (today's top 100), for comparison
    grid = pd.DataFrame(res_rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    cov.to_csv(os.path.join(OUT, "coverage.csv"), index=False)
    summary = {"rules": __doc__, "coverage": cov.to_dict("records"), "n_stocks": len(inst), "n_signals": len(sig),
               "random_pick": {c: {"mean": float(rnd[c].mean()), "p05": float(rnd[c].quantile(.05)), "p95": float(rnd[c].quantile(.95))}
                               for c in rnd.columns},
               "benchmarks": {k: {**v, "equity_weekly": [[d.date().isoformat(), round(float(x), 2)]
                                                         for d, x in e.resample("W-FRI").last().dropna().items()]}
                              for (k, v), e in zip(bm.items(), [ew_top, ew_all, spx])},
               "variants": res_rows, "runs": {}}
    for key in [("base", 3), ("base", 10), ("base", 20), ("sl1_reentry", 3), ("sl1_reentry", 10), ("sl1_reentry", 20)]:
        res, camps = keep[key]
        name = f"{key[0]}_{key[1]}"
        res.to_csv(os.path.join(OUT, f"equity_{name}.csv"))
        camps.to_csv(os.path.join(OUT, f"campaigns_{name}.csv"), index=False)
        summary["runs"][name] = {"stats": grid[(grid.variant == key[0]) & (grid.max_open == key[1])].iloc[0].to_dict(),
                                 "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                   for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                 "live": camps[camps.reason == "open"].astype(str).to_dict("records"),
                                 "exit_reasons": camps.reason.value_counts().to_dict()}
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
