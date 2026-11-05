"""Best index book + best stock book combined, cash interest, and Kelly / leverage vs the Calmar ratio.

Books (daily equity and exposure, all compounding: every new position gets equity/N, cash-capped):
  IDX5   27 DM indices + sectors: buy at the next open after a new weekly MACD up-phase if the
         S&P 500 is above its 100-day average, no stop, MACD < 0 exit, 1-year exit, max 5
  IDX3   the same with max 3
  STK_W1 point-in-time S&P 500 top-100 stocks: wait 1 month, buy if the weekly MACD stayed > 0 and
         the S&P 500 is above its 100-day average, 1 % stop with re-entry (also S&P-filtered),
         MACD < 0 exit, 11-month exit, max 10
  STK_6M the same stocks: buy at once, no filter, 1 % stop with re-entry, MACD < 0 exit, 6-month exit, max 20
Cash: the earlier backtests earn 0 on idle cash; here idle cash earns the 13-week T-bill (^IRX) and
borrowed money costs T-bill + 1 %/yr.
Combinations (1997-2026): 50/50 of capital, monthly rebalanced; inverse-volatility weights; and an
"overlay" where both books run at full size on the same capital (gross exposure can exceed 100 %:
the excess is borrowed).
Leverage: book returns scaled by a constant L (rebalanced daily): r_L = L * r_positions + (1 - L * expo) * cash
rate (negative cash = borrowing at T-bill + 1 %). Kelly: f* = annual excess mean / annual variance,
estimated in-sample (to 2012) and on the full sample, plus the growth-optimal L found by grid
search. Per-trade Kelly from the campaign returns as a second view.

Usage:  python scripts/combo_kelly_study.py   -> results/combo_kelly/
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

import delayed_entry_study as de  # noqa: E402
import stocks_ma50_study as sm  # noqa: E402

OUT = os.path.join(ROOT, "results", "combo_kelly")
SPLIT = pd.Timestamp("2013-01-01")
START = pd.Timestamp("1997-01-01")
SPREAD = 0.01  # borrowing cost over the T-bill, per year


def tbill(index):
    r = pd.read_csv(os.path.join(ROOT, "data", "rates", "IRX.csv"), index_col=0, parse_dates=True)["irx_pct"]
    r = r.reindex(index, method="ffill").fillna(0.0).clip(lower=0.0) / 100.0
    return r / 252.0  # daily rate


def books():
    out, camps = {}, {}
    spx, inst, sig, cal, _ = de.load("indices")
    for name, mo in [("IDX5", 5), ("IDX3", 3)]:
        res, c, _ = sm.run_one(inst, sig, cal, "spx100", sm.STOPS["no stop"], 365, mo)
        out[name], camps[name] = res, c
    spx, inst, sig, cal, _ = de.load("stocks")
    d1 = de.delay_signals(inst, sig, 30, False)
    res, c, _ = sm.run_one(inst, d1, cal, "spx100", sm.STOPS["1% stop"], 335, 10)
    out["STK_W1"], camps["STK_W1"] = res, c
    res, c, _ = sm.run_one(inst, sig, cal, None, sm.STOPS["1% stop"], 182, 20)
    out["STK_6M"], camps["STK_6M"] = res, c
    return out, camps


def stats(r, rc=None):
    """r: daily returns (Series). rc: daily cash rate for the excess Sharpe."""
    e = (1 + r).cumprod()
    y = (r.index[-1] - r.index[0]).days / 365.25
    cagr = 100 * (e.iloc[-1] ** (1 / y) - 1)
    dd = 100 * float((e / e.cummax() - 1).min())

    def sub(s):
        if len(s) < 50:
            return float("nan")
        ee = (1 + s).cumprod()
        return 100 * (ee.iloc[-1] ** (365.25 / (s.index[-1] - s.index[0]).days) - 1)
    out = {"cagr_%": cagr, "cagr_IS_%": sub(r[r.index < SPLIT]), "cagr_OOS_%": sub(r[r.index >= SPLIT]),
           "vol_%": 100 * float(r.std() * np.sqrt(252)), "max_dd_%": dd, "calmar": cagr / abs(dd) if dd < 0 else float("nan"),
           "sharpe": float(r.mean() / r.std() * np.sqrt(252))}
    if rc is not None:
        x = r - rc
        out["sharpe_excess"] = float(x.mean() / x.std() * np.sqrt(252))
    # worst calendar year
    yr = e.resample("YE").last().pct_change()
    yr.iloc[0] = e.resample("YE").last().iloc[0] - 1
    out["worst_year_%"] = 100 * float(yr.min())
    return out


def lever(rp, expo, rc, L):
    """Constant leverage L on a book: positions scaled by L, the rest in T-bills (or borrowed at T-bill + spread)."""
    gross = L * expo
    cash = 1.0 - gross
    borrow_cost = np.where(cash < 0, SPREAD / 252.0, 0.0)
    return L * rp + cash * rc + cash * borrow_cost  # cash < 0 -> pays rc + spread


def kelly_f(r_base, rc):
    x = r_base - rc
    return float(x.mean() / x.var())  # daily mean / daily variance = annual mean / annual variance


def per_trade_kelly(camps):
    c = camps[camps.reason != "open"]
    rr = c["ret_%"].to_numpy() / 100.0
    if not len(rr):
        return {}
    grid = np.linspace(0.01, 3.0, 300)
    g = [np.mean(np.log1p(np.clip(f * rr, -0.999, None))) for f in grid]
    f_star = float(grid[int(np.argmax(g))])
    w = rr[rr > 0]
    lo = rr[rr <= 0]
    W = len(w) / len(rr)
    R = (w.mean() / -lo.mean()) if len(lo) and lo.mean() < 0 else float("nan")
    return {"trades": int(len(rr)), "win_rate_%": 100 * W, "avg_win_%": 100 * float(w.mean()) if len(w) else 0.0,
            "avg_loss_%": 100 * float(lo.mean()) if len(lo) else 0.0, "payoff_ratio": float(R),
            "kelly_simple_W-(1-W)/R": float(W - (1 - W) / R) if R == R else float("nan"), "kelly_growth_opt": f_star}


def main():
    os.makedirs(OUT, exist_ok=True)
    bk, camps = books()
    idx = pd.DatetimeIndex(sorted(set().union(*[set(b.index) for b in bk.values()])))
    rc_all = tbill(idx)
    R, X = {}, {}
    for k, b in bk.items():
        b = b.reindex(idx).ffill()
        R[k] = b["equity"].pct_change().fillna(0.0)
        X[k] = b["expo"].fillna(0.0).clip(lower=0.0)
    R, X = pd.DataFrame(R), pd.DataFrame(X)
    w = idx >= START
    R, X, rc = R[w], X[w], rc_all[w]
    for k in R:  # each book starts with its first trading day
        first = bk[k].index[0]
        R.loc[R.index < first, k] = 0.0

    rows = []
    base = {}
    for k in R:
        st0 = stats(R[k], rc)
        rb = lever(R[k], X[k], rc, 1.0)  # same book, idle cash earns the T-bill
        base[k] = rb
        st1 = stats(rb, rc)
        rows.append({"book": k, "variant": "as backtested (cash earns 0)", "avg_invested_%": 100 * float(X[k].mean()), **st0})
        rows.append({"book": k, "variant": "idle cash earns T-bill", "avg_invested_%": 100 * float(X[k].mean()), **st1})
        print(f"{k:7s} invested {100 * X[k].mean():3.0f}% | cash 0: CAGR {st0['cagr_%']:5.2f} DD {st0['max_dd_%']:6.1f} Calmar {st0['calmar']:.2f} "
              f"Sharpe {st0['sharpe']:.2f} | T-bill: CAGR {st1['cagr_%']:5.2f} DD {st1['max_dd_%']:6.1f} Calmar {st1['calmar']:.2f}", flush=True)

    # ---- combinations (T-bill on idle cash)
    combos = {}

    def monthly_rebal(ra, rb, wa):
        ea, eb, out = wa, 1 - wa, []
        prev_m = None
        for d, a, b in zip(ra.index, ra.to_numpy(), rb.to_numpy()):
            m = (d.year, d.month)
            if prev_m is not None and m != prev_m:
                tot = ea + eb
                ea, eb = wa * tot, (1 - wa) * tot
            prev_m = m
            tot0 = ea + eb
            ea, eb = ea * (1 + a), eb * (1 + b)
            out.append((ea + eb) / tot0 - 1)
        return pd.Series(out, index=ra.index)

    pairs = [("IDX5", "STK_W1"), ("IDX5", "STK_6M"), ("IDX3", "STK_W1")]
    corr = {}
    for a, b in pairs:
        corr[f"{a}+{b}"] = {"daily": float(np.corrcoef(R[a], R[b])[0, 1]),
                            "monthly": float(np.corrcoef((1 + R[a]).resample("ME").prod() - 1, (1 + R[b]).resample("ME").prod() - 1)[0, 1])}
        combos[f"{a} + {b}: 50/50"] = monthly_rebal(base[a], base[b], 0.5)
        va, vb = base[a].std(), base[b].std()
        wa = (1 / va) / (1 / va + 1 / vb)
        combos[f"{a} + {b}: inverse-vol ({100 * wa:.0f}/{100 * (1 - wa):.0f})"] = monthly_rebal(base[a], base[b], wa)
        # overlay: both books at full size on one capital; excess gross exposure is borrowed
        gross = X[a] + X[b]
        combos[f"{a} + {b}: overlay 100% + 100%"] = R[a] + R[b] + (1 - gross) * rc + np.minimum(1 - gross, 0) * SPREAD / 252
        X[f"{a}+{b} overlay"] = gross
    for k, r in combos.items():
        st = stats(r, rc)
        rows.append({"book": k, "variant": "combination", **st})
        print(f"{k:45s} | CAGR {st['cagr_%']:5.2f} (IS {st['cagr_IS_%']:5.2f} / OOS {st['cagr_OOS_%']:5.2f}) DD {st['max_dd_%']:6.1f} "
              f"Calmar {st['calmar']:.2f} Sharpe {st['sharpe']:.2f} vol {st['vol_%']:.1f}", flush=True)
    for a, b in pairs:
        g = X[f"{a}+{b} overlay"]
        print(f"overlay {a}+{b}: gross exposure mean {100 * g.mean():.0f}%, 95th pct {100 * g.quantile(.95):.0f}%, max {100 * g.max():.0f}%, "
              f"days > 100%: {100 * (g > 1).mean():.0f}%; corr daily {corr[f'{a}+{b}']['daily']:.2f} monthly {corr[f'{a}+{b}']['monthly']:.2f}", flush=True)

    # ---- Kelly / leverage
    kel_rows, kel_info = [], {}
    targets = {"IDX5": (R["IDX5"], X["IDX5"]), "STK_W1": (R["STK_W1"], X["STK_W1"]), "STK_6M": (R["STK_6M"], X["STK_6M"])}
    # the 50/50 combination as one book: positions = half of each, exposure = half of each
    targets["IDX5 + STK_W1 (50/50)"] = (0.5 * R["IDX5"] + 0.5 * R["STK_W1"], 0.5 * X["IDX5"] + 0.5 * X["STK_W1"])
    targets["IDX5 + STK_6M (50/50)"] = (0.5 * R["IDX5"] + 0.5 * R["STK_6M"], 0.5 * X["IDX5"] + 0.5 * X["STK_6M"])
    Ls = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0]
    for k, (rp, ex) in targets.items():
        rb = lever(rp, ex, rc, 1.0)
        f_full = kelly_f(rb, rc)
        f_is = kelly_f(rb[rb.index < SPLIT], rc[rc.index < SPLIT])
        grid = np.round(np.arange(0.25, 15.01, 0.25), 2)
        growth = [np.log1p(lever(rp, ex, rc, L).clip(lower=-0.999)).mean() for L in grid]
        L_opt = float(grid[int(np.argmax(growth))])
        cal = []
        for L in grid:
            s = stats(lever(rp, ex, rc, L))
            cal.append((L, s["calmar"]))
        L_cal = max(cal, key=lambda t: t[1])[0]
        kel_info[k] = {"kelly_full_sample": f_full, "kelly_in_sample_to_2012": f_is, "growth_optimal_L": L_opt, "calmar_optimal_L": float(L_cal)}
        print(f"\n{k}: Kelly f* full {f_full:.2f}, in-sample {f_is:.2f}, growth-optimal L {L_opt:.2f}, Calmar-optimal L {L_cal:.2f}", flush=True)
        lev_set = [(f"L={L:g}", L) for L in Ls] + [("1/4 Kelly (IS)", f_is / 4), ("1/2 Kelly (IS)", f_is / 2), ("full Kelly (IS)", f_is)]
        for lab, L in lev_set:
            s = stats(lever(rp, ex, rc, L), rc)
            s_oos = stats(lever(rp, ex, rc, L)[rp.index >= SPLIT], rc[rc.index >= SPLIT])
            kel_rows.append({"book": k, "sizing": lab, "L": L, **s, "oos_cagr_%": s_oos["cagr_%"], "oos_max_dd_%": s_oos["max_dd_%"],
                             "oos_calmar": s_oos["calmar"], "avg_gross_%": 100 * float((L * ex).mean()), "max_gross_%": 100 * float((L * ex).max())})
            print(f"  {lab:16s} L {L:5.2f} | CAGR {s['cagr_%']:6.2f} DD {s['max_dd_%']:6.1f} Calmar {s['calmar']:.2f} Sharpe {s['sharpe']:.2f} "
                  f"vol {s['vol_%']:5.1f} worst yr {s['worst_year_%']:6.1f} | OOS CAGR {s_oos['cagr_%']:6.2f} DD {s_oos['max_dd_%']:6.1f} "
                  f"Calmar {s_oos['calmar']:.2f} | gross avg {100 * (L * ex).mean():4.0f}% max {100 * (L * ex).max():4.0f}%", flush=True)

    trade_kelly = {k: per_trade_kelly(c) for k, c in camps.items()}
    print("\nper-trade Kelly:", json.dumps(trade_kelly, indent=1), flush=True)

    pd.DataFrame(rows).to_csv(os.path.join(OUT, "books_and_combos.csv"), index=False)
    pd.DataFrame(kel_rows).to_csv(os.path.join(OUT, "kelly_leverage.csv"), index=False)

    def weekly(r):
        e = (1 + r).cumprod() * 100000
        return [[d.date().isoformat(), round(float(v), 2)] for d, v in e.resample("W-FRI").last().dropna().items()]
    eq = {k: weekly(base[k]) for k in base}
    eq.update({k: weekly(v) for k, v in combos.items()})
    for k, (rp, ex) in targets.items():
        if "50/50" in k:
            fis = kel_info[k]["kelly_in_sample_to_2012"]
            for lab, L in [("L=1.5", 1.5), ("1/2 Kelly (IS)", fis / 2), ("full Kelly (IS)", fis)]:
                eq[f"{k} {lab}"] = weekly(lever(rp, ex, rc, L))
    spx = pd.read_csv(os.path.join(ROOT, "data", "raw", "GSPC.csv"), index_col=0, parse_dates=True)["Close"]
    sp = spx.reindex(R.index).ffill().pct_change().fillna(0.0)
    rows.append({"book": "S&P 500 (price)", "variant": "benchmark", **stats(sp, rc)})
    eq["S&P 500 (price)"] = weekly(sp)
    with open(os.path.join(OUT, "summary.json"), "w") as fh:
        json.dump({"rules": __doc__, "books_and_combos": rows, "correlation": corr, "kelly": kel_info, "kelly_rows": kel_rows,
                   "per_trade_kelly": trade_kelly, "equity_weekly": eq}, fh, indent=1,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("S&P 500 price 1997-2026:", {k: round(v, 2) for k, v in stats(sp, rc).items()})


if __name__ == "__main__":
    main()
