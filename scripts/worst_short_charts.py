"""Chart for the worst-MACD-profile short study (results/worst_short/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "worst_short")
S = json.load(open(os.path.join(RES, "summary.json")))
V = pd.DataFrame(S["variants"])
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})
sc = S["chosen_score"]
fig = plt.figure(figsize=(13, 5.6), dpi=150)
gs = fig.add_gridspec(1, 2, width_ratios=[2.1, 1])
ax = fig.add_subplot(gs[0, 0])


def line(key, col, ls, lab, st=None):
    e = pd.DataFrame(S["runs"][key]["equity_weekly"] if key in S["runs"] else S[key], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    e = e[e.date >= "1990-01-01"]
    y = (e.date.iloc[-1] - e.date.iloc[0]).days / 365.25
    cagr = 100 * ((e.equity.iloc[-1] / e.equity.iloc[0]) ** (1 / y) - 1)
    dd = 100 * (e.equity / e.equity.cummax() - 1).min()
    ax.plot(e.date, e.equity / 1000, color=col, ls=ls, lw=1.7 if ls == "-" else 1.4, label=f"{lab}  ({cagr:.1f}%/yr, DD {dd:.0f}%)")


line("long: earlier MACD rules", "#2a78d6", "-", "Long: new MACD up-phase, max 3")
line(f"short {sc} K3 M6 1y", "#e34948", "-", "Short: 3 worst MACD profiles")
line(f"earlier long rules 100% + worst-profile short 50% overlay", "#1baf7a", "-", "Long + 50% worst-profile short overlay")
line(f"contrarian long {sc} K3 M6 1y", "#eda100", "-", "Contrarian: BUY the 3 worst profiles")
line("bh_equity_weekly", MUTED, "--", "Equal-weight buy & hold, 27")
ax.set_yscale("log")
ax.set_yticks([10, 20, 50, 100, 200, 500, 1000, 2000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
ax.set_ylabel("Equity, log (start \\$100k)")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_title("27 instruments (16 DM indices + 11 US sectors): shorting the worst weekly-MACD profile", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=7.8, loc="upper left")
ax2 = fig.add_subplot(gs[0, 1])
by = pd.Series(S["runs"][f"short {sc} K3 M6 1y"]["by_year"])
by.index = by.index.astype(int)
ax2.bar(by.index, by.values, color=["#0ca30c" if v > 0 else "#d03b3b" for v in by.values], width=0.8)
ax2.axhline(0, color=AXIS, lw=1)
for yr in by.abs().nlargest(5).index:
    ax2.text(yr, by[yr] + (2 if by[yr] > 0 else -2), str(yr), ha="center", va="bottom" if by[yr] > 0 else "top", fontsize=7, color=INK2)
ax2.set_title("Worst-profile short leg: return by year (%)", color=INK, loc="left", fontsize=10)
ax2.grid(axis="x", visible=False)
fig.tight_layout()
fig.savefig(os.path.join(RES, "worst_short.png"))
print("chart written")
