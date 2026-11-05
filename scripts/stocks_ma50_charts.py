"""Chart for the single-stock S&P 50-day / 3-month study (results/stocks_ma50/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "stocks_ma50")
S = json.load(open(os.path.join(RES, "summary.json")))
V = pd.DataFrame(S["variants"])
B = S["pit_benchmarks"]
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})


def stat(f, h, s, mo):
    return V[(V.universe == "PIT") & (V["filter"] == f) & (V.hold == h) & (V.stop == s) & (V.max_open == mo)].iloc[0]


fig = plt.figure(figsize=(13, 5.6), dpi=150)
gs = fig.add_gridspec(1, 2, width_ratios=[1.9, 1])
ax = fig.add_subplot(gs[0, 0])
lines = [("PIT_none_1year_nostop_10", MUTED, "-", "MACD only, 1-year hold, 10 stocks", stat("none", "1 year", "no stop", 10)),
         ("PIT_SP100d_1year_1pctstop_10", "#2a78d6", "-", "S&P>100d, 1 year, 1% stop, 10 stocks", stat("S&P 100d", "1 year", "1% stop", 10)),
         ("PIT_SP50d_3months_1pctstop_10", "#eb6834", "-", "S&P>50d, 3 months, 1% stop, 10 stocks", stat("S&P 50d", "3 months", "1% stop", 10)),
         ("PIT_SP50d_3months_1pctstop_20", "#1baf7a", "-", "S&P>50d, 3 months, 1% stop, 20 stocks", stat("S&P 50d", "3 months", "1% stop", 20)),
         ("PIT_none_3months_1pctstop_20", "#c9a227", "-", "No filter, 3 months, 1% stop, 20 stocks", stat("none", "3 months", "1% stop", 20)),
         ("EW_top100_pit", "#8a5cd6", ":", "Equal-weight PIT top 100", B["EW_top100_pit"]),
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
ax.set_title("Weekly-MACD long on point-in-time top-100 stocks: S&P 50-day filter + 3-month hold", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")

# right: return vs drawdown for the 1 % stop variants, by filter and holding period
ax2 = fig.add_subplot(gs[0, 1])
cols = {"none": MUTED, "S&P 50d": "#eb6834", "S&P 100d": "#2a78d6", "stock 50d": "#8a5cd6"}
mk = {"3 months": "o", "1 year": "s"}
for _, r in V[(V.universe == "PIT") & (V.stop == "1% stop") & (V.max_open.isin([10, 20]))].iterrows():
    filled = r["max_open"] == 10
    ax2.scatter(-r["max_dd_%"], r["cagr_%"], marker=mk[r["hold"]], s=52, zorder=3, lw=1.3,
                color=cols[r["filter"]] if filled else "white", edgecolor=cols[r["filter"]])
for k, c, lab in [("EW_top100_pit", "#8a5cd6", "EW top 100"), ("SP500TR", INK2, "S&P 500 TR")]:
    ax2.scatter(-B[k]["max_dd_%"], B[k]["cagr_%"], color="white", edgecolor=c, marker="*", s=130, lw=1.2, zorder=3)
    ax2.annotate(lab, (-B[k]["max_dd_%"], B[k]["cagr_%"]), xytext=(-8, 6), textcoords="offset points", ha="right", fontsize=8, color=INK2)
h1 = [plt.Line2D([], [], color=c, marker="o", ls="", label=f) for f, c in cols.items()]
h2 = [plt.Line2D([], [], color=MUTED, marker=m, ls="", label=h) for h, m in mk.items()]
h3 = [plt.Line2D([], [], color=MUTED, marker="o", ls="", label="10 stocks (filled)"),
      plt.Line2D([], [], color=MUTED, marker="o", ls="", markerfacecolor="white", label="20 stocks (hollow)")]
ax2.legend(handles=h1 + h2 + h3, frameon=False, fontsize=7.5, loc="lower right", labelspacing=0.3)
ax2.set_xlabel("Max drawdown, % (lower is better)")
ax2.set_ylabel("CAGR, %")
ax2.set_title("1% stop variants: filter x holding period", color=INK, loc="left", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(RES, "stocks_ma50.png"))
print("chart written")
