"""Charts for the 'martingale until the old high' study (reads results/oldhigh/summary.json)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "oldhigh")
S = json.load(open(os.path.join(RES, "summary.json")))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
SERIES = [("martingale_x2_10re", "#e34948", "-", "x2 martingale, 10 re-entries"),
          ("martingale_x2_5re", "#eb6834", "-", "x2 martingale, 5 re-entries"),
          ("linear_5re", "#2a78d6", "-", "linear 1,2,3..., 5 re-entries"),
          ("flat_5re", "#1baf7a", "-", "flat size, 5 re-entries"),
          ("no_reentry", MUTED, "--", "no re-entry")]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})

fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), dpi=150)
for ax, tf, title in [(axs[0], "W", "Weekly 9"), (axs[1], "D", "Daily 9")]:
    run = S["runs"][tf]
    for key, col, ls, lab in SERIES:
        d = run["details"].get(key)
        if not d:
            continue
        e = pd.DataFrame(d["equity_weekly"], columns=["date", "equity"])
        e["date"] = pd.to_datetime(e["date"])
        st = d["equity_stats"]["FULL"]
        ax.plot(e["date"], e["equity"] / 1000, color=col, ls=ls, lw=1.8,
                label=f"{lab}  (DD {st['max_dd_%_of_capital']:.0f}%)")
    ax.axhline(0, color=INK, lw=0.8)
    ax.axhline(100, color=AXIS, lw=0.8, ls=":")
    ax.set_title(f"{title}: exit at the old high ({run['old_high_label']}), one campaign at a time",
                 color=INK, loc="left", fontsize=10)
    ax.set_ylabel("Equity (\\$k), start \\$100k, 0.5% base risk")
    ax.xaxis.set_major_locator(mdates.YearLocator(6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(frameon=False, fontsize=7.5, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(RES, "equity_oldhigh.png"))
print("chart written")
