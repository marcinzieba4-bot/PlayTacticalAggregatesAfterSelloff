"""MACD signal on 100 single US stocks with the S&P 500 100-day filter and a 1-2 % stop + re-entry.

Universe (main): the point-in-time S&P 500 top 100 by trailing dollar volume, rebuilt monthly
(see sp500_pit_study.py; less survivorship bias). Reference: today's top 100 (us100_study.py).
Rules: buy a new weekly MACD up-phase at the next open only if the S&P 500 closed above its
100-day average (or: the stock itself above its own 100-day average, or both); stop 1 % / 2 %
below the entry, re-enter at the entry price only while the same filter is on; exit when the
stock's weekly MACD < 0 or after 1 year.
N positions at once (3 / 10 / 20), 1/N of equity each, cash-capped, compounding, 3 bps/side.

Usage:  python scripts/stocks_regime_study.py   -> results/stocks_regime/
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
import sp500_pit_study as pit  # noqa: E402
import us100_study as u100  # noqa: E402
from strategy.data import load_daily, to_weekly  # noqa: E402
from strategy.macd_engine import simulate_campaign as _sim  # noqa: E402

OUT = os.path.join(ROOT, "results", "stocks_regime")
CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")


def build_pit():
    tickers = sorted(f[:-4] for f in os.listdir(os.path.join(pit.DIR, "raw")) if f.endswith(".csv"))
    data = {t: pit.load(t) for t in tickers}
    data = {t: d for t, d in data.items() if len(d) > 300}
    cal = pd.DatetimeIndex(sorted(set().union(*[set(d.index) for d in data.values()])))
    cal = cal[cal >= pd.Timestamp("1996-01-02")]
    mem = pit.membership(cal)
    dv = pd.DataFrame({t: (d["Close"] * d["Volume"]).rolling(252, min_periods=200).mean() for t, d in data.items()}).reindex(cal)
    month_starts = pd.DatetimeIndex(sorted(set(cal.to_series().groupby(cal.to_period("M")).min())))
    elig = pd.DataFrame(False, index=cal, columns=list(data))
    for k, ms in enumerate(month_starts):
        members = [t for t in mem.loc[ms] if t in data]
        top = list(dv.loc[ms, members].dropna().sort_values(ascending=False).index[:100])
        end = month_starts[k + 1] if k + 1 < len(month_starts) else cal[-1] + pd.Timedelta(days=1)
        elig.loc[(elig.index >= ms) & (elig.index < end), top] = True
    inst, rows = {}, []
    for t, d in data.items():
        w = to_weekly(d)
        macd = w["Close"].ewm(span=12, adjust=False).mean() - w["Close"].ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        on = (macd > 0) & (sig > 0)
        on.iloc[:35] = False
        fresh = (on & ~on.shift(1, fill_value=False)).reindex(d.index).fillna(False).to_numpy(dtype=bool)
        x = {"name": t, "dates": d.index.values, "idx": d.index, "O": d["Open"].to_numpy(), "H": d["High"].to_numpy(),
             "L": d["Low"].to_numpy(), "C": d["Close"].to_numpy(), "macd": macd.reindex(d.index, method="ffill").to_numpy(),
             "wk_close": d.index.isin(w.index), "strength": (macd / w["Close"]).reindex(d.index, method="ffill").to_numpy()}
        inst[t] = x
        el = elig[t].reindex(d.index).fillna(False).to_numpy(dtype=bool)
        for j in np.flatnonzero(fresh & el):
            if j + 1 < len(d) and d.index[j + 1] >= pit.START:
                rows.append({"ticker": t, "e": int(j + 1), "entry_date": d.index[j + 1], "strength": x["strength"][j]})
    sig = pd.DataFrame(rows).sort_values(["entry_date", "strength"], ascending=[True, False]).reset_index(drop=True)
    return inst, sig, cal[cal >= pit.START]


def main():
    os.makedirs(OUT, exist_ok=True)
    spx = load_daily("^GSPC", drop_after=CUTOFF)["Close"]
    sma = spx.rolling(100).mean()
    reg = (spx > sma) & sma.notna()
    rows, keep = [], {}

    def prepare_regime(inst):
        for x in inst.values():
            x["reg_on"] = reg.reindex(x["idx"], method="ffill").fillna(False).to_numpy(dtype=bool)
            c = pd.Series(x["C"], index=x["idx"])
            m = c.rolling(100).mean()
            x["own_on"] = ((c > m) & m.notna()).to_numpy(dtype=bool)   # the stock above its own 100-day average
            x["both_on"] = x["reg_on"] & x["own_on"]

    def go(uni, inst, sig, cal, label, kw, filt, mo):
        s = sig[[inst[r.ticker][filt][r.e - 1] for r in sig.itertuples()]] if filt else sig
        for x in inst.values():
            x["reentry_ok"] = x[filt] if filt else None
            x["exit_flag"] = None
        mv.MAX_OPEN = mo
        res, camps = mv.run(inst, s.reset_index(drop=True), cal, kw, 365, None)
        st = mv.stats(res, camps)
        rows.append({"universe": uni, "variant": label, "max_open": mo, **st})
        keep[(uni, label, mo)] = (res, camps)
        print(f"{uni:9s} {label:31s} max {mo:2d} | CAGR {st['cagr_%']:6.2f} (IS {st['cagr_IS_%']:6.2f} / OOS {st['cagr_OOS_%']:6.2f}) "
              f"DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:3.0f}% camp {st['campaigns']} "
              f"win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}% stops {st['avg_stops']:.1f}", flush=True)

    # filter = None, or the per-day bool array checked at the signal close and before every re-entry:
    #   reg_on  = S&P 500 above its 100-day average, own_on = the stock above its own 100-day average, both_on = both
    sl1, sl2 = dict(mode="sl_reentry", sl=0.01), dict(mode="sl_reentry", sl=0.02)
    variants = [("no filter, no stop", dict(mode="base"), None), ("S&P filter, no stop", dict(mode="base"), "reg_on"),
                ("no filter, 1% stop", sl1, None),
                ("S&P filter, 1% stop", sl1, "reg_on"),
                ("S&P filter, 2% stop", sl2, "reg_on"),
                ("stock MA filter, no stop", dict(mode="base"), "own_on"),
                ("stock MA filter, 1% stop", sl1, "own_on"),
                ("stock MA filter, 2% stop", sl2, "own_on"),
                ("S&P + stock MA filter, 1% stop", sl1, "both_on")]

    # point-in-time universe
    inst, sig, cal = build_pit()
    prepare_regime(inst)
    last_day = cal[-1]

    def sim(x, e, **kw):
        r = _sim(x, e, **kw)
        if r["reason"] == "open" and x["idx"][-1] < last_day - pd.Timedelta(days=7):
            r["reason"] = "delisted"
        return r
    mv.simulate_campaign = sim
    print(f"point-in-time: {len(inst)} stocks, {len(sig)} signals", flush=True)
    for mo in [3, 10, 20]:
        for label, kw, filt in variants:
            go("PIT", inst, sig, cal, label, kw, filt, mo)
    # robustness: which same-day signal gets the slot is random (20 draws), instead of the MACD-strength order
    rnd = []
    rng = np.random.default_rng(7)
    for draw in range(20):
        s2 = sig.assign(strength=rng.random(len(sig))).sort_values(["entry_date", "strength"], ascending=[True, False])
        for label, kw, filt in [variants[0], variants[3], variants[6], variants[8]]:
            for mo in [10, 20]:
                ss = s2[[inst[r.ticker][filt][r.e - 1] for r in s2.itertuples()]] if filt else s2
                for x in inst.values():
                    x["reentry_ok"] = x[filt] if filt else None
                    x["exit_flag"] = None
                mv.MAX_OPEN = mo
                st = mv.stats(*mv.run(inst, ss.reset_index(drop=True), cal, kw, 365, None))
                rnd.append({"variant": label, "max_open": mo, "draw": draw, **st})
        print(f"random draw {draw} done", flush=True)
    rnd = pd.DataFrame(rnd)
    rnd.to_csv(os.path.join(OUT, "random_pick.csv"), index=False)
    rnd_sum = rnd.groupby(["variant", "max_open"])[["cagr_%", "max_dd_%", "sharpe"]].describe(percentiles=[.05, .5, .95])
    print(rnd_sum.round(2).to_string(), flush=True)
    # benchmarks over the same window
    pit_sum = json.load(open(os.path.join(ROOT, "results", "sp500_pit", "summary.json")))
    bench = {k: {kk: v[kk] for kk in ["cagr_%", "cagr_IS_%", "cagr_OOS_%", "max_dd_%", "sharpe"]} for k, v in pit_sum["benchmarks"].items()}

    # reference: today's top 100 (survivorship-biased), from 1990
    mv.simulate_campaign = _sim
    uni = pd.read_csv(os.path.join(ROOT, "data", "us100", "universe.csv"))
    inst_b = u100.build(uni)
    sig_b = mv.signals(inst_b)
    cal_b = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst_b.values()])))
    cal_b = cal_b[cal_b >= mv.START]
    prepare_regime(inst_b)
    for mo in [3, 10, 20]:
        for label, kw, filt in variants:
            go("today100", inst_b, sig_b, cal_b, label, kw, filt, mo)

    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    summary = {"rules": __doc__, "variants": rows, "pit_benchmarks": bench, "runs": {},
               "random_pick": [{"variant": v, "max_open": int(m), **{f"{c}_{q}": float(g[c].quantile(p)) for c in ["cagr_%", "max_dd_%", "sharpe"]
                                                                     for q, p in [("p05", .05), ("p50", .5), ("p95", .95)]},
                                "cagr_mean_%": float(g["cagr_%"].mean())}
                               for (v, m), g in rnd.groupby(["variant", "max_open"])]}
    for key in [("PIT", "no filter, no stop", 10), ("PIT", "S&P filter, no stop", 10), ("PIT", "S&P filter, 1% stop", 10),
                ("PIT", "S&P filter, 2% stop", 10), ("PIT", "S&P filter, 1% stop", 20), ("PIT", "S&P filter, 1% stop", 3),
                ("PIT", "stock MA filter, no stop", 10), ("PIT", "stock MA filter, 1% stop", 10), ("PIT", "stock MA filter, 1% stop", 20),
                ("PIT", "S&P + stock MA filter, 1% stop", 10), ("PIT", "S&P + stock MA filter, 1% stop", 20)]:
        res, camps = keep[key]
        name = f"{key[0]}_{key[1].replace(' ', '_').replace(',', '').replace('&', '').replace('%', 'pct').replace('+', 'and')}_{key[2]}"
        res.to_csv(os.path.join(OUT, f"equity_{name}.csv"))
        summary["runs"][name] = {"key": key, "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                               for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                 "live": camps[camps.reason == "open"].astype(str).to_dict("records")}
    for k in ["EW_top100_pit", "SP500TR"]:
        summary["runs"][k] = {"equity_weekly": pit_sum["benchmarks"][k]["equity_weekly"]}
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("benchmarks (1997-2026):", {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in bench.items()})


if __name__ == "__main__":
    main()
