import numpy as np
import pandas as pd
import pytest

from strategy.demark import buy_setup_signals, td_buy_setup_count
from strategy.engine import PathParams, simulate_sequence


def test_buy_setup_counts_nine_consecutive_lower_closes():
    close = pd.Series([106, 107, 108, 109, 110] + [100 - i for i in range(11)], dtype=float)
    cnt = td_buy_setup_count(close)
    assert cnt.max() == 11
    assert int(np.flatnonzero(cnt.to_numpy() == 9)[0]) == 13
    df = pd.DataFrame({"Open": close, "High": close + 1, "Low": close - 1, "Close": close})
    sig = buy_setup_signals(df, dd_lookback=20)
    assert len(sig) == 1 and sig.iloc[0]["pos"] == 13
    assert sig.iloc[0]["tdst"] == pytest.approx(close.iloc[5:14].max() + 1)


def _run(bars, p, hi=110.0, lo=100.0):
    O, H, L, C = (list(map(float, x)) for x in zip(*([(0, 0, 0, 0)] + bars)))
    return simulate_sequence(O, H, L, C, 0, hi, lo, 10.0, 130.0, set(), p)


def test_stop_reentry_and_target():
    p = PathParams(entry_mode="next_open", buf=0.0, target="R2", time_stop=50, window=50, cost_bps=0.0)
    bars = [
        (105, 106, 99, 100),    # enter 105 at open, stopped at 100 (low 99)
        (100, 111, 99.5, 108),  # re-entry buy-stop at 110 hit
        (108, 131, 107, 130),   # target 110 + 2*(110-100) = 130 hit
    ]
    atts, end, status = _run(bars, p)
    assert [a["reason"] for a in atts] == ["stop", "target"]
    assert atts[0]["entry_px"] == 105 and atts[0]["exit_px"] == 100
    assert atts[0]["R"] == pytest.approx(-1.0)
    assert atts[1]["entry_px"] == 110 and atts[1]["exit_px"] == 130
    assert atts[1]["R"] == pytest.approx(2.0)
    assert status == "done" and end == 3


def test_gap_through_stop_fills_at_open_and_max_attempts():
    p = PathParams(entry_mode="break_high", buf=0.0, target="R2", time_stop=50, window=50, cost_bps=0.0)
    bars = [(111, 112, 109, 111), (95, 96, 94, 95)]  # gap entry at 111, then gap below stop at 95
    atts, _, _ = _run(bars, p)
    assert atts[0]["entry_px"] == 111 and atts[0]["exit_px"] == 95
    assert atts[0]["R"] == pytest.approx((95 - 111) / 10)  # sized off planned entry 110
    # whipsaw forever -> stops after 6 attempts (1 initial + 5 re-entries)
    bars = [(105, 111, 104, 109), (109, 109.5, 99, 100)] * 10
    atts, _, status = _run(bars, p)
    assert len(atts) == 6 and status == "done"


def test_reentry_window_expires():
    p = PathParams(entry_mode="next_open", buf=0.0, target="R2", time_stop=50, window=3, cost_bps=0.0)
    bars = [(105, 106, 99, 100)] + [(98, 99, 97, 98)] * 5
    atts, end, status = _run(bars, p)
    assert len(atts) == 1 and status == "expired" and end == 3


def test_one_campaign_at_a_time():
    from strategy.backtest import select_one_campaign
    D = pd.Timestamp
    seqs = pd.DataFrame({
        "ticker": ["A", "B", "C", "D", "E"],
        "s0": [1, 1, 1, 1, 1],
        # B fills while A is live -> skipped; C and D fill the same day after A ends -> deeper wins;
        # E never fills -> ignored
        "first_entry_date": [D("2020-01-02"), D("2020-01-10"), D("2020-03-02"), D("2020-03-02"), pd.NaT],
        "end_date_m5": [D("2020-02-28"), D("2020-04-01"), D("2020-05-01"), D("2020-06-01"), D("2020-03-05")],
        "drawdown": [-0.10, -0.20, -0.05, -0.15, -0.30],
    })
    sel = select_one_campaign(seqs, 5, "deepest_dd")
    assert sel["ticker"].tolist() == ["A", "D"]
    sel = select_one_campaign(seqs, 5, "shallowest_dd")
    assert sel["ticker"].tolist() == ["A", "C"]


def test_oldhigh_target_no_time_stop_and_reanchor():
    from strategy.engine import NO_LIMIT
    p = PathParams(entry_mode="next_open", buf=0.0, target="oldhigh", time_stop=NO_LIMIT, window=NO_LIMIT,
                   cost_bps=0.0, max_attempts=11, near=0.0, on_new9="continue")
    O, H, L, C = (list(map(float, x)) for x in zip(*([(0, 0, 0, 0)] + [
        (105, 106, 99, 100),     # 1: enter 105, stopped at 100
        (100, 104, 90, 92),      # 2: flat, keeps falling
        (92, 95, 88, 94),        # 3
        (94, 111, 93, 110),      # 4: re-entry above 110 (attempt 2)
        (110, 140, 109, 135),    # 5: reaches old high 130 -> flat, campaign ends
    ])))
    atts, end, status = simulate_sequence(O, H, L, C, 0, 110.0, 100.0, 10.0, 120.0, set(), p, old_high=130.0)
    assert [a["reason"] for a in atts] == ["stop", "target"] and atts[-1]["exit_px"] == 130.0
    assert status == "done" and end == 5
    # re-anchor: a new 9 on day 3 (high 96, low 88) moves the re-entry trigger down to 96
    p2 = PathParams(**{**p.__dict__, "on_new9": "reanchor"})
    atts, _, _ = simulate_sequence(O, H, L, C, 0, 110.0, 100.0, 10.0, 120.0, {3}, p2, old_high=130.0,
                                   reanchor={3: (96.0, 88.0, 10.0)})
    assert atts[1]["entry_px"] == 96.0 and atts[1]["reason"] == "target"
    # already at the old high -> nothing to play
    atts, _, status = simulate_sequence(O, H, L, C, 0, 110.0, 100.0, 10.0, 120.0, set(), p, old_high=104.0)
    assert atts == [] and status == "at_high"


def test_grid_starting_size_and_flat_at_target():
    from strategy.grid import grid_levels_needed, simulate_grid
    T, step = 110.0, 0.01
    j0 = grid_levels_needed(100.0, T, step)
    assert T * 0.99 ** j0 <= 100.0 < T * 0.99 ** (j0 - 1)      # 10 steps of 1% from 100 to 110
    O, H, L, C = (list(map(float, x)) for x in zip(*([(0, 0, 0, 0)] + [
        (100, 100.5, 97, 98),    # entry 100: j0 units, then 2-3 more bought on the way to 97
        (98, 104, 97.5, 103),    # sells on the way up
        (103, 112, 102, 111),    # reaches 110 -> position 0
    ])))
    r = simulate_grid(O, H, L, C, 0, T, step, 1000.0, cost_bps=0.0)
    assert r["status"] == "target" and r["j0"] == j0 and r["end"] == 3
    assert r["max_units"] > j0 and r["qty"][-1] == pytest.approx(0.0, abs=1e-9)
    assert r["pnl"] > 0
    # never reaching the target -> campaign stays open, losses are unrealised
    O2, H2, L2, C2 = (list(map(float, x)) for x in zip(*([(0, 0, 0, 0)] + [(100, 100, 80, 80), (80, 81, 60, 60)])))
    r2 = simulate_grid(O2, H2, L2, C2, 0, T, step, 1000.0, cost_bps=0.0)
    assert r2["status"] == "open" and r2["pnl"] < 0 and r2["max_units"] >= j0 + 45


def _bars(rows):
    O, H, L, C = (np.asarray(list(map(float, x))) for x in zip(*rows))
    n = len(C)
    return {"O": O, "H": H, "L": L, "C": C, "dates": np.datetime64("2020-01-01") + np.arange(n),
            "macd": np.ones(n), "wk_close": np.zeros(n, bool)}


def test_macd_engine_sl_reentry_and_level_tp():
    from strategy.macd_engine import simulate_campaign
    x = _bars([(100, 100.5, 98.5, 99), (99, 100.2, 98, 100), (100, 111, 99.5, 110)])
    r = simulate_campaign(x, 0, mode="sl_reentry", tp_days=None, tp_level=0.10, sl=0.01, cost=0.0)
    assert r["stops"] == 1 and r["reason"] == "level TP" and r["end"] == 2
    assert r["ret"] == pytest.approx(-0.01 + 0.10, abs=1e-9)      # -1 % stop, then +10 % from E0


def test_macd_engine_ladder_martingale_and_macd_stop():
    from strategy.macd_engine import simulate_campaign
    x = _bars([(100, 100, 97.5, 98), (98, 98, 96, 97), (95, 96, 94, 95)])
    x["wk_close"][1] = True
    x["macd"][1] = -0.5                                             # MACD < 0 at bar 1's weekly close
    r = simulate_campaign(x, 0, mode="ladder", tp_days=None, tp_level=None, step=0.01, K=5, sizing="mart", cost=0.0)
    assert r["reason"] == "MACD < 0" and r["end"] == 2
    assert r["fills"] == 5                                          # 100, 99, 98.01, 97.03, 96.06


def test_macd_engine_pyramid_up():
    from strategy.macd_engine import simulate_campaign
    x = _bars([(100, 101.5, 99.5, 101), (101, 103.5, 100.5, 103), (103, 103, 98, 99)])
    x["wk_close"][2] = True
    x["macd"][2] = -1.0
    r = simulate_campaign(x, 0, mode="pyramid", tp_days=None, tp_level=None, step=0.01, K=10, cost=0.0)
    # units at 100, 101, 102.01, 103.03 -> 4 of 11 units, all out at the next open after the MACD < 0 close
    assert r["fills"] == 4 and r["reason"] == "open"
    assert r["notional"][1] == pytest.approx((1 / 11) * 103 * (1 / 100 + 1 / 101 + 1 / 102.01 + 1 / 103.0301), rel=1e-9)


def test_macd_engine_regime_exit():
    from strategy.macd_engine import simulate_campaign
    x = _bars([(100, 101, 99, 100), (100, 102, 99, 101), (101, 103, 100, 102), (102, 104, 101, 103)])
    x["exit_flag"] = np.array([False, True, False, False, False])   # regime off at bar 1's close
    r = simulate_campaign(x, 0, mode="base", tp_days=None, tp_level=None, cost=0.0)
    assert r["reason"] == "regime" and r["end"] == 2
    assert r["ret"] == pytest.approx(101 / 100 - 1)                 # out at bar 2's open
