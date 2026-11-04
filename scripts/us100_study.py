"""The weekly-MACD strategy and its variants on the 100 biggest US stocks (today's top 100 by market
cap among S&P 500 members; see scripts/us100_universe.py).

Same rules as the index/sector study: buy at the next open when the weekly MACD line and signal
line both turn > 0, sell when the weekly MACD line < 0 (next open) or at the take-profit; max N
stocks at once (N = 3 as before; 5/10/20 tested); 1/N of equity per position, compounding.
Variants: take-profit grid, 1 % stop + re-entry, 1 % ladder (martingale / flat), pyramiding up.

SURVIVORSHIP BIAS: the universe is today's 100 biggest companies, i.e. the winners. Results
are compared with buy & hold of the SAME 100 stocks (same bias) as well as the S&P 500.

Usage:  python scripts/us100_study.py   -> results/us100/
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

OUT = os.path.join(ROOT, "results", "us100")
RAW = os.path.join(ROOT, "data", "us100", "raw")
DATA_CUTOFF = pd.Timestamp(os.environ.get("DATA_CUTOFF", "2026-11-04"))
START = pd.Timestamp("1990-01-01")


def load(t):
    d = pd.read_csv(os.path.join(RAW, f"{t}.csv"), index_col=0, parse_dates=True)
    d = d[["Open", "High", "Low", "Close"]].astype(float).dropna()
    d = d[d.index < DATA_CUTOFF]
    d = d[(d > 0).all(axis=1)]
    ok = (d.High > d.Low).rolling(60).mean() > 0.95
    if ok.any():
        d = d[d.index >= ok.idxmax() - pd.Timedelta(days=90)]
    d["High"] = d[["High", "Open", "Close"]].max(axis=1)
    d["Low"] = d[["Low", "Open", "Close"]].min(axis=1)
    return d[~d.index.duplicated()]


def build(uni):
    from strategy.data import to_weekly
    inst = {}
    for t, name in zip(uni.ticker, uni.name):
        d = load(t)
        if len(d) < 300:
            continue
        w = to_weekly(d)
        macd = w["Close"].ewm(span=12, adjust=False).mean() - w["Close"].ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        on = (macd > 0) & (sig > 0)
        on.iloc[:35] = False
        fresh = on & ~on.shift(1, fill_value=False)
        inst[t] = {"name": name, "dates": d.index.values, "idx": d.index, "O": d["Open"].to_numpy(),
                   "H": d["High"].to_numpy(), "L": d["Low"].to_numpy(), "C": d["Close"].to_numpy(),
                   "macd": macd.reindex(d.index, method="ffill").to_numpy(), "wk_close": d.index.isin(w.index),
                   "fresh_close": fresh.reindex(d.index).fillna(False).to_numpy(dtype=bool),
                   "strength": (macd / w["Close"]).reindex(d.index, method="ffill").to_numpy(),
                   "on_now": bool(on.iloc[-1]), "macd_now": float(macd.iloc[-1] / w["Close"].iloc[-1]),
                   "phase_start": str(w.index[on & ~on.shift(1, fill_value=False)][-1].date()) if on.iloc[-1] else ""}
    return inst


def bench_ew(inst, cal):
    rets = pd.concat([pd.Series(x["C"], index=x["idx"]).pct_change().rename(t) for t, x in inst.items()], axis=1, sort=True)
    r = rets.reindex(cal).mean(axis=1, skipna=True).fillna(0.0)
    return (1 + r).cumprod() * mv.CAPITAL


def bench_index(sym, cal):
    import yfinance as yf
    path = os.path.join(ROOT, "data", "us100", f"{sym.replace('^', '')}.csv")
    if not os.path.exists(path):
        d = yf.download(sym, start="1988-01-01", progress=False, auto_adjust=True)
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = d.columns.get_level_values(0)
        d.to_csv(path)
    c = pd.read_csv(path, index_col=0, parse_dates=True)["Close"]
    c = c[c.index < DATA_CUTOFF].reindex(cal).ffill().dropna()
    return c / c.iloc[0] * mv.CAPITAL


def eq_stats(e):
    r = e.pct_change().fillna(0.0)
    y = (e.index[-1] - e.index[0]).days / 365.25

    def cagr(s):
        yy = (s.index[-1] - s.index[0]).days / 365.25
        return 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / yy) - 1)
    return {"cagr_%": cagr(e), "cagr_IS_%": cagr(e[e.index < SPLIT_DATE]), "cagr_OOS_%": cagr(e[e.index >= SPLIT_DATE]),
            "max_dd_%": 100 * float((e / e.cummax() - 1).min()), "sharpe": float(r.mean() / r.std() * np.sqrt(252)),
            "years": y}


def main():
    os.makedirs(OUT, exist_ok=True)
    uni = pd.read_csv(os.path.join(ROOT, "data", "us100", "universe.csv"))
    inst = build(uni)
    sig = mv.signals(inst)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
    cal = cal[cal >= START]
    print(f"{len(inst)} stocks, {len(sig)} MACD up-phase signals since 1990", flush=True)
    rows, keep = [], {}

    def go(label, kw, td, tl, max_open=3, s=sig):
        mv.MAX_OPEN = max_open
        res, camps = mv.run(inst, s, cal, kw, td, tl)
        st = mv.stats(res, camps)
        tt = f"{td}d" if td else "none"
        tlv = f"+{int(tl * 100)}%" if tl else "none"
        rows.append({"variant": label, "max_open": max_open, "tp_time": tt, "tp_level": tlv, **st})
        keep[(label, max_open, tt, tlv)] = (res, camps)
        print(f"{label:22s} max {max_open:2d} time {tt:5s} level {tlv:5s} | CAGR {st['cagr_%']:6.2f} "
              f"(IS {st['cagr_IS_%']:6.2f} / OOS {st['cagr_OOS_%']:6.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} "
              f"inv {st['avg_invested_%']:4.0f}% camp {st['campaigns']} win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}%", flush=True)
        return res, camps

    base = dict(mode="base")
    for td, tl in itertools.product(mv.TP_DAYS, mv.TP_LEVELS):           # take-profit grid, max 3
        go("base", base, td, tl)
    for mo in [5, 10, 20]:                                              # more slots
        go("base", base, 365, None, mo)
        go("base", base, None, None, mo)
    for label, kw in [("sl1_reentry", dict(mode="sl_reentry", sl=0.01)), ("sl5_reentry", dict(mode="sl_reentry", sl=0.05)),
                      ("ladder_mart_K5", dict(mode="ladder", step=0.01, K=5, sizing="mart")),
                      ("ladder_flat_K10", dict(mode="ladder", step=0.01, K=10, sizing="flat")),
                      ("pyr_1pct_K3", dict(mode="pyramid", step=0.01, K=3)), ("pyr_1pct_K5", dict(mode="pyramid", step=0.01, K=5)),
                      ("pyr_1pct_K10", dict(mode="pyramid", step=0.01, K=10)), ("pyr_1pct_K20", dict(mode="pyramid", step=0.01, K=20))]:
        go(label, kw, 365, None, 3)
        go(label, kw, 365, None, 10)
    # how much does WHICH signal gets the slot matter? random tie-break / random pick among same-day signals
    rng = np.random.default_rng(3)
    rnd = []
    for _ in range(30):
        s2 = sig.assign(strength=rng.random(len(sig))).sort_values(["entry_date", "strength"], ascending=[True, False])
        mv.MAX_OPEN = 3
        res, camps = mv.run(inst, s2.reset_index(drop=True), cal, base, 365, None)
        st = mv.stats(res, camps)
        rnd.append({k: st[k] for k in ["cagr_%", "sharpe", "max_dd_%"]})
    rnd = pd.DataFrame(rnd)
    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)

    ew = bench_ew(inst, cal)
    spx_tr = bench_index("^SP500TR", cal)
    bm = {"EW_100": {**eq_stats(ew), "label": "Equal-weight buy & hold of the same 100 stocks"},
          "SP500TR": {**eq_stats(spx_tr), "label": "S&P 500 total return"}}
    print("benchmarks:", {k: {kk: round(vv, 2) for kk, vv in v.items() if kk != "label"} for k, v in bm.items()})
    print("random slot pick (30 draws):", rnd.describe().loc[["mean", "5%" if "5%" in rnd.describe().index else "min", "max"]].round(2).to_dict())

    summary = {"rules": __doc__, "n_stocks": len(inst), "n_signals": len(sig), "benchmarks": {}, "runs": {},
               "random_pick": {c: {"mean": float(rnd[c].mean()), "p05": float(rnd[c].quantile(.05)),
                                   "p95": float(rnd[c].quantile(.95))} for c in rnd.columns}}
    for k, e in [("EW_100", ew), ("SP500TR", spx_tr)]:
        summary["benchmarks"][k] = {**bm[k], "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                               for d, v in e.resample("W-FRI").last().dropna().items()]}
    for key in [("base", 3, "365d", "none"), ("base", 10, "365d", "none"), ("base", 3, "none", "none"),
                ("base", 10, "none", "none"), ("pyr_1pct_K5", 3, "365d", "none"), ("sl1_reentry", 3, "365d", "none"),
                ("sl1_reentry", 10, "365d", "none"), ("base", 20, "365d", "none")]:
        res, camps = keep[key]
        name = "_".join(map(str, key)).replace("+", "").replace("%", "")
        res.to_csv(os.path.join(OUT, f"equity_{name}.csv"))
        camps.to_csv(os.path.join(OUT, f"campaigns_{name}.csv"), index=False)
        summary["runs"][name] = {"key": key, "stats": grid[(grid.variant == key[0]) & (grid.max_open == key[1]) &
                                                           (grid.tp_time == key[2]) & (grid.tp_level == key[3])].iloc[0].to_dict(),
                                 "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                   for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                 "live": camps[camps.reason == "open"].astype(str).to_dict("records"),
                                 "by_stock": camps.groupby("name")["pnl_$"].sum().sort_values().round(0).to_dict()}
    summary["state_now"] = [{"ticker": t, "name": x["name"], "on": x["on_now"], "macd_pct": 100 * x["macd_now"],
                             "phase_start": x["phase_start"]} for t, x in inst.items()]
    summary["variants"] = rows
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
