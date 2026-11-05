"""27 DM indices + US sectors: S&P 500 50-day filter + weekly MACD + 1-2 % stop, 3-month holding period.

The single-stock test of stocks_ma50_study.py applied to the original universe (16 DM indices + 11 SPDR
sectors, 1990-2026, price indices without dividends):
  * signal  : new weekly MACD up-phase (MACD and signal both > 0) -> buy at the next open
  * filter  : S&P 500 close above its 50-day average at the signal close; re-entries after a stop
              also only while it is on (checked at the previous close)
  * stop    : 1 % / 2 % below the entry E0, re-entry at E0 (any number of times)
  * exits   : next open after a weekly MACD < 0 close, or after 3 months (first open >= entry + 91 days)
  * book    : max 3 positions (also 5), 1/N of equity each, cash-capped, compounding, 3 bps per side
Grid: filter (none / S&P 50d / S&P 100d / asset's own 50d) x hold (3 months / 1 year) x stop (none / 1 % / 2 %)
x max 3/5 on all 27; key variants also on the 16 DM indices and the 11 sectors alone; random pick
among same-day signals (50 draws) for the key variants.

Usage:  python scripts/indices_ma50_study.py   -> results/indices_ma50/
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
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import macd_variants_study as mv  # noqa: E402
import stocks_ma50_study as sm  # noqa: E402
from strategy.data import load_daily  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "indices_ma50")
FILTERS, STOPS, HOLDS = sm.FILTERS, sm.STOPS, sm.HOLDS
KEY = [("none", "1 year", "no stop"), ("none", "1 year", "1% stop"), ("S&P 100d", "1 year", "no stop"),
       ("S&P 100d", "1 year", "1% stop"), ("S&P 50d", "1 year", "1% stop"), ("S&P 50d", "3 months", "1% stop"),
       ("S&P 50d", "3 months", "no stop"), ("S&P 100d", "3 months", "1% stop"), ("none", "3 months", "1% stop"),
       ("none", "3 months", "no stop")]


def eq_stats(e):
    r = e.pct_change().fillna(0.0)

    def cagr(s):
        y = (s.index[-1] - s.index[0]).days / 365.25
        return 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1)
    return {"cagr_%": cagr(e), "cagr_IS_%": cagr(e[e.index < mv.SPLIT_DATE]), "cagr_OOS_%": cagr(e[e.index >= mv.SPLIT_DATE]),
            "max_dd_%": 100 * float((e / e.cummax() - 1).min()), "sharpe": float(r.mean() / r.std() * np.sqrt(252))}


def main():
    os.makedirs(OUT, exist_ok=True)
    spx, reg = sm.regimes()
    inst = mv.build()
    sm.prepare(inst, reg)
    sig_all = mv.signals(inst)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
    cal = cal[cal >= mv.START]
    dm = [t for t, v in UNIVERSE.items() if v[1] == "DM index"]
    sectors = [t for t in UNIVERSE if t not in dm]
    unis = {"27": list(inst), "DM 16": dm, "sectors 11": sectors}
    print(f"{len(sig_all)} signals; pass S&P 50d {np.mean([inst[r.ticker]['spx50'][r.e - 1] for r in sig_all.itertuples()]):.1%}, "
          f"S&P 100d {np.mean([inst[r.ticker]['spx100'][r.e - 1] for r in sig_all.itertuples()]):.1%}, own 50d "
          f"{np.mean([inst[r.ticker]['own50'][r.e - 1] for r in sig_all.itertuples()]):.1%}", flush=True)
    rows, keep = [], {}

    def go(uni, f, h, sname, mo, sig=None):
        sub = {t: inst[t] for t in unis[uni]}
        s = sig_all[sig_all.ticker.isin(unis[uni])] if sig is None else sig
        res, camps, st = sm.run_one(sub, s, cal, FILTERS[f], STOPS[sname], HOLDS[h], mo)
        if sig is not None:
            return st
        rows.append({"universe": uni, "filter": f, "hold": h, "stop": sname, "max_open": mo, **st})
        keep[(uni, f, h, sname, mo)] = (res, camps)
        print(f"{uni:10s} {f:9s} {h:8s} {sname:7s} max {mo} | CAGR {st['cagr_%']:5.2f} (IS {st['cagr_IS_%']:5.2f} / OOS "
              f"{st['cagr_OOS_%']:5.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:3.0f}% "
              f"camp {st['campaigns']} win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}% days {st['avg_days']:.0f} "
              f"stops {st['avg_stops']:.1f} exit time/macd {st['exit_time%']:.0f}/{st['exit_macd%']:.0f}%", flush=True)

    for (f, h, sname), mo in itertools.product(itertools.product(FILTERS, HOLDS, STOPS), [3, 5]):
        go("27", f, h, sname, mo)
    for uni in ["DM 16", "sectors 11"]:
        for f, h, sname in KEY:
            go(uni, f, h, sname, 3)

    # robustness: random pick among same-day signals (weekly signals often coincide), 50 draws
    rnd = []
    rng = np.random.default_rng(5)
    for draw in range(50):
        s2 = sig_all.assign(strength=rng.random(len(sig_all))).sort_values(["entry_date", "strength"], ascending=[True, False])
        for f, h, sname in KEY:
            rnd.append({"filter": f, "hold": h, "stop": sname, "draw": draw, **go("27", f, h, sname, 3, s2)})
    rnd = pd.DataFrame(rnd)
    rnd.to_csv(os.path.join(OUT, "random_pick.csv"), index=False)
    rnd_sum = []
    for (f, h, sname), g in rnd.groupby(["filter", "hold", "stop"]):
        rnd_sum.append({"filter": f, "hold": h, "stop": sname,
                        **{f"{c}_{q}": float(g[c].quantile(p)) for c in ["cagr_%", "max_dd_%", "sharpe"]
                           for q, p in [("p05", .05), ("p50", .5), ("p95", .95)]},
                        **{f"{c}_mean": float(g[c].mean()) for c in ["cagr_%", "max_dd_%", "sharpe"]}})
    print(pd.DataFrame(rnd_sum).round(2).to_string(), flush=True)

    # benchmarks: equal-weight buy & hold of the 27 (daily rebalanced), S&P 500 price
    cl = pd.concat([pd.Series(x["C"], index=x["idx"]).pct_change().rename(t) for t, x in inst.items()], axis=1, sort=True)
    bh = (1 + cl[cl.index >= mv.START].mean(axis=1).fillna(0.0)).cumprod() * mv.CAPITAL
    sp = spx[spx.index >= mv.START]
    sp = sp / sp.iloc[0] * mv.CAPITAL
    bench = {"EW_27": eq_stats(bh), "SPX": eq_stats(sp)}
    print("benchmarks", {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in bench.items()}, flush=True)

    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    c, m50, m100 = spx.iloc[-1], spx.rolling(50).mean().iloc[-1], spx.rolling(100).mean().iloc[-1]
    summary = {"rules": __doc__, "variants": rows, "random_pick": rnd_sum, "benchmarks": bench, "runs": {},
               "now": {"date": str(spx.index[-1].date()), "spx_close": float(c), "sma50": float(m50), "sma100": float(m100),
                       "dist50_%": float(100 * (c / m50 - 1)), "filter50_on": bool(c > m50)}}
    for key in [("27", "none", "1 year", "no stop", 3), ("27", "S&P 100d", "1 year", "no stop", 3),
                ("27", "S&P 50d", "3 months", "1% stop", 3), ("27", "S&P 50d", "3 months", "no stop", 3),
                ("27", "none", "3 months", "1% stop", 3), ("27", "S&P 50d", "1 year", "1% stop", 3),
                ("27", "S&P 50d", "3 months", "1% stop", 5), ("DM 16", "S&P 50d", "3 months", "1% stop", 3)]:
        res, camps = keep[key]
        name = "_".join(str(k) for k in key).replace(" ", "").replace("&", "").replace("%", "pct")
        res.to_csv(os.path.join(OUT, f"equity_{name}.csv"))
        camps.to_csv(os.path.join(OUT, f"campaigns_{name}.csv"), index=False)
        eq = res["equity"]
        summary["runs"][name] = {"key": key, "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                               for d, v in eq.resample("W-FRI").last().dropna().items()],
                                 "by_year": eq.resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict(),
                                 "live": camps[camps.reason == "open"].astype(str).to_dict("records")}
    for k, e in [("EW_27", bh), ("SPX", sp)]:
        summary["runs"][k] = {"equity_weekly": [[d.date().isoformat(), round(float(v), 2)] for d, v in e.resample("W-FRI").last().dropna().items()],
                              "by_year": e.resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict()}
    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("now:", summary["now"])


if __name__ == "__main__":
    main()
