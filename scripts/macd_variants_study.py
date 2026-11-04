"""Weekly-MACD strategy (no DeMark), entry/exit variants, max 3 assets.

Signal: weekly MACD line and signal line both turn > 0 (new up-phase) -> campaign starts at the
next open. Always: MACD stop (weekly close with MACD < 0 -> out). Max 3 campaigns at once
(different assets); a signal that finds no free slot is skipped; ties -> strongest MACD/price.
Each campaign gets a budget of 1/3 of equity at its start (compounding, no leverage).

Modes (see strategy/macd_engine.py):
  base        buy and hold the budget
  sl_reentry  1 % stop below the first entry E0, re-enter on a buy-stop at E0, unlimited times
  ladder      buy every 1 % down from E0: martingale (sizes 1,2,4,...) or flat, full ladder = budget
Take-profits: time {3, 6, 12, 24 months, none} x level {+5, +10, +20, +30 %, none}
(level vs E0 for base / sl_reentry, vs average cost for ladder).

Usage:  python scripts/macd_variants_study.py   -> results/macd_variants/
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

from strategy.backtest import SPLIT_DATE  # noqa: E402
from strategy.data import load_daily, to_weekly  # noqa: E402
from strategy.macd_engine import simulate_campaign  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "macd_variants")
DATA_CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")
CAPITAL = 100_000.0
START = pd.Timestamp("1990-01-01")
MAX_OPEN = 3
NO_LEVERAGE = True  # a new campaign never gets more than the cash not committed to open campaigns
TP_DAYS = [91, 182, 365, 730, None]
TP_LEVELS = [0.05, 0.10, 0.20, 0.30, None]
MODES = {  # name -> engine kwargs
    "base": dict(mode="base"),
    "sl1_reentry": dict(mode="sl_reentry", sl=0.01),
    "ladder_mart_K5": dict(mode="ladder", step=0.01, K=5, sizing="mart"),
    "ladder_flat_K10": dict(mode="ladder", step=0.01, K=10, sizing="flat"),
}
EXTRA = {  # sensitivities at the default take-profit (1 year, no level)
    "sl2_reentry": dict(mode="sl_reentry", sl=0.02),
    "sl3_reentry": dict(mode="sl_reentry", sl=0.03),
    "sl5_reentry": dict(mode="sl_reentry", sl=0.05),
    "ladder_mart_K7": dict(mode="ladder", step=0.01, K=7, sizing="mart"),
    "ladder_flat_K20": dict(mode="ladder", step=0.01, K=20, sizing="flat"),
    "ladder_mart_K5_step2": dict(mode="ladder", step=0.02, K=5, sizing="mart"),
}


def build():
    inst = {}
    for t in UNIVERSE:
        d = load_daily(t, drop_after=DATA_CUTOFF)
        w = to_weekly(d)
        macd = w["Close"].ewm(span=12, adjust=False).mean() - w["Close"].ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        on = (macd > 0) & (sig > 0)
        on.iloc[:35] = False
        fresh = on & ~on.shift(1, fill_value=False)
        inst[t] = {"dates": d.index.values, "idx": d.index, "O": d["Open"].to_numpy(), "H": d["High"].to_numpy(),
                   "L": d["Low"].to_numpy(), "C": d["Close"].to_numpy(),
                   "macd": macd.reindex(d.index, method="ffill").to_numpy(),
                   "wk_close": d.index.isin(w.index),
                   "fresh_close": fresh.reindex(d.index).fillna(False).to_numpy(dtype=bool),
                   "strength": (macd / w["Close"]).reindex(d.index, method="ffill").to_numpy()}
    return inst


def signals(inst):
    rows = []
    for t, x in inst.items():
        for j in np.flatnonzero(x["fresh_close"]):
            if j + 1 < len(x["C"]) and x["idx"][j + 1] >= START:
                rows.append({"ticker": t, "e": int(j + 1), "entry_date": x["idx"][j + 1], "strength": x["strength"][j]})
    return pd.DataFrame(rows).sort_values(["entry_date", "strength"], ascending=[True, False]).reset_index(drop=True)


def run(inst, sig, cal, kw, tp_days, tp_level):
    cal_pos = pd.Series(np.arange(len(cal)), index=cal)
    pnl_day = np.zeros(len(cal))
    expo_day = np.zeros(len(cal))
    eq = np.zeros(len(cal))
    active = []  # dicts: end, ticker, pos (calendar indices), notional ($ path), budget
    camps = []
    equity = CAPITAL
    sig_by_day = {d: g for d, g in sig.groupby("entry_date")}
    for di, day in enumerate(cal):
        active = [a for a in active if a["end"] > day]
        if day in sig_by_day and len(active) < MAX_OPEN:
            for r in sig_by_day[day].itertuples(index=False):
                if len(active) >= MAX_OPEN or any(a["ticker"] == r.ticker for a in active):
                    continue
                x = inst[r.ticker]
                budget = equity / MAX_OPEN
                if NO_LEVERAGE:
                    committed = 0.0
                    for a in active:  # capital tied up: current position value, at least the reserved budget
                        k = np.searchsorted(a["pos"], di - 1, side="right") - 1
                        committed += max(a["notional"][k] if k >= 0 else 0.0, a["budget"])
                    budget = min(budget, max(0.0, equity - committed))
                if budget <= 0:
                    continue
                res = simulate_campaign(x, r.e, tp_days=tp_days, tp_level=tp_level, **kw)
                dts = x["idx"][r.e:r.e + len(res["pnl"])]
                pos = cal_pos.reindex(dts).to_numpy()
                inc = np.diff(np.concatenate([[0.0], res["pnl"]])) * budget
                pnl_day[pos] += inc
                expo_day[pos] += res["notional"] * budget
                end_date = x["idx"][res["end"]] if res["reason"] != "open" else pd.Timestamp.max
                active.append({"end": end_date, "ticker": r.ticker, "pos": pos,
                               "notional": res["notional"] * budget, "budget": budget})
                camps.append({"ticker": r.ticker, "name": x.get("name") or UNIVERSE[r.ticker][0], "entry_date": day,
                              "end_date": x["idx"][res["end"]], "reason": res["reason"], "ret_%": 100 * res["ret"],
                              "fills": res["fills"], "stops": res["stops"], "budget": budget,
                              "pnl_$": res["ret"] * budget})
        equity += pnl_day[di]
        eq[di] = equity
    res = pd.DataFrame({"equity": eq, "expo": expo_day / np.maximum(eq, 1e-9)}, index=cal)
    return res, pd.DataFrame(camps)


def stats(res, camps):
    e = res["equity"]
    r = e.pct_change().fillna(0.0)

    def cagr(s):
        y = (s.index[-1] - s.index[0]).days / 365.25
        return 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1)
    cl = camps[camps.reason != "open"]
    dd = e / e.cummax() - 1
    return {"campaigns": len(camps), "win%": 100 * float((cl["ret_%"] > 0).mean()),
            "avg_campaign_%": float(cl["ret_%"].mean()), "worst_campaign_%": float(cl["ret_%"].min()),
            "avg_fills": float(camps.fills.mean()), "avg_stops": float(camps.stops.mean()),
            "exit_time%": 100 * float((cl.reason == "time TP").mean()), "exit_level%": 100 * float((cl.reason == "level TP").mean()),
            "exit_macd%": 100 * float((cl.reason == "MACD < 0").mean()),
            "avg_days": float((pd.to_datetime(camps.end_date) - pd.to_datetime(camps.entry_date)).dt.days.mean()),
            "cagr_%": cagr(e), "cagr_IS_%": cagr(e[e.index < SPLIT_DATE]), "cagr_OOS_%": cagr(e[e.index >= SPLIT_DATE]),
            "max_dd_%": 100 * float(dd.min()), "sharpe": float(r.mean() / r.std() * np.sqrt(252)),
            "vol_%": 100 * float(r.std() * np.sqrt(252)), "avg_invested_%": 100 * float(res["expo"].mean()),
            "final_equity_$": float(e.iloc[-1])}


def main():
    os.makedirs(OUT, exist_ok=True)
    inst = build()
    sig = signals(inst)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
    cal = cal[cal >= START]
    rows, keep = [], {}
    jobs = [(m, kw, td, tl) for (m, kw), td, tl in itertools.product(MODES.items(), TP_DAYS, TP_LEVELS)]
    jobs += [(m, kw, 365, None) for m, kw in EXTRA.items()]
    for m, kw, td, tl in jobs:
        res, camps = run(inst, sig, cal, kw, td, tl)
        st = stats(res, camps)
        tp_t = f"{td}d" if td else "none"
        tp_l = f"+{int(tl * 100)}%" if tl else "none"
        rows.append({"mode": m, "tp_time": tp_t, "tp_level": tp_l, **st})
        print(f"{m:22s} time {tp_t:5s} level {tp_l:5s} | CAGR {st['cagr_%']:5.2f} (IS {st['cagr_IS_%']:5.2f} / OOS {st['cagr_OOS_%']:5.2f}) "
              f"DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:4.0f}% "
              f"camp {st['campaigns']} win {st['win%']:.0f}% avg {st['avg_campaign_%']:.1f}% stops {st['avg_stops']:.1f}", flush=True)
        keep[(m, tp_t, tp_l)] = (res, camps)
    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    # save the reference runs (1 year, no level) of each main mode + best Sharpe per mode
    summary = {"rules": __doc__, "data_cutoff": DATA_CUTOFF, "runs": {}}
    for m in list(MODES) + list(EXTRA):
        g = grid[grid["mode"] == m]
        best = g.sort_values("sharpe", ascending=False).iloc[0]
        for tag, (tt, tl) in {"ref": ("365d", "none"), "best": (best.tp_time, best.tp_level)}.items():
            if (m, tt, tl) not in keep:
                continue
            res, camps = keep[(m, tt, tl)]
            key = f"{m}__{tag}"
            res.to_csv(os.path.join(OUT, f"equity_{key}.csv"))
            camps.to_csv(os.path.join(OUT, f"campaigns_{key}.csv"), index=False)
            summary["runs"][key] = {"mode": m, "tp_time": tt, "tp_level": tl,
                                    "stats": g[(g.tp_time == tt) & (g.tp_level == tl)].iloc[0].to_dict(),
                                    "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                      for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                    "live": camps[camps.reason == "open"].astype(str).to_dict("records")}
    summary["variants"] = rows
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
