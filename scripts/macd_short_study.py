"""Short leg on DM indices: the weekly-MACD strategy mirrored for downtrends.

  signal      : weekly MACD line and signal line both turn < 0 (new down-phase) -> SHORT at the next open
  stop        : first weekly close with the MACD line > 0 -> cover at the next open
  take-profit : 1 year (also 3/6 months, none, and price targets tested)
  re-entry    : optional 1 % stop above the short entry E0, re-short when price falls back to E0
  portfolio   : max 3 shorts at once, 1/3 of equity each, compounding, no leverage, 3 bps/side.
                Combined long/short books (each half the capital, or long 100 % + short overlay).

Shorts are simulated with the long engine on prices mirrored around the entry price
(P' = 2*E0 - P, high/low swapped, MACD sign flipped), which gives the exact short P&L per unit.
Price indices without dividends; financing / borrow not modelled (index futures).

Usage:  python scripts/macd_short_study.py   -> results/macd_short/
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
from strategy.backtest import SPLIT_DATE  # noqa: E402
from strategy.data import load_daily, to_weekly  # noqa: E402
from strategy.macd_engine import simulate_campaign as _sim  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "macd_short")
CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")


def build(tickers, side):
    inst = {}
    for t in tickers:
        d = load_daily(t, drop_after=CUTOFF)
        w = to_weekly(d)
        macd = w["Close"].ewm(span=12, adjust=False).mean() - w["Close"].ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        cond = ((macd > 0) & (sig > 0)) if side == "long" else ((macd < 0) & (sig < 0))
        cond.iloc[:35] = False
        fresh = cond & ~cond.shift(1, fill_value=False)
        strength = (macd / w["Close"]) * (1 if side == "long" else -1)
        inst[t] = {"name": UNIVERSE[t][0], "dates": d.index.values, "idx": d.index, "O": d["Open"].to_numpy(),
                   "H": d["High"].to_numpy(), "L": d["Low"].to_numpy(), "C": d["Close"].to_numpy(),
                   "macd": macd.reindex(d.index, method="ffill").to_numpy(), "wk_close": d.index.isin(w.index),
                   "fresh_close": fresh.reindex(d.index).fillna(False).to_numpy(dtype=bool),
                   "strength": strength.reindex(d.index, method="ffill").to_numpy(),
                   "cond_now": bool(cond.iloc[-1]), "macd_now": float(macd.iloc[-1] / w["Close"].iloc[-1]),
                   "phase_start": str(w.index[cond & ~cond.shift(1, fill_value=False)][-1].date()) if cond.iloc[-1] else ""}
    return inst


def short_sim(x, e, **kw):
    """Short campaign = long campaign on prices mirrored around the entry open E0."""
    E0 = x["O"][e]
    m = {"dates": x["dates"], "wk_close": x["wk_close"], "macd": -x["macd"],
         "O": np.maximum(2 * E0 - x["O"], 1e-6 * E0), "H": np.maximum(2 * E0 - x["L"], 1e-6 * E0),
         "L": np.maximum(2 * E0 - x["H"], 1e-6 * E0), "C": np.maximum(2 * E0 - x["C"], 1e-6 * E0)}
    r = _sim(m, e, **kw)
    n = len(r["notional"])
    cm = m["C"][e:e + n]
    r["notional"] = r["notional"] / cm * x["C"][e:e + n]  # short notional at real prices
    return r


def run_book(inst, side, kw, td, tl, max_open=3):
    mv.simulate_campaign = short_sim if side == "short" else _sim
    mv.MAX_OPEN = max_open
    sig = mv.signals(inst)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
    cal = cal[cal >= mv.START]
    res, camps = mv.run(inst, sig, cal, kw, td, tl)
    return res, camps


def eq_stats(e):
    r = e.pct_change().fillna(0.0)

    def cagr(s):
        y = (s.index[-1] - s.index[0]).days / 365.25
        return 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1)
    return {"cagr_%": cagr(e), "cagr_IS_%": cagr(e[e.index < SPLIT_DATE]), "cagr_OOS_%": cagr(e[e.index >= SPLIT_DATE]),
            "max_dd_%": 100 * float((e / e.cummax() - 1).min()), "sharpe": float(r.mean() / r.std() * np.sqrt(252)),
            "vol_%": 100 * float(r.std() * np.sqrt(252))}


def main():
    os.makedirs(OUT, exist_ok=True)
    dm = [t for t, v in UNIVERSE.items() if v[1] == "DM index"]
    books = {("short", "DM"): build(dm, "short"), ("long", "DM"): build(dm, "long"),
             ("short", "all27"): build(list(UNIVERSE), "short")}
    rows, keep = [], {}

    def go(side, uni, label, kw, td, tl, mo=3):
        res, camps = run_book(books[(side, uni)], side, kw, td, tl, mo)
        st = mv.stats(res, camps)
        tt = f"{td}d" if td else "none"
        tlv = f"{'-' if side == 'short' else '+'}{int(tl * 100)}%" if tl else "none"
        rows.append({"side": side, "universe": uni, "variant": label, "max_open": mo, "tp_time": tt, "tp_level": tlv, **st})
        keep[(side, uni, label, mo, tt, tlv)] = (res, camps)
        print(f"{side:5s} {uni:5s} {label:12s} max {mo} time {tt:5s} level {tlv:5s} | CAGR {st['cagr_%']:6.2f} "
              f"(IS {st['cagr_IS_%']:6.2f} / OOS {st['cagr_OOS_%']:6.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:5.2f} "
              f"inv {st['avg_invested_%']:3.0f}% camp {st['campaigns']} win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}% "
              f"stops {st['avg_stops']:.1f}", flush=True)
        return res

    base, sl1 = dict(mode="base"), dict(mode="sl_reentry", sl=0.01)
    for (lab, kw), td, tl in itertools.product([("base", base), ("sl1_reentry", sl1)], [91, 182, 365, None], [0.10, 0.20, None]):
        go("short", "DM", lab, kw, td, tl)
    for lab, kw in [("base", base), ("sl1_reentry", sl1), ("sl3_reentry", dict(mode="sl_reentry", sl=0.03))]:
        go("short", "DM", lab, kw, 365, None, 5)
        go("short", "all27", lab, kw, 365, None)
    go("short", "DM", "sl3_reentry", dict(mode="sl_reentry", sl=0.03), 365, None)
    for lab, kw in [("base", base), ("sl1_reentry", sl1)]:
        go("long", "DM", lab, kw, 365, None)

    # combined books (daily returns): 50/50 capital, and long 100 % + short 100 % overlay
    def ret(key):
        return keep[key][0]["equity"].pct_change().fillna(0.0)
    combos = {}
    for lname, skey in [("base", ("short", "DM", "base", 3, "365d", "none")), ("sl1_reentry", ("short", "DM", "sl1_reentry", 3, "365d", "none"))]:
        rl = ret(("long", "DM", lname, 3, "365d", "none"))
        rs = ret(skey)
        rl, rs = rl.align(rs, join="outer", fill_value=0.0)
        for cname, rc in [(f"50/50 long+short ({lname})", 0.5 * rl + 0.5 * rs), (f"long 100% + short overlay 100% ({lname})", rl + rs)]:
            e = (1 + rc).cumprod() * mv.CAPITAL
            combos[cname] = (e, {**eq_stats(e), "corr_long_short": float(np.corrcoef(rl, rs)[0, 1])})
            print(cname, {k: round(v, 2) for k, v in combos[cname][1].items()})
    # benchmark: equal-weight DM indices buy & hold
    cl = pd.concat([pd.Series(x["C"], index=x["idx"]).pct_change().rename(t) for t, x in books[("long", "DM")].items()], axis=1, sort=True)
    bh = (1 + cl[cl.index >= mv.START].mean(axis=1).fillna(0.0)).cumprod() * mv.CAPITAL
    bh_st = eq_stats(bh)
    print("EW DM buy & hold", {k: round(v, 2) for k, v in bh_st.items()})

    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    summary = {"rules": __doc__, "variants": rows, "combos": {k: v[1] for k, v in combos.items()},
               "bh_dm": {**bh_st, "equity_weekly": [[d.date().isoformat(), round(float(v), 2)] for d, v in bh.resample("W-FRI").last().dropna().items()]},
               "runs": {}, "state_now": [{"ticker": t, "name": x["name"], "short_on": x["cond_now"], "macd_pct": 100 * x["macd_now"],
                                          "phase_start": x["phase_start"]} for t, x in books[("short", "DM")].items()]}
    for key in [("short", "DM", "base", 3, "365d", "none"), ("short", "DM", "sl1_reentry", 3, "365d", "none"),
                ("long", "DM", "base", 3, "365d", "none"), ("long", "DM", "sl1_reentry", 3, "365d", "none")]:
        res, camps = keep[key]
        name = "_".join(map(str, key[:4]))
        res.to_csv(os.path.join(OUT, f"equity_{name}.csv"))
        camps.to_csv(os.path.join(OUT, f"campaigns_{name}.csv"), index=False)
        summary["runs"][name] = {"stats": grid[(grid.side == key[0]) & (grid.universe == key[1]) & (grid.variant == key[2]) &
                                               (grid.max_open == key[3]) & (grid.tp_time == key[4]) & (grid.tp_level == key[5])].iloc[0].to_dict(),
                                 "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                   for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                 "live": camps[camps.reason == "open"].astype(str).to_dict("records"),
                                 "by_year": res["equity"].resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict()}
    for cname, (e, st) in combos.items():
        summary["runs"][cname] = {"stats": st, "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                                 for d, v in e.resample("W-FRI").last().dropna().items()]}
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
