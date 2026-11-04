"""Backtest plumbing: signal preparation, path simulation, sizing, portfolio metrics."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import load_daily, to_weekly
from .demark import buy_setup_signals
from .engine import MAX_ATTEMPTS, PathParams, simulate_sequence
from .universe import UNIVERSE

# size multiplier of attempt k (k=0 initial entry, k=1..5 re-entries), in units of base risk
SIZE_SCHEMES = {
    "flat":   [1, 1, 1, 1, 1, 1],
    "linear": [1, 2, 3, 4, 5, 6],
    "geo1.5": [1.5 ** k for k in range(MAX_ATTEMPTS)],
    "geo2":   [2.0 ** k for k in range(MAX_ATTEMPTS)],   # martingale
}

SPLIT_DATE = pd.Timestamp("2013-01-01")  # in-sample < split <= out-of-sample


@dataclass(frozen=True)
class Account:
    capital: float = 100_000.0
    base_risk: float = 0.005      # 0.5% of capital risked on the first attempt
    notional_cap: float = 2.0     # max notional per position, x capital


# --------------------------------------------------------------------------- signals
def prepare(timeframe: str, tickers=None, drop_after: str | None = None) -> dict:
    """timeframe 'W' (weekly setups) or 'D' (daily setups). Execution is daily in both."""
    tickers = tickers or list(UNIVERSE)
    out = {}
    for t in tickers:
        d = load_daily(t, drop_after=drop_after)
        if timeframe == "W":
            bars = to_weekly(d)
            sig = buy_setup_signals(bars, dd_lookback=52)
        else:
            bars = d
            sig = buy_setup_signals(bars, dd_lookback=252)
        if len(sig):
            pos_map = pd.Series(np.arange(len(d)), index=d.index)
            sig["s0"] = pos_map.reindex(sig["date"]).to_numpy()
            sig = sig.dropna(subset=["s0"]).astype({"s0": int})
            sig = sig[sig["s0"] >= 0].reset_index(drop=True)
        out[t] = {
            "dates": d.index,
            "O": d["Open"].tolist(), "H": d["High"].tolist(),
            "L": d["Low"].tolist(), "C": d["Close"].tolist(),
            "signals": sig, "bars": bars,
        }
    return out


def filter_signals(sig: pd.DataFrame, min_dd: float, perfected: bool) -> pd.DataFrame:
    m = sig["drawdown"] <= -min_dd
    if perfected:
        m &= sig["perfected"]
    return sig[m]


# --------------------------------------------------------------------------- paths
def random_signals(prep: dict, min_dd: float, perfected: bool, dd_lookback: int, rng) -> dict:
    """Placebo signals: for each instrument, as many random bars as it has real (filtered)
    setup-9s, drawn from bars in the same sell-off state (drawdown <= -min_dd). The signal
    candle is the random bar itself. Isolates the DeMark timing from 'just buy a dip'."""
    from .demark import atr as _atr

    out = {}
    for t, x in prep.items():
        n = len(filter_signals(x["signals"], min_dd, perfected))
        b = x["bars"]
        if n == 0:
            out[t] = x["signals"].iloc[0:0]
            continue
        dd = b["Close"] / b["Close"].rolling(dd_lookback, min_periods=max(20, dd_lookback // 4)).max() - 1
        cand = np.flatnonzero((dd <= -min_dd).to_numpy() & (np.arange(len(b)) >= 20))
        pick = np.sort(rng.choice(cand, size=min(n, len(cand)), replace=False))
        a = _atr(b).to_numpy()
        tdst = b["High"].rolling(9).max().to_numpy()
        pos_map = pd.Series(np.arange(len(x["dates"])), index=x["dates"])
        df = pd.DataFrame({"date": b.index[pick], "high": b["High"].to_numpy()[pick], "low": b["Low"].to_numpy()[pick],
                           "close": b["Close"].to_numpy()[pick], "atr": a[pick], "tdst": tdst[pick],
                           "drawdown": dd.to_numpy()[pick], "perfected": True})
        df["s0"] = pos_map.reindex(df["date"]).to_numpy().astype(int)
        out[t] = df
    return out


def run_paths(prep: dict, min_dd: float, perfected: bool, p: PathParams,
              signals_override: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate every filtered signal independently with the max number of attempts.
    Returns (attempts, sequences)."""
    att_rows, seq_rows = [], []
    for t, x in prep.items():
        if signals_override is not None:
            sig = signals_override[t]
        else:
            sig = filter_signals(x["signals"], min_dd, perfected)
        if sig.empty:
            continue
        s0s = sig["s0"].to_numpy()
        for j, r in enumerate(sig.itertuples(index=False)):
            kill = set(s0s[j + 1:].tolist())
            atts, end, status = simulate_sequence(x["O"], x["H"], x["L"], x["C"], int(r.s0), r.high, r.low,
                                                  r.atr, r.tdst, kill, p)
            # end position if the sequence were capped at m re-entries (m = 0..5)
            ends = [atts[m]["exit_pos"] if len(atts) > m and atts[m]["reason"] == "stop" else end
                    for m in range(MAX_ATTEMPTS)]
            seq_rows.append({"ticker": t, "sig_date": r.date, "s0": int(r.s0), "end": end, "status": status,
                             "n_att": len(atts), "drawdown": r.drawdown, "perfected": r.perfected,
                             **{f"end_m{m}": ends[m] for m in range(MAX_ATTEMPTS)}})
            for a in atts:
                a = dict(a)
                a.update(ticker=t, sig_date=r.date, s0=int(r.s0),
                         entry_date=x["dates"][a["entry_pos"]], exit_date=x["dates"][a["exit_pos"]])
                att_rows.append(a)
    return pd.DataFrame(att_rows), pd.DataFrame(seq_rows)


def select_sequences(seqs: pd.DataFrame, m: int) -> pd.DataFrame:
    """One sequence at a time per instrument: a signal is taken only if the previous taken
    sequence (capped at m re-entries) has ended."""
    if seqs.empty:
        return seqs
    keep = []
    col = f"end_m{m}"
    for t, g in seqs.sort_values("s0").groupby("ticker", sort=False):
        last_end = -1
        for idx, s0, e in zip(g.index, g["s0"], g[col]):
            if s0 >= last_end:
                keep.append(idx)
                last_end = e
    return seqs.loc[keep]


def apply_sizing(atts: pd.DataFrame, seqs_sel: pd.DataFrame, m: int, scheme: str, acct: Account) -> pd.DataFrame:
    """Attach effective size weights (with notional cap) and $ PnL to selected attempts."""
    if atts.empty or seqs_sel.empty:
        return atts.iloc[0:0].assign(w=[], pnl_R=[], pnl=[], capped=[])
    key = seqs_sel[["ticker", "s0"]]
    a = atts[atts["k"] <= m].merge(key, on=["ticker", "s0"], how="inner")
    w = np.asarray(SIZE_SCHEMES[scheme])[a["k"].to_numpy()]
    risk_usd = acct.base_risk * acct.capital
    w_cap = acct.notional_cap * acct.capital * a["dist"].to_numpy() / (a["entry_px"].to_numpy() * risk_usd)
    w_eff = np.minimum(w, w_cap)
    a = a.assign(w=w_eff, capped=w_eff < w, pnl_R=w_eff * a["R"].to_numpy())
    a["pnl"] = a["pnl_R"] * risk_usd
    a["qty"] = risk_usd * a["w"] / a["dist"]
    return a


# --------------------------------------------------------------------------- metrics
def metrics(a: pd.DataFrame, years: float) -> dict:
    """Metrics in R units (1R = base risk of the first attempt) on realized PnL."""
    if a.empty:
        return {"n_seq": 0}
    seq = a.groupby(["ticker", "s0"]).agg(pnl_R=("pnl_R", "sum"), n_att=("k", "size"),
                                          last_exit=("exit_date", "max"))
    wins, losses = seq.loc[seq.pnl_R > 0, "pnl_R"].sum(), -seq.loc[seq.pnl_R < 0, "pnl_R"].sum()
    cum = a.sort_values("exit_date")["pnl_R"].cumsum().to_numpy()
    peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
    max_dd = float((peak - cum).max()) if len(cum) else 0.0
    total = float(seq.pnl_R.sum())
    return {
        "n_seq": len(seq),
        "n_att": len(a),
        "seq_win%": 100.0 * float((seq.pnl_R > 0).mean()),
        "avg_R_seq": float(seq.pnl_R.mean()),
        "total_R": total,
        "R_per_yr": total / years,
        "PF": float(wins / losses) if losses > 0 else np.inf,
        "maxDD_R": max_dd,
        "MAR": (total / years) / max_dd if max_dd > 0 else np.inf,
        "worst_seq_R": float(seq.pnl_R.min()),
        "best_seq_R": float(seq.pnl_R.max()),
        "capped%": 100.0 * float(a["capped"].mean()) if "capped" in a else 0.0,
    }


def by_attempt(a: pd.DataFrame) -> pd.DataFrame:
    """Expectancy of attempt k in R of its OWN risk (size-independent)."""
    g = a.groupby("k")
    return pd.DataFrame({
        "n": g.size(),
        "win%": g["R"].apply(lambda r: 100 * (r > 0).mean()),
        "avg_R_own_risk": g["R"].mean(),
        "stopped%": g["reason"].apply(lambda r: 100 * (r == "stop").mean()),
        "target%": g["reason"].apply(lambda r: 100 * (r == "target").mean()),
        "time%": g["reason"].apply(lambda r: 100 * (r == "time").mean()),
        "avg_w": g["w"].mean() if "w" in a else np.nan,
        "pnl_R_total": g["pnl_R"].sum() if "pnl_R" in a else np.nan,
    })


def daily_equity(a: pd.DataFrame, prep: dict, acct: Account, cost_bps: float) -> pd.DataFrame:
    """Daily mark-to-market portfolio PnL ($) and gross exposure from sized attempts."""
    pnl_parts, expo_parts = [], []
    cost = cost_bps / 1e4
    for t, g in a.groupby("ticker"):
        x = prep[t]
        C = np.asarray(x["C"])
        n = len(C)
        pnl = np.zeros(n)
        expo = np.zeros(n)
        for r in g.itertuples(index=False):
            e, xp, q = r.entry_pos, r.exit_pos, r.qty
            if xp == e:
                pnl[e] += q * (r.exit_px - r.entry_px)
            else:
                pnl[e] += q * (C[e] - r.entry_px)
                if xp - e > 1:
                    pnl[e + 1:xp] += q * np.diff(C[e:xp])
                pnl[xp] += q * (r.exit_px - C[xp - 1])
            pnl[e] -= q * r.entry_px * cost
            pnl[xp] -= q * r.exit_px * cost
            expo[e:xp] += q * C[e:xp]
        pnl_parts.append(pd.Series(pnl, index=x["dates"], name=t))
        expo_parts.append(pd.Series(expo, index=x["dates"], name=t))
    pnl = pd.concat(pnl_parts, axis=1).fillna(0.0).sum(axis=1)
    expo = pd.concat(expo_parts, axis=1).fillna(0.0).sum(axis=1)
    eq = acct.capital + pnl.cumsum()
    return pd.DataFrame({"pnl": pnl, "equity": eq, "gross_expo_x": expo / acct.capital})


def equity_stats(eq: pd.DataFrame, acct: Account) -> dict:
    e = eq["equity"]
    years = (e.index[-1] - e.index[0]).days / 365.25
    peak = e.cummax()
    dd = e - peak
    r = eq["pnl"] / acct.capital
    return {
        "total_pnl_$": float(e.iloc[-1] - acct.capital),
        "pnl_per_yr_$": float((e.iloc[-1] - acct.capital) / years),
        "ret_per_yr_%_of_capital": 100 * float((e.iloc[-1] - acct.capital) / years / acct.capital),
        "max_dd_$": float(dd.min()),
        "max_dd_%_of_capital": 100 * float(dd.min() / acct.capital),
        "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else np.nan,
        "max_gross_expo_x": float(eq["gross_expo_x"].max()),
        "avg_gross_expo_x": float(eq["gross_expo_x"].mean()),
    }


def cap_concurrent(seqs_sel: pd.DataFrame, prep: dict, m: int, max_open: int | None) -> pd.DataFrame:
    """Portfolio-level limit: at most `max_open` live sequences across all instruments
    (first come, first served by signal date). Limits correlated sell-off clusters (2008)."""
    if max_open is None or seqs_sel.empty:
        return seqs_sel
    s = seqs_sel.copy()
    s["end_date"] = [prep[t]["dates"][e] for t, e in zip(s["ticker"], s[f"end_m{m}"])]
    s = s.sort_values("sig_date")
    keep, active = [], []
    for idx, d0, d1 in zip(s.index, s["sig_date"], s["end_date"]):
        active = [e for e in active if e > d0]
        if len(active) < max_open:
            keep.append(idx)
            active.append(d1)
    return seqs_sel.loc[keep]


def buy_and_hold(prep: dict, start="1990-01-01") -> pd.DataFrame:
    """Equal-weight, daily-rebalanced buy & hold of every instrument available that day."""
    rets = pd.concat([pd.Series(x["C"], index=x["dates"]).pct_change().rename(t) for t, x in prep.items()], axis=1)
    rets = rets[rets.index >= start]
    r = rets.mean(axis=1, skipna=True).fillna(0.0)
    eq = (1 + r).cumprod()
    return pd.DataFrame({"ret": r, "equity": eq})
