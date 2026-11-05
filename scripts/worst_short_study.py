"""Short leg on the WORST weekly-MACD profile among the 27 instruments (16 DM indices + 11 US sectors).

Each week (at the weekly close) every asset gets a MACD score; the lowest = worst profile:
  depth      MACD / price                               (12w EMA below 26w EMA, as % of price)
  depth_vol  MACD / (price * 26-week volatility)        (depth in units of the asset's own weekly moves)
  accel      (MACD - signal) / price                    (histogram: is the downtrend still speeding up?)
  composite  mean of the cross-sectional ranks of depth_vol and accel_vol (deep AND still worsening)
Short leg (weekly rotation, executed at the next daily open):
  * candidates: MACD < 0 and signal < 0 (a downtrend, as before)
  * hold the K = 3 worst candidates; a short is covered when MACD turns > 0 (stop), when it drops
    out of the worst M = 6, or after 1 year
  * each new short gets 1/K of equity (compounding, no leverage: total short notional <= equity),
    3 bps per side; price indices / ETFs, no borrow or futures carry modelled
Long leg for combinations: the mirror image (best profile, MACD > 0 and signal > 0), and the
earlier long strategy (new MACD up-phase, MACD stop, 1-year exit, max 3).

Usage:  python scripts/worst_short_study.py   -> results/worst_short/
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

from strategy.backtest import SPLIT_DATE  # noqa: E402
from strategy.data import load_daily, to_weekly  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "worst_short")
CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")
START = pd.Timestamp("1990-01-01")
CAPITAL = 100_000.0
COST = 3e-4
SCORES = ["depth", "depth_vol", "accel", "composite"]


def build():
    daily, weekly = {}, {}
    for t in UNIVERSE:
        d = load_daily(t, drop_after=CUTOFF)
        w = to_weekly(d)
        c = w["Close"]
        macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        vol = np.log(c).diff().rolling(26, min_periods=13).std()
        f = pd.DataFrame({"macd": macd, "sig": sig, "close": c,
                          "depth": macd / c, "depth_vol": macd / (c * vol),
                          "accel": (macd - sig) / c, "accel_vol": (macd - sig) / (c * vol)})
        f.iloc[:35] = np.nan
        f["period"] = f.index.to_period("W-FRI")
        f["wk_date"] = f.index
        weekly[t] = f.set_index("period")
        daily[t] = d
    periods = sorted(set().union(*[set(f.index) for f in weekly.values()]))
    panel = {k: pd.DataFrame({t: f[k] for t, f in weekly.items()}).reindex(periods).ffill(limit=2)
             for k in ["macd", "sig", "depth", "depth_vol", "accel", "accel_vol"]}
    wkdate = pd.DataFrame({t: f["wk_date"] for t, f in weekly.items()}).reindex(periods)
    panel["composite"] = (panel["depth_vol"].rank(axis=1, pct=True) + panel["accel_vol"].rank(axis=1, pct=True)) / 2
    return daily, panel, wkdate


def rotation(daily, panel, wkdate, score, side="short", K=3, M=6, max_days=365, cond=True, contrarian=False, allow=None):
    """Weekly rotation into the K worst (side=short) or best (side=long) MACD profiles.
    contrarian=True with side='long': BUY the K worst profiles (downtrends), sell when MACD turns > 0."""
    sgn = -1 if side == "short" else 1
    worst_first = side == "short" or contrarian
    s = panel[score] * (-1 if worst_first else 1)  # higher = more attractive for this side
    down = (panel["macd"] < 0) & (panel["sig"] < 0)
    ok = down if worst_first else (panel["macd"] > 0) & (panel["sig"] > 0)
    stop = panel["macd"] > 0 if worst_first else panel["macd"] < 0
    cal = pd.DatetimeIndex(sorted(set().union(*[set(d.index) for d in daily.values()])))
    cal = cal[cal >= START]
    # orders: per decision week, list of (ticker, 'in'/'out')
    held = {}  # ticker -> entry period date
    orders = []  # (decision_date, ticker, action)
    for p in panel["macd"].index:
        dd = wkdate.loc[p].max()
        if pd.isna(dd) or dd < START - pd.Timedelta(days=7):
            continue
        sc = s.loc[p]
        valid = sc.notna()
        if allow is not None and not bool(allow.get(p, False)):  # regime filter: flat while not allowed
            for t in list(held):
                orders.append((dd, t, "out"))
                del held[t]
            continue
        rank = sc.where(valid).rank(ascending=False)
        for t in list(held):
            if stop.loc[p, t] or rank.get(t, np.inf) > M or (dd - held[t]).days >= max_days or not valid[t]:
                orders.append((dd, t, "out"))
                del held[t]
        cands = sc[valid & (ok.loc[p] if cond else True)].sort_values(ascending=False)
        for t in cands.index:
            if len(held) >= K:
                break
            if t not in held and rank[t] <= K:
                held[t] = dd
                orders.append((dd, t, "in"))
    # execution at each asset's next open after the decision date, daily mark-to-market
    ex = {}
    for dd, t, a in orders:
        idx = daily[t].index
        k = idx.searchsorted(dd, side="right")
        if k < len(idx):
            ex.setdefault(idx[k], []).append((t, a))
    closes = {t: d["Close"].reindex(cal).ffill() for t, d in daily.items()}
    opens = {t: d["Open"] for t, d in daily.items()}
    eq, pos = CAPITAL, {}  # t -> [qty (signed), last_px, entry_date, entry_px]
    out_eq, out_expo, trades = [], [], []
    for day in cal:
        pnl = 0.0
        for t, a in sorted(ex.get(day, []), key=lambda z: z[1] != "out"):  # exits first
            px = opens[t].get(day, np.nan)
            if np.isnan(px):
                continue
            if a == "out" and t in pos:
                q, last, ed, ep = pos.pop(t)
                g = q * (px - last) - abs(q) * px * COST
                pnl += g
                trades.append({"ticker": t, "name": UNIVERSE[t][0], "entry_date": ed, "exit_date": day,
                               "ret_%": 100 * sgn * (px / ep - 1) - 0.06})
            elif a == "in" and t not in pos:
                used = sum(abs(q) * closes[u].loc[day] for u, (q, *_rest) in pos.items())
                budget = min(eq / K, max(0.0, eq - used))
                if budget <= 0:
                    continue
                q = sgn * budget / px
                pos[t] = [q, px, day, px]
                pnl -= abs(q) * px * COST
        expo = 0.0
        for t, p in pos.items():
            c = closes[t].loc[day]
            pnl += p[0] * (c - p[1])
            p[1] = c
            expo += abs(p[0]) * c
        eq += pnl
        out_eq.append(eq)
        out_expo.append(expo / eq if eq > 0 else 0.0)
    for t, (q, last, ed, ep) in pos.items():
        trades.append({"ticker": t, "name": UNIVERSE[t][0], "entry_date": ed, "exit_date": None,
                       "ret_%": 100 * sgn * (closes[t].iloc[-1] / ep - 1)})
    return pd.DataFrame({"equity": out_eq, "expo": out_expo}, index=cal), pd.DataFrame(trades)


def stats(e, tr=None, expo=None):
    r = e.pct_change().fillna(0.0)

    def cagr(s):
        y = (s.index[-1] - s.index[0]).days / 365.25
        return 100 * ((s.iloc[-1] / s.iloc[0]) ** (1 / y) - 1)
    out = {"cagr_%": cagr(e), "cagr_IS_%": cagr(e[e.index < SPLIT_DATE]), "cagr_OOS_%": cagr(e[e.index >= SPLIT_DATE]),
           "max_dd_%": 100 * float((e / e.cummax() - 1).min()), "sharpe": float(r.mean() / r.std() * np.sqrt(252)),
           "sharpe_IS": float(r[r.index < SPLIT_DATE].mean() / r[r.index < SPLIT_DATE].std() * np.sqrt(252)),
           "sharpe_OOS": float(r[r.index >= SPLIT_DATE].mean() / r[r.index >= SPLIT_DATE].std() * np.sqrt(252))}
    if tr is not None and len(tr):
        out.update({"trades": len(tr), "win%": 100 * float((tr["ret_%"] > 0).mean()), "avg_trade_%": float(tr["ret_%"].mean())})
    if expo is not None:
        out["avg_invested_%"] = 100 * float(expo.mean())
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    daily, panel, wkdate = build()
    rows, keep = [], {}

    def go(side, score, K=3, M=6, max_days=365, cond=True, tag=""):
        res, tr = rotation(daily, panel, wkdate, score, side, K, M, max_days, cond)
        st = stats(res["equity"], tr, res["expo"])
        lab = f"{side} {score} K{K} M{M} {'1y' if max_days < 9999 else 'no-time'}{tag}"
        rows.append({"side": side, "score": score, "K": K, "M": M, "max_days": max_days, "cond": cond, "label": lab, **st})
        keep[lab] = (res, tr)
        print(f"{lab:36s} | CAGR {st['cagr_%']:6.2f} (IS {st['cagr_IS_%']:6.2f} / OOS {st['cagr_OOS_%']:6.2f}) DD {st['max_dd_%']:6.1f} "
              f"Sharpe {st['sharpe']:5.2f} (IS {st['sharpe_IS']:5.2f} / OOS {st['sharpe_OOS']:5.2f}) trades {st.get('trades', 0)} "
              f"win {st.get('win%', 0):.0f}% avg {st.get('avg_trade_%', 0):.2f}% inv {st['avg_invested_%']:.0f}%", flush=True)
        return lab

    for sc in SCORES:
        go("short", sc)
    # choose the "worst profile" definition IN-SAMPLE (Sharpe 1990-2012)
    sh = pd.DataFrame(rows)
    best_score = sh.sort_values("sharpe_IS", ascending=False).iloc[0]["score"]
    print("chosen worst-profile score (in-sample):", best_score, flush=True)
    for K, M in [(1, 3), (3, 3), (5, 10)]:
        go("short", best_score, K, M)
    go("short", best_score, 3, 6, 99999)
    for sc in SCORES:
        go("long", sc)
    # what the worst profile means: does it keep falling, or rebound? -> BUY it instead (contrarian)
    for sc in SCORES:
        res, tr = rotation(daily, panel, wkdate, sc, "long", 3, 6, 365, True, contrarian=True)
        st = stats(res["equity"], tr, res["expo"])
        lab = f"contrarian long {sc} K3 M6 1y"
        rows.append({"side": "contrarian long", "score": sc, "K": 3, "M": 6, "max_days": 365, "cond": True, "label": lab, **st})
        keep[lab] = (res, tr)
        print(f"{lab:36s} | CAGR {st['cagr_%']:6.2f} (IS {st['cagr_IS_%']:6.2f} / OOS {st['cagr_OOS_%']:6.2f}) DD {st['max_dd_%']:6.1f} "
              f"Sharpe {st['sharpe']:5.2f} (IS {st['sharpe_IS']:5.2f} / OOS {st['sharpe_OOS']:5.2f}) trades {st['trades']} win {st['win%']:.0f}% avg {st['avg_trade_%']:.2f}%", flush=True)
    best_long = pd.DataFrame([r for r in rows if r["side"] == "long"]).sort_values("sharpe_IS", ascending=False).iloc[0]["score"]

    # the earlier long strategy on the same 27 instruments (event: new up-phase, MACD stop, 1 year, max 3)
    import macd_variants_study as mv
    inst = mv.build()
    sig = mv.signals(inst)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
    cal = cal[cal >= mv.START]
    mv.MAX_OPEN = 3
    long_res, long_c = mv.run(inst, sig, cal, dict(mode="base"), 365, None)
    long_e = long_res["equity"]
    rows.append({"side": "long", "score": "new up-phase (earlier rules)", "K": 3, "label": "long: earlier MACD rules", **stats(long_e)})
    print("earlier long rules", {k: round(v, 2) for k, v in stats(long_e).items()})

    short_lab = f"short {best_score} K3 M6 1y"
    sr = keep[short_lab][0]["equity"].pct_change().fillna(0.0)
    combos = {}
    for lname, le in [("earlier long rules", long_e), (f"best-profile long ({best_long})", keep[f"long {best_long} K3 M6 1y"][0]["equity"])]:
        lr = le.pct_change().fillna(0.0)
        lr, s2 = lr.align(sr, join="outer", fill_value=0.0)
        for cname, rc in [(f"50/50: {lname} + worst-profile short", 0.5 * lr + 0.5 * s2),
                          (f"{lname} 100% + worst-profile short 50% overlay", lr + 0.5 * s2),
                          (f"{lname} 100% + worst-profile short 100% overlay", lr + s2)]:
            e = (1 + rc).cumprod() * CAPITAL
            st = stats(e)
            st["corr"] = float(np.corrcoef(lr, s2)[0, 1])
            combos[cname] = (e, st)
            print(f"{cname:75s} | CAGR {st['cagr_%']:6.2f} (IS {st['cagr_IS_%']:6.2f} / OOS {st['cagr_OOS_%']:6.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} corr {st['corr']:.2f}")
    # equal-weight buy & hold of the 27
    rets = pd.concat([d["Close"].pct_change().rename(t) for t, d in daily.items()], axis=1, sort=True)
    bh = (1 + rets[rets.index >= START].mean(axis=1).fillna(0.0)).cumprod() * CAPITAL
    bh_st = stats(bh)
    print("EW buy & hold 27", {k: round(v, 2) for k, v in bh_st.items()})

    # what the worst profile looks like right now
    last = panel["macd"].index[-1]
    now = pd.DataFrame({
        "name": [UNIVERSE[t][0] for t in panel["macd"].columns], "group": [UNIVERSE[t][1] for t in panel["macd"].columns],
        "macd_pct_price": 100 * panel["depth"].loc[last], "depth_vol": panel["depth_vol"].loc[last],
        "accel_pct_price": 100 * panel["accel"].loc[last], "composite": panel["composite"].loc[last],
        "downtrend": (panel["macd"].loc[last] < 0) & (panel["sig"].loc[last] < 0)}, index=panel["macd"].columns)
    now["rank_worst"] = now[best_score if best_score != "composite" else "composite"].rank()
    now = now.sort_values("rank_worst")
    print(now.round(3).to_string())
    held_now = keep[short_lab][1]
    held_now = held_now[held_now.exit_date.isna()]

    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    now.to_csv(os.path.join(OUT, "worst_profile_now.csv"))
    summary = {"rules": __doc__, "chosen_score": best_score, "chosen_long_score": best_long, "variants": rows,
               "combos": {k: v[1] for k, v in combos.items()}, "bh": bh_st, "now": now.reset_index().astype(str).to_dict("records"),
               "short_held_now": held_now.astype(str).to_dict("records"), "as_of_week": str(last), "runs": {}}
    for lab in [short_lab, f"short depth K3 M6 1y", f"long {best_long} K3 M6 1y", f"contrarian long {best_score} K3 M6 1y"]:
        res, tr = keep[lab]
        res.to_csv(os.path.join(OUT, f"equity_{lab.replace(' ', '_')}.csv"))
        tr.to_csv(os.path.join(OUT, f"trades_{lab.replace(' ', '_')}.csv"), index=False)
        summary["runs"][lab] = {"equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                  for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                "by_year": res["equity"].resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict()}
    summary["runs"]["long: earlier MACD rules"] = {"equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                                     for d, v in long_e.resample("W-FRI").last().dropna().items()]}
    for k, (e, st) in combos.items():
        summary["runs"][k] = {"equity_weekly": [[d.date().isoformat(), round(float(v), 2)] for d, v in e.resample("W-FRI").last().dropna().items()]}
    summary["bh_equity_weekly"] = [[d.date().isoformat(), round(float(v), 2)] for d, v in bh.resample("W-FRI").last().dropna().items()]
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
