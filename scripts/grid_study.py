"""Averaging-down grid after a DeMark 9, no stop-loss, exit at a 30 % retracement, max 3 assets.

  old high   = highest high of the lookback before the 9 (weekly 52 w / daily 63 d; 26 w / 252 d tested)
  sell-off low = lowest low between that high and the 9
  target T   = low + RETR * (old high - low)                     RETR = 30 %  (50 % tested)
  grid       = every STEP below T                                 STEP = 1 %   (2 % tested)
  start      = j0 units, j0 = number of steps from the entry (next open) up to T
  then       = +1 unit per step down, -1 unit per step up, position 0 at T; no stop-loss
  unit       = 1 % of starting capital ($1,000 of $100k), fixed $ (no compounding)
  portfolio  = at most 3 campaigns (3 different assets) open at once; first come first served,
               same-day ties -> deepest sell-off first; a new 9 on an asset already in a
               campaign is ignored.

Usage:  python scripts/grid_study.py   -> results/grid/
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

from strategy.backtest import SPLIT_DATE, buy_and_hold, prepare  # noqa: E402
from strategy.grid import simulate_grid  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "grid")
DATA_CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")
CAPITAL, UNIT = 100_000.0, 1_000.0
START = pd.Timestamp("1990-01-01")
LOOKBACK = {"W": {"long": 52, "short": 26}, "D": {"long": 252, "short": 63}}
LB_LABEL = {"W": {"long": "52-week high", "short": "26-week high"}, "D": {"long": "252-day high", "short": "63-day high"}}
PRIMARY = {"W": dict(lb="long", retr=0.30, step=0.01), "D": dict(lb="short", retr=0.30, step=0.01)}
MAX_OPEN = 3


def candidates(prep, tf, lb, retr):
    rows = []
    n_lb = LOOKBACK[tf][lb]
    for t, x in prep.items():
        b = x["bars"]
        Hb, Lb = b["High"].to_numpy(), b["Low"].to_numpy()
        for r in x["signals"].itertuples(index=False):
            i = int(r.pos)
            w0 = max(0, i - n_lb + 1)
            k = w0 + int(np.argmax(Hb[w0:i + 1]))
            old_high, low = Hb[k], Lb[k:i + 1].min()
            if old_high <= low:
                continue
            e = int(r.s0) + 1
            if e >= len(x["C"]):
                continue
            rows.append({"ticker": t, "sig_date": r.date, "s0": int(r.s0), "entry_date": x["dates"][e],
                         "old_high": old_high, "low": low, "target": low + retr * (old_high - low),
                         "drawdown": r.drawdown})
    return pd.DataFrame(rows).sort_values(["entry_date", "drawdown", "ticker"]).reset_index(drop=True)


def run(prep, tf, lb, retr, step, max_open=MAX_OPEN):
    cand = candidates(prep, tf, lb, retr)
    active = []  # (end_date, ticker)
    camps = []
    for c in cand.itertuples(index=False):
        active = [(e, t) for e, t in active if e >= c.entry_date]
        if len(active) >= max_open or any(t == c.ticker for _, t in active):
            continue
        x = prep[c.ticker]
        res = simulate_grid(x["O"], x["H"], x["L"], x["C"], c.s0, c.target, step, UNIT)
        if res["status"] not in ("target", "open"):
            continue
        end_date = x["dates"][res["end"]]
        active.append((end_date if res["status"] == "target" else pd.Timestamp.max, c.ticker))
        dates = x["dates"][res["start"]:res["start"] + len(res["values"])]
        camps.append({**c._asdict(), "name": UNIVERSE[c.ticker][0], "status": res["status"], "end_date": end_date,
                      "days": (end_date - c.entry_date).days, "entry": res["entry"], "j0": res["j0"],
                      "max_units": res["max_units"], "pnl": res["pnl"], "worst_open": res["worst_open"],
                      "_dates": dates, "_values": res["values"], "_notional": res["qty"] * np.asarray(
                          x["C"][res["start"]:res["start"] + len(res["values"])])})
    return camps


def portfolio(camps, cal):
    pnl = pd.Series(0.0, index=cal)
    expo = pd.Series(0.0, index=cal)
    for c in camps:
        v = pd.Series(c["_values"], index=c["_dates"])
        d = v.diff().fillna(v.iloc[0])
        pnl = pnl.add(d.reindex(cal).fillna(0.0), fill_value=0.0)
        # carry the value forward on dates this instrument doesn't trade (keeps exposure series honest)
        expo = expo.add(pd.Series(c["_notional"], index=c["_dates"]).reindex(cal).ffill()
                        .where(lambda s: s.index <= c["_dates"][-1]).fillna(0.0), fill_value=0.0)
    eq = CAPITAL + pnl.cumsum()
    return pd.DataFrame({"pnl": pnl, "equity": eq, "gross_expo_x": expo / CAPITAL})


def stats(eq: pd.DataFrame, camps):
    e = eq["equity"]
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    dd = e - e.cummax()
    r = eq["pnl"] / CAPITAL
    c = pd.DataFrame([{k: v for k, v in x.items() if not k.startswith("_")} for x in camps])
    done = c[c.status == "target"]
    return {
        "campaigns": len(c), "completed%": 100 * len(done) / max(1, len(c)), "open_at_end": int((c.status == "open").sum()),
        "win%_completed": 100 * float((done.pnl > 0).mean()) if len(done) else np.nan,
        "avg_days": float(c.days.clip(lower=0).mean()), "median_days": float(done.days.median()) if len(done) else np.nan,
        "max_days": float(c.days.max()), "avg_start_units": float(c.j0.mean()), "max_units": int(c.max_units.max()),
        "total_pnl_$": float(e.iloc[-1] - CAPITAL), "ret_per_yr_%": 100 * float((e.iloc[-1] - CAPITAL) / yrs / CAPITAL),
        "max_dd_%": 100 * float(dd.min() / CAPITAL), "dd_trough": str(dd.idxmin().date()),
        "dd_peak": str(e[:dd.idxmin()].idxmax().date()),
        "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan,
        "worst_campaign_$": float(c.pnl.min()), "worst_open_loss_$": float(c.worst_open.min()),
        "max_gross_expo_x": float(eq["gross_expo_x"].max()), "avg_gross_expo_x": float(eq["gross_expo_x"].mean()),
        "pnl_IS_$": float(eq.loc[eq.index < SPLIT_DATE, "pnl"].sum()), "pnl_OOS_$": float(eq.loc[eq.index >= SPLIT_DATE, "pnl"].sum()),
        "unit_for_25pct_dd_$": float(UNIT * 25 / max(1e-9, -100 * dd.min() / CAPITAL)),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = {"rules": __doc__, "data_cutoff": DATA_CUTOFF, "unit_$": UNIT, "capital_$": CAPITAL, "runs": {}}
    rows = []
    for tf in ["W", "D"]:
        prep = prepare(tf, drop_after=DATA_CUTOFF)
        cal = pd.DatetimeIndex(sorted(set().union(*[set(x["dates"]) for x in prep.values()])))
        cal = cal[cal >= START]
        for lb, retr, step in itertools.product(["long", "short"], [0.30, 0.50], [0.01, 0.02]):
            camps = run(prep, tf, lb, retr, step)
            eq = portfolio(camps, cal)
            st = stats(eq, camps)
            rows.append({"tf": tf, "old_high": LB_LABEL[tf][lb], "retracement": retr, "step": step, **st})
            prim = PRIMARY[tf]
            if (lb, retr, step) == (prim["lb"], prim["retr"], prim["step"]):
                c = pd.DataFrame([{k: v for k, v in x.items() if not k.startswith("_")} for x in camps])
                c.to_csv(os.path.join(OUT, f"campaigns_{tf}.csv"), index=False)
                eq.to_csv(os.path.join(OUT, f"equity_{tf}.csv"))
                live = c[c.status == "open"].copy()
                live["last_close"] = [prep[t]["C"][-1] for t in live.ticker]
                live["units_now"] = [int(round(x["_notional"][-1] / x["_values"][-1] * 0)) for x in camps if x["status"] == "open"] if len(live) else []
                summary["runs"][tf] = {
                    "old_high": LB_LABEL[tf][lb], "stats": st,
                    "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                      for d, v in eq["equity"].resample("W-FRI").last().dropna().items()],
                    "worst": c.nsmallest(5, "worst_open")[["name", "sig_date", "entry_date", "end_date", "status", "days",
                                                           "max_units", "worst_open", "pnl"]].astype(str).to_dict("records"),
                    "longest": c.nlargest(5, "days")[["name", "sig_date", "entry_date", "end_date", "status", "days",
                                                      "max_units", "pnl"]].astype(str).to_dict("records"),
                    "live": live.drop(columns=["units_now"]).astype(str).to_dict("records"),
                }
            print(tf, lb, retr, step, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in st.items()}, flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    bh = buy_and_hold(prepare("D", drop_after=DATA_CUTOFF))
    summary["buy_and_hold_sharpe"] = float(bh["ret"].mean() / bh["ret"].std() * np.sqrt(252))
    summary["variants"] = grid.to_dict("records")
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
