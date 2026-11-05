"""Chart for the S&P 500 regime study (results/macd_regime/)."""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from strategy.data import load_daily  # noqa: E402

RES = os.path.join(ROOT, "results", "macd_regime")
S = json.load(open(os.path.join(RES, "summary.json")))
V = pd.DataFrame(S["variants"]).set_index("variant")
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})
fig = plt.figure(figsize=(13, 5.6), dpi=150)
gs = fig.add_gridspec(1, 2, width_ratios=[1.9, 1])
ax = fig.add_subplot(gs[0, 0])
for key, col, ls, lab in [("no filter (earlier rules)", MUTED, "-", "No filter (earlier rules)"),
                          ("SPX>100d: entry filter only", "#2a78d6", "-", "Buy only if S&P > 100-day avg"),
                          ("SPX>100d: entry filter + daily exit", "#eb6834", "-", "+ sell all when S&P < 100-day avg"),
                          ("S&P 500 buy & hold (price)", INK2, ":", "S&P 500 buy & hold")]:
    e = pd.DataFrame(S["runs"][key]["equity_weekly"], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    v = V.loc[key]
    ax.plot(e["date"], e["equity"] / 1000, color=col, ls=ls, lw=1.8 if ls == "-" else 1.4,
            label=f"{lab}  ({v['cagr_%']:.1f}%/yr, DD {v['max_dd_%']:.0f}%, Sharpe {v['sharpe']:.2f})")
ax.set_yscale("log")
ax.set_yticks([100, 200, 500, 1000, 2000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
ax.set_ylabel("Equity, log (start \\$100k)")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_title("Weekly-MACD long on 27 indices + sectors, with an S&P 500 100-day regime filter", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax2 = fig.add_subplot(gs[0, 1])
c = load_daily("^GSPC", drop_after="2026-11-04")["Close"]
sma = c.rolling(100).mean()
c2, s2 = c[c.index >= "2025-05-01"], sma[sma.index >= "2025-05-01"]
ax2.plot(c2.index, c2, color="#2a78d6", lw=1.6, label="S&P 500")
ax2.plot(s2.index, s2, color="#eb6834", lw=1.6, label="100-day average")
ax2.fill_between(c2.index, c2.min() * 0.98, c2.max() * 1.02, where=(c2 > s2).to_numpy(), color="#1baf7a", alpha=0.10, lw=0)
n = S["now"]
ax2.annotate(f"{n['date']}: {n['spx_close']:,.0f}\n{n['dist_%']:+.1f}% vs 100-day avg\n-> filter OFF", (c2.index[-1], c2.iloc[-1]),
             xytext=(-150, -170), textcoords="offset points", fontsize=8, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED))
ax2.set_title("S&P 500 vs its 100-day average (green = filter on)", color=INK, loc="left", fontsize=10)
ax2.legend(frameon=False, fontsize=8, loc="upper left")
ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
fig.tight_layout()
fig.savefig(os.path.join(RES, "macd_regime.png"))
print("chart written")
