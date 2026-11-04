"""Weekly-MACD strategy with pyramiding UP (no DeMark), max 3 assets.

Same signal, MACD < 0 stop, slots and compounding as scripts/macd_variants_study.py.
Pyramid: 1 unit at the first entry E0, +1 unit on a buy-stop every 1 % above E0
(E0*1.01, E0*1.01^2, ...), up to K extra units; the K+1 units together = the slot's budget
(1/3 of equity), so there is no leverage. Exit everything on MACD < 0 or the take-profit.
Take-profits: time {3, 6, 12, 24 months, none} x level {+5, +10, +20, +30 %, none} (level vs E0).

Usage:  python scripts/macd_pyramid_study.py   -> results/macd_pyramid/
"""
from __future__ import annotations

import itertools
import json
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import macd_variants_study as mv  # noqa: E402

OUT = os.path.join(ROOT, "results", "macd_pyramid")
MAIN = {"base": dict(mode="base"),
        "pyr_1pct_K5": dict(mode="pyramid", step=0.01, K=5),
        "pyr_1pct_K10": dict(mode="pyramid", step=0.01, K=10),
        "pyr_1pct_K20": dict(mode="pyramid", step=0.01, K=20)}
EXTRA = {"pyr_1pct_K3": dict(mode="pyramid", step=0.01, K=3),
         "pyr_1pct_K40": dict(mode="pyramid", step=0.01, K=40),
         "pyr_2pct_K10": dict(mode="pyramid", step=0.02, K=10),
         "pyr_0.5pct_K20": dict(mode="pyramid", step=0.005, K=20)}


def main():
    os.makedirs(OUT, exist_ok=True)
    inst = mv.build()
    sig = mv.signals(inst)
    cal = pd.DatetimeIndex(sorted(set().union(*[set(x["idx"]) for x in inst.values()])))
    cal = cal[cal >= mv.START]
    rows, keep = [], {}
    jobs = [(m, kw, td, tl) for (m, kw), td, tl in itertools.product(MAIN.items(), mv.TP_DAYS, mv.TP_LEVELS)]
    jobs += [(m, kw, 365, None) for m, kw in EXTRA.items()]
    for m, kw, td, tl in jobs:
        res, camps = mv.run(inst, sig, cal, kw, td, tl)
        st = mv.stats(res, camps)
        tt = f"{td}d" if td else "none"
        tlv = f"+{int(tl * 100)}%" if tl else "none"
        rows.append({"mode": m, "tp_time": tt, "tp_level": tlv, **st})
        keep[(m, tt, tlv)] = (res, camps)
        print(f"{m:16s} time {tt:5s} level {tlv:5s} | CAGR {st['cagr_%']:5.2f} (IS {st['cagr_IS_%']:5.2f} / OOS {st['cagr_OOS_%']:5.2f}) "
              f"DD {st['max_dd_%']:6.1f} Sharpe {st['sharpe']:.2f} inv {st['avg_invested_%']:4.0f}% win {st['win%']:.0f}% "
              f"avg {st['avg_campaign_%']:.1f}% worst {st['worst_campaign_%']:.1f}% fills {st['avg_fills']:.1f}", flush=True)
    grid = pd.DataFrame(rows)
    grid.to_csv(os.path.join(OUT, "variants.csv"), index=False)
    summary = {"rules": __doc__, "runs": {}, "variants": rows}
    for m in list(MAIN) + list(EXTRA):
        g = grid[grid["mode"] == m]
        best = g.sort_values("sharpe", ascending=False).iloc[0]
        for tag, (tt, tlv) in {"ref": ("365d", "none"), "best": (best.tp_time, best.tp_level)}.items():
            if (m, tt, tlv) not in keep:
                continue
            res, camps = keep[(m, tt, tlv)]
            key = f"{m}__{tag}"
            res.to_csv(os.path.join(OUT, f"equity_{key}.csv"))
            camps.to_csv(os.path.join(OUT, f"campaigns_{key}.csv"), index=False)
            summary["runs"][key] = {"mode": m, "tp_time": tt, "tp_level": tlv,
                                    "stats": g[(g.tp_time == tt) & (g.tp_level == tlv)].iloc[0].to_dict(),
                                    "equity_weekly": [[d.date().isoformat(), round(float(v), 2)]
                                                      for d, v in res["equity"].resample("W-FRI").last().dropna().items()],
                                    "live": camps[camps.reason == "open"].astype(str).to_dict("records")}
    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
