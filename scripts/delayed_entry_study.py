"""Delayed entry: confirm the weekly-MACD signal for 2 months, then hold 10 months.

  signal  : new weekly MACD up-phase (MACD and signal line both turn > 0), as before
  wait    : do nothing for 2 months. At the first weekly close >= signal + 61 days, the trade is taken
            only if the weekly MACD line stayed > 0 on every weekly close since the signal (the up-phase
            was never broken). Variant "+ price up": the close must also be above the close at the signal.
  entry   : next open after that check close (entry price E0)
  exits   : the usual stop -- 1 % (or 2 %) below E0 with re-entry at E0; a weekly close with MACD < 0
            -> sell at the next open; time exit after 10 months (first open >= entry + 304 days)
  filters : none / S&P 500 above its 50-day / 100-day average (checked at the entry decision and before
            every re-entry), as in the earlier studies
Baseline: immediate entry at the next open after the signal with a 1-year hold (the earlier rules).
Sensitivity: wait 1 month + hold 11 months, wait 3 months + hold 9 months.
Universes: 27 DM indices + US sectors (max 3 / 5, 1990-2026) and the point-in-time S&P 500 top 100
(max 10 / 20, 1997-2026; delisted stocks closed at their last price). Random pick among same-day
signals for the key variants.

Usage:  python scripts/delayed_entry_study.py indices|stocks|stocks-wait1m   -> results/delayed_entry/
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
import stocks_regime_study as sr  # noqa: E402
from strategy.macd_engine import simulate_campaign as _sim  # noqa: E402

OUT = os.path.join(ROOT, "results", "delayed_entry")
FILTERS = {"none": None, "S&P 50d": "spx50", "S&P 100d": "spx100"}
STOPS = sm.STOPS
# entry rule -> (wait days, hold days, require price above the signal close)
ENTRIES = {"immediate, hold 12m": (0, 365, False), "wait 2m, hold 10m": (61, 304, False),
           "wait 2m + price up, hold 10m": (61, 304, True)}
SENS = {"wait 1m, hold 11m": (30, 335, False), "wait 3m, hold 9m": (91, 274, False)}


def delay_signals(inst, sig, wait_days, price_up):
    """Move each signal to the first weekly close >= signal + wait_days if the MACD up-phase held."""
    if wait_days == 0:
        return sig.copy()
    rows = []
    for r in sig.itertuples(index=False):
        x = inst[r.ticker]
        j = r.e - 1
        idx, wk, macd, C = x["idx"], x["wk_close"], x["macd"], x["C"]
        target = idx[j] + pd.Timedelta(days=wait_days)
        k0 = idx.searchsorted(target)
        cand = np.flatnonzero(wk[k0:])
        if not len(cand):
            continue
        k = k0 + int(cand[0])
        seg = slice(j + 1, k + 1)
        if not np.all(macd[seg][wk[seg]] > 0):
            continue  # the MACD went below 0 on a weekly close during the wait -> no trade
        if price_up and not C[k] > C[j]:
            continue
        if k + 1 >= len(C):
            continue
        rows.append({"ticker": r.ticker, "e": int(k + 1), "entry_date": idx[k + 1], "strength": x["strength"][k]})
    out = pd.DataFrame(rows, columns=["ticker", "e", "entry_date", "strength"])
    return out.sort_values(["entry_date", "strength"], ascending=[True, False]).reset_index(drop=True)


def load(universe):
    spx, reg = sm.regimes()
    if universe == "indices":
        inst = mv.build()
        sig = mv.signals(inst)
        cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
        cal = cal[cal >= mv.START]
        mv.simulate_campaign = _sim
        sizes = [3, 5]
    else:
        inst, sig, cal = sr.build_pit()
        last_day = cal[-1]

        def sim(x, e, **kw):
            r = _sim(x, e, **kw)
            if r["reason"] == "open" and x["idx"][-1] < last_day - pd.Timedelta(days=7):
                r["reason"] = "delisted"
            return r
        mv.simulate_campaign = sim
        sizes = [10, 20]
    sm.prepare(inst, reg)
    return spx, inst, sig, cal, sizes


def main(universe):
    os.makedirs(OUT, exist_ok=True)
    spx, inst, sig, cal, sizes = load(universe)
    delayed = {k: delay_signals(inst, sig, w, p) for k, (w, _, p) in {**ENTRIES, **SENS}.items()}
    print(f"{universe}: {len(sig)} signals; kept after the wait: " +
          ", ".join(f"{k} {len(v)} ({len(v) / len(sig):.0%})" for k, v in delayed.items()), flush=True)
    rows, keep = [], {}

    def go(entry, f, sname, mo, s=None):
        hold = {**ENTRIES, **SENS}[entry][1]
        res, camps, st = sm.run_one(inst, delayed[entry] if s is None else s, cal, FILTERS[f], STOPS[sname], hold, mo)
        if s is not None:
            return st
        rows.append({"universe": universe, "entry": entry, "filter": f, "stop": sname, "max_open": mo, **st})
        keep[(entry, f, sname, mo)] = (res, camps)
        print(f"{entry:28s} {f:8s} {sname:7s} max {mo:2d} | CAGR {st['cagr_%']:6.2f} (IS {st['cagr_IS_%']:6.2f} / OOS "
              f"{st['cagr_OOS_%']:6.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:3.0f}% "
              f"camp {st['campaigns']} win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}% days {st['avg_days']:.0f} "
              f"stops {st['avg_stops']:.1f} exit time/macd {st['exit_time%']:.0f}/{st['exit_macd%']:.0f}%", flush=True)

    for entry, f, sname, mo in itertools.product(ENTRIES, FILTERS, STOPS, sizes):
        go(entry, f, sname, mo)
    for entry, f, sname in itertools.product(SENS, FILTERS, STOPS):
        go(entry, f, sname, sizes[0])

    # robustness: random pick among same-day signals
    key = [("immediate, hold 12m", "none", "1% stop"), ("wait 2m, hold 10m", "none", "1% stop"),
           ("wait 2m, hold 10m", "none", "no stop"), ("wait 2m, hold 10m", "S&P 50d", "1% stop"),
           ("wait 2m, hold 10m", "S&P 100d", "no stop"), ("immediate, hold 12m", "S&P 100d", "no stop")]
    n_draws = 50 if universe == "indices" else 20
    rng = np.random.default_rng(13)
    rnd = []
    for draw in range(n_draws):
        for entry, f, sname in key:  # random priority among entries that fall on the same day
            d2 = delayed[entry].assign(strength=rng.random(len(delayed[entry])))
            d2 = d2.sort_values(["entry_date", "strength"], ascending=[True, False]).reset_index(drop=True)
            for mo in sizes:
                rnd.append({"entry": entry, "filter": f, "stop": sname, "max_open": mo, "draw": draw, **go(entry, f, sname, mo, d2)})
        if draw % 5 == 4:
            print(f"random draw {draw} done", flush=True)
    rnd = pd.DataFrame(rnd)
    rnd.to_csv(os.path.join(OUT, f"{universe}_random_pick.csv"), index=False)
    rnd_sum = []
    for (entry, f, sname, mo), g in rnd.groupby(["entry", "filter", "stop", "max_open"]):
        rnd_sum.append({"entry": entry, "filter": f, "stop": sname, "max_open": int(mo),
                        **{f"{c}_{q}": float(g[c].quantile(p)) for c in ["cagr_%", "max_dd_%", "sharpe"]
                           for q, p in [("p05", .05), ("p50", .5), ("p95", .95)]},
                        **{f"{c}_mean": float(g[c].mean()) for c in ["cagr_%", "max_dd_%", "sharpe"]}})
    print(pd.DataFrame(rnd_sum).round(2).to_string(), flush=True)

    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, f"{universe}_variants.csv"), index=False)
    summary = {"rules": __doc__, "universe": universe, "signals": len(sig),
               "kept": {k: len(v) for k, v in delayed.items()}, "variants": rows, "random_pick": rnd_sum, "runs": {}}
    m = sizes[0]
    for k in [("immediate, hold 12m", "none", "no stop", m), ("immediate, hold 12m", "none", "1% stop", m),
              ("immediate, hold 12m", "S&P 100d", "no stop", m), ("wait 2m, hold 10m", "none", "no stop", m),
              ("wait 2m, hold 10m", "none", "1% stop", m), ("wait 2m, hold 10m", "S&P 50d", "1% stop", m),
              ("wait 2m, hold 10m", "S&P 100d", "no stop", m), ("wait 2m, hold 10m", "none", "1% stop", sizes[1]),
              ("immediate, hold 12m", "none", "1% stop", sizes[1]), ("wait 2m + price up, hold 10m", "none", "1% stop", m)]:
        res, camps = keep[k]
        name = "_".join(str(v) for v in k).replace(" ", "").replace(",", "_").replace("&", "").replace("%", "pct").replace("+", "and")
        res.to_csv(os.path.join(OUT, f"{universe}_equity_{name}.csv"))
        eq = res["equity"]
        summary["runs"][name] = {"key": k, "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                             for d, v in eq.resample("W-FRI").last().dropna().items()],
                                 "by_year": eq.resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict(),
                                 "live": camps[camps.reason == "open"].astype(str).to_dict("records")}
    # pending: signals still inside the 2-month wait at the data end
    last = cal[-1]
    pend = []
    for r in sig.itertuples(index=False):
        x = inst[r.ticker]
        j = r.e - 1
        if x["idx"][j] >= last - pd.Timedelta(days=61) and x["idx"][-1] >= last - pd.Timedelta(days=7):
            wk = x["wk_close"][j + 1:]
            ok = bool(np.all(x["macd"][j + 1:][wk] > 0))
            pend.append({"ticker": r.ticker, "name": x.get("name") or r.ticker, "signal_close": str(x["idx"][j].date()),
                         "check_from": str((x["idx"][j] + pd.Timedelta(days=61)).date()), "macd_still_up": ok,
                         "price_vs_signal_%": float(100 * (x["C"][-1] / x["C"][j] - 1))})
    summary["pending"] = pend
    with open(os.path.join(OUT, f"{universe}_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("pending:", pend, flush=True)


def check_wait1m():
    """Robustness of the one stand-out sensitivity result on stocks: wait 1 month, hold 11 months."""
    spx, inst, sig, cal, sizes = load("stocks")
    d1 = delay_signals(inst, sig, *[SENS["wait 1m, hold 11m"][i] for i in (0, 2)])
    hold = SENS["wait 1m, hold 11m"][1]
    combos = [("S&P 100d", "1% stop"), ("S&P 100d", "no stop"), ("S&P 50d", "no stop"), ("none", "1% stop")]
    det, rnd, runs = [], [], {}
    for (f, sname), mo in itertools.product(combos, sizes):
        res, camps, st = sm.run_one(inst, d1, cal, FILTERS[f], STOPS[sname], hold, mo)
        det.append({"filter": f, "stop": sname, "max_open": mo, **st})
        if (f, sname) == ("S&P 100d", "1% stop"):
            runs[f"wait1m_SP100d_1pctstop_{mo}"] = {
                "equity_weekly": [[d.date().isoformat(), round(float(v), 2)] for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                "by_year": res["equity"].resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict(),
                "live": camps[camps.reason == "open"].astype(str).to_dict("records")}
        print(f"wait 1m, hold 11m {f:8s} {sname:7s} max {mo} | CAGR {st['cagr_%']:5.2f} DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f}", flush=True)
    rng = np.random.default_rng(17)
    for draw in range(20):
        d2 = d1.assign(strength=rng.random(len(d1))).sort_values(["entry_date", "strength"], ascending=[True, False]).reset_index(drop=True)
        for (f, sname), mo in itertools.product(combos, sizes):
            st = sm.run_one(inst, d2, cal, FILTERS[f], STOPS[sname], hold, mo)[2]
            rnd.append({"filter": f, "stop": sname, "max_open": mo, "draw": draw, **st})
    rnd = pd.DataFrame(rnd)
    summ = rnd.groupby(["filter", "stop", "max_open"])[["cagr_%", "max_dd_%", "sharpe"]].agg(["mean", lambda v: v.quantile(.05), lambda v: v.quantile(.95)])
    print(summ.round(2).to_string(), flush=True)
    out = {"deterministic": det, "runs": runs, "random_pick": [{"filter": f, "stop": s_, "max_open": int(m), **{f"{c}_mean": float(g[c].mean()) for c in ["cagr_%", "max_dd_%", "sharpe"]},
                                                   **{f"{c}_p05": float(g[c].quantile(.05)) for c in ["cagr_%", "max_dd_%", "sharpe"]},
                                                   **{f"{c}_p95": float(g[c].quantile(.95)) for c in ["cagr_%", "max_dd_%", "sharpe"]}}
                                                  for (f, s_, m), g in rnd.groupby(["filter", "stop", "max_open"])]}
    with open(os.path.join(OUT, "stocks_wait1m_check.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "indices"
    check_wait1m() if arg == "stocks-wait1m" else main(arg)
