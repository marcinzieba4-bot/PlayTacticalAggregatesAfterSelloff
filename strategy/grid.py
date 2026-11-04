"""Averaging-down grid ("martingale" without stop-loss) after a DeMark buy setup 9.

  * target T = sell-off low + RETR x (old high - sell-off low)        (RETR = 0.30)
  * grid levels L_j = T * (1 - step)^j, j = 0, 1, 2, ...              (step = 1 %)
  * position rule: hold n units  <=>  next sell at L_{n-1}, next buy at L_{n+1}
      - price falls through a level -> buy 1 unit (averaging down, no stop-loss)
      - price rises through a level -> sell 1 unit (the last one bought, LIFO)
      - at T (= L_0) the position is 0 and the campaign is over
  * starting size: at the signal we buy j0 units, j0 = number of 1 % steps from the entry
    price up to T, so that selling one unit per 1 % up-step reaches 0 exactly at T.
  * a unit is a fixed $ notional (e.g. 1 % of starting capital) at the price it is bought.

Execution on daily bars along O->H->L->C or O->L->H->C (nearest extreme first); levels gapped
through at the open fill at the open.
"""
from __future__ import annotations

import math

import numpy as np


def grid_levels_needed(entry: float, target: float, step: float) -> int:
    """Number of 1-step levels from entry up to the target (starting units)."""
    if entry >= target:
        return 0
    return max(1, math.ceil(math.log(entry / target) / math.log(1.0 - step) - 1e-12))


def simulate_grid(O, H, L, C, s0, target, step, unit_usd, cost_bps=3.0):
    """Run one campaign from the open after bar s0. Returns dict with fills, daily value path
    (cash + qty*close, from the entry bar to the end bar), status and summary numbers."""
    n_bars = len(C)
    i = s0 + 1
    if i >= n_bars:
        return {"status": "live", "fills": []}
    entry = O[i]
    j0 = grid_levels_needed(entry, target, step)
    if j0 == 0:
        return {"status": "at_target", "fills": []}
    cost = cost_bps / 1e4
    lvl = lambda j: target * (1.0 - step) ** j  # noqa: E731
    stack = []  # quantities bought, LIFO
    qty = 0.0
    cash = 0.0
    fills = []

    def buy(px, pos):
        nonlocal qty, cash
        q = unit_usd / px
        stack.append(q)
        qty += q
        cash -= q * px * (1 + cost)
        fills.append((pos, px, q))

    def sell(px, pos):
        nonlocal qty, cash
        q = stack.pop()
        qty -= q
        cash += q * px * (1 - cost)
        fills.append((pos, px, -q))

    for _ in range(j0):
        buy(entry, i)
    start = i
    values, qtys, units = [], [], []
    max_units, done = j0, False
    while i < n_bars:
        o, h, l, c = O[i], H[i], L[i], C[i]
        pts = (o, h, l, c) if (h - o) < (o - l) else (o, l, h, c)
        segs = [(a, b, False) for a, b in zip(pts[:-1], pts[1:])]
        if i > start:
            segs.insert(0, (C[i - 1], o, True))  # overnight gap: resting orders fill at the open
        for a, b, gap in segs:
            if b > a:  # up-leg: sell the last unit at L_{n-1}
                while stack and lvl(len(stack) - 1) <= b:
                    sell(b if gap else lvl(len(stack) - 1), i)
                if not stack:
                    done = True
                    break
            elif b < a:  # down-leg: buy one more unit at L_{n+1}
                while lvl(len(stack) + 1) >= b:
                    buy(b if gap else lvl(len(stack) + 1), i)
                max_units = max(max_units, len(stack))
        values.append(cash + qty * c)
        qtys.append(qty)
        units.append(len(stack))
        if done:
            break
        i += 1
    end = min(i, n_bars - 1)
    status = "target" if done else "open"
    vals = np.asarray(values)
    return {
        "status": status, "start": start, "end": end, "entry": entry, "target": target, "j0": j0,
        "fills": fills, "values": vals, "qty": np.asarray(qtys), "units": np.asarray(units),
        "pnl": float(vals[-1]), "max_units": int(max_units),
        "worst_open": float(vals.min()), "max_notional": float(max(u * unit_usd for u in units)) if units else 0.0,
    }
