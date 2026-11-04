"""Fast (numpy) aggregation of one path simulation over all (max re-entries x size scheme)
combinations and over the in-sample / out-of-sample / full periods. Used by the optimizer."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import SIZE_SCHEMES, SPLIT_DATE, Account
from .engine import MAX_ATTEMPTS

PERIODS = {
    "IS": (pd.Timestamp("1990-01-01"), SPLIT_DATE),
    "OOS": (SPLIT_DATE, pd.Timestamp("2100-01-01")),
    "FULL": (pd.Timestamp("1990-01-01"), pd.Timestamp("2100-01-01")),
}


def _years(start, end, data_end):
    end = min(end, data_end)
    return (end - start).days / 365.25


def _select(seqs: pd.DataFrame, m: int) -> np.ndarray:
    col = f"end_m{m}"
    keep = np.zeros(len(seqs), dtype=bool)
    tick = seqs["ticker"].to_numpy()
    s0 = seqs["s0"].to_numpy()
    end = seqs[col].to_numpy()
    last = {}
    for i in range(len(seqs)):  # seqs sorted by (ticker, s0)
        if s0[i] >= last.get(tick[i], -1):
            keep[i] = True
            last[tick[i]] = end[i]
    return keep


def aggregate_all(atts: pd.DataFrame, seqs: pd.DataFrame, acct: Account, data_end: pd.Timestamp) -> list[dict]:
    out = []
    if atts.empty:
        return out
    seqs = seqs.sort_values(["ticker", "s0"]).reset_index(drop=True)
    seq_id = {(t, s): i for i, (t, s) in enumerate(zip(seqs["ticker"], seqs["s0"]))}
    a = atts.sort_values("exit_date").reset_index(drop=True)
    sid = np.array([seq_id[(t, s)] for t, s in zip(a["ticker"], a["s0"])])
    k = a["k"].to_numpy()
    R = a["R"].to_numpy()
    risk_usd = acct.base_risk * acct.capital
    w_cap = acct.notional_cap * acct.capital * a["dist"].to_numpy() / (a["entry_px"].to_numpy() * risk_usd)
    sig_date = seqs["sig_date"].to_numpy()
    nseq = len(seqs)

    for m in range(MAX_ATTEMPTS):
        keep_seq = _select(seqs, m)
        base_mask = keep_seq[sid] & (k <= m)
        for scheme, wts in SIZE_SCHEMES.items():
            if m == 0 and scheme != "flat":
                continue  # identical to flat
            w = np.minimum(np.asarray(wts)[k], w_cap)
            pnl = w * R
            for pname, (p0, p1) in PERIODS.items():
                in_p = (sig_date >= np.datetime64(p0)) & (sig_date < np.datetime64(p1))
                mask = base_mask & in_p[sid]
                if not mask.any():
                    continue
                seq_pnl = np.bincount(sid[mask], weights=pnl[mask], minlength=nseq)
                traded = np.bincount(sid[mask], minlength=nseq) > 0
                taken = keep_seq & in_p & traded  # sequences that actually got filled
                sp = seq_pnl[taken]
                cum = np.cumsum(pnl[mask])
                peak = np.maximum.accumulate(np.concatenate([[0.0], cum]))[1:]
                maxdd = float((peak - cum).max())
                yrs = _years(p0, p1, data_end)
                tot = float(sp.sum())
                gw, gl = sp[sp > 0].sum(), -sp[sp < 0].sum()
                out.append({
                    "m": m, "scheme": scheme, "period": pname,
                    "n_seq": int(taken.sum()), "n_att": int(mask.sum()),
                    "seq_win%": 100 * float((sp > 0).mean()),
                    "avg_R_seq": float(sp.mean()),
                    "total_R": tot, "R_per_yr": tot / yrs,
                    "PF": float(gw / gl) if gl > 0 else np.inf,
                    "maxDD_R": maxdd,
                    "MAR": (tot / yrs) / maxdd if maxdd > 0 else np.inf,
                    "worst_seq_R": float(sp.min()),
                })
    return out
