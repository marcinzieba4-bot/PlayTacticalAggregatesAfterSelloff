"""Chart for the MACD-filtered DeMark 9 study (results/macd/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "macd")
S = json.load(open(os.path.join(RES, "summary.json")))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})
fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
series = [(S["runs"]["D"]["equity_weekly"], "#eb6834", "-", "Daily 9 + weekly MACD filter", S["runs"]["D"]["stats"]),
          (S["runs"]["W"]["equity_weekly"], "#2a78d6", "-", "Weekly 9 + weekly MACD filter", S["runs"]["W"]["stats"]),
          (S["buy_and_hold_EW"]["equity_weekly"], MUTED, "--", "Equal-weight buy & hold, all 27", None)]
for data, col, ls, lab, st in series:
    e = pd.DataFrame(data, columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    e = e[e.date >= "1990-01-01"]
    if st:
        lab += f"  (CAGR {st['cagr_%']:.1f}%, DD {st['max_dd_%']:.0f}%, Sharpe {st['sharpe']:.2f})"
    else:
        b = S["buy_and_hold_EW"]
        lab += f"  (CAGR {b['cagr_%']:.1f}%, DD {b['max_dd_%']:.0f}%, Sharpe {b['sharpe']:.2f})"
    ax.plot(e["date"], e["equity"] / 1000, color=col, ls=ls, lw=1.8 if ls == "-" else 1.4, label=lab)
ax.set_yscale("log")
ax.set_yticks([100, 200, 500, 1000, 2000, 3000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}k"))
ax.set_ylabel("Equity, log scale (start \\$100k, compounding)")
ax.set_title("DeMark 9 only when weekly MACD and signal > 0; stop when MACD < 0; exit after 1 year; max 3 assets",
             color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig(os.path.join(RES, "equity_macd.png"))
print("chart written")
