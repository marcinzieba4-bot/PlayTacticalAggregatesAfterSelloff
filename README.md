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

## Weekly MACD as the only signal (no DeMark): MACD stop, 1-year exit, max 3 assets

Rules (`scripts/macd_only_study.py`, results in `results/macd_only/`):

* **Signal:** the weekly close where **both the MACD line (EMA12 − EMA26, "fast") and its signal line (EMA9 of MACD, "slow") are above 0** for the first time in a new up-phase. **Buy at the next open.**
* **Stop-loss:** the first weekly close with the **MACD line below 0**, exit at the next open. **Take-profit:** exit after **1 year** in the position.
* **Max 3 assets at once.** Each new position gets 1/3 of current equity, with compounding and no leverage; 3 bps per side. If several turn on in the same week, the strongest MACD (as % of price) goes first.
  * Asked version ("fresh only"): a signal that finds no free slot is lost.
  * "Queue" variant: an asset still in an untraded up-phase can take a slot later, freshest up-phase first. One trade per up-phase.

| Compounded, 1990-2026 | Trades | Win % | Avg trade | Exit after 1 year (avg) | Stopped by MACD < 0 (avg) | CAGR (in / out of sample) | Max DD | Sharpe | Invested |
|---|---|---|---|---|---|---|---|---|---|
| **MACD signal, max 3 (asked)** | 133 (3.6/yr) | 48 % | **+7.8 %** | 40 % (**+26.0 %**) | 59 % (**−4.4 %**) | **8.5 %** (7.4 / 10.3) | **−26 %** | **0.79** | 72 % |
| Queue: free slot to the freshest up-phase | 195 | 44 % | +5.9 % | 30 % (+27.9 %) | 70 % (−3.4 %) | 9.3 % (9.1 / 9.5) | −32 % | 0.69 | 90 % |
| Stop on the signal line < 0 instead | 116 | 55 % | +8.8 % | 50 % | 50 % (−5.9 %) | 8.1 % | −31 % | 0.75 | 72 % |
| MACD stop only, no 1-year exit | 90 | 46 % | +12.1 % | – | 100 % | 9.4 % | −33 % | 0.75 | 86 % |
| MACD stop, hold up to 2 years | 109 | 44 % | +10.9 % | 16 % (+57 %) | 84 % | 9.2 % | −29 % | 0.74 | 83 % |
| 1-year exit only, no stop | 89 | 76 % | +14.0 % | 100 % | – | 10.1 % (7.7 / 14.2) | −31 % | 0.86 | 79 % |
| Max 1 asset | 50 | 49 % | +9.0 % | 39 % | 61 % | 9.9 % | −35 % | 0.65 | 78 % |
| Max 5 assets | 204 | 48 % | +7.5 % | 39 % | 61 % | 7.6 % | −27 % | 0.78 | 67 % |
| *Equal-weight buy & hold, all 27* | – | – | – | – | – | **9.7 %** | −52 % | 0.68 | 100 % |
| *S&P 500 buy & hold (price)* | – | – | – | – | – | 8.6 % | −57 % | 0.55 | 100 % |

![macd only](results/macd_only/equity_macd_only.png)

**What to take from it**

1. **This is the best risk-adjusted design in the project.** With the asked rules you get about the S&P 500's return (8.5 % vs 8.6 % CAGR) with **half the drawdown** (−26 % vs −57 %) and a higher Sharpe (0.79 vs 0.55; 0.68 for equal-weight buy & hold). It holds up out-of-sample: 10.3 % CAGR from 2013 to 2026.
2. **It is a classic trend-following payoff.** Most trades lose a little: 59 % are stopped at about −4 %, and the worst trade is only −12.8 %. The 40 % that survive the year make about +26 %. Best trades: Nasdaq 100 1998 (+79 %), Nikkei 2013 (+63 %), Nasdaq and XLK after COVID (+58 %).
3. **The MACD stop is what keeps the drawdown small.** It cut the 2001-02 and 2008 bear markets short: the worst years were −15 % (2022), −15 % (2001) and −14 % (2008), while buy & hold fell about −50 %. Dropping the stop and only exiting after 1 year gives a higher Sharpe (0.86) and 10.1 % CAGR, but single trades can lose −37 % and the result leans on 2013-2026. That makes it riskier than it looks.
4. **Three assets at once is about right.** One asset is too concentrated (−35 % DD). Five is safer (−27 %) but earns less (7.6 %). The queue variant (always keeping 3 slots full) earns 9.3 % but with a deeper −32 % drawdown.
5. **What to use:** the asked rules as they are, or with the slower signal-line stop (8.1 %, Sharpe 0.75). Don't tune further: every variant lands between 7.6 % and 10 % CAGR. Most of the profit came from tech and Japan (XLK, Nasdaq 100, Nikkei); the losers were AEX, ASX 200 and Health Care.

**Live under the asked rules** (latest close 2026-11-03), all 3 slots full:

| Asset | Up-phase started | Entered | Entry | Last close | Open P&L | 1-year exit |
|---|---|---|---|---|---|---|
| XLB Materials | 2025-12-12 | 2025-12-15 | 44.61 | 52.59 | +17.8 % | 2026-12-15 |
| Nasdaq 100 | 2026-04-10 | 2026-04-13 | 25,069 | 28,180 | +12.3 % | 2027-04-13 |
| DAX | 2026-05-08 | 2026-05-11 | 24,333 | 25,865 | +6.2 % | 2027-05-11 |

* **Weekly MACD and signal are both above 0 now (19 assets):** S&P 500, Nasdaq 100, Dow, Russell 2000, TSX, Euro Stoxx 50, DAX, FTSE 100, AEX, IBEX, SMI, FTSE MIB, Nikkei, and the sectors XLK, XLF, XLE, XLV, XLP, XLB.
* **Not on (8 assets):** CAC 40, ASX 200, Hang Seng, XLI, XLY, XLU, XLRE, XLC.

These are backtest model states, not investment advice.

Reproduce: `python scripts/macd_only_study.py && python scripts/macd_only_charts.py`.

---

## (First reading of the MACD idea) DeMark 9 only in an uptrend: weekly MACD filter, MACD stop, 1-year exit, max 3 assets

Rules (`scripts/macd_study.py`, results in `results/macd/`):

* **Signal:** a TD buy setup 9, taken **only if the weekly MACD line (EMA12 − EMA26) and its signal line (EMA9 of MACD) are both above 0**. Both are read at the last completed week.
  * Run as a weekly-9 book and as a daily-9 book. Both use the *weekly* MACD.
* **Entry** at the next open. **Stop-loss:** the first weekly close with the MACD line below 0, exit at the next open. **Take-profit:** exit after **1 year** in the position.
* **Max 3 assets at once.** Each new position gets 1/3 of current equity, with compounding and no leverage. Ties go to the deepest sell-off; 3 bps per side.

| Compounded, 1990-2026 | Trades | Win % | Avg trade | Exit at 1 year (avg) | Exit on MACD < 0 (avg) | CAGR | Max DD | Sharpe | Time invested |
|---|---|---|---|---|---|---|---|---|---|
| **Weekly 9 + MACD filter** | 38 | 37 % | +3.3 % | 18 % of trades (+24.1 %) | 74 % (−1.9 %) | 1.1 % | −7 % | 0.42 | 9 % |
| **Daily 9 + MACD filter** | 195 | 38 % | +3.2 % | 22 % (+26.6 %) | 77 % (−3.4 %) | **4.7 %** | **−35 %** | 0.43 | 72 % |
| Daily, stop on the *signal* line < 0 instead | 152 | 47 % | +5.2 % | 34 % (+24.0 %) | 64 % (−4.6 %) | 6.2 % | −33 % | 0.54 | 77 % |
| Daily, MACD stop, hold up to 2 years | 146 | 41 % | +7.3 % | 8 % (+59 %) | 90 % (+2.6 %) | 7.8 % | −39 % | 0.60 | 78 % |
| Daily, MACD filter, no stop (1 year only) | 97 | 67 % | +5.6 % | 97 % | – | 4.1 % | −50 % | 0.35 | 86 % |
| Daily, same rules on *random* filtered days (30 draws) | – | – | +5.6 % | – | – | 6.4 % (5.1–7.5) | −38 % | 0.55 (0.46–0.65) | – |
| Equal-weight buy & hold of all 27 | – | – | – | – | – | **9.7 %** | −52 % | **0.68** | 100 % |
| S&P 500 buy & hold (price) | – | – | – | – | – | 8.6 % | −57 % | 0.55 | 100 % |

![macd](results/macd/equity_macd.png)

**What to take from it**

1. **Weekly 9 plus a positive weekly MACD almost never happens.** Nine weeks of lower closes usually push the weekly MACD below zero. That left 38 trades in 36 years, with the money in the market only 9 % of the time. The result is a safe (−7 % max DD) but nearly idle 1.1 %/yr. As a weekly strategy this filter mostly switches the 9 off.
2. **Daily 9 plus a positive weekly MACD is a trend-following profile.** You lose small on most trades: 77 % are stopped at about −3 %. You win big on the 22 % that make it to the 1-year exit (about +27 %). The result is a 4.7 % CAGR with a −35 % max DD. The worst losses come from fast crashes, which the weekly MACD reacts to too late: COVID in March 2020 cost −27 % on XLF and −26 % on AEX within 2 weeks, and 2001 cost −20 %.
3. **The 9 does not add value inside this filter.** Entering on random days that pass the same MACD > 0 test, with the same stop, exit and 3 slots, gives a better 6.4 % CAGR and 0.55 Sharpe. The real 9 lands below the random 5th percentile. In an uptrend, a 9-day pullback is more often the start of a trend break than a dip worth buying.
4. **The stop and exit are better looser.** Exiting on the signal line < 0 (slower than the MACD line) gives 6.2 % CAGR and Sharpe 0.54. Holding winners 2 years instead of 1 gives 7.8 % CAGR and Sharpe 0.60. Both hold up in-sample and out-of-sample: 5.7 → 7.1 % and 7.9 → 7.5 % CAGR. Max 1 asset is too concentrated (−60 % DD), and max 5 is no better than 3.
5. **None of the versions beats simply holding the 27 instruments** (9.7 % CAGR, Sharpe 0.68). What this rule set gives you is a smaller drawdown (−33 % to −39 % vs −52 %) for less return. With the MACD filter on, the best-scoring choices are the loosest: signal-line stop and 2-year hold.

**Live under the asked rules** (latest close 2026-11-03):
* **Weekly book:**
  * Holding: S&P 500 (9 of 2026-04-02, entered at 6,587.66, now +14.9 %, exit by 2027-04-06), Russell 2000 and FTSE MIB (entered 2026-11-02).
  * IBEX 35 and Euro Stoxx 50 had filtered 9s the same week but no free slot.
* **Daily book:**
  * Holding: SMI (+15.4 %, exit by 2027-03-13), XLE Energy (+21.5 %, exit by 2027-04-15) and Dow 30 (+0.7 %, exit by 2027-10-06).
  * Russell 2000, Nasdaq 100 and XLK had filtered 9s in late October but no free slot.

Reproduce: `python scripts/macd_study.py && python scripts/macd_charts.py`.

---

## Averaging-down grid with no stop-loss, exit at a 30 % retracement, max 3 assets

Rules (`scripts/grid_study.py`, results in `results/grid/`):

* **Target T:** the sell-off low + **30 %** × (old high − low). This is the 30 % retracement of the drop.
  * Old high = highest high of the 52 weeks (weekly) or 63 days (daily) before the 9.
  * Low = lowest low between that high and the 9.
  * 26-week and 252-day highs, and a 50 % retracement, were also tested.
* **Grid:** a level every **1 %** below T (2 % also tested). Hold *n* units: the next sell is 1 % higher and the next buy 1 % lower.
* **No stop-loss.** Each 1 % fall buys 1 unit. Each 1 % rise sells 1 unit, the last one bought.
* **Starting size:** at the 9 (next open) buy *j₀* units, where *j₀* is the number of 1 % steps from the entry up to T. Selling one unit per 1 % up-step then reaches **0 exactly at the 30 % retracement**, where the campaign ends. On average weekly starts with 5.6 units and daily with 2.2.
* **Unit:** 1 % of capital ($1,000 notional on $100k, fixed, no compounding). Costs are 3 bps per fill.
* **Max 3 assets at once.** First come, first served; same-day ties go to the deepest sell-off. A new 9 on an asset already in a campaign is ignored.

| Unit = 1 % of capital, step 1 %, 30 % retracement | Weekly 9 (52-week high) | Daily 9 (63-day high) |
|---|---|---|
| Campaigns 1990-2026 | 96 | 284 |
| Reached the 30 % retracement (position 0) | **99 %**. Every completed campaign is profitable. | **99 %** (98 % of them profitable) |
| Median / longest campaign | 14 days / **15.5 years** (FTSE MIB 2008 → 2024) | 6 days / **33 years** (Nikkei 1990 → 2023) |
| Most units held in one campaign | 140 (XLK Nov 2000 → Jul 2014) | 148 (Nikkei) |
| Worst open (unrealised) loss in one campaign | **−$48.6k** (XLK 2002) | **−$43.7k** (Nikkei) |
| Peak long exposure | 1.8× capital | 1.9× capital |
| PnL per year (% of capital) | 4.7 % | 5.0 % |
| **Max drawdown** | **−70 %** (Jan 2001 → Oct 2002) | **−85 %** (Oct 2007 → Mar 2009) |
| Sharpe | 0.31 | 0.28 |
| Unit size for a 25 % max drawdown → PnL/yr | $358 → 1.7 %/yr | $296 → 1.5 %/yr |
| Open now | Hang Seng (9 of 2026-10-23): 5 units from 23,157, target 24,179 | CAC 40 (target 8,535), ASX 200 (9,029), XLC (106.52) |

![grid](results/grid/equity_grid.png)

**What to take from it**

1. **It almost never loses a campaign, and that is the catch.** 99 % of campaigns end at the 30 % retracement in profit. But a few campaigns in long bear markets sit underwater for 10–30 years while the position keeps growing (Nasdaq 2001 → 2012, XLK 2000 → 2014, FTSE MIB 2008 → 2024, Nikkei 1990 → 2023). They eventually close in profit, and they are where most of the PnL comes from. Along the way the account falls 70–85 % and uses up to 1.9× leverage.
2. **The 3-asset cap does not protect you.** In 2000-02 and 2008 the three slots fill with the first three sell-offs and stay stuck for years. There is no stop, so nothing frees them.
3. **A wider step is better.** 2 % steps hold half the units for the same campaign, which roughly halves the drawdown (weekly −32 %, daily −40 %) and lifts Sharpe to 0.34–0.36. A 50 % retracement makes slightly more but campaigns last longer and drawdowns are deeper.
4. **Risk-adjusted it is the weakest design so far.**
   * This grid: Sharpe 0.28–0.36.
   * Earlier time-stop designs: Sharpe 0.55–0.79.
   * Equal-weight buy & hold: Sharpe 0.68.
   * At the same 25 % max drawdown, this grid makes about 1.5–1.7 %/yr. The weekly 1,2,3-sizing time-stop design makes about 4.8 %/yr and daily 1 re-entry at 2× about 4.2 %/yr.
5. **If you still want to run it:**
   * Use 2 % steps and a unit of no more than 0.35–0.6 % of capital, which keeps the historical drawdown near 25 %.
   * Accept that a campaign can tie up a slot for a decade.
   * The grid only works if you can keep adding while down 50 %+, so check margin and funding.

Reproduce: `python scripts/grid_study.py && python scripts/grid_charts.py`.

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
  grid_study.py    averaging-down grid, no stop, exit at 30 % retracement, max 3 assets -> results/grid/
  grid_charts.py   its chart
  macd_study.py    DeMark 9 with weekly MACD > 0 filter, MACD < 0 stop, 1-year exit, max 3 assets -> results/macd/
  macd_charts.py   its chart
  macd_only_study.py  weekly MACD as the only signal, MACD < 0 stop, 1-year exit, max 3 assets -> results/macd_only/
  macd_only_charts.py its chart
strategy/grid.py   the grid engine (levels, LIFO units, starting size j0)
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
