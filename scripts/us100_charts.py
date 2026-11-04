"""Chart for the US-100 study (results/us100/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "us100")
S = json.load(open(os.path.join(RES, "summary.json")))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})
fig, ax = plt.subplots(figsize=(11, 5.6), dpi=150)
series = [("base_3_365d_none", "#2a78d6", "-", "MACD signal, max 3 stocks (asked rules)"),
          ("base_10_365d_none", "#1baf7a", "-", "MACD signal, max 10 stocks"),
          ("sl1_reentry_3_365d_none", "#eb6834", "-", "+ 1% stop with re-entry, max 3"),
          ("sl1_reentry_10_365d_none", "#6250d6", "-", "+ 1% stop with re-entry, max 10")]
for key, col, ls, lab in series:
    r = S["runs"][key]
    e = pd.DataFrame(r["equity_weekly"], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    st = r["stats"]
    ax.plot(e["date"], e["equity"] / 1000, color=col, ls=ls, lw=1.6,
            label=f"{lab}  ({st['cagr_%']:.1f}%/yr, DD {st['max_dd_%']:.0f}%, Sharpe {st['sharpe']:.2f})")
for key, col, ls in [("EW_100", MUTED, "--"), ("SP500TR", INK2, ":")]:
    b = S["benchmarks"][key]
    e = pd.DataFrame(b["equity_weekly"], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    ax.plot(e["date"], e["equity"] / 1000, color=col, ls=ls, lw=1.4,
            label=f"{b['label']}  ({b['cagr_%']:.1f}%/yr, DD {b['max_dd_%']:.0f}%, Sharpe {b['sharpe']:.2f})")
ax.set_yscale("log")
ax.set_yticks([100, 1000, 10000, 100000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
ax.set_ylabel("Equity, log scale (start \\$100k, compounding)")
ax.set_title("Weekly-MACD strategy on today's 100 biggest US stocks (survivorship-biased universe), 1990-2026",
             color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=7.8, loc="upper left")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig(os.path.join(RES, "equity_us100.png"))
print("chart written")
