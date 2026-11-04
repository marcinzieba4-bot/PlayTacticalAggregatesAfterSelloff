"""Martingale "until the old high" study.

Rules (per campaign, after a DeMark buy setup 9):
  * in above the 9-candle high, out below its low (same levels for every attempt)
  * each new attempt bigger (flat / linear / x1.5 / x2 martingale)
  * NO time stop and NO re-entry window: the campaign runs until price reaches the old high
    (pre-sell-off peak) minus `near` ATR -> position 0, campaign over
  * or until the allowed number of re-entries is used up (the only way a campaign loses)
  * new 9 on the same instrument while flat: "continue" (keep the old candle), "reanchor"
    (keep the campaign, use the new 9-candle for in/out), or "supersede" (end, start a new one)
  * portfolio: ONE campaign at a time (MODE one), with "many at once" (multi) for reference

Usage:  python scripts/oldhigh_study.py      -> results/oldhigh/
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from strategy.backtest import (SIZE_SCHEMES, SPLIT_DATE, Account, apply_sizing, by_attempt,  # noqa: E402
                               daily_equity, equity_stats, metrics, prepare, run_paths, select)
from strategy.engine import NO_LIMIT, PathParams  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "oldhigh")
DATA_CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")
ACCT = Account()
START = pd.Timestamp("1990-01-01")
BASE = {"W": dict(entry_mode="next_open", buf=0.0), "D": dict(entry_mode="break_high", buf=0.5)}
OLD_HIGH = {"old_high": {"W": "52-week high", "D": "252-day high"},
            "old_high_short": {"W": "26-week high", "D": "63-day high"}}
NEARS = [0.0, 0.25, 0.5, 1.0]
NEW9 = ["continue", "reanchor", "supersede"]
MS = [0, 1, 2, 3, 5, 10]
MIN_IS = {"W": 10, "D": 30}


def outcome_stats(a: pd.DataFrame, sel: pd.DataFrame, m: int, data_end) -> dict:
    """How campaigns ended: reached the old high, ran out of re-entries, or still unresolved."""
    if a.empty:
        return {}
    g = a.sort_values(["ticker", "s0", "k"]).groupby(["ticker", "s0"])
    reached = g["reason"].apply(lambda r: (r == "target").any())
    n_att = g.size()
    last = g["reason"].last()
    exhausted = (~reached) & (n_att == m + 1) & (last == "stop")
    s = sel.set_index(["ticker", "s0"]).reindex(reached.index)
    dur = (pd.to_datetime(s[f"end_date_m{m}"]).clip(upper=data_end) - pd.to_datetime(s["first_entry_date"])).dt.days
    abandoned = (~reached) & (~exhausted) & (s["status"] == "superseded")
    return {
        "reached_high%": 100 * float(reached.mean()),
        "exhausted%": 100 * float(exhausted.mean()),
        "abandoned_on_new9%": 100 * float(abandoned.mean()),
        "still_live%": 100 * float((~reached & ~exhausted & ~abandoned).mean()),
        "avg_attempts": float(n_att.mean()),
        "avg_days": float(dur.mean()),
        "max_days": float(dur.max()),
        "max_size_x": float(a["w"].max()),
    }


def period_metrics(a, data_end):
    yrs = {"IS": (SPLIT_DATE - START).days / 365.25, "OOS": (data_end - SPLIT_DATE).days / 365.25,
           "FULL": (data_end - START).days / 365.25}
    parts = {"IS": a[a.sig_date < SPLIT_DATE], "OOS": a[a.sig_date >= SPLIT_DATE], "FULL": a}
    return {k: metrics(v, yrs[k]) for k, v in parts.items()}


def main():
    os.makedirs(OUT, exist_ok=True)
    rows, store = [], {}
    for tf in ["W", "D"]:
        prep = prepare(tf, drop_after=DATA_CUTOFF)
        data_end = max(x["dates"][-1] for x in prep.values())
        for oh, near, new9 in itertools.product(OLD_HIGH, NEARS, NEW9):
            p = PathParams(**BASE[tf], target="oldhigh", time_stop=NO_LIMIT, window=NO_LIMIT,
                           max_attempts=max(MS) + 1, near=near, old_high_col=oh, on_new9=new9)
            atts, seqs = run_paths(prep, 0.0, False, p)
            store[(tf, oh, near, new9)] = (atts, seqs, p)
            for mode, m in itertools.product(["one", "multi"], MS):
                sel = select(seqs, m, mode)
                for scheme in SIZE_SCHEMES:
                    if m == 0 and scheme != "flat":
                        continue
                    a = apply_sizing(atts, sel, m, scheme, ACCT)
                    pm = period_metrics(a, data_end)
                    base = dict(tf=tf, old_high=OLD_HIGH[oh][tf], oh_col=oh, near_atr=near, new9=new9, mode=mode,
                                reentries=m, scheme=scheme)
                    oc = outcome_stats(a, sel, m, data_end)
                    for per, mt in pm.items():
                        rows.append({**base, "period": per, **{k: mt.get(k) for k in
                                     ["n_seq", "n_att", "seq_win%", "avg_R_seq", "R_per_yr", "PF", "maxDD_R", "MAR",
                                      "worst_seq_R", "capped%"]}, **(oc if per == "FULL" else {})})
            print(tf, oh, near, new9, "done", flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "grid.csv"), index=False)

    # ---------- selection: one campaign at a time, martingale x2 with 5 re-entries (the asked design),
    # old-high variant chosen IN-SAMPLE; plus the best sizing per timeframe
    summary = {"rules": __doc__, "data_cutoff": DATA_CUTOFF, "runs": {}}
    keys = ["oh_col", "near_atr", "new9"]
    for tf in ["W", "D"]:
        g = grid[(grid.tf == tf) & (grid["mode"] == "one")]
        gis = g[(g.period == "IS") & (g.n_seq >= MIN_IS[tf])]
        # "no stopping" martingale = keep the campaign alive through new 9s (re-anchor); the
        # old-high definition and the exit distance below it are picked in-sample
        mart = gis[(gis.reentries == 5) & (gis.scheme == "geo2") & (gis.new9 == "reanchor")] \
            .sort_values("MAR", ascending=False).iloc[0]
        same = g[np.logical_and.reduce([g[k] == mart[k] for k in keys])]
        best_size = same[same.period == "IS"].sort_values("MAR", ascending=False).iloc[0]
        tf_out = {"martingale_config": {k: (mart[k].item() if hasattr(mart[k], "item") else mart[k]) for k in keys},
                  "old_high_label": mart["old_high"],
                  "matrix": same.to_dict("records"),
                  "variants_m5_geo2": g[(g.reentries == 5) & (g.scheme == "geo2")].to_dict("records"),
                  "multi_same": grid[(grid.tf == tf) & (grid["mode"] == "multi")
                                     & np.logical_and.reduce([grid[k] == mart[k] for k in keys])].to_dict("records")}
        atts, seqs, p = store[(tf, mart.oh_col, mart.near_atr, mart.new9)]
        prep = prepare(tf, drop_after=DATA_CUTOFF)
        details = {}
        for label, m, scheme in [("martingale_x2_5re", 5, "geo2"), ("martingale_x2_10re", 10, "geo2"),
                                 ("linear_5re", 5, "linear"), ("flat_5re", 5, "flat"),
                                 ("best_sizing", int(best_size.reentries), best_size.scheme), ("no_reentry", 0, "flat")]:
            sel = select(seqs, m, "one")
            a = apply_sizing(atts, sel, m, scheme, ACCT)
            eq = daily_equity(a, prep, ACCT, p.cost_bps)
            cal = pd.DatetimeIndex(sorted(set().union(*[set(x["dates"]) for x in prep.values()])))
            eq = eq.reindex(cal)
            eq["pnl"] = eq["pnl"].fillna(0.0)
            eq["gross_expo_x"] = eq["gross_expo_x"].fillna(0.0)
            eq["equity"] = ACCT.capital + eq["pnl"].cumsum()
            eq = eq[eq.index >= START]
            de = eq.index[-1]
            camp = a.groupby(["ticker", "s0"]).agg(sig_date=("sig_date", "first"), first=("entry_date", "min"),
                                                   last=("exit_date", "max"), attempts=("k", "size"),
                                                   reached=("reason", lambda r: bool((r == "target").any())),
                                                   pnl=("pnl", "sum"), pnl_R=("pnl_R", "sum"),
                                                   max_w=("w", "max"), last_w=("w", "last"),
                                                   last_reason=("reason", "last"), last_entry=("entry_px", "last"),
                                                   stop_px=("stop_px", "last"), target_px=("target_px", "last"),
                                                   ).reset_index()
            camp["last_close"] = [prep[t]["C"][-1] for t in camp.ticker]
            camp["name"] = camp.ticker.map(lambda t: UNIVERSE[t][0])
            camp = camp.sort_values("first")
            camp.to_csv(os.path.join(OUT, f"campaigns_{tf}_{label}.csv"), index=False)
            a.to_csv(os.path.join(OUT, f"trades_{tf}_{label}.csv"), index=False)
            eq.to_csv(os.path.join(OUT, f"equity_{tf}_{label}.csv"))
            details[label] = {
                "reentries": m, "scheme": scheme,
                "metrics_R": period_metrics(a, de),
                "outcomes": outcome_stats(a, sel, m, de),
                "equity_stats": {"FULL": equity_stats(eq, ACCT)},
                "by_attempt": by_attempt(a).reset_index().to_dict("records"),
                "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                  for d, v in eq["equity"].resample("W-FRI").last().dropna().items()],
                "worst_campaigns": camp.nsmallest(5, "pnl")[["name", "sig_date", "first", "last", "attempts", "pnl"]]
                .astype(str).to_dict("records"),
                "live": camp[camp["last"] >= de - pd.Timedelta(days=3)].astype(str).to_dict("records"),
            }
            st = details[label]["equity_stats"]["FULL"]
            print(f"[{tf}] {label}: m={m} {scheme} | ret/yr {st['ret_per_yr_%_of_capital']:.2f}% "
                  f"DD {st['max_dd_%_of_capital']:.1f}% Sharpe {st['sharpe']:.2f} | "
                  f"{ {k: round(v, 1) for k, v in details[label]['outcomes'].items()} }")
        tf_out["details"] = details
        summary["runs"][tf] = tf_out
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
