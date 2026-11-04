"""Chart for the averaging-down grid study (results/grid/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "grid")
S = json.load(open(os.path.join(RES, "summary.json")))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})
fig, axs = plt.subplots(2, 2, figsize=(12, 6.4), dpi=150, sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
for j, (tf, col, title) in enumerate([("W", "#2a78d6", "Weekly 9"), ("D", "#eb6834", "Daily 9")]):
    st = S["runs"][tf]["stats"]
    eq = pd.read_csv(os.path.join(RES, f"equity_{tf}.csv"), index_col=0, parse_dates=True)
    ax = axs[0, j]
    ax.plot(eq.index, eq["equity"] / 1000, color=col, lw=1.6)
    ax.axhline(100, color=AXIS, lw=0.8, ls=":")
    ax.set_title(f"{title}: grid to 30% retracement of the drop from the {S['runs'][tf]['old_high']}\n"
                 f"PnL {st['ret_per_yr_%']:.1f}%/yr, max DD {st['max_dd_%']:.0f}%, Sharpe {st['sharpe']:.2f}",
                 color=INK, loc="left", fontsize=9.5)
    ax.set_ylabel("Equity (\\$k)")
    ax2 = axs[1, j]
    ax2.fill_between(eq.index, eq["gross_expo_x"], color=col, alpha=0.35, lw=0)
    ax2.set_ylabel("Long exposure (x capital)")
    ax2.xaxis.set_major_locator(mdates.YearLocator(6))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.suptitle("Averaging-down grid after DeMark 9: no stop-loss, 1% steps, unit = 1% of capital, max 3 assets",
             x=0.01, ha="left", color=INK, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(RES, "equity_grid.png"))
print("chart written")
