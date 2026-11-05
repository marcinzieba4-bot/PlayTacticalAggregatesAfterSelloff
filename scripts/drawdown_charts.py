"""Underwater chart for the drawdown study (results/drawdowns/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "drawdowns")
S = json.load(open(os.path.join(RES, "summary.json")))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})


def uw(name):
    d = pd.DataFrame(S["underwater_weekly"][name], columns=["date", "dd"])
    d["date"] = pd.to_datetime(d["date"])
    return d[d["date"] >= "1997-01-01"]


fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 7.2), dpi=150, sharex=True, gridspec_kw={"height_ratios": [1.35, 1]})
combo = "50/50 IDX5 + STK_W1"
d = uw(combo)
a1.fill_between(d["date"], d["dd"], 0, color=INK, alpha=0.18, lw=0)
a1.plot(d["date"], d["dd"], color=INK, lw=1.4, label=f"50/50 combination (max {S['series'][combo]['max_dd_%']:.0f}%, "
        f"longest under water {S['series'][combo]['longest_underwater_years']:.1f} y)")
for name, col, lab in [("Indices, max 5 (IDX5)", "#2a78d6", "Indices, max 5"),
                       ("Stocks, wait 1m + S&P>100d + 1% stop (STK_W1)", "#eb6834", "Stocks, wait 1m + S&P>100d + 1% stop")]:
    d = uw(name)
    a1.plot(d["date"], d["dd"], color=col, lw=1.0, alpha=0.9,
            label=f"{lab} (max {S['series'][name]['max_dd_%']:.0f}%, longest {S['series'][name]['longest_underwater_years']:.1f} y)")
for ep in S["series"][combo]["deepest"][:4]:
    t = pd.Timestamp(ep["trough"])
    dx = {2009: -45, 2011: 45}.get(t.year, 0)
    a1.annotate(f"{ep['depth_%']:.0f}%\n{pd.Timestamp(ep['peak']):%b %Y}-{pd.Timestamp(ep['recovered'][:10]):%b %Y}",
                (t, ep["depth_%"]), xytext=(dx, -40), textcoords="offset points", ha="center", fontsize=7.5, color=INK2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
lg = S["series"][combo]["longest"][0]
a1.axvspan(pd.Timestamp(lg["peak"]), pd.Timestamp(lg["recovered"][:10]), color="#c9a227", alpha=0.12, lw=0)
a1.text(pd.Timestamp(lg["peak"]) + pd.Timedelta(days=40), -25.5, f"longest: {lg['underwater_days'] / 365.25:.1f} years under water",
        fontsize=8, color=INK2)
a1.set_ylim(-27, 1)
a1.set_ylabel("Drawdown from the high, %")
a1.set_title("Time under water: best index book, best stock book and their 50/50 combination (idle cash in T-bills)",
             color=INK, loc="left", fontsize=10)
a1.legend(frameon=False, fontsize=8, loc="lower right", ncol=1)
d = uw("S&P 500 (price)")
a2.fill_between(d["date"], d["dd"], 0, color=MUTED, alpha=0.35, lw=0)
a2.plot(d["date"], d["dd"], color=INK2, lw=1.0)
sp = S["series"]["S&P 500 (price)"]
a2.set_title(f"S&P 500 (price) for comparison: max {sp['max_dd_%']:.0f}%, longest under water {sp['longest_underwater_years']:.1f} years "
             f"(2000-2007), below -10% on {sp['pct_days_dd_worse_than_10']:.0f}% of days", color=INK, loc="left", fontsize=10)
a2.set_ylabel("Drawdown, %")
a2.xaxis.set_major_locator(mdates.YearLocator(2))
a2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig(os.path.join(RES, "drawdowns.png"))
print("chart written")
