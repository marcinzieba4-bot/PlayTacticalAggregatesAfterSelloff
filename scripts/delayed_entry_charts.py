"""Chart for the delayed-entry study (results/delayed_entry/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "delayed_entry")
I = json.load(open(os.path.join(RES, "indices_summary.json")))
S = json.load(open(os.path.join(RES, "stocks_summary.json")))
W = json.load(open(os.path.join(RES, "stocks_wait1m_check.json")))
IM = json.load(open(os.path.join(ROOT, "results", "indices_ma50", "summary.json")))
SM = json.load(open(os.path.join(ROOT, "results", "stocks_ma50", "summary.json")))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})


def stat(summary, entry, f, s, mo):
    v = pd.DataFrame(summary["variants"])
    return v[(v.entry == entry) & (v["filter"] == f) & (v.stop == s) & (v.max_open == mo)].iloc[0]


def wstat(f, s, mo):
    return next(d for d in W["deterministic"] if d["filter"] == f and d["stop"] == s and d["max_open"] == mo)


def bstat(summary, key):
    return summary.get("benchmarks", summary.get("pit_benchmarks"))[key]


def panel(ax, lines, title, start):
    for runs, key, col, ls, lab, v in lines:
        e = pd.DataFrame(runs[key]["equity_weekly"], columns=["date", "equity"])
        e["date"] = pd.to_datetime(e["date"])
        e = e[e["date"] >= start]
        ax.plot(e["date"], e["equity"] / e["equity"].iloc[0] * 100, color=col, ls=ls, lw=1.7 if ls == "-" else 1.3,
                label=f"{lab}  ({v['cagr_%']:.1f}%, DD {v['max_dd_%']:.0f}%, Sh {v['sharpe']:.2f})")
    ax.set_yscale("log")
    ax.set_yticks([100, 200, 500, 1000, 2000, 5000])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
    ax.xaxis.set_major_locator(mdates.YearLocator(6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title(title, color=INK, loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=7.4, loc="upper left")


fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5.6), dpi=150)
panel(a1, [(I["runs"], "immediate_hold12m_none_nostop_3", MUTED, "-", "Buy at once, hold 12m (original)", stat(I, "immediate, hold 12m", "none", "no stop", 3)),
           (I["runs"], "immediate_hold12m_SP100d_nostop_3", "#2a78d6", "-", "Buy at once, S&P>100d, hold 12m", stat(I, "immediate, hold 12m", "S&P 100d", "no stop", 3)),
           (I["runs"], "wait2m_hold10m_none_nostop_3", "#eb6834", "-", "Wait 2m, hold 10m, no stop", stat(I, "wait 2m, hold 10m", "none", "no stop", 3)),
           (I["runs"], "wait2m_hold10m_none_1pctstop_3", "#1baf7a", "-", "Wait 2m, hold 10m, 1% stop", stat(I, "wait 2m, hold 10m", "none", "1% stop", 3)),
           (IM["runs"], "EW_27", "#8a5cd6", ":", "Equal-weight 27", bstat(IM, "EW_27"))],
      "27 DM indices + US sectors, max 3", "1990-01-01")
a1.set_ylabel("Equity, log (start \\$100k)")
panel(a2, [(S["runs"], "immediate_hold12m_none_1pctstop_10", MUTED, "-", "Buy at once, 1% stop, hold 12m", stat(S, "immediate, hold 12m", "none", "1% stop", 10)),
           (S["runs"], "wait2m_hold10m_none_1pctstop_10", "#eb6834", "-", "Wait 2m, 1% stop, hold 10m", stat(S, "wait 2m, hold 10m", "none", "1% stop", 10)),
           (S["runs"], "wait2m_hold10m_SP50d_1pctstop_10", "#1baf7a", "-", "Wait 2m, S&P>50d, 1% stop, hold 10m", stat(S, "wait 2m, hold 10m", "S&P 50d", "1% stop", 10)),
           (W["runs"], "wait1m_SP100d_1pctstop_10", "#2a78d6", "-", "Wait 1m, S&P>100d, 1% stop, hold 11m", wstat("S&P 100d", "1% stop", 10)),
           (SM["runs"], "PIT_none_6months_1pctstop_20", "#c9a227", "-", "Buy at once, 1% stop, hold 6m, 20 stocks",
            pd.DataFrame(SM["variants"]).query("universe == 'PIT' and filter == 'none' and hold == '6 months' and stop == '1% stop' and max_open == 20").iloc[0]),
           (SM["runs"], "EW_top100_pit", "#8a5cd6", ":", "Equal-weight PIT top 100", bstat(SM, "EW_top100_pit"))],
      "Point-in-time top-100 stocks, 10 stocks unless noted", "1997-01-01")
fig.suptitle("Delayed entry: wait 2 months after the MACD signal, buy only if the MACD stayed > 0, hold 10 months",
             x=0.01, ha="left", fontsize=10.5, color=INK)
fig.tight_layout()
fig.savefig(os.path.join(RES, "delayed_entry.png"))
print("chart written")
