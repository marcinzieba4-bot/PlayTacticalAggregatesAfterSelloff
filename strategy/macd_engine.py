"""Campaign engine for the weekly-MACD strategy (no DeMark).

A campaign starts at the open after the weekly close where MACD and signal both turn > 0,
at price E0, and ends at the first of:
  * MACD stop   : a weekly close with the MACD line < 0 -> everything out at the next open
  * time TP     : first open on/after start + tp_days  -> everything out at that open
  * level TP    : price reaches the target (see modes)  -> everything out at the target
  * data end    : marked to the last close ("open")

Modes (position sizes are fractions of the campaign budget = 1.0):
  base        : buy 1.0 at E0, hold.                        level TP = E0 * (1 + tp_level)
  sl_reentry  : buy 1.0 at E0; stop at E0 * (1 - sl); after a stop, buy 1.0 again on a
                buy-stop at E0 (the first entry point), any number of times.
                                                            level TP = E0 * (1 + tp_level)
  pyramid     : pyramiding UP: 1 unit at E0, then +1 unit on a buy-stop every `step` above E0
                (levels U_k = E0 * (1 + step)^k, k = 1..K); K+1 equal units = 1.0 (no leverage).
                No price stop (only the MACD stop).              level TP = E0 * (1 + tp_level)
  ladder      : buy-limits every `step` below E0: levels L_k = E0 * (1 - step)^k, k = 0..K,
                size w_k (flat: 1, martingale: 2^k) scaled so that the full ladder = 1.0
                (no leverage). No price stop (only the MACD stop).
                                                            level TP = average cost * (1 + tp_level)

Execution on daily bars along O->H->L->C or O->L->H->C (nearest extreme first); orders gapped
through at the open fill at the open. Costs per side on notional.
Returns the campaign's cumulative PnL path per bar (budget = 1) and its notional path.
"""
from __future__ import annotations

import numpy as np


def simulate_campaign(x, e, mode="base", tp_days=365, tp_level=None, sl=0.01, step=0.01, K=5,
                      sizing="mart", cost=3e-4):
    O, H, L, C, dates = x["O"], x["H"], x["L"], x["C"], x["dates"]
    macd, wkc = x["macd"], x["wk_close"]
    exit_flag = x.get("exit_flag")  # optional bool array: True at a close -> close the campaign at the next open
    reentry_ok = x.get("reentry_ok")  # optional bool array: re-entries (sl_reentry) only if True at the previous close
    n = len(C)
    E0 = O[e]
    t_end = dates[e] + np.timedelta64(int(tp_days), "D") if tp_days else None
    qty = 0.0
    cash = 0.0
    cost_basis = 0.0  # $ spent on the open position (for average cost)
    pnl_path, notional_path = [], []
    fills = stops = 0

    def buy(px, frac):
        nonlocal qty, cash, cost_basis, fills
        q = frac / px
        qty += q
        cash -= q * px * (1 + cost)
        cost_basis += q * px
        fills += 1

    def sell_all(px):
        nonlocal qty, cash, cost_basis
        cash += qty * px * (1 - cost)
        qty = 0.0
        cost_basis = 0.0

    # ladder / pyramid setup
    if mode == "pyramid":
        w = np.full(K + 1, 1.0 / (K + 1))
        levels = E0 * (1 + step) ** np.arange(K + 1)
        next_k = 1
        buy(E0, w[0])
    elif mode == "ladder":
        w = np.array([2.0 ** k if sizing == "mart" else 1.0 for k in range(K + 1)])
        w = w / w.sum()
        levels = E0 * (1 - step) ** np.arange(K + 1)
        next_k = 1
        buy(E0, w[0])
    else:
        buy(E0, 1.0)
    stop_px = E0 * (1 - sl) if mode == "sl_reentry" else None
    in_pos = True

    def target():
        if tp_level is None or not in_pos:
            return None
        if mode == "ladder":
            return (cost_basis / qty) * (1 + tp_level)
        return E0 * (1 + tp_level)

    reason = "open"
    i = e
    while i < n:
        o, h, l, c = O[i], H[i], L[i], C[i]
        done = False
        # --- at the open: time TP / MACD stop decided at the previous close, gaps
        if i > e:
            if t_end is not None and dates[i] >= t_end:
                if in_pos:
                    sell_all(o)
                reason, done = "time TP", True
            elif wkc[i - 1] and macd[i - 1] < 0:
                if in_pos:
                    sell_all(o)
                reason, done = "MACD < 0", True
            elif exit_flag is not None and exit_flag[i - 1]:  # external regime exit, decided at the previous close
                if in_pos:
                    sell_all(o)
                reason, done = "regime", True
            else:
                T = target()
                if in_pos and T is not None and o >= T:
                    sell_all(o)
                    reason, done = "level TP", True
                elif mode == "sl_reentry":
                    if in_pos and o <= stop_px:
                        sell_all(o)
                        in_pos, stops = False, stops + 1
                    elif not in_pos and o >= E0 and (reentry_ok is None or reentry_ok[i - 1]):
                        buy(o, 1.0)
                        in_pos = True
                elif mode == "ladder":
                    while next_k <= K and o <= levels[next_k]:
                        buy(o, w[next_k])
                        next_k += 1
                elif mode == "pyramid":
                    while next_k <= K and o >= levels[next_k]:
                        buy(o, w[next_k])
                        next_k += 1
        # --- intrabar path
        if not done:
            pts = (o, h, l, c) if (h - o) < (o - l) else (o, l, h, c)
            for a, b in zip(pts[:-1], pts[1:]):
                if b > a:  # up-leg: re-entry buy-stop, then level TP
                    lo_ = a
                    if mode == "sl_reentry" and not in_pos and lo_ < E0 <= b and (reentry_ok is None or reentry_ok[i - 1]):
                        buy(E0, 1.0)
                        in_pos, lo_ = True, E0
                    if mode == "pyramid":
                        T0 = target()
                        while next_k <= K and lo_ < levels[next_k] <= b and (T0 is None or levels[next_k] < T0):
                            buy(levels[next_k], w[next_k])
                            next_k += 1
                    T = target()
                    if in_pos and T is not None and lo_ < T <= b:
                        sell_all(T)
                        reason, done = "level TP", True
                        break
                elif b < a:  # down-leg: 1% stop or ladder buys
                    if mode == "sl_reentry" and in_pos and b <= stop_px < a:
                        sell_all(stop_px)
                        in_pos, stops = False, stops + 1
                    elif mode == "ladder":
                        while next_k <= K and b <= levels[next_k] < a:
                            buy(levels[next_k], w[next_k])
                            next_k += 1
        pnl_path.append(cash + qty * c)
        notional_path.append(qty * c)
        if done:
            break
        i += 1
    end = min(i, n - 1)
    if reason == "open":
        end = n - 1
    return {"end": end, "reason": reason, "pnl": np.asarray(pnl_path), "notional": np.asarray(notional_path),
            "fills": fills, "stops": stops, "ret": float(pnl_path[-1]) if pnl_path else 0.0}
