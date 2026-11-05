"""Weekly-MACD long strategy on the 27 indices + sectors, played only when the S&P 500 is above its
100-day moving average (and sensitivities / mirror short leg).

  long signal : weekly MACD and signal both turn > 0 (new up-phase) -> buy next open; MACD stop;
                1-year exit; max 3 positions, 1/3 of equity each (cash-capped, compounding)
  regime      : S&P 500 close > its N-day simple moving average (N = 100; 50/200 tested)
  variants    : entry filter only | + exit everything when the S&P 500 closes below the average
                (daily or weekly check) | + re-entry: when the regime turns back on, assets whose
                MACD up-phase is still intact can be bought again
  short side  : worst-MACD-profile short (see worst_short_study.py) only while S&P 500 < average

Usage:  python scripts/macd_regime_study.py   -> results/macd_regime/
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
import worst_short_study as ws  # noqa: E402
from strategy.data import load_daily, to_weekly  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

OUT = os.path.join(ROOT, "results", "macd_regime")
CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")


def spx_regime(n):
    c = load_daily("^GSPC", drop_after=CUTOFF)["Close"]
    sma = c.rolling(n).mean()
    on = (c > sma) & sma.notna()
    return c, sma, on


def attach(inst, on_d, weekly_exit):
    """Per asset: regime known at each of its closes (last S&P close <= that date) + exit flags."""
    spx_wk = set(to_weekly(load_daily("^GSPC", drop_after=CUTOFF)).index)
    for t, x in inst.items():
        r = on_d.reindex(x["idx"], method="ffill").fillna(False).to_numpy(dtype=bool)
        x["reg_on"] = r
        off = ~r
        if weekly_exit:  # only act on S&P weekly closes
            wk = np.array([d in spx_wk for d in x["idx"]]) | x["wk_close"]
            off = off & wk
        x["exit_off"] = off


def mark_on(inst):
    for t in UNIVERSE:
        d = load_daily(t, drop_after=CUTOFF)
        w = to_weekly(d)
        macd = w["Close"].ewm(span=12, adjust=False).mean() - w["Close"].ewm(span=26, adjust=False).mean()
        sig = macd.ewm(span=9, adjust=False).mean()
        on = (macd > 0) & (sig > 0)
        on.iloc[:35] = False
        inst[t]["on"] = on.reindex(d.index, method="ffill").fillna(False).to_numpy(dtype=bool)


def signals(inst, regime_on_d, filt=True, reentry=False):
    base = mv.signals(inst)
    if filt:
        base = base[[inst[r.ticker]["reg_on"][r.e - 1] for r in base.itertuples()]]
    rows = [base]
    if reentry:  # regime turns on -> candidates: assets whose MACD up-phase is intact
        turns = regime_on_d.index[regime_on_d & ~regime_on_d.shift(1, fill_value=False)]
        extra = []
        for t, x in inst.items():
            for d in turns:
                j = x["idx"].searchsorted(d, side="right") - 1
                if 0 <= j < len(x["C"]) - 1 and x["on"][j] and x["idx"][j + 1] >= mv.START:
                    extra.append({"ticker": t, "e": int(j + 1), "entry_date": x["idx"][j + 1], "strength": x["strength"][j]})
        rows.append(pd.DataFrame(extra))
    s = pd.concat(rows, ignore_index=True).drop_duplicates(["ticker", "e"])
    return s.sort_values(["entry_date", "strength"], ascending=[True, False]).reset_index(drop=True)


def run(inst, sig, cal, regime_exit, kw=None):
    for x in inst.values():
        x["exit_flag"] = x["exit_off"] if regime_exit else None
    mv.MAX_OPEN = 3
    res, camps = mv.run(inst, sig, cal, kw or dict(mode="base"), 365, None)
    return res, camps


def main():
    os.makedirs(OUT, exist_ok=True)
    inst = mv.build()
    mark_on(inst)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
    cal = cal[cal >= mv.START]
    rows, keep = [], {}

    def go(label, n, filt, rexit, weekly, reentry, kw=None, universe=None):
        c, sma, on = spx_regime(n)
        sub = inst if universe is None else {t: inst[t] for t in universe}
        attach(sub, on, weekly)
        sig = signals(sub, on, filt, reentry)
        res, camps = run(sub, sig, cal, rexit, kw)
        st = mv.stats(res, camps)
        time_on = 100 * float(on[on.index >= mv.START].mean())
        rows.append({"variant": label, "sma": n, "entry_filter": filt, "regime_exit": rexit, "weekly_check": weekly,
                     "reentry": reentry, "spx_above_%": time_on, **st,
                     "exit_regime%": 100 * float((camps.reason == "regime").mean()) if len(camps) else 0})
        keep[label] = (res, camps)
        print(f"{label:46s} | CAGR {st['cagr_%']:5.2f} (IS {st['cagr_IS_%']:5.2f} / OOS {st['cagr_OOS_%']:5.2f}) DD {st['max_dd_%']:6.1f} "
              f"Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:3.0f}% camp {st['campaigns']} win {st['win%']:.0f}% "
              f"avg {st['avg_campaign_%']:.1f}% regime-exits {rows[-1]['exit_regime%']:.0f}%", flush=True)

    go("no filter (earlier rules)", 100, False, False, False, False)
    for n in [100, 50, 200]:
        go(f"SPX>{n}d: entry filter only", n, True, False, False, False)
        go(f"SPX>{n}d: entry filter + daily exit", n, True, True, False, False)
        go(f"SPX>{n}d: entry filter + weekly exit", n, True, True, True, False)
        go(f"SPX>{n}d: filter + daily exit + re-entry", n, True, True, False, True)
        go(f"SPX>{n}d: filter + weekly exit + re-entry", n, True, True, True, True)

    # with the 1 % stop + re-entry at the first entry price (27 instruments, and the 16 DM indices alone)
    sl1 = dict(mode="sl_reentry", sl=0.01)
    dm = [t for t, v in UNIVERSE.items() if v[1] == "DM index"]
    go("1% SL: no filter", 100, False, False, False, False, sl1)
    go("1% SL: SPX>100d entry filter", 100, True, False, False, False, sl1)
    go("1% SL: SPX>200d entry filter", 200, True, False, False, False, sl1)
    go("2% SL: SPX>100d entry filter", 100, True, False, False, False, dict(mode="sl_reentry", sl=0.02))
    go("DM only: no filter", 100, False, False, False, False, None, dm)
    go("DM only: SPX>100d entry filter", 100, True, False, False, False, None, dm)
    go("DM only, 1% SL: no filter", 100, False, False, False, False, sl1, dm)
    go("DM only, 1% SL: SPX>100d entry filter", 100, True, False, False, False, sl1, dm)

    # mirror short: worst-MACD-profile short only while S&P 500 < 100-day average
    daily, panel, wkdate = ws.build()
    c, sma, on = spx_regime(100)
    spx_w = to_weekly(load_daily("^GSPC", drop_after=CUTOFF))
    off_w = pd.Series((~on).reindex(spx_w.index).to_numpy(), index=spx_w.index.to_period("W-FRI"))
    short_rows = {}
    for lab, allow in [("worst-profile short, always", None), ("worst-profile short, only S&P < 100d", off_w)]:
        res, tr = ws.rotation(daily, panel, wkdate, "composite", "short", 3, 6, 365, True, allow=allow)
        st = ws.stats(res["equity"], tr, res["expo"])
        short_rows[lab] = (res, st)
        rows.append({"variant": lab, "sma": 100, **{k: v for k, v in st.items()}})
        print(f"{lab:46s} | CAGR {st['cagr_%']:5.2f} (IS {st['cagr_IS_%']:5.2f} / OOS {st['cagr_OOS_%']:5.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} trades {st.get('trades')}")
    # switching book: regime long + regime short (they rarely overlap in time)
    best_long = "SPX>100d: filter + daily exit + re-entry"
    combos = {}
    for lname in ["SPX>100d: entry filter only", "SPX>100d: entry filter + daily exit", best_long]:
        lr = keep[lname][0]["equity"].pct_change().fillna(0.0)
        sr = short_rows["worst-profile short, only S&P < 100d"][0]["equity"].pct_change().fillna(0.0)
        lr, sr = lr.align(sr, join="outer", fill_value=0.0)
        e = (1 + lr + sr).cumprod() * mv.CAPITAL
        st = ws.stats(e)
        combos[f"{lname} + short when S&P < 100d"] = (e, st)
        rows.append({"variant": f"{lname} + regime short", "sma": 100, **st})
        print(f"{lname + ' + regime short':46s} | CAGR {st['cagr_%']:5.2f} (IS {st['cagr_IS_%']:5.2f} / OOS {st['cagr_OOS_%']:5.2f}) DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f}")
    # S&P 500 buy & hold and S&P timing itself (in when above 100d) for context
    spx = load_daily("^GSPC", drop_after=CUTOFF)["Close"]
    spx = spx[spx.index >= mv.START]
    r = spx.pct_change().fillna(0.0)
    on_lag = on.reindex(spx.index).shift(1).fillna(False)
    for lab, rr in [("S&P 500 buy & hold (price)", r), ("S&P 500 only when above 100d (price)", r.where(on_lag, 0.0))]:
        e = (1 + rr).cumprod() * mv.CAPITAL
        st = ws.stats(e)
        combos[lab] = (e, st)
        rows.append({"variant": lab, "sma": 100, **st})
        print(f"{lab:46s} | CAGR {st['cagr_%']:5.2f} DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f}")

    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    now = {"spx_close": float(c.iloc[-1]), "sma100": float(sma.iloc[-1]), "above": bool(on.iloc[-1]),
           "date": str(c.index[-1].date()), "dist_%": 100 * float(c.iloc[-1] / sma.iloc[-1] - 1),
           "sma50": float(c.rolling(50).mean().iloc[-1]), "sma200": float(c.rolling(200).mean().iloc[-1])}
    summary = {"rules": __doc__, "variants": rows, "now": now, "runs": {}}
    for lab in ["no filter (earlier rules)", "SPX>100d: entry filter only", "SPX>100d: entry filter + daily exit", best_long,
                "1% SL: SPX>100d entry filter", "1% SL: no filter", "DM only, 1% SL: SPX>100d entry filter"]:
        res, camps = keep[lab]
        res.to_csv(os.path.join(OUT, f"equity_{lab.replace(' ', '_').replace('>', 'gt').replace(':', '').replace('+', 'plus')}.csv"))
        summary["runs"][lab] = {"equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                  for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                "live": camps[camps.reason == "open"].astype(str).to_dict("records"),
                                "by_year": res["equity"].resample("YE").last().pct_change().mul(100).round(2).dropna().rename(lambda d: d.year).to_dict()}
    for lab, (e, st) in combos.items():
        summary["runs"][lab] = {"equity_weekly": [[d.date().isoformat(), round(float(v), 2)] for d, v in e.resample("W-FRI").last().dropna().items()]}
    for lab, (res, st) in short_rows.items():
        summary["runs"][lab] = {"equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                  for d, v in res["equity"].resample("W-FRI").last().dropna().items()]}
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print("now:", now)


if __name__ == "__main__":
    main()
