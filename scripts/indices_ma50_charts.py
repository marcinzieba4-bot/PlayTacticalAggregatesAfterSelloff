"""Chart for the 27 indices + sectors S&P 50-day / 3-month study (results/indices_ma50/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "indices_ma50")
S = json.load(open(os.path.join(RES, "summary.json")))
V = pd.DataFrame(S["variants"])
B = S["benchmarks"]
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})


def stat(f, h, s, mo=3, uni="27"):
    return V[(V.universe == uni) & (V["filter"] == f) & (V.hold == h) & (V.stop == s) & (V.max_open == mo)].iloc[0]


fig = plt.figure(figsize=(13, 5.6), dpi=150)
gs = fig.add_gridspec(1, 2, width_ratios=[1.9, 1])
ax = fig.add_subplot(gs[0, 0])
lines = [("27_none_1year_nostop_3", MUTED, "-", "MACD only, 1-year hold", stat("none", "1 year", "no stop")),
         ("27_SP100d_1year_nostop_3", "#2a78d6", "-", "S&P>100d, 1 year, no stop (best)", stat("S&P 100d", "1 year", "no stop")),
         ("27_SP50d_3months_1pctstop_3", "#eb6834", "-", "S&P>50d, 3 months, 1% stop (asked)", stat("S&P 50d", "3 months", "1% stop")),
         ("27_SP50d_6months_1pctstop_3", "#1baf7a", "-", "S&P>50d, 6 months, 1% stop", stat("S&P 50d", "6 months", "1% stop")),
         ("27_SP50d_6months_nostop_3", "#c9a227", "-", "S&P>50d, 6 months, no stop", stat("S&P 50d", "6 months", "no stop")),
         ("EW_27", "#8a5cd6", ":", "Equal-weight 27, buy & hold", B["EW_27"]),
         ("SPX", INK2, ":", "S&P 500 (price)", B["SPX"])]
for key, col, ls, lab, v in lines:
    e = pd.DataFrame(S["runs"][key]["equity_weekly"], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    ax.plot(e["date"], e["equity"] / e["equity"].iloc[0] * 100, color=col, ls=ls, lw=1.8 if ls == "-" else 1.4,
            label=f"{lab}  ({v['cagr_%']:.1f}%/yr, DD {v['max_dd_%']:.0f}%, Sharpe {v['sharpe']:.2f})")
ax.set_yscale("log")
ax.set_yticks([100, 200, 500, 1000, 2000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
ax.set_ylabel("Equity, log (start \\$100k in 1990)")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_title("Weekly-MACD long on 16 DM indices + 11 US sectors, max 3: 3 / 6 / 12-month hold", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="upper left")

ax2 = fig.add_subplot(gs[0, 1])
cols = {"3 months": "#eb6834", "6 months": "#1baf7a", "1 year": "#2a78d6"}
mk = {"none": "o", "S&P 50d": "D", "S&P 100d": "s", "stock 50d": "^"}
for _, r in V[V.universe == "27"].iterrows():
    filled = r["max_open"] == 3
    ax2.scatter(-r["max_dd_%"], r["cagr_%"], marker=mk[r["filter"]], s=40, zorder=3, lw=1.1,
                color=cols[r["hold"]] if filled else "white", edgecolor=cols[r["hold"]])
a = stat("S&P 50d", "3 months", "1% stop")
ax2.annotate("asked: S&P>50d,\n3 months, 1% stop", (-a["max_dd_%"], a["cagr_%"]), xytext=(-75, 45), textcoords="offset points",
             fontsize=8, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED))
b = stat("S&P 100d", "1 year", "no stop")
ax2.annotate("S&P>100d, 1 year,\nno stop", (-b["max_dd_%"], b["cagr_%"]), xytext=(12, 14), textcoords="offset points",
             fontsize=8, color=INK2, arrowprops=dict(arrowstyle="-", color=MUTED))
h1 = [plt.Line2D([], [], color=c, marker="o", ls="", label=f"{h} hold") for h, c in cols.items()]
h2 = [plt.Line2D([], [], color=MUTED, marker=m, ls="", label=f"filter: {f}") for f, m in mk.items()]
h3 = [plt.Line2D([], [], color=MUTED, marker="o", ls="", label="max 3 (filled)"),
      plt.Line2D([], [], color=MUTED, marker="o", ls="", markerfacecolor="white", label="max 5 (hollow)")]
ax2.legend(handles=h1 + h2 + h3, frameon=False, fontsize=7.5, loc="lower right", labelspacing=0.3)
ax2.set_xlabel("Max drawdown, % (lower is better)")
ax2.set_ylabel("CAGR, %")
ax2.set_ylim(2.5, 10)
ax2.set_title("All 72 runs on the 27: hold x filter x stop", color=INK, loc="left", fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(RES, "indices_ma50.png"))
print("chart written")
