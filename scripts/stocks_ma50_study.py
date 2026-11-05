"""Single stocks: S&P 500 50-day filter + weekly MACD + 1-2 % stop, 3-month holding period.

Same as stocks_regime_study.py, with two changes asked for:
  * regime filter = S&P 500 close above its 50-day average (was 100-day); it gates the entry
    (checked at the signal close) and every re-entry after a stop (checked at the previous close);
  * time exit after 3 months (first open on/after entry + 91 days) instead of 1 year.
Everything else is unchanged: a new weekly MACD up-phase (MACD and signal both > 0) is the signal,
stop 1 % / 2 % below the entry E0 with re-entry at E0, exit at the next open after a weekly
MACD < 0 close, 1/N of equity per stock, cash-capped, compounding, 3 bps per side.
To separate the two effects every combination of filter (none / S&P 50d / S&P 100d / stock's own
50d) x holding period (3 months / 1 year) x stop (none / 1 % / 2 %) x max 3/10/20 is run on the
point-in-time S&P 500 top 100 (1997-2026), with a 20-draw random-pick check for the key variants
and a reference run on today's top 100 (survivorship-biased, 1990-2026).

Usage:  python scripts/stocks_ma50_study.py   -> results/stocks_ma50/
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
import stocks_regime_study as sr  # noqa: E402
import us100_study as u100  # noqa: E402
from strategy.data import load_daily  # noqa: E402
from strategy.macd_engine import simulate_campaign as _sim  # noqa: E402

OUT = os.path.join(ROOT, "results", "stocks_ma50")
CUTOFF = sr.CUTOFF
FILTERS = {"none": None, "S&P 50d": "spx50", "S&P 100d": "spx100", "stock 50d": "own50"}
STOPS = {"no stop": dict(mode="base"), "1% stop": dict(mode="sl_reentry", sl=0.01), "2% stop": dict(mode="sl_reentry", sl=0.02)}
HOLDS = {"3 months": 91, "1 year": 365}


def regimes():
    spx = load_daily("^GSPC", drop_after=CUTOFF)["Close"]
    out = {}
    for n in (50, 100):
        m = spx.rolling(n).mean()
        out[f"spx{n}"] = (spx > m) & m.notna()
    return spx, out


def prepare(inst, reg):
    for x in inst.values():
        for k, r in reg.items():
            x[k] = r.reindex(x["idx"], method="ffill").fillna(False).to_numpy(dtype=bool)
        c = pd.Series(x["C"], index=x["idx"])
        m = c.rolling(50).mean()
        x["own50"] = ((c > m) & m.notna()).to_numpy(dtype=bool)


def run_one(inst, sig, cal, filt, kw, td, mo):
    s = sig[[inst[r.ticker][filt][r.e - 1] for r in sig.itertuples()]] if filt else sig
    for x in inst.values():
        x["reentry_ok"] = x[filt] if filt else None
        x["exit_flag"] = None
    mv.MAX_OPEN = mo
    res, camps = mv.run(inst, s.reset_index(drop=True), cal, kw, td, None)
    return res, camps, mv.stats(res, camps)


def main():
    os.makedirs(OUT, exist_ok=True)
    spx, reg = regimes()
    rows, keep = [], {}

    def log(uni, f, h, sname, mo, st):
        print(f"{uni:8s} {f:9s} {h:8s} {sname:7s} max {mo:2d} | CAGR {st['cagr_%']:6.2f} (IS {st['cagr_IS_%']:6.2f} / OOS "
              f"{st['cagr_OOS_%']:6.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:3.0f}% "
              f"camp {st['campaigns']} win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}% days {st['avg_days']:.0f} "
              f"stops {st['avg_stops']:.1f} exit time/macd {st['exit_time%']:.0f}/{st['exit_macd%']:.0f}%", flush=True)

    # point-in-time universe (delisted stocks are closed at their last price)
    inst, sig, cal = sr.build_pit()
    prepare(inst, reg)
    last_day = cal[-1]

    def sim(x, e, **kw):
        r = _sim(x, e, **kw)
        if r["reason"] == "open" and x["idx"][-1] < last_day - pd.Timedelta(days=7):
            r["reason"] = "delisted"
        return r
    mv.simulate_campaign = sim
    print(f"point-in-time: {len(inst)} stocks, {len(sig)} signals; pass S&P 50d "
          f"{np.mean([inst[r.ticker]['spx50'][r.e - 1] for r in sig.itertuples()]):.1%}, S&P 100d "
          f"{np.mean([inst[r.ticker]['spx100'][r.e - 1] for r in sig.itertuples()]):.1%}, own 50d "
          f"{np.mean([inst[r.ticker]['own50'][r.e - 1] for r in sig.itertuples()]):.1%}", flush=True)
    for (f, filt), (h, td), (sname, kw), mo in itertools.product(FILTERS.items(), HOLDS.items(), STOPS.items(), [3, 10, 20]):
        res, camps, st = run_one(inst, sig, cal, filt, kw, td, mo)
        rows.append({"universe": "PIT", "filter": f, "hold": h, "stop": sname, "max_open": mo, **st})
        keep[("PIT", f, h, sname, mo)] = (res, camps)
        log("PIT", f, h, sname, mo, st)

    # robustness: random pick among same-day signals, 20 draws
    rnd = []
    rng = np.random.default_rng(11)
    key_variants = [("none", "1 year", "no stop"), ("S&P 50d", "3 months", "1% stop"), ("S&P 50d", "1 year", "1% stop"),
                    ("S&P 100d", "3 months", "1% stop"), ("S&P 100d", "1 year", "1% stop"),
                    ("none", "3 months", "no stop"), ("none", "3 months", "1% stop")]
    for draw in range(20):
        s2 = sig.assign(strength=rng.random(len(sig))).sort_values(["entry_date", "strength"], ascending=[True, False])
        for (f, h, sname), mo in itertools.product(key_variants, [10, 20]):
            st = run_one(inst, s2, cal, FILTERS[f], STOPS[sname], HOLDS[h], mo)[2]
            rnd.append({"filter": f, "hold": h, "stop": sname, "max_open": mo, "draw": draw, **st})
        print(f"random draw {draw} done", flush=True)
    rnd = pd.DataFrame(rnd)
    rnd.to_csv(os.path.join(OUT, "random_pick.csv"), index=False)
    rnd_sum = []
    for (f, h, sname, mo), g in rnd.groupby(["filter", "hold", "stop", "max_open"]):
        rnd_sum.append({"filter": f, "hold": h, "stop": sname, "max_open": int(mo),
                        **{f"{c}_{q}": float(g[c].quantile(p)) for c in ["cagr_%", "max_dd_%", "sharpe"]
                           for q, p in [("p05", .05), ("p50", .5), ("p95", .95)]},
                        **{f"{c}_mean": float(g[c].mean()) for c in ["cagr_%", "max_dd_%", "sharpe"]}})
    print(pd.DataFrame(rnd_sum).round(2).to_string(), flush=True)

    # reference: today's top 100 (survivorship-biased), from 1990
    mv.simulate_campaign = _sim
    uni = pd.read_csv(os.path.join(ROOT, "data", "us100", "universe.csv"))
    inst_b = u100.build(uni)
    sig_b = mv.signals(inst_b)
    cal_b = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst_b.values()])))
    cal_b = cal_b[cal_b >= mv.START]
    prepare(inst_b, reg)
    for (f, h, sname), mo in itertools.product(key_variants, [3, 10, 20]):
        res, camps, st = run_one(inst_b, sig_b, cal_b, FILTERS[f], STOPS[sname], HOLDS[h], mo)
        rows.append({"universe": "today100", "filter": f, "hold": h, "stop": sname, "max_open": mo, **st})
        log("today100", f, h, sname, mo, st)

    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    pit_sum = json.load(open(os.path.join(ROOT, "results", "sp500_pit", "summary.json")))
    bench = {k: {kk: v[kk] for kk in ["cagr_%", "cagr_IS_%", "cagr_OOS_%", "max_dd_%", "sharpe"]} for k, v in pit_sum["benchmarks"].items()}
    c, m50, m100 = spx.iloc[-1], spx.rolling(50).mean().iloc[-1], spx.rolling(100).mean().iloc[-1]
    summary = {"rules": __doc__, "variants": rows, "random_pick": rnd_sum, "pit_benchmarks": bench, "runs": {},
               "now": {"date": str(spx.index[-1].date()), "spx_close": float(c), "sma50": float(m50), "sma100": float(m100),
                       "dist50_%": float(100 * (c / m50 - 1)), "dist100_%": float(100 * (c / m100 - 1)),
                       "filter50_on": bool(c > m50), "filter100_on": bool(c > m100)}}
    for key in [("PIT", "none", "1 year", "no stop", 10), ("PIT", "S&P 50d", "3 months", "1% stop", 10),
                ("PIT", "S&P 50d", "3 months", "1% stop", 20), ("PIT", "S&P 100d", "1 year", "1% stop", 10),
                ("PIT", "S&P 100d", "1 year", "1% stop", 20), ("PIT", "S&P 50d", "1 year", "1% stop", 10),
                ("PIT", "S&P 100d", "3 months", "1% stop", 10), ("PIT", "S&P 50d", "3 months", "2% stop", 10),
                ("PIT", "none", "3 months", "1% stop", 10), ("PIT", "none", "3 months", "1% stop", 20)]:
        res, camps = keep[key]
        name = "_".join(str(k) for k in key).replace(" ", "").replace("&", "").replace("%", "pct")
        res.to_csv(os.path.join(OUT, f"equity_{name}.csv"))
        eq = res["equity"]
        summary["runs"][name] = {"key": key, "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                               for d, v in eq.resample("W-FRI").last().dropna().items()],
                                 "by_year": eq.resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict(),
                                 "live": camps[camps.reason == "open"].astype(str).to_dict("records")}
    for k in ["EW_top100_pit", "SP500TR"]:
        summary["runs"][k] = {"equity_weekly": pit_sum["benchmarks"][k]["equity_weekly"]}
    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("now:", summary["now"])


if __name__ == "__main__":
    main()
