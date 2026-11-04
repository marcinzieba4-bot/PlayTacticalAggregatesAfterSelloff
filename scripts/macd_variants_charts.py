"""Charts for the MACD variants study (results/macd_variants/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "macd_variants")
S = json.load(open(os.path.join(RES, "summary.json")))
G = pd.read_csv(os.path.join(RES, "variants.csv"))
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True})
fig = plt.figure(figsize=(13, 8.4), dpi=150)
gs = fig.add_gridspec(2, 3, height_ratios=[1.25, 1])
ax = fig.add_subplot(gs[0, :])
ax.grid(True, color=GRID)
for key, col, lab in [("base__ref", "#2a78d6", "Base: MACD signal, MACD stop, 1-year exit"),
                      ("sl1_reentry__ref", "#eb6834", "+ 1% stop, re-entry at the first entry price"),
                      ("ladder_flat_K10__ref", "#1baf7a", "Ladder: +1 unit every 1% down (10 steps)"),
                      ("ladder_mart_K5__ref", "#e34948", "Martingale ladder: x2 every 1% down (5 steps)")]:
    r = S["runs"][key]
    e = pd.DataFrame(r["equity_weekly"], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    st = r["stats"]
    ax.plot(e["date"], e["equity"] / 1000, color=col, lw=1.7,
            label=f"{lab}  (CAGR {st['cagr_%']:.1f}%, DD {st['max_dd_%']:.0f}%, Sharpe {st['sharpe']:.2f}, invested {st['avg_invested_%']:.0f}%)")
ax.set_yscale("log")
ax.set_yticks([100, 200, 500, 1000, 2000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v:,.0f}k"))
ax.set_ylabel("Equity, log (start \\$100k)")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_title("Weekly-MACD strategy, max 3 assets: entry/exit variants (take-profit 1 year, no level)", color=INK, loc="left")
rows = ["91d", "182d", "365d", "730d", "none"]
cols = ["+5%", "+10%", "+20%", "+30%", "none"]
for j, (mode, metric, title, cmap) in enumerate([("base", "cagr_%", "Base: CAGR % by take-profit", "Blues"),
                                                 ("base", "sharpe", "Base: Sharpe by take-profit", "Blues"),
                                                 ("sl1_reentry", "sharpe", "1% stop + re-entry: Sharpe", "Oranges")]):
    a = fig.add_subplot(gs[1, j])
    p = G[G["mode"] == mode].pivot(index="tp_time", columns="tp_level", values=metric).reindex(index=rows, columns=cols)
    im = a.imshow(p.to_numpy(), cmap=cmap, aspect="auto")
    for (i, k), v in np.ndenumerate(p.to_numpy()):
        a.text(k, i, f"{v:.2f}" if metric == "sharpe" else f"{v:.1f}", ha="center", va="center", fontsize=8.5,
               color="white" if v > np.nanpercentile(p.to_numpy(), 60) else INK)
    a.set_xticks(range(5), cols)
    a.set_yticks(range(5), ["3 m", "6 m", "1 y", "2 y", "none"])
    a.set_xlabel("level take-profit")
    a.set_ylabel("time take-profit")
    a.set_title(title, color=INK, loc="left", fontsize=9.5)
    for sp in a.spines.values():
        sp.set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(RES, "macd_variants.png"))
print("chart written")
