"""Grid-search the DeMark-9 stop / re-entry strategy on weekly and daily setups.

Usage:  python scripts/optimize.py [W|D|both]
Writes results/grid_<tf>.csv (one row per config x period).
"""
from __future__ import annotations

import itertools
import os
import sys
import time
from multiprocessing import Pool

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.backtest import Account, prepare, run_paths  # noqa: E402
from strategy.engine import PathParams  # noqa: E402
from strategy.fastagg import aggregate_all  # noqa: E402

DATA_CUTOFF = os.environ.get("DATA_CUTOFF", "2026-11-04")  # drop the still-forming bar
RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

GRIDS = {
    "W": dict(min_dd=[0.0, 0.05, 0.10, 0.15, 0.20], perfected=[False, True],
              entry_mode=["next_open", "break_high"], buf=[0.0, 0.1, 0.25, 0.5],
              target=["R1", "R1.5", "R2", "R3", "tdst", "none"],
              time_stop=[40, 65, 130], window=[20, 65, 130]),
    "D": dict(min_dd=[0.0, 0.03, 0.05, 0.10, 0.15], perfected=[False, True],
              entry_mode=["next_open", "break_high"], buf=[0.0, 0.1, 0.25, 0.5],
              target=["R1", "R1.5", "R2", "R3", "tdst", "none"],
              time_stop=[5, 10, 20], window=[5, 10, 20]),
}

_PREP = None
_DATA_END = None


def _init(tf):
    global _PREP, _DATA_END
    _PREP = prepare(tf, drop_after=DATA_CUTOFF)
    _DATA_END = max(x["dates"][-1] for x in _PREP.values())


def _work(cfg):
    min_dd, perfected, entry_mode, buf, target, time_stop, window = cfg
    p = PathParams(entry_mode=entry_mode, buf=buf, target=target, time_stop=time_stop, window=window)
    atts, seqs = run_paths(_PREP, min_dd, perfected, p)
    rows = aggregate_all(atts, seqs, Account(), _DATA_END)
    base = dict(min_dd=min_dd, perfected=perfected, entry_mode=entry_mode, buf=buf,
                target=target, time_stop=time_stop, window=window)
    return [{**base, **r} for r in rows]


def run(tf):
    g = GRIDS[tf]
    cfgs = list(itertools.product(*g.values()))
    print(f"[{tf}] {len(cfgs)} path configs x (re-entries 0..5 x size schemes) ...", flush=True)
    t0 = time.time()
    rows = []
    with Pool(os.cpu_count(), initializer=_init, initargs=(tf,)) as pool:
        for i, r in enumerate(pool.imap_unordered(_work, cfgs, chunksize=8)):
            rows.extend(r)
            if (i + 1) % 500 == 0:
                print(f"  {i + 1}/{len(cfgs)}  {time.time() - t0:.0f}s", flush=True)
    df = pd.DataFrame(rows)
    os.makedirs(RESULTS, exist_ok=True)
    df.to_csv(os.path.join(RESULTS, f"grid_{tf}.csv.gz"), index=False, compression="gzip")
    print(f"[{tf}] done: {len(df)} rows in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    for tf in (["W", "D"] if which == "both" else [which]):
        run(tf)
