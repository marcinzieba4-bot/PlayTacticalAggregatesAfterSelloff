"""Charts: point-in-time S&P study (results/sp500_pit/) and DM short leg (results/macd_short/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})


def ew(data):
    e = pd.DataFrame(data, columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    return e


def fmt_axis(ax, ticks):
    ax.set_yscale("log")
    ax.set_yticks(ticks)
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
    ax.xaxis.set_major_locator(mdates.YearLocator(4))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))


# 1) point-in-time vs survivorship-biased
P = json.load(open(os.path.join(ROOT, "results", "sp500_pit", "summary.json")))
U = json.load(open(os.path.join(ROOT, "results", "us100", "summary.json")))
fig, ax = plt.subplots(figsize=(11, 5.4), dpi=150)
for data, col, ls, lab in [
        (U["runs"]["base_3_365d_none"]["equity_weekly"], "#2a78d6", ":", "Today's top 100 (biased): MACD, max 3"),
        (P["runs"]["base_3"]["equity_weekly"], "#2a78d6", "-", "Point-in-time top 100: MACD, max 3"),
        (P["runs"]["sl1_reentry_20"]["equity_weekly"], "#eb6834", "-", "Point-in-time: 1% stop + re-entry, max 20"),
        (P["benchmarks"]["EW_top100_pit"]["equity_weekly"], MUTED, "--", "Equal-weight point-in-time top 100"),
        (P["benchmarks"]["SP500TR"]["equity_weekly"], INK2, "-.", "S&P 500 total return")]:
    e = ew(data)
    e = e[e.date >= "1997-01-01"]
    e["equity"] = e["equity"] / e["equity"].iloc[0] * 100
    y = (e.date.iloc[-1] - e.date.iloc[0]).days / 365.25
    cagr = 100 * ((e.equity.iloc[-1] / e.equity.iloc[0]) ** (1 / y) - 1)
    dd = 100 * (e.equity / e.equity.cummax() - 1).min()
    ax.plot(e.date, e.equity, color=col, ls=ls, lw=1.7 if ls == "-" else 1.4, label=f"{lab}  ({cagr:.1f}%/yr, DD {dd:.0f}%)")
fmt_axis(ax, [100, 300, 1000, 3000, 10000])
ax.set_ylabel("Equity, log (start \\$100k in 1997)")
ax.set_title("US stocks: removing survivorship bias with point-in-time S&P 500 membership (1997-2026)", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(ROOT, "results", "sp500_pit", "equity_pit.png"))

# 2) short leg on DM indices
Q = json.load(open(os.path.join(ROOT, "results", "macd_short", "summary.json")))
fig, ax = plt.subplots(figsize=(11, 5.4), dpi=150)
for key, col, ls, lab in [("long_DM_sl1_reentry_3", "#2a78d6", "-", "Long leg: MACD > 0, 1% stop + re-entry"),
                          ("short_DM_base_3", "#e34948", "-", "Short leg: MACD < 0, MACD stop"),
                          ("short_DM_sl1_reentry_3", "#eb6834", "-", "Short leg + 1% stop and re-entry"),
                          ("50/50 long+short (sl1_reentry)", "#1baf7a", "-", "50/50 long + short (both with 1% stop)")]:
    r = Q["runs"][key]
    e = ew(r["equity_weekly"])
    st = r["stats"]
    ax.plot(e.date, e.equity / 1000, color=col, ls=ls, lw=1.7,
            label=f"{lab}  ({st['cagr_%']:.1f}%/yr, DD {st['max_dd_%']:.0f}%, Sharpe {st['sharpe']:.2f})")
e = ew(Q["bh_dm"]["equity_weekly"])
ax.plot(e.date, e.equity / 1000, color=MUTED, ls="--", lw=1.4,
        label=f"Equal-weight DM indices buy & hold  ({Q['bh_dm']['cagr_%']:.1f}%/yr, DD {Q['bh_dm']['max_dd_%']:.0f}%)")
fmt_axis(ax, [20, 50, 100, 200, 500, 1000, 2000])
ax.set_ylabel("Equity, log (start \\$100k)")
ax.set_title("Weekly MACD on 16 DM indices, max 3 positions: long leg vs short leg", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(ROOT, "results", "macd_short", "equity_short.png"))
print("charts written")
