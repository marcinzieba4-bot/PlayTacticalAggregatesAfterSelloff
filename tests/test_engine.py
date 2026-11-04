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
