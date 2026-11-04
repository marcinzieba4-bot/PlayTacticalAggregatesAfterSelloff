"""Trade engine: DeMark-9 signal candle -> stop below its low, re-entry above its high,
up to 5 re-entries with increasing size.

Execution is always simulated on DAILY bars (also for weekly signals), walking each
day along an O->H->L->C or O->L->H->C path (whichever extreme is nearer the open is
visited first). Stop/entry orders that are gapped through fill at the open.

Per signal ("sequence"):
  E = high(signal candle) + buf*ATR      re-entry buy-stop
  S = low(signal candle)  - buf*ATR      protective sell-stop (fixed for all attempts)
  attempt 0  : entry_mode "next_open"  -> buy next day's open (if it is above S)
               entry_mode "break_high" -> buy-stop at E (confirmation entry)
  stop-out   : wait for price to trade back above E -> re-enter (attempt k+1)
  exit       : profit target (k*R or TDST), or time stop, or stop-loss
  sequence ends on a winning/time exit, when attempts are exhausted, when the
  re-entry window expires while flat, or when a newer buy-setup 9 appears while flat.

Each attempt's result is stored in R of *its own* risk (R = (exit-entry-costs)/(entry-S)),
so any position-size progression can be applied afterwards without re-simulating.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

MAX_ATTEMPTS = 6  # initial entry + 5 re-entries


@dataclass(frozen=True)
class PathParams:
    entry_mode: str = "next_open"   # "next_open" | "break_high"
    buf: float = 0.0                # buffer (x ATR of the signal timeframe) beyond high/low
    target: str = "R2"              # "R1.5" | "R2" | "R3" | "tdst" | "none"
    time_stop: int = 65             # max trading days in a position
    window: int = 65                # max trading days after signal to allow (re-)entries
    cost_bps: float = 3.0           # per side, commission + slippage, on notional

    def key(self):
        return tuple(asdict(self).values())


def _target_price(target: str, entry: float, stop: float, tdst: float):
    if target == "none":
        return None
    if target == "tdst":
        return tdst if tdst > entry + 0.5 * (entry - stop) else entry + 1.0 * (entry - stop)
    k = float(target[1:])
    return entry + k * (entry - stop)


def simulate_sequence(O, H, L, C, s0, sig_high, sig_low, sig_atr, tdst, kill_set, p: PathParams):
    """Simulate one signal. `s0` = daily index of the bar whose close completes the signal.
    `kill_set` = daily indices of later buy-setup-9s on this instrument; a new setup
    that completes while this sequence is flat (waiting to re-enter) replaces it.

    Returns (attempts, natural_end_pos, status) with attempts a list of dicts.
    """
    n = len(C)
    E = sig_high + p.buf * sig_atr
    S = sig_low - p.buf * sig_atr
    cost = p.cost_bps / 1e4
    attempts = []
    state = "WAIT"
    entry_px = entry_pos = T = None
    dist = None

    def open_pos(i, px, planned):
        nonlocal state, entry_px, entry_pos, T, dist
        state = "LONG"
        entry_px, entry_pos = px, i
        # size is fixed from the *planned* entry (gap fills cost extra); never size off a
        # stop tighter than 0.1 ATR (protects against degenerate candles / opens at the stop)
        dist = max(planned - S, 0.1 * sig_atr)
        T = _target_price(p.target, px, S, tdst)

    def close_pos(i, px, reason):
        nonlocal state
        r = (px - entry_px - cost * (px + entry_px)) / dist
        attempts.append({"k": len(attempts), "entry_pos": entry_pos, "entry_px": entry_px,
                         "exit_pos": i, "exit_px": px, "reason": reason, "dist": dist, "R": r})
        if reason == "stop":
            state = "WAIT" if len(attempts) < MAX_ATTEMPTS else "DONE"
        else:
            state = "DONE"

    i = s0 + 1
    if i >= n:
        return attempts, s0, "live"
    if p.entry_mode == "next_open" and O[i] > S:
        open_pos(i, O[i], O[i])

    while i < n:
        o, h, l, c = O[i], H[i], L[i], C[i]
        # --- open (gap) ---
        if state == "LONG" and not (entry_pos == i and entry_px == o):
            if o <= S:
                close_pos(i, o, "stop")
            elif T is not None and o >= T:
                close_pos(i, o, "target")
        if state == "WAIT" and o >= E:
            open_pos(i, o, E)
        # --- intrabar path ---
        pts = (o, h, l, c) if (h - o) < (o - l) else (o, l, h, c)
        prev = o
        for q in pts[1:]:
            if q > prev:  # up-leg: re-entry buy-stop, then profit target
                lo_ = prev
                if state == "WAIT" and lo_ < E <= q:
                    open_pos(i, E, E)
                    lo_ = E
                if state == "LONG" and T is not None and lo_ < T <= q:
                    close_pos(i, T, "target")
            elif q < prev:  # down-leg: protective stop
                if state == "LONG" and q <= S < prev:
                    close_pos(i, S, "stop")
            prev = q
        # --- end of day ---
        if state == "LONG" and i - entry_pos >= p.time_stop:
            close_pos(i, c, "time")
        if state == "WAIT":
            if i - s0 >= p.window:
                return attempts, i, "expired"
            if i in kill_set:
                return attempts, i, "superseded"
        if state == "DONE":
            return attempts, i, "done"
        i += 1

    if state == "LONG":  # still open at the end of data -> mark to last close
        close_pos(n - 1, C[n - 1], "open")
        return attempts, n - 1, "open"
    return attempts, n - 1, "waiting"
