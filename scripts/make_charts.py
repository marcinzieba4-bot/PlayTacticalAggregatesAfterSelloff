"""Static PNG charts for the README (reads results/summary.json)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
S = json.load(open(os.path.join(RES, "summary.json")))

INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.8, "axes.axisbelow": True})


def eq(run):
    e = pd.DataFrame(run["equity_weekly"], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    return e.set_index("date")["equity"]


# 1) equity curves
fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
lines = [("W", "design", BLUE, "-", "Weekly 9 - with 5 re-entries"), ("W", "no_reentry", BLUE, "--", "Weekly 9 - no re-entry"),
         ("D", "design", ORANGE, "-", "Daily 9 - with 5 re-entries"), ("D", "no_reentry", ORANGE, "--", "Daily 9 - no re-entry")]
for tf, k, c, ls, lab in lines:
    e = eq(S["runs"][tf][k]) / 1000
    ax.plot(e.index, e.values, color=c, ls=ls, lw=2 if ls == "-" else 1.6, label=lab)
    ax.annotate(f"\\${e.iloc[-1]:,.0f}k", (e.index[-1], e.iloc[-1]), xytext=(4, 0), textcoords="offset points",
                color=INK2, fontsize=8, va="center")
ax.axvline(pd.Timestamp(S["split"]), color=MUTED, lw=1, ls=":")
ax.text(pd.Timestamp(S["split"]), ax.get_ylim()[1] * 0.97, "  out-of-sample ->", color=MUTED, fontsize=8, va="top")
ax.set_ylabel("Equity (\\$k) - start \\$100k, 0.5% base risk, no compounding")
ax.set_title("DeMark buy-setup 9 on DM indices + US sectors - portfolio equity (1990-2026)", color=INK, loc="left", fontsize=11)
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
fig.tight_layout()
fig.savefig(os.path.join(RES, "equity_curves.png"))

# 2) expectancy per attempt (R of own risk)
fig, ax = plt.subplots(figsize=(8, 4), dpi=150)
w = 0.38
for i, (tf, c, lab) in enumerate([("W", BLUE, "Weekly"), ("D", ORANGE, "Daily")]):
    ba = pd.DataFrame(S["runs"][tf]["design"]["by_attempt"])
    x = ba["k"] + (i - 0.5) * w
    ax.bar(x, ba["avg_R_own_risk"], width=w - 0.04, color=c, label=lab)
    for xx, v, n in zip(x, ba["avg_R_own_risk"], ba["n"]):
        ax.text(xx, v + (0.04 if v >= 0 else -0.04), f"n={n}", ha="center", va="bottom" if v >= 0 else "top",
                fontsize=7, color=INK2)
ax.axhline(0, color=AXIS, lw=1)
ax.set_xticks(range(6), ["initial", "re-entry 1", "re-entry 2", "re-entry 3", "re-entry 4", "re-entry 5"])
ax.set_ylabel("avg R per attempt (own risk)")
ax.set_title("Does each re-entry still have an edge? (size-independent)", color=INK, loc="left", fontsize=11)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(os.path.join(RES, "expectancy_by_attempt.png"))

# 3) re-entries x sizing: return vs drawdown
fig, axs = plt.subplots(1, 2, figsize=(10, 4), dpi=150, sharey=False)
for ax, (tf, lab) in zip(axs, [("W", "Weekly"), ("D", "Daily")]):
    r = pd.DataFrame(S["runs"][tf]["risk_table"])
    for sc, c, mk in [("flat", "#1baf7a", "o"), ("linear", BLUE, "s"), ("geo1.5", "#eda100", "^"), ("geo2", ORANGE, "D")]:
        g = r[(r.scheme == sc) | ((r.m == 0) & (sc == "flat"))].sort_values("m")
        ax.plot(-g["max_dd_%_of_capital"], g["ret_per_yr_%_of_capital"], marker=mk, color=c, lw=1.5, ms=6, label=sc)
        if sc == "flat":
            first = g.iloc[0]
            ax.annotate("m=0 (no re-entry)", (-first["max_dd_%_of_capital"], first["ret_per_yr_%_of_capital"]),
                        xytext=(4, -10), textcoords="offset points", fontsize=7, color=INK2)
        last = g.iloc[-1]
        ax.annotate("m=5", (-last["max_dd_%_of_capital"], last["ret_per_yr_%_of_capital"]), xytext=(4, -3),
                    textcoords="offset points", fontsize=7, color=INK2)
    ax.set_xlabel("max drawdown, % of capital")
    ax.set_ylabel("PnL per year, % of capital")
    ax.set_title(f"{lab}: more re-entries / bigger size", color=INK, loc="left", fontsize=10)
axs[0].legend(frameon=False, fontsize=8, title="size scheme", title_fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(RES, "reentry_risk_return.png"))
print("charts written")
