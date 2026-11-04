"""Weekly MACD as the ONLY signal (no DeMark): trend entries, MACD stop, 1-year take-profit, max 3 assets.

  MACD line   = EMA12 - EMA26 of weekly closes ("fast"), signal line = EMA9 of MACD ("slow")
  "on"        = both lines above 0 at a weekly close
  entry       : next daily open after the weekly close where the asset turns "on"
                (the start of a new up-phase); variants for what happens when no slot is free
  stop-loss   : first weekly close with the MACD line < 0 -> exit next daily open
  take-profit : 1 year in the position -> exit at the first open on/after entry + 365 days
  portfolio   : at most 3 positions (different assets), each 1/3 of current equity (compounding,
                no leverage), 3 bps per side

Entry variants
  fresh_only  : only on the week the asset turns on; if all 3 slots are busy the signal is lost
  queue       : any asset that is "on" and not yet traded in its current up-phase can take a free
                slot later; the most recent up-phase start goes first (one trade per up-phase)
  rebuy       : like queue, but after the 1-year exit the same up-phase may be bought again

Usage:  python scripts/macd_only_study.py   -> results/macd_only/
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
from strategy.data import load_daily, to_weekly  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "macd_only")
DATA_CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")
CAPITAL = 100_000.0
COST = 3 / 1e4
START = pd.Timestamp("1990-01-01")
WARMUP_WEEKS = 35


def build():
    inst = {}
    for t in UNIVERSE:
        d = load_daily(t, drop_after=DATA_CUTOFF)
        w = to_weekly(d)
        macd = w["Close"].ewm(span=12, adjust=False).mean() - w["Close"].ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        on_w = (macd > 0) & (sig > 0)
        on_w.iloc[:WARMUP_WEEKS] = False
        start_w = pd.Series(np.where(on_w & ~on_w.shift(1, fill_value=False), w.index, pd.NaT), index=w.index)
        start_w = start_w.where(on_w).ffill().where(on_w)  # phase start date while "on", NaT while off
        fresh_w = on_w & ~on_w.shift(1, fill_value=False)
        al = lambda s: s.reindex(d.index, method="ffill")  # noqa: E731  (known from the week's last day on)
        inst[t] = {
            "dates": d.index, "O": d["Open"].to_numpy(), "C": d["Close"].to_numpy(),
            "macd": al(macd).to_numpy(), "sig": al(sig).to_numpy(),
            "on": al(on_w).fillna(False).to_numpy(dtype=bool),
            "phase": al(start_w).to_numpy(),
            "wk_close": d.index.isin(w.index),
            "fresh_close": pd.Series(fresh_w.reindex(d.index).fillna(False).to_numpy(dtype=bool), index=d.index).to_numpy(),
            "pos": pd.Series(np.arange(len(d)), index=d.index),
        }
    return inst


def exit_for(x, e, stop, hold_days):
    dates, n = x["dates"], len(x["C"])
    t_end = dates[e] + pd.Timedelta(days=hold_days) if hold_days else None
    for i in range(e, n):
        if t_end is not None and i > e and dates[i] >= t_end:
            return i, "1 year" if hold_days == 365 else f"{hold_days}d"
        if stop != "none" and x["wk_close"][i]:
            v = x["macd"][i] if stop == "macd" else x["sig"][i]
            if v < 0 and i + 1 < n:
                return i + 1, "MACD < 0" if stop == "macd" else "signal < 0"
    return n - 1, "open"


def run(inst, cal, mode="fresh_only", stop="macd", hold_days=365, max_open=3):
    closes = {t: pd.Series(x["C"], index=x["dates"]).reindex(cal).ffill().to_numpy() for t, x in inst.items()}
    cal_pos = {d: k for k, d in enumerate(cal)}
    eq, open_pos, trades = CAPITAL, {}, []
    traded_phase = {t: set() for t in inst}
    out_eq, out_expo = [], []
    for k, day in enumerate(cal):
        pnl = 0.0
        # exits at the open
        for t in [t for t, p in open_pos.items() if p["exit_date"] == day]:
            p = open_pos.pop(t)
            x = inst[t]
            px = x["O"][p["exit_i"]]
            g = p["qty"] * (px - p["last"]) - p["qty"] * px * COST
            pnl += g
            p["pnl"] += g
            trades.append({**{kk: vv for kk, vv in p.items() if kk not in ("qty", "last")}, "exit_px": px})
        # entries at the open
        if len(open_pos) < max_open:
            cands = []
            for t, x in inst.items():
                if t in open_pos:
                    continue
                i = x["pos"].get(day)
                if i is None or i < 1:
                    continue
                j = i - 1  # state known at the previous close
                if not x["on"][j]:
                    continue
                ph = x["phase"][j]
                if mode == "fresh_only":
                    if not x["fresh_close"][j]:
                        continue
                elif mode == "queue":
                    if ph in traded_phase[t]:
                        continue
                cands.append((pd.Timestamp(ph), x["macd"][j] / x["C"][j], t, i))
            cands.sort(key=lambda c: (-c[0].value, -c[1], c[2]))  # freshest phase, then strongest MACD
            for ph, _, t, i in cands[: max_open - len(open_pos)]:
                x = inst[t]
                xi, why = exit_for(x, i, stop, hold_days)
                px = x["O"][i]
                qty = (eq / max_open) / px
                g = -qty * px * COST
                pnl += g
                traded_phase[t].add(np.datetime64(ph))
                open_pos[t] = {"ticker": t, "name": UNIVERSE[t][0], "phase_start": ph, "entry_date": day, "entry_px": px,
                               "entry_i": i, "exit_i": xi, "exit_date": x["dates"][xi] if why != "open" else pd.Timestamp.max,
                               "reason": why, "qty": qty, "last": px, "pnl": g, "equity_at_entry": eq}
        # mark to close
        expo = 0.0
        for t, p in open_pos.items():
            c = closes[t][k]
            g = p["qty"] * (c - p["last"])
            p["last"] = c
            p["pnl"] += g
            pnl += g
            expo += p["qty"] * c
        eq += pnl
        out_eq.append(eq)
        out_expo.append(expo / eq if eq > 0 else 0.0)
    for t, p in open_pos.items():  # still open at the end
        trades.append({**{kk: vv for kk, vv in p.items() if kk not in ("qty", "last")}, "exit_px": inst[t]["C"][-1],
                       "exit_date": cal[-1], "reason": "open"})
    tr = pd.DataFrame(trades)
    tr["ret_%"] = 100 * (tr.exit_px * (1 - COST) / (tr.entry_px * (1 + COST)) - 1)
    tr["days"] = (pd.to_datetime(tr.exit_date) - pd.to_datetime(tr.entry_date)).dt.days
    return pd.DataFrame({"equity": out_eq, "expo": out_expo}, index=cal), tr


def stats(res, tr):
    e = res["equity"]
    r = e.pct_change().fillna(0.0)

    def cagr(s):
        y = (s.index[-1] - s.index[0]).days / 365.25
        return 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1)
    cl = tr[tr.reason != "open"]
    dd = e / e.cummax() - 1
    return {
        "trades": len(tr), "trades_per_yr": len(tr) / ((e.index[-1] - e.index[0]).days / 365.25),
        "win%": 100 * float((cl["ret_%"] > 0).mean()), "avg_trade_%": float(cl["ret_%"].mean()),
        "median_trade_%": float(cl["ret_%"].median()), "worst_trade_%": float(cl["ret_%"].min()),
        "best_trade_%": float(cl["ret_%"].max()),
        "exit_time%": 100 * float(cl.reason.str.contains("year|d$").mean()),
        "avg_ret_time_exit_%": float(cl.loc[cl.reason.str.contains("year|d$"), "ret_%"].mean()),
        "avg_ret_stop_exit_%": float(cl.loc[cl.reason.str.contains("<"), "ret_%"].mean()),
        "avg_days": float(tr.days.mean()),
        "final_equity_$": float(e.iloc[-1]), "cagr_%": cagr(e), "cagr_IS_%": cagr(e[e.index < SPLIT_DATE]),
        "cagr_OOS_%": cagr(e[e.index >= SPLIT_DATE]), "max_dd_%": 100 * float(dd.min()),
        "dd_peak": str(e[:dd.idxmin()].idxmax().date()), "dd_trough": str(dd.idxmin().date()),
        "sharpe": float(r.mean() / r.std() * np.sqrt(252)), "vol_%": 100 * float(r.std() * np.sqrt(252)),
        "avg_invested_%": 100 * float(res["expo"].mean()),
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    inst = build()
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["dates"]) for x in inst.values()])))
    cal = cal[cal >= START]
    rows, summary = [], {"rules": __doc__, "data_cutoff": DATA_CUTOFF}
    variants = [("fresh_only", "macd", 365, 3)] + [
        ("queue", "macd", 365, 3), ("rebuy", "macd", 365, 3),
        ("fresh_only", "signal", 365, 3), ("queue", "signal", 365, 3),
        ("fresh_only", "macd", None, 3), ("queue", "macd", None, 3),
        ("fresh_only", "macd", 730, 3), ("fresh_only", "none", 365, 3),
        ("fresh_only", "macd", 365, 1), ("fresh_only", "macd", 365, 5),
        ("queue", "macd", 365, 5), ("queue", "macd", 365, 27)]
    for mode, stop, hold, mo in variants:
        res, tr = run(inst, cal, mode, stop, hold, mo)
        st = stats(res, tr)
        lab = f"{mode}, stop {stop}, {'hold ' + str(hold) + 'd' if hold else 'no time exit'}, max {mo}"
        rows.append({"mode": mode, "stop": stop, "hold_days": hold or 0, "max_open": mo, "label": lab, **st})
        print(lab, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in st.items()}, flush=True)
        if (mode, stop, hold, mo) in [("fresh_only", "macd", 365, 3), ("queue", "macd", 365, 3)]:
            key = mode
            tr.to_csv(os.path.join(OUT, f"trades_{key}.csv"), index=False)
            res.to_csv(os.path.join(OUT, f"equity_{key}.csv"))
            summary[key] = {
                "stats": st,
                "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                  for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                "by_year": res["equity"].resample("YE").last().pct_change().mul(100).round(2).dropna()
                .rename(lambda d: d.year).to_dict(),
                "live": tr[tr.reason == "open"].astype(str).to_dict("records"),
                "worst_trades": tr.nsmallest(5, "ret_%")[["name", "entry_date", "exit_date", "reason", "ret_%"]]
                .astype(str).to_dict("records"),
                "by_asset": tr.groupby("name")["pnl"].sum().sort_values().round(0).to_dict(),
            }
    # current state of every asset
    now = []
    for t, x in inst.items():
        now.append({"ticker": t, "name": UNIVERSE[t][0], "macd": float(x["macd"][-1]), "signal": float(x["sig"][-1]),
                    "macd_pct_of_price": 100 * float(x["macd"][-1] / x["C"][-1]), "on": bool(x["on"][-1]),
                    "phase_start": str(pd.Timestamp(x["phase"][-1]).date()) if x["on"][-1] else ""})
    summary["state_now"] = now
    bh = buy_and_hold(prepare("D", drop_after=DATA_CUTOFF))
    be = bh["equity"]
    y = (be.index[-1] - be.index[0]).days / 365.25
    summary["buy_and_hold_EW"] = {"cagr_%": 100 * (be.iloc[-1] ** (1 / y) - 1), "max_dd_%": 100 * float((be / be.cummax() - 1).min()),
                                  "sharpe": float(bh["ret"].mean() / bh["ret"].std() * np.sqrt(252)),
                                  "equity_weekly": [[d.date().isoformat(), round(float(v) * CAPITAL, 2)]
                                                    for d, v in be.resample("W-FRI").last().dropna().items()]}
    spx = load_daily("^GSPC", drop_after=DATA_CUTOFF)["Close"]
    spx = spx[spx.index >= START]
    ys = (spx.index[-1] - spx.index[0]).days / 365.25
    rs = spx.pct_change().dropna()
    summary["buy_and_hold_SPX"] = {"cagr_%": 100 * ((spx.iloc[-1] / spx.iloc[0]) ** (1 / ys) - 1),
                                   "max_dd_%": 100 * float((spx / spx.cummax() - 1).min()),
                                   "sharpe": float(rs.mean() / rs.std() * np.sqrt(252)),
                                   "equity_weekly": [[d.date().isoformat(), round(float(v) / spx.iloc[0] * CAPITAL, 2)]
                                                     for d, v in spx.resample("W-FRI").last().dropna().items()]}
    summary["variants"] = rows
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "variants.csv"), index=False)
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("B&H EW", {k: round(v, 2) for k, v in summary["buy_and_hold_EW"].items() if k != "equity_weekly"},
          "SPX", {k: round(v, 2) for k, v in summary["buy_and_hold_SPX"].items() if k != "equity_weekly"})


if __name__ == "__main__":
    main()
