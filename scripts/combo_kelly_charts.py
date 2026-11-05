"""Chart for the combination + Kelly study (results/combo_kelly/)."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "combo_kelly")
S = json.load(open(os.path.join(RES, "summary.json")))
B = pd.DataFrame(S["books_and_combos"])
K = pd.DataFrame(S["kelly_rows"])
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9.5, "axes.edgecolor": AXIS, "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF, "figure.facecolor": SURF,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "axes.axisbelow": True})


def st(book, variant=None):
    b = B[B.book == book]
    return (b[b.variant == variant] if variant else b).iloc[0]


def kst(book, sizing):
    return K[(K.book == book) & (K.sizing == sizing)].iloc[0]


fig = plt.figure(figsize=(14, 5.8), dpi=150)
gs = fig.add_gridspec(1, 3, width_ratios=[1.75, 1, 1])
ax = fig.add_subplot(gs[0, 0])
combo = "IDX5 + STK_W1: 50/50"
lines = [("IDX5", "#2a78d6", "-", "Indices: S&P>100d, 12m, max 5", st("IDX5", "idle cash earns T-bill")),
         ("STK_W1", "#eb6834", "-", "Stocks: wait 1m, S&P>100d, 1% stop, 10", st("STK_W1", "idle cash earns T-bill")),
         (combo, INK, "-", "50/50 combination", st(combo)),
         ("IDX5 + STK_W1 (50/50) L=1.5", "#1baf7a", "-", "50/50 combination at 1.5x", kst("IDX5 + STK_W1 (50/50)", "L=1.5")),
         ("IDX5 + STK_W1 (50/50) 1/2 Kelly (IS)", "#c9a227", "-", "50/50 at half Kelly (2.9x)", kst("IDX5 + STK_W1 (50/50)", "1/2 Kelly (IS)")),
         ("S&P 500 (price)", INK2, ":", "S&P 500 (price)", st("S&P 500 (price)"))]
for key, col, ls, lab, v in lines:
    e = pd.DataFrame(S["equity_weekly"][key], columns=["date", "equity"])
    e["date"] = pd.to_datetime(e["date"])
    ax.plot(e["date"], e["equity"] / e["equity"].iloc[0] * 100, color=col, ls=ls, lw=1.9 if key == combo else 1.5,
            label=f"{lab}  ({v['cagr_%']:.1f}%, DD {v['max_dd_%']:.0f}%, Calmar {v['calmar']:.2f})")
ax.set_yscale("log")
ax.set_yticks([100, 200, 500, 1000, 2000, 5000, 10000])
ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"${v/1000:,.0f}M" if v >= 1000 else f"${v:,.0f}k"))
ax.xaxis.set_major_locator(mdates.YearLocator(4))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_ylabel("Equity, log (start \\$100k in 1997)")
ax.set_title("Best index book + best stock book, 1997-2026 (idle cash earns T-bills)", color=INK, loc="left", fontsize=10)
ax.legend(frameon=False, fontsize=7.5, loc="upper left")

ax2 = fig.add_subplot(gs[0, 1])
cols = {"IDX5": "#2a78d6", "STK_W1": "#eb6834", "STK_6M": "#8a5cd6", "IDX5 + STK_W1 (50/50)": INK, "IDX5 + STK_6M (50/50)": "#1baf7a"}
for book, c in cols.items():
    k = K[(K.book == book) & K.sizing.str.startswith("L=")].sort_values("L")
    ax2.plot(k["L"], k["calmar"], color=c, lw=1.6, marker="o", ms=3, label=book)
    fk = kst(book, "full Kelly (IS)")
    ax2.scatter([fk["L"]], [fk["calmar"]], color=c, marker="X", s=60, zorder=4)
ax2.set_xscale("log")
ax2.set_xticks([0.5, 1, 2, 4, 8])
ax2.get_xaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}x"))
ax2.get_xaxis().set_minor_formatter(matplotlib.ticker.NullFormatter())
ax2.set_xlabel("Leverage on the book (X = full Kelly, in-sample)")
ax2.set_ylabel("Calmar = CAGR / |max drawdown|")
ax2.set_title("Calmar falls as leverage rises", color=INK, loc="left", fontsize=10)
ax2.legend(frameon=False, fontsize=7.2, loc="upper right")

ax3 = fig.add_subplot(gs[0, 2])
k = K[(K.book == "IDX5 + STK_W1 (50/50)") & K.sizing.str.startswith("L=")].sort_values("L")
ax3.plot(k["L"], k["cagr_%"], color="#1baf7a", lw=1.8, marker="o", ms=3, label="CAGR %")
ax3.plot(k["L"], -k["max_dd_%"], color="#d6432a", lw=1.8, marker="o", ms=3, label="max drawdown %")
for lab, mk in [("1/4 Kelly (IS)", "s"), ("1/2 Kelly (IS)", "D"), ("full Kelly (IS)", "X")]:
    r = kst("IDX5 + STK_W1 (50/50)", lab)
    ax3.scatter([r["L"]], [r["cagr_%"]], color="#1baf7a", marker=mk, s=50, zorder=4)
    ax3.scatter([r["L"]], [-r["max_dd_%"]], color="#d6432a", marker=mk, s=50, zorder=4)
    ax3.annotate(lab.replace(" (IS)", ""), (r["L"], -r["max_dd_%"]), xytext=(4, -12), textcoords="offset points", fontsize=7.5, color=INK2)
ax3.set_xscale("log")
ax3.set_xticks([0.5, 1, 2, 4, 8])
ax3.get_xaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}x"))
ax3.get_xaxis().set_minor_formatter(matplotlib.ticker.NullFormatter())
ax3.set_xlabel("Leverage on the 50/50 combination")
ax3.set_title("Growth vs drawdown, 50/50 combination", color=INK, loc="left", fontsize=10)
ax3.legend(frameon=False, fontsize=7.5, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(RES, "combo_kelly.png"))
print("chart written")
