"""DeMark 9 in an uptrend: weekly MACD filter, MACD-below-zero stop, 1-year take-profit, max 3 assets.

  signal      : TD buy setup 9 (weekly 9s, and daily 9s as a second book)
  filter      : weekly MACD line (EMA12-EMA26 of weekly closes) > 0 AND its signal line
                (EMA9 of MACD) > 0, read at the last COMPLETED week as of the signal close
  entry       : next daily open
  stop-loss   : first weekly close after entry with the MACD line < 0 -> exit next daily open
  take-profit : 1 year in the position -> exit at the first open on/after entry + 365 days
  portfolio   : at most 3 positions (3 different assets) at once, first come first served,
                same-day ties -> deepest sell-off first; each new position gets 1/3 of current
                equity (compounding, no leverage); 3 bps per side

Usage:  python scripts/macd_study.py   -> results/macd/
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

OUT = os.path.join(ROOT, "results", "macd")
DATA_CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")
CAPITAL = 100_000.0
COST = 3 / 1e4
START = pd.Timestamp("1990-01-01")


def weekly_macd(close: pd.Series):
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    sig = macd.ewm(span=9, adjust=False).mean()
    return macd, sig


def build(tf: str):
    """Per instrument: daily arrays + weekly MACD aligned to the daily calendar + signals."""
    prep = prepare(tf, drop_after=DATA_CUTOFF)
    inst = {}
    for t, x in prep.items():
        d = load_daily(t, drop_after=DATA_CUTOFF)
        w = to_weekly(d)
        macd, sig = weekly_macd(w["Close"])
        # value known at each daily close = last completed week (week's last day <= that day)
        m_d = macd.reindex(d.index, method="ffill")
        s_d = sig.reindex(d.index, method="ffill")
        # completed weeks only: a week's MACD is known from its last day onwards (ffill above does this
        # because the weekly index IS the week's last trading day). Mark weekly-close days for the stop.
        is_wk_close = pd.Series(d.index.isin(w.index), index=d.index)
        inst[t] = {"dates": d.index, "O": d["Open"].to_numpy(), "C": d["Close"].to_numpy(),
                   "macd": m_d.to_numpy(), "sig": s_d.to_numpy(), "wk_close": is_wk_close.to_numpy(),
                   "signals": x["signals"]}
    return inst


def trade_exit(x, e, stop_mode, hold_days):
    """Exit index (daily) and reason for a long opened at the open of day e."""
    dates, n = x["dates"], len(x["C"])
    t_end = dates[e] + pd.Timedelta(days=hold_days)
    for i in range(e, n):
        if dates[i] >= t_end and i > e:
            return i, "1 year"
        if stop_mode != "none" and x["wk_close"][i]:
            v = x["macd"][i] if stop_mode == "macd" else x["sig"][i]
            if v < 0 and i + 1 < n:
                return i + 1, "MACD < 0"
    return n - 1, "open"


def candidates(inst, use_filter=True, stop_mode="macd", hold_days=365, rng=None, placebo=False):
    rows = []
    for t, x in inst.items():
        sig = x["signals"]
        if placebo:  # random days that pass the same filter, as many as the real filtered 9s
            ok = (x["macd"] > 0) & (x["sig"] > 0)
            n_real = int(sum(ok[int(s)] for s in sig["s0"])) if len(sig) else 0
            pool = np.flatnonzero(ok[:-2])
            if n_real == 0 or len(pool) == 0:
                continue
            s0s = np.sort(rng.choice(pool, size=min(n_real, len(pool)), replace=False))
            dd = np.zeros(len(s0s))
        else:
            s0s, dd = sig["s0"].to_numpy(), sig["drawdown"].to_numpy()
        for s0, ddv in zip(s0s, dd):
            s0 = int(s0)
            e = s0 + 1
            if e >= len(x["C"]):
                continue
            if use_filter and not (x["macd"][s0] > 0 and x["sig"][s0] > 0):
                continue
            xi, why = trade_exit(x, e, stop_mode, hold_days)
            rows.append({"ticker": t, "sig_date": x["dates"][s0], "entry_i": e, "exit_i": xi,
                         "entry_date": x["dates"][e], "exit_date": x["dates"][xi], "reason": why,
                         "entry_px": x["O"][e], "exit_px": x["O"][xi] if why != "open" else x["C"][xi],
                         "drawdown": ddv})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["entry_date", "drawdown", "ticker"]).reset_index(drop=True)


def select(cand, max_open=3):
    keep, active = [], []
    for idx, r in cand.iterrows():
        active = [(e, t) for e, t in active if e > r.entry_date]
        if len(active) >= max_open or any(t == r.ticker for _, t in active):
            continue
        keep.append(idx)
        active.append((r.exit_date, r.ticker))
    return cand.loc[keep].reset_index(drop=True)


def simulate(inst, trades, cal, max_open=3):
    """Daily portfolio with compounding: each entry gets equity/max_open notional."""
    closes = {t: pd.Series(x["C"], index=x["dates"]).reindex(cal).ffill() for t, x in inst.items()}
    by_entry = {}
    for k, r in trades.iterrows():
        by_entry.setdefault(r.entry_date, []).append(k)
    eq = CAPITAL
    open_pos = {}  # k -> dict(qty, last_px)
    out_eq, out_expo, pnl_tr = [], [], {}
    for day in cal:
        day_pnl = 0.0
        # exits at today's open
        for k in [k for k, p in open_pos.items() if trades.at[k, "exit_date"] == day and trades.at[k, "reason"] != "open"]:
            p = open_pos.pop(k)
            px = trades.at[k, "exit_px"]
            g = p["qty"] * (px - p["last"]) - p["qty"] * px * COST
            day_pnl += g
            pnl_tr[k] = pnl_tr.get(k, 0.0) + g
        # entries at today's open (sized on yesterday's equity)
        for k in by_entry.get(day, []):
            px = trades.at[k, "entry_px"]
            qty = (eq / max_open) / px
            open_pos[k] = {"qty": qty, "last": px}
            g = -qty * px * COST
            day_pnl += g
            pnl_tr[k] = pnl_tr.get(k, 0.0) + g
        # mark to close
        expo = 0.0
        for k, p in open_pos.items():
            c = closes[trades.at[k, "ticker"]].loc[day]
            g = p["qty"] * (c - p["last"])
            p["last"] = c
            day_pnl += g
            pnl_tr[k] = pnl_tr.get(k, 0.0) + g
            expo += p["qty"] * c
        eq += day_pnl
        out_eq.append(eq)
        out_expo.append(expo / eq if eq > 0 else 0.0)
    res = pd.DataFrame({"equity": out_eq, "expo": out_expo}, index=cal)
    trades = trades.copy()
    trades["pnl_$"] = trades.index.map(lambda k: pnl_tr.get(k, 0.0))
    trades["ret_%"] = 100 * (trades.exit_px * (1 - COST) / (trades.entry_px * (1 + COST)) - 1)
    return res, trades


def stats(res, trades):
    e = res["equity"]
    r = e.pct_change().fillna(0.0)
    yrs = (e.index[-1] - e.index[0]).days / 365.25

    def cagr(s):
        y = (s.index[-1] - s.index[0]).days / 365.25
        return 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1) if y > 0 else np.nan
    closed = trades[trades.reason != "open"]
    return {
        "trades": len(trades), "win%": 100 * float((closed["ret_%"] > 0).mean()) if len(closed) else np.nan,
        "avg_trade_%": float(closed["ret_%"].mean()), "median_trade_%": float(closed["ret_%"].median()),
        "worst_trade_%": float(closed["ret_%"].min()), "best_trade_%": float(closed["ret_%"].max()),
        "exit_1y%": 100 * float((trades.reason == "1 year").mean()), "exit_macd%": 100 * float((trades.reason == "MACD < 0").mean()),
        "avg_ret_1y_exit_%": float(trades.loc[trades.reason == "1 year", "ret_%"].mean()),
        "avg_ret_macd_exit_%": float(trades.loc[trades.reason == "MACD < 0", "ret_%"].mean()),
        "avg_days": float((trades.exit_date - trades.entry_date).dt.days.mean()),
        "final_equity_$": float(e.iloc[-1]), "cagr_%": cagr(e),
        "cagr_IS_%": cagr(e[e.index < SPLIT_DATE]), "cagr_OOS_%": cagr(e[e.index >= SPLIT_DATE]),
        "max_dd_%": 100 * float((e / e.cummax() - 1).min()),
        "dd_trough": str((e / e.cummax() - 1).idxmin().date()),
        "sharpe": float(r.mean() / r.std() * np.sqrt(252)), "vol_%": 100 * float(r.std() * np.sqrt(252)),
        "avg_invested_%": 100 * float(res["expo"].mean()), "years": yrs,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    summary = {"rules": __doc__, "data_cutoff": DATA_CUTOFF, "runs": {}, "variants": []}
    rows = []
    for tf in ["W", "D"]:
        inst = build(tf)
        cal = pd.DatetimeIndex(sorted(set().union(*[set(x["dates"]) for x in inst.values()])))
        cal = cal[cal >= START]
        for use_filter, stop_mode, hold, max_open in itertools.chain(
                [(True, "macd", 365, 3)],                                   # the asked design
                [(False, "macd", 365, 3), (True, "none", 365, 3), (True, "signal", 365, 3),
                 (False, "none", 365, 3), (True, "macd", 182, 3), (True, "macd", 730, 3),
                 (True, "macd", 365, 1), (True, "macd", 365, 5)]):
            cand = candidates(inst, use_filter, stop_mode, hold)
            trades = select(cand, max_open)
            res, trades = simulate(inst, trades, cal, max_open)
            st = stats(res, trades)
            label = (f"{'MACD filter' if use_filter else 'no filter'}, stop: "
                     f"{ {'macd': 'MACD<0', 'signal': 'signal<0', 'none': 'none'}[stop_mode] }, "
                     f"hold {hold}d, max {max_open}")
            rows.append({"tf": tf, "label": label, "filter": use_filter, "stop": stop_mode, "hold_days": hold,
                         "max_open": max_open, **st})
            print(tf, label, {k: (round(v, 2) if isinstance(v, float) else v) for k, v in st.items()}, flush=True)
            if (use_filter, stop_mode, hold, max_open) == (True, "macd", 365, 3):
                trades.assign(name=trades.ticker.map(lambda t: UNIVERSE[t][0])).to_csv(
                    os.path.join(OUT, f"trades_{tf}.csv"), index=False)
                res.to_csv(os.path.join(OUT, f"equity_{tf}.csv"))
                # placebo: random filtered days instead of 9s
                rng = np.random.default_rng(5)
                plc = []
                for _ in range(30):
                    pc = select(candidates(inst, True, "macd", 365, rng=rng, placebo=True), 3)
                    pr, pt = simulate(inst, pc, cal, 3)
                    ps = stats(pr, pt)
                    plc.append({k: ps[k] for k in ["cagr_%", "sharpe", "max_dd_%", "avg_trade_%"]})
                plc = pd.DataFrame(plc)
                live = trades[trades.reason == "open"].copy()
                live["last_close"] = [inst[t]["C"][-1] for t in live.ticker]
                live["unreal_%"] = 100 * (live.last_close / live.entry_px - 1)
                live["exit_by"] = (live.entry_date + pd.Timedelta(days=365)).dt.date.astype(str)
                live["name"] = live.ticker.map(lambda t: UNIVERSE[t][0])
                # current filter state for every asset
                now = [{"ticker": t, "name": UNIVERSE[t][0], "macd": float(x["macd"][-1]), "signal": float(x["sig"][-1]),
                        "filter_on": bool(x["macd"][-1] > 0 and x["sig"][-1] > 0)} for t, x in inst.items()]
                pending = cand[(cand.entry_date > cal[-1] - pd.Timedelta(days=21))]
                summary["runs"][tf] = {
                    "stats": st,
                    "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                      for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                    "placebo": {c: {"mean": float(plc[c].mean()), "p05": float(plc[c].quantile(.05)),
                                    "p95": float(plc[c].quantile(.95))} for c in plc.columns},
                    "by_year": res["equity"].resample("YE").last().pct_change().mul(100).round(2).dropna()
                    .rename(lambda d: d.year).to_dict(),
                    "live": live[["name", "sig_date", "entry_date", "entry_px", "last_close", "unreal_%", "exit_by"]]
                    .astype(str).to_dict("records"),
                    "recent_candidates": pending.assign(name=pending.ticker.map(lambda t: UNIVERSE[t][0]))[
                        ["name", "sig_date", "entry_date", "reason"]].astype(str).to_dict("records"),
                    "filter_now": now,
                }
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
                                   "sharpe": float(rs.mean() / rs.std() * np.sqrt(252))}
    summary["variants"] = rows
    pd.DataFrame(rows).to_csv(os.path.join(OUT, "variants.csv"), index=False)
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("B&H EW", {k: v for k, v in summary["buy_and_hold_EW"].items() if k != "equity_weekly"}, "SPX", summary["buy_and_hold_SPX"])


if __name__ == "__main__":
    main()
