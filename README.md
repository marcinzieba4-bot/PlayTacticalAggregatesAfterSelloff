# Play Tactical Aggregates After Sell-off: DeMark 9 with stop and re-entry

This repo backtests a tactical long strategy on **developed-market equity indices and US sectors**:

1. Wait for a sell-off that completes a **DeMark TD buy setup 9**, on the **weekly** chart (main case) and on the **daily** chart.
2. Use the 9th candle as the trade's anchor:
   * **stop-loss** just below the candle's **low**
   * after a stop-out, **re-enter** when price trades back above the candle's **high**
   * each re-entry is **bigger** than the one before, and you get **up to 5 re-entries** (6 attempts in total)
3. Simulate everything, optimize the candle rules, and report the PnL.

Data runs from 1990-01 to 2026-11-03 (Yahoo Finance daily OHLC). The in-sample period is 1990–2012 and the out-of-sample period is 2013–2026.

---

## Martingale until the old high (no time stop)

The question: keep going in above the 9-candle high and out below its low, making each new attempt bigger, until price gets back to the **old high**. Near the old high the position goes to 0 and the campaign ends. Rules as simulated:

* **Old high:** the pre-sell-off peak, i.e. the highest high of the 52 weeks (weekly) or 63 days (daily) before the 9. These lookbacks and the exit distance were picked in-sample. Tested alternatives were 26 weeks / 252 days, and exiting 0, 0.25, 0.5 or 1 ATR below the high.
* **Exit:** weekly exits exactly at the old high; daily exits 1 ATR below it.
* **No time stop and no re-entry window.** A campaign ends only at the old high, or as a loss when the allowed re-entries are used up.
* **New 9 on the same instrument while flat:** the campaign carries on and in/out moves to the new 9-candle. The size step and the old-high target stay the same.
  * The other two options were tested and fail. Keeping the old candle forever let a single campaign wait for decades and block the slot: only 4 weekly campaigns in 36 years. Ending the campaign on a new 9 resets the martingale, so earlier losses are never won back.
* One campaign at a time, the same $100k account, 0.5 % base risk, notional capped at 2× capital per position.

| One campaign at a time | Campaigns | Reached old high | Ran out of re-entries | Avg length | PnL / yr | Max DD | Sharpe | Worst campaign |
|---|---|---|---|---|---|---|---|---|
| **Weekly ×2 martingale, 5 re-entries** | 16 | 75 % | 19 % | 723 days (max 8.2 yrs) | 2.7 % | **−97 %** | 0.12 | **−$45.9k** (XLF 2007-09) |
| Weekly ×2 martingale, 10 re-entries | 8 | 62 % | 25 % | 1,589 days | 0.6 % | **account wiped out (2009)** | 0.02 | −$84.0k (Nikkei 1990-95) |
| Weekly linear 1,2,3…, 5 re-entries | 16 | 75 % | 19 % | 723 days | 1.9 % | −26 % | 0.27 | −$15.4k |
| Weekly flat size, 5 re-entries | 16 | 75 % | 19 % | 723 days | 1.6 % | −14 % | 0.39 | −$4.1k |
| **Daily ×2 martingale, 5 re-entries** | 103 | 93 % | 6 % | 111 days (max 2.7 yrs) | **6.5 %** | **−42 %** | 0.41 | **−$26.9k** (Hang Seng 2021-22) |
| Daily ×2 martingale, 10 re-entries | 38 | 92 % | 5 % | 335 days | 9.7 % | **−148 % (wiped out)** | 0.23 | −$87.1k (Nikkei 1990-98) |
| Daily linear, 5 re-entries | 103 | 93 % | 6 % | 111 days | 2.3 % | −24 % | 0.37 | −$11.6k |
| Daily flat size, 5 re-entries | 103 | 93 % | 6 % | 111 days | 0.9 % | −7 % | 0.45 | −$3.5k |
| *For comparison: previous one-campaign design, daily 1 re-entry 2×, time stop* | 288 | – | – | ~1 month | 1.9 % | −11 % | **0.65** | −$1.9k |
| *For comparison: previous weekly linear, ~26-week time stop* | 43 | – | – | ~6 months | 2.9 % | −15 % | **0.55** | −$3.6k |

![old high](results/oldhigh/equity_oldhigh.png)

**What to take from it**

1. **The martingale feels great and fails badly.** 75 % (weekly) to 93 % (daily) of campaigns do get back to the old high. The rest are catastrophic: −92R in one weekly campaign (XLF, Aug 2007 → Jan 2009), and −54R daily (Hang Seng 2021-22). With 10 re-entries the account is wiped out on both timeframes (Nikkei 1990s, FTSE MIB 2008). These failures are the crash years.
2. **On weekly, "no stopping" locks the only slot for years.** The average campaign lasts 2 years. The Hang Seng campaign from the 9 of 2018-08-03 is **still open after 8 years**. Its 6th attempt is at 31× size (2× notional cap), entered at 15,994 with a stop at 14,770, and its target is the 2018 high of 33,484. Meanwhile every other weekly 9 since 2018 has been skipped.
3. **Daily works better than weekly with this exit**, because the 63-day high is close and campaigns resolve in about 4 months. The ×2 martingale makes 6.5 %/yr but with a −42 % drawdown and Sharpe 0.41. Scaled down to the same −11 % drawdown, it would make about 1.7 %/yr, less than the previous time-stop design (1.9 %/yr at Sharpe 0.65).
4. **If you want to run to the old high, keep the size flat.** Flat sizing gives the same 93 % / 75 % hit rate with a worst campaign of −7R (daily) and −8R (weekly). On daily the drawdown is −7 % at Sharpe 0.45. The higher win rate comes from the re-entries and the far target, not from increasing the size.
5. **Bottom line:** the earlier design is better than martingale-to-the-old-high on every risk-adjusted measure here: re-enter once (daily) or with 1,2,3 sizing (weekly), and exit on a time stop.

**Live under this rule** (latest close 2026-11-03, one campaign per book):
* **Weekly:** Hang Seng, as described in point 2. Last close 23,526.
* **Daily:** Hang Seng, 9 from 2026-07-02, first attempt (1×), entered at 23,554, stop 22,735.6, exit at 26,408.6. Last close 23,526.

Files: `results/oldhigh/` (grid of all 2,304 variants, campaigns, trades and equity per variant, summary.json). Reproduce with `python scripts/oldhigh_study.py && python scripts/oldhigh_charts.py`.

---

## Rule: only ONE DeMark-9 campaign at a time

A **campaign** starts at its first fill and lasts until its final exit, re-entries included. While a campaign is live, **no other 9 is played**, whichever instrument it comes from. A 9 whose first fill falls inside a live campaign is skipped completely.
* A 9 that is armed but never fills blocks nothing.
* If several 9s fill on the same day, the one with the **deepest sell-off** (largest drawdown from its 52-week or 252-day high) takes the slot.
* Weekly and daily are run as two separate books, each limited to one campaign.

Results are in `results/one_campaign/`. Reproduce with `MODE=one`, as shown in the Reproduce section.

| Same account: $100k, 0.5 % base risk, no compounding | Weekly 9, 5 re-entries ×2 | Weekly 9, 5 re-entries linear (1,2,3…) | Weekly 9, no re-entry | **Daily 9, 1 re-entry ×2** | Daily 9, 5 re-entries linear | Daily 9, no re-entry |
|---|---|---|---|---|---|---|
| Campaigns (1990–2026) | 43 | 43 | 92 | 288 | 283 | 377 |
| Campaign win rate | 53.5 % | 53.5 % | 22.8 % | 53.1 % | 53.7 % | 43.2 % |
| Avg PnL per campaign | **+5.94 R** | +4.88 R | +0.97 R | +0.49 R | +0.46 R | +0.21 R |
| Profit factor, in-sample → out-of-sample | 6.25 → **6.11** | 6.18 → 4.20 | 2.69 → 1.47 | 1.85 → 1.66 | 1.64 → 1.69 | 1.31 → 1.49 |
| Total PnL | +$128k | ≈ +$105k | +$45k | +$71k | +$65k | +$39k |
| PnL per year, % of capital | 3.5 % | 2.9 % | 1.2 % | 1.9 % | 1.8 % | 1.1 % |
| Max drawdown (daily mark-to-market) | −24.2 % | **−14.9 %** | −10.9 % | **−11.4 %** | −12.0 % | −17.8 % |
| Sharpe | 0.49 | **0.55** | 0.27 | **0.65** | 0.57 | 0.47 |
| Worst campaign | −$4.3k | −$3.6k | −$1.3k | −$1.9k | −$7.0k | −$1.1k |
| Max gross exposure | 2.3× | 1.8× | 1.7× | 1.0× | 1.0× | 0.7× |

![equity one campaign](results/one_campaign/equity_curves.png)

**What changes with one campaign at a time**

1. **Risk falls sharply.** The same weekly ×2 martingale goes from a −72 % to a **−24 %** max drawdown, and from 6.9× to 2.3× peak leverage. Daily goes from −43 % to **−11 %**. There is never more than one instrument's risk on the book.
2. **Profit falls too.** Only about 1.2 weekly campaigns (each ~6 months long) or ~8 daily campaigns fit per year, and average exposure is just 0.1–0.2×. So 0.5 % base risk is now very conservative. Everything scales linearly with base risk. For a ~20 % max drawdown you can risk about **0.67 %** on weekly-linear (≈3.8 %/yr) or **0.88 %** on daily one-re-entry (≈3.4 %/yr). Running **one weekly and one daily book together** gives 5.4 %/yr, −25.7 % max DD and Sharpe 0.67 at 0.5 % base risk, because the two books' daily PnL correlation is only 0.13.
3. **Re-entries matter even more now.** With one slot, a failed first attempt would otherwise waste months of capacity.
   * **Weekly:** the first attempt wins only 16 % of the time (+1.0R), but **re-entry #1 wins 46 % (+1.6R)**. With re-entries, average PnL per campaign rises from +0.97R to +5.9R and stays stable out-of-sample (PF 6.1).
   * **Daily:** re-entry #1 wins 60 % (+0.67R) vs 41 % (+0.18R) on the first attempt.
   * In practice weekly never needs more than 3 re-entries, and daily needs 1. Daily re-entry #2 loses money (−0.49R, 8 cases).
4. **Best sizing under this rule:**
   * **Weekly: linear (1, 2, 3…).** It has the best Sharpe (0.55) and return per unit of drawdown (0.19). ×2 makes ~20 % more profit but with 60 % more drawdown.
   * **Daily: one re-entry at 2×.**
5. **Which 9 gets the slot matters a lot on weekly.** Picking the **deepest** sell-off when several fire together gives +5.9R per campaign (PF 6.2). Picking the **shallowest** gives +2.4R (PF 1.7) with a 4× bigger drawdown. A random pick gives a median of +5.2R (PF 3.5, 90 % band 2.2–7.6). With only 43 campaigns, luck in which signal you take is a big part of the result. On daily the pick barely matters (0.41–0.46R).
6. **Don't re-optimize the rules under this constraint.** There are too few campaigns.
   * A full re-optimization picks a 40-day weekly hold (in-sample PF 4.4 → out-of-sample 2.6). On daily it picks perfected setups with a TDST target and falls from PF 1.84 to **1.05** out-of-sample.
   * The rules chosen on the many-campaign sample (6–7× more trades) hold up: weekly PF 6.25 → 6.11, daily 1.85 → 1.66. They are used above, and only the size scheme was chosen under the rule.
7. **The edge vs random gets harder to prove.** With so few trades, the TD9 results now fall inside the random-entry 90 % band on both timeframes:
   * weekly +5.9R vs random 0.5–7.7R
   * daily +0.46R vs random 0.20–0.50R

**Live state under this rule** (latest close 2026-11-03):
* **Weekly book:** the active campaign is **XLI (Industrials)**. Its 9 came on 2026-10-16. The first attempt was stopped, and re-entry #1 (2×) filled at 170.06 with a stop at 164.66. It took the slot after the XLF campaign (2026-03-16 → 2026-10-13) ended. The later weekly 9s are **skipped** under this rule: Euro Stoxx 50, IBEX, FTSE MIB, Russell 2000, CAC 40, Hang Seng, XLU and XLRE.
* **Daily book:** no campaign is live. Armed buy-stops are Nasdaq 100 (29,936.29), IBEX (19,149.94, new 9 on 2026-11-03) and XLC (104.72). The first one to fill takes the slot. Full table: `results/one_campaign/live_sequences_{W,D}.csv`.

---

## Earlier version: many campaigns at once (one per instrument)

### TL;DR for the many-campaigns version

| | Weekly 9, 5 re-entries (geo ×2) | Weekly 9, no re-entry | Daily 9, 5 re-entries (linear) | **Daily 9, 1 re-entry ×2 (recommended)** | Equal-weight buy & hold |
|---|---|---|---|---|---|
| Sequences (signals traded) | 319 | 321 | 1,605 | 1,605 | – |
| Sequence win rate | 55.8 % | 29.0 % | 55.1 % | 54.7 % | – |
| Avg PnL per sequence | **+3.11 R** | +1.04 R | +0.43 R | +0.42 R | – |
| Profit factor (sequences) | 3.12 | 2.46 | 1.72 | 1.73 | – |
| **Total PnL on $100k** (0.5 % base risk, no compounding) | **+$496k** | +$167k | +$343k | +$340k | – |
| PnL per year, % of capital | 13.5 % | 4.6 % | 9.3 % | 9.2 % | 9.7 % CAGR |
| **Max drawdown, % of capital** | **−72 %** | −30 % | −51 % | −43 % | −52 % |
| Sharpe (daily MTM) | 0.59 | 0.51 | 0.76 (OOS 1.04) | **0.79** | 0.68 |
| Worst single sequence | **−$20.0k** | −$1.3k | −$7.0k | −$2.2k | – |
| Max gross exposure | 6.9× | 3.1× | 4.5× | 4.5× | 1× |

![equity](results/equity_curves.png)

**What to take away**

1. **Weekly 9 is a "buy the sell-off and hold" trade, not a quick bounce trade.** The best weekly rules use **no profit target**, a **~26-week time stop**, entry at the **next open** after the 9, and the stop **exactly at the 9-candle low** (no buffer). Tight targets (1–2R) destroy the edge because rebounds after a weekly 9 run for months. The median R/year across the whole grid falls in this order: no target > TDST > 3R > 2R > 1.5R > 1R.
2. **Daily 9 is a short-term trade, and the edge sits in the first re-entry.** On its own the first daily attempt barely breaks even (+0.17R, no better than random). **Re-entry #1** (price takes out the 9-candle high + 0.5 ATR after a stop-out) earns **+0.70R with a 59 % win rate**. Re-entries #2–#5 almost never trigger (20 times in 36 years with a 20-day window), so on daily, **"5 re-entries" in practice means "1 re-entry at 2×"**.
3. **Bigger size on re-entries mostly just adds leverage.** On weekly, re-entries keep a similar edge to the first attempt (+0.9R, +0.7R, +1.1R… per unit of own risk), so a geometric size-up raises profit, but drawdown rises almost one for one (risk-adjusted return MAR goes from 0.15 to 0.19). The ×2 martingale can lose **20 % of capital in one sequence** and needs up to **6.9× gross exposure**. If you want to size up, use a **linear** progression (1, 2, 3…) or **×1.5**, not ×2.
4. **Is DeMark itself the edge? A placebo test.** The placebo runs the same rules on random bars from the same instruments and the same sell-off state:
   * **Daily:** real TD9 hold-20d gives **+1.03 %** vs **+0.69 %** random (90 % band 0.56–0.85). The full design earns **0.43R** vs **0.31R** random (band 0.23–0.39). **The daily TD9 has a real short-term edge.**
   * **Weekly:** real TD9 hold-26w gives **+5.9 %** vs **+4.4 %** random (band 3.0–5.9), right at the top of the random band. With the re-entry rules, real **3.11R** vs random **3.42R**. **Most of the weekly profit is long-equity drift plus position sizing, not timing.**
5. **Deeper sell-offs are worse, not better.** Requiring the 9 to come with a ≥10–15 % drawdown lowers results on both timeframes. Deep drawdowns are bear markets (2001-02, 2008), where 9s fail one after another. **The max drawdown bottoms in March 2009 in every variant**, so 2008 dominates the risk.
6. **Filters that don't help:** a *perfected* setup (worse), a buy-stop entry on weekly (worse; the weekly high is too far away), and stop buffers on weekly (worse).
7. **The main risk is correlation.** The 27 instruments sell off together, so a crash triggers many 9s at once. Capping open sequences (2/3/5/8) lowers drawdown but lowers PnL proportionally, so MAR does not improve. **The cheapest risk control is a smaller base risk.** Everything scales linearly. For a ~25 % max drawdown, use ≈0.17 % base risk on the weekly ×2 design, ≈0.29 % on daily 1× re-entry, or ≈0.42 % on weekly with no re-entry.
8. **Robustness:** the weekly parameter ranking is stable in-sample vs out-of-sample (rank correlation 0.67 across 90,720 configs). The daily ranking is not (0.13), so don't over-tune daily parameters. The chosen daily config still did better out-of-sample (Sharpe 1.04).

---

## Strategy rules (as simulated)

**Signal: TD buy setup 9.** It needs 9 consecutive closes below the close 4 bars earlier, after a bearish price flip. Bar 9 is the *signal candle*. The signal is known at bar 9's close; for weekly that is the last trading day of the week.

**Per signal ("sequence"):**

| Element | Rule | Optimized over |
|---|---|---|
| Initial entry | `next_open` (buy next session's open) or `break_high` (buy-stop above the candle high) | both |
| Stop-loss | candle low − buf × ATR(14) of the signal timeframe; the same stop for every attempt | buf ∈ {0, 0.1, 0.25, 0.5} |
| Re-entry trigger | candle high + buf × ATR (buy-stop) after a stop-out | ↑ |
| Re-entries | up to *m* re-entries | m ∈ {0…5} |
| Size of attempt k | base risk × w_k, with w = flat (1,1,1,…), linear (1,2,3,…), ×1.5, ×2 | 4 schemes |
| Profit exit | target at 1/1.5/2/3 R, TDST (highest high of the setup), or none | 6 options |
| Time exit | close after N days in the trade | weekly 40/65/130 d, daily 5/10/20 d |
| Re-entry window | re-entries allowed only within N days of the signal | weekly 20/65/130 d, daily 5/10/20 d |
| Sell-off filter | drawdown at the 9 vs the 52-week (weekly) or 252-day (daily) max close | weekly 0–20 %, daily 0–15 % |
| Perfected filter | low of bar 8 or 9 ≤ lows of bars 6 and 7 | on/off |

A sequence ends when one of these happens:
* a winning or time exit
* all allowed attempts are used up
* the re-entry window expires while flat
* a newer 9 on the same instrument appears while flat

Each instrument has one sequence at a time.

**Execution realism**
* Weekly signals are also **executed on daily bars**. Each day's path is O→H→L→C or O→L→H→C, whichever extreme is nearer the open is visited first. Stops and buy-stops that gap through fill at the open.
* Costs are **3 bps per side** on notional.
* Size is fixed from the *planned* entry, so a gap fill costs extra R.
* A stop is never sized tighter than 0.1 ATR.
* Notional is capped at **2× capital per position**. This cap binds for the large martingale attempts on daily.

**Account:** $100k, base risk 0.5 % ($500) on the first attempt. Risk is a fixed dollar amount (no compounding), and any number of instruments may be open at once. PnL is FX-neutral: each index is traded like a USD-quanto future.

**Optimization:** 4,320 path configs × 21 (re-entries × sizing) = 90,720 configs per timeframe. Configs are selected by **in-sample MAR** (R per year ÷ max drawdown in R) with at least 60 weekly or 250 daily sequences, then checked out-of-sample.

## Universe

* **DM indices (16):** S&P 500, Nasdaq 100, Dow 30, Russell 2000, S&P/TSX, Euro Stoxx 50, DAX, FTSE 100, CAC 40, AEX, IBEX 35, SMI, FTSE MIB, Nikkei 225, ASX 200, Hang Seng
* **US sectors (11):** SPDR sector ETFs XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB, XLRE, XLC (dividend-adjusted)

Each series starts at its first date with real OHLC candles. Before that, Yahoo has close-only data for some indices (DAX before 1994, FTSE MIB before 2004, ASX before 2001).

## Detailed results

### The value of each re-entry (avg R in units of that attempt's *own* risk)

![attempts](results/expectancy_by_attempt.png)

| Attempt | Weekly n | Weekly win % | Weekly avg R | Daily n | Daily win % | Daily avg R |
|---|---|---|---|---|---|---|
| initial | 319 | 28.8 | +0.92 | 1,605 | 45.2 | +0.17 |
| re-entry 1 | 158 | 41.1 | +0.88 | 297 | **58.9** | **+0.70** |
| re-entry 2 | 47 | 34.0 | +0.67 | 20 | 50.0 | +0.04 |
| re-entry 3 | 16 | 37.5 | +1.10 | 0 | – | – |
| re-entry 4 | 8 | 37.5 | +0.41 | 0 | – | – |
| re-entry 5 | 4 | 50.0 | +3.15 | 0 | – | – |

Weekly re-entries 3–5 rest on very few cases (16/8/4), so don't rely on those numbers.

### Re-entries × size scheme: return vs drawdown

![risk-return](results/reentry_risk_return.png)

Full tables are in `results/risk_table_W.csv` and `results/risk_table_D.csv`.

### Best weekly configs, in-sample → out-of-sample (R per year)

| Config | IS R/yr | IS MAR | OOS R/yr | OOS MAR |
|---|---|---|---|---|
| next_open, buf 0, no target, 130 d, m=4 ×2, perfected only | 19.3 | 0.20 | 14.8 | 0.11 |
| same, all 9s | 25.8 | 0.19 | 20.3 | 0.15 |
| same, all 9s, m=5 ×2 (design) | 25.2 | 0.19 | 29.8 | 0.26 |

More rows are in `results/top25_IS_W.csv` and `results/top25_IS_D.csv`.

### PnL by instrument (weekly design)

Every instrument except ASX 200, IBEX 35 and Euro Stoxx 50 is profitable. The best are Nikkei (+$75k), Russell 2000, CAC 40, Nasdaq 100 and Dow 30. DM indices made +$368k and US sectors +$129k. Daily per-instrument PnL is in `results/summary.json`.

## Live state (as of the 2026-11-03 close; weekly as of the week ending 2026-10-30)

Running the same engine on today's data gives the following model states. They are for research and are not investment advice.

**Weekly design** (stop = 9-candle low, re-entry = 9-candle high):

| Instrument | Weekly 9 on | Stop | Re-entry trigger | State |
|---|---|---|---|---|
| Russell 2000 | 2026-10-30 | 2,778.17 | 2,868.37 | in position (attempt 1, 1×) |
| Euro Stoxx 50 | 2026-10-30 | 6,061.50 | 6,222.72 | in position (1×) |
| IBEX 35 | 2026-10-30 | 18,643.70 | 19,187.40 | in position (1×) |
| FTSE MIB | 2026-10-30 | 48,674 | 50,145 | in position (1×) |
| CAC 40 | 2026-10-23 | 7,728.45 | 7,926.38 | in position (1×) |
| Hang Seng | 2026-10-23 | 22,803.77 | 24,139.11 | in position (1×) |
| XLI Industrials | 2026-10-16 | 164.66 | 170.06 | in position (**re-entry 1, 2×**) |
| XLU Utilities | 2026-09-25 | 39.13 | 40.93 | in position (**re-entry 1, 2×**) |
| XLRE Real Estate | 2026-10-09 | 40.28 | 41.69 | in position (1×) |

This is a cluster of weekly 9s across Europe, small caps and Hong Kong. Historically, clusters like this are both the best rebounds (2009, 2003) and the worst losses (2008), so keep the **total** risk in mind. The daily states (armed buy-stops on Nasdaq 100 and XLC, Hang Seng and XLK waiting for a 2× re-entry, a new IBEX daily 9) are in `results/live_sequences_D.csv`.

## Files

```
strategy/
  universe.py   instruments + clean start dates
  data.py       Yahoo download/cache, weekly candles
  demark.py     TD buy setup count, setup-9 signals, perfection, TDST, ATR
  engine.py     per-signal state machine: entry, stop, re-entry, target/time exit (daily path)
  backtest.py   signal prep, path runs, sequence selection (per instrument / one campaign at a time),
                sizing, metrics, MTM equity, placebo
  fastagg.py    vectorized aggregation used by the optimizer
scripts/
  optimize.py      grid search  -> results/grid_{W,D}.csv.gz (not committed, ~3.5 min)
  run_backtest.py  picks configs (in-sample), detail runs, placebo, risk tables, live state
  make_charts.py   PNG charts
  oldhigh_study.py martingale-until-the-old-high study (no time stop) -> results/oldhigh/
  oldhigh_charts.py its equity chart
tests/test_engine.py
results/        many-campaigns run: summary.json, equity_*.csv, trades_*.csv, risk/concurrency tables, live state, charts
results/one_campaign/   the same outputs under the one-campaign-at-a-time rule (+ priority_*.csv tie-break test)
```

## Reproduce

```bash
pip install -r requirements.txt
```

```bash
python scripts/optimize.py both
```

```bash
MODE=one python scripts/optimize.py both
```

```bash
python scripts/run_backtest.py && python scripts/make_charts.py
```

```bash
MODE=one python scripts/run_backtest.py && MODE=one python scripts/make_charts.py
```

```bash
python -m pytest -q tests
```

Set `DATA_CUTOFF=YYYY-MM-DD` to drop bars on or after a date. The default drops 2026-11-04, the session that was still forming.

## Caveats

* The indices are price indices without dividends, and they are not directly tradable. Futures and ETFs have roll costs, financing and tracking differences. Costs are modeled flat at 3 bps per side.
* Intraday order of high and low is a heuristic. Same-day stop and re-entry fills are approximations.
* Results are on a fixed $ risk with no compounding and no portfolio-level risk cap. Leverage reaches 4–7× gross in clusters.
* The best configs sit at the edge of the grid: no target, the longest time stop, the longest window. On weekly this shows the edge comes from holding long equities. Extending the grid further would mostly add more beta.
* The universe has survivorship-free index levels but is concentrated in correlated developed markets.
