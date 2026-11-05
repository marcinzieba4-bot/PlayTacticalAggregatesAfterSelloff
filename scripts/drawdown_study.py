"""Drawdown episodes of the best books and their combination: depth, dates and time under water.

For each daily equity curve (same books and rules as combo_kelly_study.py, idle cash in T-bills):
an episode starts at a high-water mark, bottoms at the trough and ends when the old high is regained
(or is still open at the data end). Reported: the deepest episodes, the longest time under water,
the share of days below the high, and the drawdown in well-known market stress periods.

Usage:  python scripts/drawdown_study.py   -> results/drawdowns/
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

import combo_kelly_study as ck  # noqa: E402

OUT = os.path.join(ROOT, "results", "drawdowns")
EPISODES = {"dot-com bust": ("2000-03-01", "2003-03-31"), "global financial crisis": ("2007-10-01", "2009-03-31"),
            "euro crisis": ("2011-05-01", "2011-12-31"), "2015-16 China / oil": ("2015-05-01", "2016-02-29"),
            "Q4 2018": ("2018-09-20", "2018-12-31"), "Covid crash": ("2020-02-19", "2020-04-30"),
            "2022 bear market": ("2022-01-01", "2022-10-31")}


def episodes(e):
    e = e.dropna()
    peak = e.cummax()
    under = e < peak * (1 - 1e-9)
    out = []
    i, n = 0, len(e)
    vals, idx = e.to_numpy(), e.index
    while i < n:
        if not under.iloc[i]:
            i += 1
            continue
        start = i - 1 if i > 0 else 0  # last day at the high
        j = i
        while j < n and under.iloc[j]:
            j += 1
        seg = slice(i, j)
        t = i + int(np.argmin(vals[seg]))
        depth = vals[t] / vals[start] - 1
        rec = idx[j] if j < n else None
        out.append({"peak": idx[start], "trough": idx[t], "recovered": rec, "depth_%": 100 * depth,
                    "fall_days": (idx[t] - idx[start]).days, "recovery_days": (rec - idx[t]).days if rec is not None else None,
                    "underwater_days": ((rec if rec is not None else idx[-1]) - idx[start]).days, "ongoing": rec is None})
        i = j
    return pd.DataFrame(out)


def series():
    bk, _ = ck.books()
    idx = pd.DatetimeIndex(sorted(set().union(*[set(b.index) for b in bk.values()])))
    rc_all = ck.tbill(idx)
    R, X = {}, {}
    for k, b in bk.items():
        b = b.reindex(idx).ffill()
        R[k] = b["equity"].pct_change().fillna(0.0)
        X[k] = b["expo"].fillna(0.0).clip(lower=0.0)
    R, X = pd.DataFrame(R), pd.DataFrame(X)
    full = {}
    # the index book over its full history (1990-2026), idle cash in T-bills
    for k in ["IDX5", "IDX3"]:
        first = bk[k].index[0]
        m = R.index >= first
        full[f"{k} (1990-2026)"] = (1 + ck.lever(R[k][m], X[k][m], rc_all[m], 1.0)).cumprod()
    w = idx >= ck.START
    R, X, rc = R[w], X[w], rc_all[w]
    base = {k: ck.lever(R[k], X[k], rc, 1.0) for k in R}
    s = {"Indices, max 5 (IDX5)": base["IDX5"], "Indices, max 3 (IDX3)": base["IDX3"],
         "Stocks, wait 1m + S&P>100d + 1% stop (STK_W1)": base["STK_W1"], "Stocks, 6m hold + 1% stop (STK_6M)": base["STK_6M"]}
    rp, ex = 0.5 * R["IDX5"] + 0.5 * R["STK_W1"], 0.5 * X["IDX5"] + 0.5 * X["STK_W1"]
    s["50/50 IDX5 + STK_W1"] = ck.lever(rp, ex, rc, 1.0)
    s["50/50 IDX5 + STK_W1 at 1/4 Kelly (1.45x)"] = ck.lever(rp, ex, rc, 1.45)
    rp3, ex3 = 0.5 * R["IDX3"] + 0.5 * R["STK_W1"], 0.5 * X["IDX3"] + 0.5 * X["STK_W1"]
    s["50/50 IDX3 + STK_W1"] = ck.lever(rp3, ex3, rc, 1.0)
    spx = pd.read_csv(os.path.join(ROOT, "data", "raw", "GSPC.csv"), index_col=0, parse_dates=True)["Close"]
    s["S&P 500 (price)"] = spx.reindex(R.index).ffill().pct_change().fillna(0.0)
    eq = {k: (1 + v).cumprod() for k, v in s.items()}
    eq.update(full)
    return eq


def main():
    os.makedirs(OUT, exist_ok=True)
    eq = series()
    summary, all_eps = {}, []
    for name, e in eq.items():
        ep = episodes(e)
        ep["series"] = name
        all_eps.append(ep)
        dd = e / e.cummax() - 1
        deep = ep.sort_values("depth_%").head(5)
        longest = ep.sort_values("underwater_days", ascending=False).head(3)
        stress = {}
        for lab, (a, b) in EPISODES.items():
            seg = e[(e.index >= a) & (e.index <= b)]
            if len(seg) > 5:
                stress[lab] = 100 * float((seg / seg.cummax() - 1).min())
        summary[name] = {
            "max_dd_%": 100 * float(dd.min()), "max_dd_date": str(dd.idxmin().date()),
            "longest_underwater_days": int(ep["underwater_days"].max()) if len(ep) else 0,
            "longest_underwater_years": round(float(ep["underwater_days"].max()) / 365.25, 2) if len(ep) else 0,
            "pct_days_below_high": 100 * float((dd < -1e-9).mean()),
            "pct_days_dd_worse_than_10": 100 * float((dd < -0.10).mean()),
            "episodes_deeper_than_10": int((ep["depth_%"] < -10).sum()), "episodes_deeper_than_15": int((ep["depth_%"] < -15).sum()),
            "ulcer_index": float(np.sqrt(np.mean((100 * dd) ** 2))),
            "current_dd_%": 100 * float(dd.iloc[-1]),
            "deepest": deep.assign(peak=deep.peak.astype(str), trough=deep.trough.astype(str), recovered=deep.recovered.astype(str)).drop(columns="series").to_dict("records"),
            "longest": longest.assign(peak=longest.peak.astype(str), trough=longest.trough.astype(str), recovered=longest.recovered.astype(str)).drop(columns="series").to_dict("records"),
            "stress_periods_%": stress}
        sm = summary[name]
        print(f"\n=== {name}: max DD {sm['max_dd_%']:.1f}% on {sm['max_dd_date']}, longest under water {sm['longest_underwater_days']} days "
              f"({sm['longest_underwater_years']} y), below high {sm['pct_days_below_high']:.0f}% of days, DD worse than -10% "
              f"{sm['pct_days_dd_worse_than_10']:.0f}% of days, ulcer {sm['ulcer_index']:.1f}, now {sm['current_dd_%']:.1f}%", flush=True)
        print("  deepest:")
        for r in deep.itertuples():
            print(f"    {r._4:6.1f}%  peak {r.peak.date()}  trough {r.trough.date()}  recovered "
                  f"{r.recovered.date() if r.recovered is not None and not pd.isna(r.recovered) else 'not yet'}  "
                  f"fall {r.fall_days} d, recovery {r.recovery_days if r.recovery_days == r.recovery_days and r.recovery_days is not None else '-'} d, "
                  f"under water {r.underwater_days} d", flush=True)
        print("  longest:")
        for r in longest.itertuples():
            print(f"    {r.underwater_days:5d} d ({r.underwater_days / 365.25:.1f} y)  depth {r._4:6.1f}%  peak {r.peak.date()}  trough {r.trough.date()}  "
                  f"recovered {r.recovered.date() if r.recovered is not None and not pd.isna(r.recovered) else 'not yet'}", flush=True)
        print("  stress periods:", {k: round(v, 1) for k, v in stress.items()}, flush=True)
    eps = pd.concat(all_eps, ignore_index=True)
    eps.to_csv(os.path.join(OUT, "episodes.csv"), index=False)
    uw = {}
    for name, e in eq.items():
        dd = (e / e.cummax() - 1).resample("W-FRI").min().dropna()
        uw[name] = [[d.date().isoformat(), round(100 * float(v), 2)] for d, v in dd.items()]
    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump({"rules": __doc__, "series": summary, "underwater_weekly": uw}, fh, indent=1,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
