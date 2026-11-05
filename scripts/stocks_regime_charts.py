"""Chart for the single-stock S&P 500 regime study (results/stocks_regime/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "stocks_regime")
S = json.load(open(os.path.join(RES, "summary.json")))
V = pd.DataFrame(S["variants"])
B = S["pit_benchmarks"]
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})


def stat(variant, mo):
    return V[(V.universe == "PIT") & (V.variant == variant) & (V.max_open == mo)].iloc[0]


fig = plt.figure(figsize=(13, 5.6), dpi=150)
gs = fig.add_gridspec(1, 2, width_ratios=[1.9, 1])
ax = fig.add_subplot(gs[0, 0])
lines = [("PIT_no_filter_no_stop_10", MUTED, "-", "MACD only, 10 stocks", stat("no filter, no stop", 10)),
         ("PIT_SP_filter_1pct_stop_10", "#2a78d6", "-", "S&P>100d + 1% stop, 10 stocks", stat("S&P filter, 1% stop", 10)),
         ("PIT_SP_filter_1pct_stop_20", "#1baf7a", "-", "S&P>100d + 1% stop, 20 stocks", stat("S&P filter, 1% stop", 20)),
         ("PIT_stock_MA_filter_1pct_stop_10", "#8a5cd6", "-", "Stock>own 100d + 1% stop, 10 stocks", stat("stock MA filter, 1% stop", 10)),
         ("EW_top100_pit", "#eb6834", ":", "Equal-weight PIT top 100", B["EW_top100_pit"]),
         ("SP500TR", INK2, ":", "S&P 500 total return", B["SP500TR"])]
for key, col, ls, lab, v in lines:
    e = pd.DataFrame(S["runs"][key]["equity_weekly"], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    e = e[e["date"] >= "1997-01-01"]
    ax.plot(e["date"], e["equity"] / e["equity"].iloc[0] * 100, color=col, ls=ls, lw=1.8 if ls == "-" else 1.4,
            label=f"{lab}  ({v['cagr_%']:.1f}%/yr, DD {v['max_dd_%']:.0f}%, Sharpe {v['sharpe']:.2f})")
ax.set_yscale("log")
ax.set_yticks([100, 200, 500, 1000, 2000, 5000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
ax.set_ylabel("Equity, log (start \\$100k in 1997)")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_title("Weekly-MACD long on point-in-time S&P 500 top-100 stocks: S&P vs own-stock 100-day filter", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")

# right panel: max drawdown vs CAGR for every PIT variant
ax2 = fig.add_subplot(gs[0, 1])
cols = {3: "#eb6834", 10: "#2a78d6", 20: "#1baf7a"}
mk = {"no filter, no stop": "o", "S&P filter, no stop": "s", "no filter, 1% stop": "^", "S&P filter, 1% stop": "D",
      "S&P filter, 2% stop": "v", "stock MA filter, no stop": "P", "stock MA filter, 1% stop": "X", "stock MA filter, 2% stop": "h",
      "S&P + stock MA filter, 1% stop": "p"}
for _, r in V[V.universe == "PIT"].iterrows():
    ax2.scatter(-r["max_dd_%"], r["cagr_%"], color=cols[r["max_open"]], marker=mk[r["variant"]], s=46, edgecolor="white",
                lw=0.6, zorder=3)
for k, c, lab in [("EW_top100_pit", "#eb6834", "EW top 100"), ("SP500TR", INK2, "S&P 500 TR")]:
    ax2.scatter(-B[k]["max_dd_%"], B[k]["cagr_%"], color="white", edgecolor=c, marker="*", s=130, lw=1.2, zorder=3)
    ax2.annotate(lab, (-B[k]["max_dd_%"], B[k]["cagr_%"]), xytext=(-8, 6), textcoords="offset points", ha="right", fontsize=8, color=INK2)
best = stat("S&P filter, 1% stop", 10)
ax2.annotate("10 stocks,\nS&P filter + 1% stop", (-best["max_dd_%"], best["cagr_%"]), xytext=(-70, -55), textcoords="offset points",
             fontsize=8, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED))
low = stat("S&P filter, 1% stop", 20)
ax2.annotate("20 stocks,\nS&P filter + 1% stop", (-low["max_dd_%"], low["cagr_%"]), xytext=(4, -30), textcoords="offset points",
             fontsize=8, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED))
h1 = [plt.Line2D([], [], color=c, marker="o", ls="", label=f"max {m}") for m, c in cols.items()]
h2 = [plt.Line2D([], [], color=MUTED, marker=m, ls="", label=v) for v, m in mk.items()]
ax2.legend(handles=h1 + h2, frameon=False, fontsize=7, loc="upper left", ncol=1, handletextpad=0.2, labelspacing=0.25)
ax2.set_xlabel("Max drawdown, % (lower is better)")
ax2.set_ylabel("CAGR, %")
ax2.set_xlim(15, 70)
ax2.set_title("Return vs drawdown, all point-in-time variants", color=INK, loc="left", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(RES, "stocks_regime.png"))
print("chart written")
