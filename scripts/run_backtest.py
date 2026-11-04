"""Pick the best configs from the grid (in-sample only), then simulate them in full detail:
daily mark-to-market equity, PnL by attempt / instrument / year, benchmarks, live status.

Usage:  python scripts/run_backtest.py      (after scripts/optimize.py)
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from strategy.backtest import (SIZE_SCHEMES, SPLIT_DATE, Account, apply_sizing, buy_and_hold,  # noqa: E402
                               by_attempt, cap_concurrent, daily_equity, equity_stats, metrics, prepare,
                               run_paths, select_sequences)
from strategy.engine import MAX_ATTEMPTS, simulate_sequence  # noqa: E402
from strategy.demark import td_buy_setup_count  # noqa: E402
from strategy.engine import PathParams  # noqa: E402
from strategy.universe import UNIVERSE  # noqa: E402

RESULTS = os.path.join(ROOT, "results")
DATA_CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")
PATH_COLS = ["min_dd", "perfected", "entry_mode", "buf", "target", "time_stop", "window"]
MIN_SEQ_IS = {"W": 60, "D": 250}
ACCT = Account()


def load_grid(tf):
    return pd.read_csv(os.path.join(RESULTS, f"grid_{tf}.csv.gz"))


def pick_best(grid: pd.DataFrame, tf: str, m_fixed=None, scheme_fixed=None) -> pd.Series:
    """Best in-sample MAR (R/yr divided by max drawdown in R) with enough trades."""
    g = grid[(grid.period == "IS") & (grid.n_seq >= MIN_SEQ_IS[tf])]
    if m_fixed is not None:
        g = g[g.m == m_fixed]
    if scheme_fixed is not None:
        g = g[g.scheme == scheme_fixed]
    return g.sort_values("MAR", ascending=False).iloc[0]


def cfg_rows(grid, best, keys=PATH_COLS + ["m", "scheme"]):
    m = np.ones(len(grid), dtype=bool)
    for k in keys:
        m &= grid[k].to_numpy() == best[k]
    return grid[m].set_index("period")


def path_params(best) -> PathParams:
    return PathParams(entry_mode=best.entry_mode, buf=float(best.buf), target=best.target,
                      time_stop=int(best.time_stop), window=int(best.window))


def reentry_matrix(grid, best):
    """For the chosen path config: every (max re-entries, size scheme) combination."""
    m = np.ones(len(grid), dtype=bool)
    for k in PATH_COLS:
        m &= grid[k].to_numpy() == best[k]
    g = grid[m]
    return g[["period", "m", "scheme", "n_seq", "n_att", "seq_win%", "avg_R_seq", "total_R", "R_per_yr",
              "PF", "maxDD_R", "MAR", "worst_seq_R"]].sort_values(["period", "m", "scheme"])


def hold_benchmark(prep, min_dd, perfected, hold, signals_override=None):
    """Buy next open after every filtered setup 9, sell after `hold` days, no stop (in % return)."""
    rows = []
    for t, x in prep.items():
        if signals_override is not None:
            sig = signals_override[t]
        else:
            sig = x["signals"]
            sig = sig[(sig.drawdown <= -min_dd) & (sig.perfected | (not perfected))]
        O, C = x["O"], x["C"]
        last = -1
        for r in sig.itertuples(index=False):
            e = r.s0 + 1
            if e <= last or e >= len(C):
                continue
            xp = min(e + hold, len(C) - 1)
            rows.append({"ticker": t, "sig_date": r.date, "ret%": 100 * (C[xp] / O[e] - 1)})
            last = xp
    return pd.DataFrame(rows)


def live_status(prep_w, prep_d, best_w, best_d):
    rows = []
    for t in UNIVERSE:
        wb, db = prep_w[t]["bars"], prep_d[t]["bars"]
        wc, dc = td_buy_setup_count(wb["Close"]), td_buy_setup_count(db["Close"])
        wdd = wb["Close"].iloc[-1] / wb["Close"].iloc[-52:].max() - 1
        ddd = db["Close"].iloc[-1] / db["Close"].iloc[-252:].max() - 1
        # last weekly / daily setup-9 and whether its re-entry window is still open
        def last_sig(prep, win):
            s = prep[t]["signals"]
            if s.empty:
                return None, None, None, False
            r = s.iloc[-1]
            n_after = len(prep[t]["C"]) - 1 - int(r.s0)
            return r.date.date().isoformat(), float(r.high), float(r.low), n_after <= win
        lw = last_sig(prep_w, int(best_w.window))
        ld = last_sig(prep_d, int(best_d.window))
        rows.append({
            "ticker": t, "name": UNIVERSE[t][0], "group": UNIVERSE[t][1],
            "last_close": float(db["Close"].iloc[-1]), "last_date": db.index[-1].date().isoformat(),
            "weekly_buy_count": int(wc.iloc[-1]), "weekly_dd_52w%": round(100 * wdd, 1),
            "daily_buy_count": int(dc.iloc[-1]), "daily_dd_252d%": round(100 * ddd, 1),
            "last_weekly_9": lw[0], "w9_high": lw[1], "w9_low": lw[2], "weekly_window_open": lw[3],
            "last_daily_9": ld[0], "d9_high": ld[1], "d9_low": ld[2], "daily_window_open": ld[3],
        })
    return pd.DataFrame(rows)


def detail(tf, prep, best, label):
    p = path_params(best)
    m, scheme = int(best.m), best.scheme
    atts, seqs = run_paths(prep, float(best.min_dd), bool(best.perfected), p)
    sel = select_sequences(seqs, m)
    a = apply_sizing(atts, sel, m, scheme, ACCT)
    eq = daily_equity(a, prep, ACCT, p.cost_bps)
    eq = eq[eq.index >= "1990-01-01"]
    data_end = eq.index[-1]
    yrs_full = (data_end - pd.Timestamp("1990-01-01")).days / 365.25
    res = {"label": label, "timeframe": tf,
           "config": {k: (v.item() if hasattr(v, "item") else v) for k, v in best[PATH_COLS + ["m", "scheme"]].items()},
           "metrics_R": {"FULL": metrics(a, yrs_full),
                         "IS": metrics(a[a.sig_date < SPLIT_DATE], (SPLIT_DATE - pd.Timestamp("1990-01-01")).days / 365.25),
                         "OOS": metrics(a[a.sig_date >= SPLIT_DATE], (data_end - SPLIT_DATE).days / 365.25)},
           "equity_stats": {"FULL": equity_stats(eq, ACCT),
                            "IS": equity_stats(eq[eq.index < SPLIT_DATE].assign(), ACCT),
                            "OOS": equity_stats(eq[eq.index >= SPLIT_DATE].assign(
                                equity=ACCT.capital + eq.loc[eq.index >= SPLIT_DATE, "pnl"].cumsum()), ACCT)}}
    ba = by_attempt(a)
    a = a.assign(year=pd.to_datetime(a.exit_date).dt.year)
    by_year = a.groupby("year").agg(pnl=("pnl", "sum"), n_att=("k", "size")).reset_index()
    by_inst = a.groupby("ticker").agg(pnl=("pnl", "sum"), pnl_R=("pnl_R", "sum"), n_att=("k", "size"),
                                      n_seq=("s0", "nunique")).reset_index()
    by_inst["name"] = by_inst.ticker.map(lambda t: UNIVERSE[t][0])
    by_inst["group"] = by_inst.ticker.map(lambda t: UNIVERSE[t][1])
    seq_pnl = a.groupby(["ticker", "sig_date"]).agg(pnl_R=("pnl_R", "sum"), n_att=("k", "size")).reset_index()
    a.to_csv(os.path.join(RESULTS, f"trades_{label}.csv"), index=False)
    eq.to_csv(os.path.join(RESULTS, f"equity_{label}.csv"))
    return res, ba, by_year, by_inst, seq_pnl, eq


def placebo(prep, tf, best, n_rep=30, seed=7):
    """Same rules on random sell-off bars instead of DeMark-9 bars (n_rep draws)."""
    from strategy.backtest import random_signals
    rng = np.random.default_rng(seed)
    p = path_params(best)
    m, scheme = int(best.m), best.scheme
    lookback = 52 if tf == "W" else 252
    out = []
    for _ in range(n_rep):
        sigs = random_signals(prep, float(best.min_dd), bool(best.perfected), lookback, rng)
        atts, seqs = run_paths(prep, 0.0, False, p, signals_override=sigs)
        a = apply_sizing(atts, select_sequences(seqs, m), m, scheme, ACCT)
        a0 = apply_sizing(atts, select_sequences(seqs, 0), 0, "flat", ACCT)
        mt, m0 = metrics(a, 1.0), metrics(a0, 1.0)
        hb = hold_benchmark(prep, 0.0, False, int(best.time_stop), signals_override=sigs)
        out.append({"avg_R_seq": mt["avg_R_seq"], "PF": mt["PF"], "win%": mt["seq_win%"],
                    "avg_R_seq_no_reentry": m0["avg_R_seq"], "PF_no_reentry": m0["PF"],
                    "hold_avg_ret%": float(hb["ret%"].mean()), "hold_win%": float((hb["ret%"] > 0).mean() * 100)})
    df = pd.DataFrame(out)
    return {c: {"mean": float(df[c].mean()), "p05": float(df[c].quantile(0.05)), "p95": float(df[c].quantile(0.95))}
            for c in df.columns}


def risk_tables(tf, prep, design):
    """$-equity stats (FULL period) for every (re-entries, size scheme) on the design's path
    config, and for portfolio-level caps on concurrently open sequences."""
    p = path_params(design)
    atts, seqs = run_paths(prep, float(design.min_dd), bool(design.perfected), p)
    rows = []
    for m in range(MAX_ATTEMPTS):
        sel = select_sequences(seqs, m)
        for scheme in SIZE_SCHEMES:
            if m == 0 and scheme != "flat":
                continue
            a = apply_sizing(atts, sel, m, scheme, ACCT)
            eq = daily_equity(a, prep, ACCT, p.cost_bps)
            eq = eq[eq.index >= "1990-01-01"]
            st = equity_stats(eq, ACCT)
            seq_usd = a.groupby(["ticker", "s0"])["pnl"].sum()
            rows.append({"m": m, "scheme": scheme, **st, "worst_seq_$": float(seq_usd.min()),
                         "MAR_$": st["ret_per_yr_%_of_capital"] / -st["max_dd_%_of_capital"]})
    risk = pd.DataFrame(rows)
    conc = []
    m, scheme = int(design.m), design.scheme
    for k in [2, 3, 5, 8, None]:
        sel = cap_concurrent(select_sequences(seqs, m), prep, m, k)
        a = apply_sizing(atts, sel, m, scheme, ACCT)
        eq = daily_equity(a, prep, ACCT, p.cost_bps)
        eq = eq[eq.index >= "1990-01-01"]
        st = equity_stats(eq, ACCT)
        conc.append({"max_open": k if k else "unlimited", "n_seq": int(a.groupby(["ticker", "s0"]).ngroups), **st,
                     "MAR_$": st["ret_per_yr_%_of_capital"] / -st["max_dd_%_of_capital"]})
    return risk, pd.DataFrame(conc)


def live_sequences(tf, prep, design):
    """State of every sequence whose signal is recent enough to still be active today."""
    p = path_params(design)
    out = []
    for t, x in prep.items():
        sig = x["signals"]
        sig = sig[(sig.drawdown <= -float(design.min_dd)) & (sig.perfected | (not bool(design.perfected)))]
        n = len(x["C"])
        s0s = sig["s0"].to_numpy()
        for j, r in enumerate(sig.itertuples(index=False)):
            if n - 1 - int(r.s0) > p.window + p.time_stop:
                continue
            atts, end, status = simulate_sequence(x["O"], x["H"], x["L"], x["C"], int(r.s0), r.high, r.low,
                                                  r.atr, r.tdst, set(s0s[j + 1:].tolist()), p)
            atts = atts[: int(design.m) + 1]
            if status not in ("open", "waiting", "live"):
                continue
            stop = r.low - p.buf * r.atr
            trig = r.high + p.buf * r.atr
            wts = SIZE_SCHEMES[design.scheme]
            k_next = len(atts) if status != "open" else len(atts) - 1
            if status == "waiting":
                state = "ARMED - buy-stop above signal high" if not atts else "STOPPED - waiting for re-entry"
            else:
                state = {"open": "IN POSITION",
                         "live": "NEW SIGNAL - buy next open" if p.entry_mode == "next_open"
                         else "NEW SIGNAL - buy-stop above signal high"}[status]
            if status == "waiting" and len(atts) > int(design.m):
                continue
            out.append({"timeframe": tf, "ticker": t, "name": UNIVERSE[t][0], "signal_date": r.date.date().isoformat(),
                        "signal_high": round(r.high, 2), "signal_low": round(r.low, 2),
                        "stop_level": round(stop, 2), "reentry_trigger": round(trig, 2),
                        "state": state, "attempts_used": len(atts) if status != "live" else 0,
                        "current_attempt_size_x": wts[k_next] if k_next < len(wts) else None,
                        "entry_px": round(atts[-1]["entry_px"], 2) if status == "open" else None,
                        "last_close": round(x["C"][-1], 2), "open_R": round(atts[-1]["R"], 2) if status == "open" else None,
                        "days_since_signal": n - 1 - int(r.s0)})
    return pd.DataFrame(out)


def main():
    prep = {"W": prepare("W", drop_after=DATA_CUTOFF), "D": prepare("D", drop_after=DATA_CUTOFF)}
    summary = {"data_cutoff": DATA_CUTOFF, "split": SPLIT_DATE.date().isoformat(),
               "account": ACCT.__dict__, "runs": {}}
    chosen = {}
    for tf in ["W", "D"]:
        grid = load_grid(tf)
        best_any = pick_best(grid, tf)               # unconstrained optimum (any # re-entries)
        design = pick_best(grid, tf, m_fixed=5)      # the requested design: up to 5 re-entries
        no_re = pd.concat([design[PATH_COLS], pd.Series({"m": 0, "scheme": "flat"})])
        chosen[tf] = design
        rm = reentry_matrix(grid, design)
        rm.to_csv(os.path.join(RESULTS, f"reentry_matrix_{tf}.csv"), index=False)
        # robustness: how do the top-25 in-sample configs do out-of-sample?
        keys = PATH_COLS + ["m", "scheme"]
        is_ = grid[(grid.period == "IS") & (grid.n_seq >= MIN_SEQ_IS[tf])].sort_values("MAR", ascending=False)
        oos = grid[grid.period == "OOS"].set_index(keys)
        top = is_.head(25).set_index(keys).join(oos[["n_seq", "R_per_yr", "MAR", "PF", "maxDD_R"]],
                                                rsuffix="_OOS").reset_index()
        top.to_csv(os.path.join(RESULTS, f"top25_IS_{tf}.csv"), index=False)
        both = grid[grid.period.isin(["IS", "OOS"])].pivot_table(index=keys, columns="period", values="R_per_yr")
        rank_corr = float(both["IS"].rank().corr(both["OOS"].rank()))
        gf = grid[grid.period == "FULL"]
        sens = {c: gf.groupby(c)[["R_per_yr", "MAR", "PF"]].median().reset_index().to_dict("records") for c in keys}

        runs = {}
        for label, cfg in [(f"{tf}_design", design), (f"{tf}_no_reentry", no_re)]:
            res, ba, by_year, by_inst, seq_pnl, eq = detail(tf, prep[tf], cfg, label)
            res["by_attempt"] = ba.reset_index().to_dict("records")
            res["by_year"] = by_year.to_dict("records")
            res["by_instrument"] = by_inst.sort_values("pnl", ascending=False).to_dict("records")
            res["seq_R"] = seq_pnl.assign(sig_date=seq_pnl.sig_date.astype(str)).to_dict("records")
            res["equity_weekly"] = [[d.date().isoformat(), round(float(v), 2)]
                                    for d, v in eq["equity"].resample("W-FRI").last().dropna().items()]
            runs[label] = res
            print(f"\n===== {label} =====")
            print(cfg[keys].to_dict())
            print(cfg_rows(grid, cfg)[["n_seq", "seq_win%", "avg_R_seq", "R_per_yr", "PF", "maxDD_R", "MAR",
                                        "worst_seq_R"]].round(2))
            print("equity:", {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in res["equity_stats"].items()})
            print(ba.round(2))
        risk, conc = risk_tables(tf, prep[tf], design)
        risk.to_csv(os.path.join(RESULTS, f"risk_table_{tf}.csv"), index=False)
        conc.to_csv(os.path.join(RESULTS, f"concurrency_{tf}.csv"), index=False)
        print(risk[["m", "scheme", "ret_per_yr_%_of_capital", "max_dd_%_of_capital", "MAR_$", "sharpe",
                    "worst_seq_$", "max_gross_expo_x"]].round(2).to_string())
        print(conc[["max_open", "n_seq", "ret_per_yr_%_of_capital", "max_dd_%_of_capital", "MAR_$", "sharpe"]].round(2).to_string())
        lv = live_sequences(tf, prep[tf], design)
        hold = hold_benchmark(prep[tf], float(design.min_dd), bool(design.perfected), int(design.time_stop))
        plc = placebo(prep[tf], tf, design)
        print("placebo:", plc)
        summary["runs"][tf] = {
            "design": runs[f"{tf}_design"], "no_reentry": runs[f"{tf}_no_reentry"],
            "best_any": {**{k: (v.item() if hasattr(v, "item") else v) for k, v in best_any[keys].items()},
                         "rows": cfg_rows(grid, best_any).reset_index()[["period", "n_seq", "avg_R_seq", "R_per_yr",
                                                                          "PF", "maxDD_R", "MAR", "worst_seq_R"]].to_dict("records")},
            "reentry_matrix": rm.to_dict("records"),
            "top25_IS_with_OOS": top.to_dict("records"),
            "IS_OOS_rank_corr_R_per_yr": rank_corr,
            "n_configs": int((grid.period == "FULL").sum()),
            "sensitivity": sens,
            "hold_benchmark": {"n": len(hold), "avg_ret%": float(hold["ret%"].mean()),
                               "win%": float((hold["ret%"] > 0).mean() * 100),
                               "median_ret%": float(hold["ret%"].median())},
            "placebo": plc,
            "risk_table": risk.to_dict("records"),
            "concurrency": conc.to_dict("records"),
            "live_sequences": lv.to_dict("records"),
            "n_signals_total": int(sum(len(x["signals"]) for x in prep[tf].values())),
        }
        print(f"IS/OOS rank corr of R/yr across {summary['runs'][tf]['n_configs']} configs: {rank_corr:.2f}")
    bh = buy_and_hold(prep["D"])
    bh_eq = bh["equity"]
    yrs = (bh_eq.index[-1] - bh_eq.index[0]).days / 365.25
    summary["buy_and_hold_equal_weight"] = {
        "cagr%": 100 * float(bh_eq.iloc[-1] ** (1 / yrs) - 1),
        "max_dd%": 100 * float((bh_eq / bh_eq.cummax() - 1).min()),
        "sharpe": float(bh["ret"].mean() / bh["ret"].std() * np.sqrt(252)),
        "equity_weekly": [[d.date().isoformat(), round(float(v) * ACCT.capital, 2)]
                          for d, v in bh_eq.resample("W-FRI").last().dropna().items()]}
    print("buy&hold EW:", {k: v for k, v in summary["buy_and_hold_equal_weight"].items() if k != "equity_weekly"})
    live = live_status(prep["W"], prep["D"], chosen["W"], chosen["D"])
    live.to_csv(os.path.join(RESULTS, "live_status.csv"), index=False)
    summary["live"] = live.to_dict("records")
    with open(os.path.join(RESULTS, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    for tf in ["W", "D"]:
        lv = pd.DataFrame(summary["runs"][tf]["live_sequences"])
        lv.to_csv(os.path.join(RESULTS, f"live_sequences_{tf}.csv"), index=False)
        print(f"\nlive sequences {tf}:\n", lv.to_string() if len(lv) else "none")
    print("\nlive:\n", live[["ticker", "weekly_buy_count", "daily_buy_count", "weekly_dd_52w%", "last_weekly_9",
                             "weekly_window_open", "last_daily_9", "daily_window_open"]].to_string())


if __name__ == "__main__":
    main()
