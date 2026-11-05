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

## Weekly-MACD strategy: 1 % stop with re-entry, 1 % ladder / martingale, take-profit grid

These tests start from the MACD-only strategy above: a new up-phase signal, the MACD < 0 stop, max 3 assets with 1/3 of equity each, and compounding. Scripts: `scripts/macd_variants_study.py` and `strategy/macd_engine.py`; results in `results/macd_variants/`.

* **1 % stop + re-entry at the first entry point:** stop 1 % below the first entry price E0. After a stop-out, re-enter on a buy-stop at E0, any number of times while the MACD trend lasts. The size is the same each time. 2 %, 3 % and 5 % stops were also tested.
* **1 % ladder / martingale:** buy more every 1 % below E0. Martingale sizes are 1, 2, 4, 8, 16, 32 (5 steps); flat sizes are 1 unit per step (10 steps). The full ladder is sized to the slot's 1/3 of equity, so there is no leverage. The only stop is MACD < 0, as usual.
* **Take-profit grid:** time of 3 months / 6 months / 1 year / 2 years / none × level of +5 / +10 / +20 / +30 % / none. The level is measured from E0, or from the average cost for the ladder.

| Take-profit 1 year, no level | Campaigns | Win % | Avg campaign | Stop-outs per campaign | CAGR (in / out of sample) | Max DD | Sharpe | Invested |
|---|---|---|---|---|---|---|---|---|
| **Base (no price stop)** | 133 | 48 % | +7.8 % | – | **8.5 %** (7.4 / 10.3) | **−26 %** | **0.79** | 69 % |
| 1 % stop, re-entry at E0 | 133 | 43 % | +7.0 % | 2.9 (max 14) | 7.7 % (6.8 / 9.2) | −28 % | 0.77 | 63 % |
| 2 % / 3 % / 5 % stop, re-entry at E0 | 133 | 43-45 % | +6.8 to +7.3 % | 1.7 / 1.1 / 0.5 | 7.3 / 7.5 / 8.0 % | −30 to −33 % | 0.73-0.76 | 65-67 % |
| Martingale ladder ×2, 1 % step, 5 steps | 133 | 62 % | +1.9 % | – | 2.1 % | −19 % | 0.43 | 19 % |
| Martingale ladder ×2, 7 steps | 133 | 67 % | +1.0 % | – | 1.2 % | −16 % | 0.32 | 11 % |
| Flat ladder, 1 % step, 10 steps | 133 | 56 % | +2.3 % | – | 2.6 % | −13 % | 0.55 | 22 % |

![variants](results/macd_variants/macd_variants.png)

**What to take from it**

1. **The 1 % stop with re-entry doesn't help.** In a weekly uptrend a 1 % stop is just daily noise. You get stopped about 3 times per campaign (up to 14 times: XLI 2023, CAC 2025-26) and buy back at the same price. That costs about 0.8 %/yr of CAGR with no drawdown benefit (−28 % vs −26 %). Wider stops move steadily back toward the base result (5 % stop: 8.0 %), which shows the extra stop has no edge.
2. **The ladder / martingale doesn't help either.** With no leverage it leaves most of the money idle: 11-22 % invested on average, versus 69 % for the base. Return per unit invested is about the same (11-12 % vs 12.2 %), so buying lower adds nothing. The ×2 martingale has the worst Sharpe (0.32-0.43): its biggest buys land in the pullbacks that turn into the MACD < 0 exit. Levering it up to the base's exposure would give a worse result than the base.
3. **Take-profit:**
   * **Time:** longer means more return but a deeper drawdown. No time exit gives 9.4 % CAGR at −33 %; 2 years gives 9.1 % at −29 %. **1 year is the Sharpe sweet spot (0.79).**
   * **Level:** a tight target kills the edge, because the winners are what pay for the many small MACD stop losses. +5 % gives 3.6 % CAGR and Sharpe 0.50; +10 % gives 5.7 %. +30 % is about neutral. **No level target is best.**
   * Lowest drawdown with a decent Sharpe: 6 months / +20 % gives 6.9 % CAGR, −22 % DD, Sharpe 0.75.
   * The top Sharpe cells for the 1 % stop variant (0.80 at 6 m / +20 % and 2 y / +30 %) only tie the base, and the first one is unstable: 4.2 % in-sample vs 9.6 % out-of-sample.
4. **Bottom line:** keep the plain rules. Buy the new MACD up-phase, use no price stop, exit when MACD < 0 or after 1 year, with no level target. If you want a smaller drawdown, use 6 months / +20 % and accept about 1.6 %/yr less return. Neither the 1 % stop nor the martingale ladder improves anything.

Reproduce: `python scripts/macd_variants_study.py && python scripts/macd_variants_charts.py`.

---

## MACD long strategy only when the S&P 500 is above its 100-day average

Scripts: `scripts/macd_regime_study.py` and `scripts/macd_regime_charts.py`; results in `results/macd_regime/`.

Rules:
* Same long rules on the 27 indices + sectors: a new weekly MACD up-phase is the signal, MACD < 0 is the stop, 1-year exit, max 3 positions, 1/3 of equity each.
* **A signal is taken only if the S&P 500 closed above its 100-day simple moving average** on the signal day.
* Variants:
  * also sell everything when the S&P 500 closes below its average (checked daily or weekly);
  * also re-enter when the S&P 500 recovers, buying assets whose MACD up-phase is still intact;
  * 50- and 200-day averages;
  * the mirror-image short leg (worst MACD profile, only while the S&P 500 is below its average).

| 1990-2026, compounded | Trades | Win % | Avg trade | CAGR (in / out of sample) | Max DD | Sharpe |
|---|---|---|---|---|---|---|
| No filter (earlier rules) | 133 | 48 % | +7.8 % | 8.4 % (7.4 / 10.1) | −24 % | 0.80 |
| **Buy only if S&P > 100-day avg** | 110 | **56 %** | **+9.7 %** | **8.8 %** (8.3 / 9.6) | **−20 %** | **0.85** |
| Buy only if S&P > 200-day avg | 109 | 57 % | +9.7 % | 8.7 % (8.5 / 8.9) | −19 % | 0.86 |
| Buy only if S&P > 50-day avg | 125 | 49 % | +8.0 % | 8.1 % | −25 % | 0.77 |
| 100-day filter + sell all when S&P < avg (daily) | 188 | 51 % | +3.3 % | 5.2 % | −19 % | 0.67 |
| 100-day filter + sell all when S&P < avg (weekly) | 168 | 54 % | +4.0 % | 5.5 % | −22 % | 0.67 |
| 100-day filter + weekly sell + re-entry | 376 | 50 % | +3.0 % | 9.3 % (9.9 / 8.1) | −38 % | 0.79 |
| 200-day filter + daily sell + re-entry | 355 | 44 % | +3.4 % | 9.7 % (10.0 / 9.1) | −34 % | 0.87 |
| 1 % stop + re-entry, no filter | 133 | 43 % | +7.0 % | 7.6 % (6.8 / 8.9) | −27 % | 0.78 |
| **1 % stop + re-entry, S&P > 100-day filter** | 110 | 51 % | +8.5 % | 7.7 % (7.3 / 8.5) | −21 % | 0.81 |
| 1 % stop + re-entry, S&P > 200-day filter | 109 | 50 % | +8.6 % | 7.6 % (7.6 / 7.5) | **−17 %** | 0.81 |
| 2 % stop + re-entry, S&P > 100-day filter | 110 | 51 % | +8.7 % | 7.9 % | −23 % | 0.81 |
| 1 % stop, **entry AND re-entry** only while S&P > 100-day avg | 110 | 49 % | +8.1 % | 7.4 % (6.9 / 8.1) | −21 % | 0.79 |
| 1 % stop, entry and re-entry only while S&P > 200-day avg | 109 | 47 % | +8.1 % | 7.2 % (7.0 / 7.3) | −20 % | 0.78 |
| 2 % / 3 % stop, entry and re-entry only while S&P > 100-day avg | 110 | 51-52 % | +8.3-8.4 % | 7.6 % / 7.6 % | −21 / −22 % | 0.80 / 0.79 |
| *16 DM indices only:* no filter / 100-day filter | 125 / 110 | 46 / 50 % | | 6.9 % / 6.3 % | −23 / −25 % | 0.71 / 0.68 |
| *16 DM indices only, 1 % stop:* no filter / 100-day filter | 125 / 110 | 41 / 44 % | | 6.9 % / 6.2 % | −20 / **−16.5 %** | 0.76 / 0.73 |
| *16 DM indices only, 1 % stop, entry and re-entry filtered* | 110 | 44 % | | 5.9 % | −17 % | 0.70 |
| Worst-profile short only while S&P < 100-day avg | 280 | – | – | −2.5 % | −68 % | −0.16 |
| 100-day filtered long + that regime short | – | – | – | 6.3 % | −29 % | 0.49 |
| *S&P 500 buy & hold (price)* | – | – | – | 8.6 % | −57 % | 0.55 |
| *S&P 500 held only while above its 100-day avg* | – | – | – | 4.7 % | −51 % | 0.47 |

![regime](results/macd_regime/macd_regime.png)

**What to take from it**

1. **The S&P filter on entries is a real, if modest, improvement.** You skip signals that appear while the US market is in a correction. Trades drop from 133 to 110, the win rate rises from 48 % to 56 %, and the average trade from +7.8 % to +9.7 %. Overall: **8.8 %/yr, max DD −20 % (from −24 %), Sharpe 0.85 (from 0.80)**. The bad years get much milder: 2008 −6.7 % instead of −14.1 %, 2022 −5.5 % instead of −15.1 %. The cost is a smaller rebound year in 2020 (+10.9 % instead of +25.2 %).
2. **It is robust to the length of the average.** 200 days gives the same result (8.7 %, −19 %, Sharpe 0.86); only the noisy 50-day average is worse. Out-of-sample (2013-2026) the filter is about neutral (9.6 % vs 10.1 %), so treat it as **risk control**, not a return booster.
3. **Use it to filter entries, not to trigger exits.** Selling everything when the S&P dips below its average cuts CAGR to about 5 %. The S&P crossed its 100-day average 421 times in 36 years, so each position gets whipsawed out. 76-88 % of trades ended that way instead of by their own MACD stop. Even the S&P itself timed on its 100-day average only makes 4.7 %/yr. The asset's own weekly MACD is the better exit.
4. **Re-entry adds return but doubles the drawdown** (−34 to −38 %), because it buys into trends late after each crossing. That is not worth it.
5. **The short side doesn't improve with the regime either.** The worst-profile short, run only while the S&P is below its average, still loses 2.5 %/yr. Adding it to the long book drops the Sharpe to 0.49.
6. **The 1 % stop with re-entry does not add value on top of the filter (27 instruments).** It costs about 1 %/yr: 7.7 % vs 8.8 %, with a similar drawdown (−21 % vs −20 %) and Sharpe 0.81 vs 0.85. That matches the earlier finding on these 27: the 1 % stop only helped on single stocks and on the DM indices alone. With the stricter 200-day filter it gives the **lowest drawdown, −17 %**, at 7.6 %/yr. On the 16 DM indices alone the 1 % stop still trims the drawdown (−20 %, or −16.5 % with the filter), but the S&P filter itself doesn't help there: 6.3 % vs 6.9 %/yr, and only 4.2 % out-of-sample. A US regime says less about Europe and Asia. **Making the re-entries conditional too** (re-buy at the first entry price only while the S&P 500 is above its average) does *not* help either. It gives 7.4 %/yr, −21 % DD and Sharpe 0.79, versus 7.7 % / −21 % / 0.81 with unconditional re-entry and 8.8 % / −20 % / 0.85 with no stop. While the S&P is below its average the 1 % stop has already taken you out, so the extra condition mostly makes you miss the rebound. When the S&P recovers, the asset is often already above the entry price, so you re-buy at a higher open or not at all. The 200-day and 2-3 % stop versions tell the same story.
7. **Current state (2026-11-03):** the S&P 500 at 7,569 is **0.7 % below its 100-day average (7,619)**. That is above the 200-day (7,316) and below the 50-day (7,693). **The filter is OFF: no new MACD buys until the S&P closes back above about 7,620.** The open positions (XLB +17.8 %, Nasdaq 100 +12.4 %) are kept under their own MACD stop and 1-year exit. The DAX trade of May 2026 was never taken in the filtered book, because the S&P was below its average at the time. These are backtest model states, not investment advice.

Reproduce: `python scripts/macd_regime_study.py && python scripts/macd_regime_charts.py`.

---

## Drawdowns: how deep, how long under water, and when

Scripts: `scripts/drawdown_study.py` and `scripts/drawdown_charts.py`; results in `results/drawdowns/` (`episodes.csv` lists every drawdown episode). Same books as the section below, daily equity, idle cash in T-bills, 1997-2026 (the index books also 1990-2026). "Under water" = from a high-water mark until that high is regained.

| 1997-2026 | Max DD (peak → trough → recovered) | **Longest time under water** | Days > 10 % below the high | Ulcer index | Now (2026-11-03) |
|---|---|---|---|---|---|
| Indices, max 5 | −18 % (Apr 2015 → Jun 2016 → Feb 2017) | **3.7 years** (Mar 2000 → Dec 2003, depth −14 %) | 15 % | 6.1 | −0.8 % |
| Indices, max 3 | −18 % (Jul 2007 → Jul 2009 → Oct 2009) | 3.3 years (Sep 2000 → Dec 2003, −16 %) | 17 % | 6.9 | −2.4 % |
| Stocks, wait 1 m + S&P > 100d + 1 % stop | −18 % (Feb 2020 → Jun 2020 → Nov 2020) | 3.2 years (Aug 2000 → Oct 2003, −13 %) | 16 % | 6.6 | −8.9 % |
| Stocks, 6 m hold + 1 % stop | −23 % (Dec 2000 → Feb 2003 → Nov 2005) | **4.9 years** (Dec 2000 → Nov 2005, −23 %) | 18 % | 7.3 | −3.6 % |
| **50/50 indices (max 5) + stocks (wait 1 m)** | **−16 %** (Feb 2020 → Jun 2020 → Nov 2020) | **3.1 years** (Aug 2000 → Oct 2003, −12 %) | **10 %** | **5.6** | −4.5 % |
| 50/50 indices (max 3) + stocks (wait 1 m) | −16 % (Feb 2020 → Jun 2020 → Sep 2020) | 3.1 years (Sep 2000 → Oct 2003, −13 %) | 12 % | 5.9 | −5.2 % |
| 50/50 at ¼ Kelly (1.45×) | −23 % (Feb 2020 → Jun 2020 → Nov 2020) | 3.3 years (Aug 2000 → Dec 2003, −20 %) | 25 % | 8.6 | −6.8 % |
| *S&P 500 (price)* | *−57 % (Oct 2007 → Mar 2009 → Mar 2013)* | ***7.2 years*** *(Mar 2000 → May 2007, −49 %)* | *42 %* | *17.2* | *−3.2 %* |

The five deepest drawdowns of the 50/50 combination:

| # | Depth | Peak → trough → recovered | Time under water | What happened |
|---|---|---|---|---|
| 1 | −16.4 % | 19 Feb 2020 → 11 Jun 2020 → 24 Nov 2020 | 9 months | Covid crash: too fast for a weekly MACD exit, then whipsaws on re-entry in May-June |
| 2 | −14.2 % | 19 Jul 2007 → 8 Jul 2009 → 16 Sep 2009 | 2.2 years | Global financial crisis: a slow bleed of stopped trades; the filter kept the book mostly in cash during the crash itself |
| 3 | −13.8 % | 28 Apr 2011 → 8 Aug 2011 → 4 Oct 2012 | 1.4 years | Euro crisis / US downgrade, the August 2011 gap down |
| 4 | −12.4 % | 31 Aug 2000 → 24 Jul 2002 → 6 Oct 2003 | **3.1 years** (the longest) | Dot-com bust: shallow but long; few new signals and small losses on each rally attempt |
| 5 | −11.9 % | 23 Jun 2015 → 27 Jun 2016 → 15 Feb 2017 | 1.7 years | China devaluation / oil crash / Brexit vote: choppy, trendless market, repeated whipsaws |

Worst drawdown inside the classic stress periods (50/50 combination vs S&P 500): dot-com bust −12 % vs −49 %, financial crisis −9 % vs −57 %, euro crisis 2011 −14 % vs −19 %, 2015-16 −10 % vs −14 %, Q4 2018 −10 % vs −20 %, Covid −16 % vs −34 %, 2022 −4 % vs −25 %.

![drawdowns](results/drawdowns/drawdowns.png)

**What to take from it**

1. **The longest time under water is about 3 years for every book (3.1 years for the combination): August 2000 to October 2003.** The worst stock version (6-month hold) needed 4.9 years. The S&P 500 needed 7.2 years for the same bust (2000-2007), then 5.5 years after 2007 (to March 2013).
2. **The deepest drawdowns don't come in the big bear markets.** They come in **fast shocks and choppy markets**: Covid 2020 (−16 %), August 2011 (−14 %) and 2015-16 (−12 %). In the long bear markets of 2000-02 and 2008 the weekly MACD exit and the S&P filter take the book to cash early. Losses stay small (−9 % to −14 %), but it takes years to make a new high because few new trends start.
3. **Typical pattern:** the strategy is more than 10 % below its high on only 10 % of days, against 42 % for the S&P 500. Nine episodes in 30 years went deeper than −10 %, and none deeper than −16.4 %.
4. **¼ Kelly leverage (1.45×) deepens the drawdowns (−23 %) without shortening them** (3.3 years). Leverage scales the depth, not the recovery time.
5. **Practical:** be prepared to go 2-3 years without a new equity high even with this low-drawdown setup, especially after a market top. The 2000-03 and 2007-09 episodes would test discipline, even at −12 to −14 %. Judge the strategy over a full cycle, not over one or two years. Current drawdown (3 Nov 2026): −4.5 % for the combination, −8.9 % for the stock book.

Reproduce: `python scripts/drawdown_study.py && python scripts/drawdown_charts.py`.

---

## Reinvestment, Kelly sizing vs the Calmar ratio, and the best index book + the best stock book combined

Scripts: `scripts/combo_kelly_study.py` and `scripts/combo_kelly_charts.py`; results in `results/combo_kelly/`. T-bill yields (13-week, `^IRX`) are in `data/rates/IRX.csv`.

**Are profits reinvested? Yes.** Every backtest in this repo compounds. Each new position gets 1/N of the *current* equity (capped by the cash that is actually free), so profits grow the next positions and losses shrink them. Open positions are not resized. Two conservative simplifications in the earlier sections: **idle cash earns nothing**, and no dividends are included (price indices; Yahoo's adjusted prices for stocks). Below, idle cash earns the T-bill and any borrowing costs T-bill + 1 %/yr.

The books (all 1997-2026 here, so they share the stock data period):
* **IDX5**: 27 DM indices + sectors, buy at the next open after a weekly MACD up-phase if the S&P 500 > its 100-day average, no stop, MACD < 0 exit, 1-year exit, max 5 (IDX3 = max 3).
* **STK_W1**: point-in-time top-100 stocks, wait 1 month and buy if the MACD stayed > 0 and the S&P 500 > its 100-day average, 1 % stop with S&P-filtered re-entry, MACD < 0 exit, 11-month exit, max 10.
* **STK_6M**: the same stocks, buy at once, no filter, 1 % stop, MACD < 0 exit, 6-month exit, max 20.

| 1997-2026 (CAGR · max DD · **Calmar** · Sharpe · worst year) | Idle cash earns 0 (as before) | Idle cash earns T-bills |
|---|---|---|
| IDX5 (62 % invested on average) | 8.0 % · −18 % · 0.44 · 0.84 · −8 % | 8.9 % · −18 % · **0.49** · 0.92 · −8 % |
| IDX3 | 8.8 % · −20 % · 0.44 · 0.81 · −11 % | 9.5 % · −18 % · **0.52** · 0.87 · −9 % |
| STK_W1 (62 % invested) | 8.4 % · −18 % · 0.46 · 0.69 · −10 % | 9.4 % · −18 % · **0.52** · 0.75 · −8 % |
| STK_6M (60 % invested) | 7.8 % · −25 % · 0.31 · 0.74 · −14 % | 8.7 % · −23 % · **0.38** · 0.83 · −12 % |
| *S&P 500 (price) / S&P 500 total return* | *8.1 % · −57 % · 0.14 / 10.1 % · −55 % · 0.18* | |

**Combined: best index book + best stock book** (idle cash earns T-bills; monthly rebalanced). Daily return correlation between the books: 0.59-0.64.

| 1997-2026 | CAGR (in / out of sample) | Max DD | **Calmar** | Sharpe | Worst year |
|---|---|---|---|---|---|
| **IDX5 + STK_W1, 50/50** | **9.2 %** (8.9 / 9.6) | **−16 %** | **0.56** | 0.91 | −6.7 % |
| **IDX3 + STK_W1, 50/50** | **9.6 %** (9.2 / 10.1) | **−16 %** | **0.61** | 0.90 | −6.0 % |
| IDX5 + STK_6M, 50/50 | 8.9 % (7.3 / 10.8) | −17 % | 0.52 | 0.97 | −8.7 % |
| Inverse-volatility weights (≈55/45) | about the same as 50/50 | | | | |
| IDX5 + STK_W1, overlay (both books at 100 %, i.e. 2× the 50/50) | 15.0 % (13.8 / 16.3) | −31 % | 0.49 | 0.78 | −14.9 % |

**Kelly and leverage.** Kelly sizing maximises the long-run growth rate. For a return stream it says: use leverage f* = excess mean / variance. These books have low volatility (9-13 %/yr) and Sharpe ratios around 0.75-0.95, so Kelly asks for a lot of leverage. Here L scales every position and the cash balance follows: below 1× the rest sits in T-bills, above 1× the excess is borrowed at T-bill + 1 %.

| Kelly fraction f* (estimated 1997-2012 / full sample) | IDX5 | STK_W1 | STK_6M | IDX5 + STK_W1 50/50 | IDX5 + STK_6M 50/50 |
|---|---|---|---|---|---|
| Full Kelly leverage | 6.2× / 7.2× | 3.9× / 4.6× | 3.1× / 5.9× | 5.8× / 6.9× | 5.6× / 8.1× |

IDX5 + STK_W1 50/50 at different sizes (full period; the out-of-sample part 2013-2026 behaves the same):

| Size | Avg / max gross exposure | CAGR | Max DD | **Calmar** | Sharpe | Worst year |
|---|---|---|---|---|---|---|
| 0.5× | 31 / 51 % | 5.9 % | −8 % | **0.69** | 1.13 | −2.5 % |
| **1× (no leverage)** | 62 / 101 % | **9.3 %** | **−16 %** | **0.56** | 0.91 | −6.7 % |
| **1.45× = ¼ Kelly** | 90 / 147 % | **12.0 %** | −23 % | 0.52 | 0.83 | −10.4 % |
| 2× | 124 / 203 % | 15.0 % | −31 % | 0.49 | 0.78 | −14.9 % |
| 2.9× = ½ Kelly | 179 / 294 % | 19.1 % | −46 % | 0.42 | 0.73 | −22.2 % |
| 5.8× = full Kelly | 359 / 588 % | 25.9 % | **−79 %** | 0.33 | 0.68 | −43.4 % |
| 8× (over-Kelly) | 495 / 812 % | 23.5 % | −92 % | 0.26 | 0.66 | −56.8 % |

Per-trade view: a simple Kelly per campaign (W − (1 − W)/R) is 44 % of capital for IDX5 (win rate 57 %, average win +22 % vs loss −6 %), 22 % for STK_W1 (win rate 36 %, +32 % vs −7 %) and 18 % for STK_6M. The books currently stake 20 %, 10 % and 5 % per position, i.e. roughly ¼ to ½ of per-trade Kelly. This view ignores that 5-20 positions are open at the same time and move together, which is why the portfolio Kelly above is the relevant number.

![combo kelly](results/combo_kelly/combo_kelly.png)

**What to take from it**

1. **Kelly does not improve the Calmar ratio; it lowers it.** Calmar falls steadily as leverage rises, for every book: 0.69 at 0.5×, 0.56 at 1×, 0.42 at ½ Kelly and 0.33 at full Kelly for the combination. Leverage scales returns roughly linearly, but drawdowns grow faster (volatility drag and the compounding of losses). Kelly maximises *growth*, not return per unit of drawdown. Full Kelly here means −63 % to −85 % drawdowns (−79 % for the combination), and estimation error makes it worse in real life. Beyond full Kelly, growth itself falls (8×: 23.5 % with −92 %).
2. **Calmar, taken alone, always says "less leverage"** (its maximum is near cash). So use it with a return target. Calmar is only raised by a better or more diversified strategy, not by sizing. That is what the combination does.
3. **Combining the best index book with the best stock book is the best result in the project on a risk-adjusted basis.** IDX5 + STK_W1 50/50 makes **9.2 %/yr with −16 % max DD, Calmar 0.56, Sharpe 0.91 and a worst year of −6.7 %**. IDX3 + STK_W1 makes 9.6 % / −16 % / Calmar 0.61. Either book alone has a Calmar of 0.49-0.52, and the S&P 500 has 0.14-0.18. The diversification is real but limited (correlation about 0.6), because both books are long equities with US-led timing.
4. **Sensible sizing, if you want more return: about ¼ Kelly (≈1.25-1.5×) on the combination.** That gives about **12 %/yr with −23 % max DD** (Calmar 0.52, worst year −10 %). That beats the S&P 500 total return (10.1 %, −55 %) on both return and drawdown, at an average gross exposure of 90 % (peaks around 150 %). ½ Kelly (≈2.9×) gives about 19 %/yr but −46 % drawdowns. That is index-like pain and needs real margin, so it isn't recommended. Full Kelly is not usable.
5. **Crediting T-bills on idle cash adds about +0.7-1.0 %/yr** to every book, because they are only about 60 % invested. In practice, park the idle cash in T-bills or a money-market fund.
6. Caveats: daily-rebalanced constant leverage, financing at T-bill + 1 %, no taxes, no margin calls or gap risk beyond what the daily data shows. The stock book and its parameters were selected from a large grid, so expect the live result to be somewhat below the backtest.

Reproduce: `python scripts/combo_kelly_study.py && python scripts/combo_kelly_charts.py` (needs `data/rates/IRX.csv`).

---

## Delayed entry: wait 2 months after the MACD signal, buy only if the MACD is still > 0, hold 10 months

Scripts: `scripts/delayed_entry_study.py` (`indices`, `stocks`, `stocks-wait1m`) and `scripts/delayed_entry_charts.py`; results in `results/delayed_entry/`.

Rules:
* **Signal** as always: a new weekly MACD up-phase (MACD and signal line both turn > 0).
* **Wait 2 months.** At the first weekly close at least 61 days after the signal, take the trade only if the weekly MACD line stayed **> 0 on every weekly close since the signal**. If it dipped below 0, the signal is dropped. A stricter variant also requires the price to be above the signal-day close.
* **Entry** at the next open (E0). **Stop as usual:** 1 % (or 2 %) below E0 with re-entry at E0. A weekly close with MACD < 0 means sell at the next open. **Time exit after 10 months** (first open ≥ entry + 304 days), so about 12 months after the signal in total.
* Filters: none / S&P 500 above its 50- or 100-day average (at the entry decision and before every re-entry). Sensitivity: wait 1 month + hold 11 months, and wait 3 months + hold 9 months.
* Baseline: the earlier rules (buy at the next open after the signal, hold up to 12 months).

How many signals survive the wait, and what happens meanwhile (buy-and-hold returns, before any stops):

| | Kept after 1 m / 2 m | Move during the wait (kept) | Move during the wait (dropped) | 12 m from the signal: kept / dropped |
|---|---|---|---|---|
| 27 indices + sectors | 87 % / 82 % | +2.1 % / **+3.5 %** | −5.0 % / −4.7 % | +11.7 % / −1.3 % (2 m) |
| PIT top-100 stocks | 86 % / 78 % | +2.6 % / **+5.2 %** | −9.4 % / −9.8 % | +16.0 % / −3.8 % (2 m) |

The wait does separate good signals from bad ones. But you pay for it with the move you miss before you are in (+3.5 % on indices and +5.2 % on stocks for a 2-month wait).

**27 DM indices + US sectors, 1990-2026** (CAGR · max DD · Sharpe; random-pick means are within ±0.3 %/yr):

| | max 3 | max 5 |
|---|---|---|
| *Buy at once, hold 12 m, no stop (original rules)* | *8.4 % · −24 % · 0.80* | *7.5 % · −25 % · 0.78* |
| *Buy at once, S&P > 100d, hold 12 m, no stop (best)* | ***8.8 % · −20 % · 0.85*** | ***8.4 % · −18 % · 0.91*** |
| **Wait 2 m, hold 10 m, 1 % stop (asked)** | **4.2 % · −34 % · 0.50** | 4.1 % · −29 % · 0.55 |
| Wait 2 m, hold 10 m, no stop | 5.1 % · −35 % · 0.54 | 5.3 % · −30 % · 0.61 |
| Wait 2 m, S&P > 100d, no stop | 5.9 % · −25 % · 0.64 | 5.8 % · −18 % · 0.69 |
| Wait 2 m, S&P > 50d, 1 % stop | 3.9 % · −27 % · 0.49 | 3.8 % · −20 % · 0.56 |
| Wait 2 m + price above the signal, 1 % stop | 3.8 % · −33 % · 0.47 | 3.7 % · −26 % · 0.52 |
| Wait 1 m, hold 11 m: no filter / S&P > 50d, no stop | 5.9 % · −34 % · 0.57 / 6.4 % · −21 % · 0.64 | |
| Wait 3 m, hold 9 m: no filter, 1 % stop | 4.1 % · −29 % · 0.51 | |

**Point-in-time top-100 US stocks, 1997-2026** (CAGR · max DD · Sharpe; random-pick mean in brackets):

| | 10 stocks | 20 stocks |
|---|---|---|
| *Buy at once, 1 % stop, hold 12 m* | *6.8 % · −45 % · 0.53 (7.2 % · −40 % · 0.56)* | *8.0 % · −36 % · 0.67 (7.8 % · −32 % · 0.66)* |
| **Wait 2 m, 1 % stop, hold 10 m (asked)** | **7.7 % · −32 % · 0.63** (6.9 % · −30 % · 0.58) | 6.5 % · −25 % · 0.62 (6.1 % · −27 % · 0.59) |
| Wait 2 m, no stop | 7.4 % · −47 % · 0.52 (7.2 % · −45 % · 0.52) | 6.0 % · −34 % · 0.48 |
| Wait 2 m, S&P > 50d, 1 % stop | 4.8 % · −26 % · 0.49 (5.7 % · −29 % · 0.56) | 4.7 % · −18 % · 0.53 |
| Wait 2 m, S&P > 100d, 1 % stop | 5.8 % · −20 % · 0.56 | 5.1 % · −16 % · 0.55 |
| Wait 2 m + price above the signal, 1 % stop | 6.9 % · −29 % · 0.61 | 6.5 % · −20 % · 0.63 |
| Wait 3 m, hold 9 m, 1 % stop | 5.6 % · −29 % · 0.49 | |
| **Wait 1 m, hold 11 m, S&P > 100d, 1 % stop** | **8.4 % · −18 % · 0.70** (**8.2 %** · −21 % · 0.71; range 7.4-9.1 %) | 7.0 % · −21 % · 0.65 (7.1 % · −19 % · 0.68) |
| Wait 1 m, hold 11 m, S&P > 100d, no stop | 9.9 % · −33 % · 0.68 (9.6 % · −33 % · 0.69) | 8.2 % · −29 % · 0.63 |
| *Buy at once, 1 % stop, hold 6 m (previous best balance)* | *7.9 % · −36 % · 0.66* | *7.8 % · −25 % · 0.76 (7.4 % · −25 % · 0.73)* |
| *Equal-weight PIT top 100 / S&P 500 TR* | *12.8 % · −58 % · 0.67 / 10.1 % · −55 % · 0.60* | |

Selected years, stocks, 10 stocks: buy at once (1 % stop, 12 m) / wait 2 m (1 % stop) / wait 1 m + S&P > 100d (1 % stop): 2008 −20 / −22 / **−6 %**, 2009 +12 / +10 / +20 %, 2022 −12 / −22 / −10 %, 2024 +3 / +19 / +27 %. Indices, max 3: original / wait 2 m (1 % stop): 2009 +24 / +7 %, 2020 +25 / +9 %, 2023 +23 / −5 %.

![delayed entry](results/delayed_entry/delayed_entry.png)

**What to take from it**

1. **On DM indices + sectors the 2-month wait clearly hurts:** 4.2 %/yr, −34 % max DD and Sharpe 0.50, against 8.4 % / −24 % / 0.80 for the original rules. Every filter, stop and size combination is worse than buying at once. Index MACD signals rarely fail (82 % survive the wait), so the confirmation adds little. The 3.5 % you miss is a large part of the trend, and later entries sit closer to the next top, which is why even the drawdown gets worse.
2. **On single stocks the 2-month wait is roughly neutral.** The asked version (1 % stop) makes 7.7 % / −32 % / 0.63 with 10 stocks; on random picks that is 6.9 % / −30 % / 0.58. Buying at once gives 7.2 % / −40 % / 0.56. So it cuts the drawdown by about 10 points at about the same return. With 20 stocks it is worse than buying at once (6.1 % vs 7.8 %). Requiring the price to be up as well doesn't help, and a 3-month wait is worse.
3. **A shorter wait works better on stocks: wait 1 month + S&P > 100-day filter + 1 % stop + hold 11 months.** With 10 stocks it makes **8.4 %/yr, max DD −18 %, Sharpe 0.70**. Random picks give 8.2 % (7.4-9.1 %) / −21 % / 0.71, and it is consistent in and out of sample (7.8 / 9.1 %). That is the best return-to-drawdown of all the stock books tested. One month is enough to drop the stock signals that fail quickly (they lose −9 % in that month) while giving up only +2.6 % on the good ones. Caveat: it came out of a large grid of variants, so treat it as a candidate to keep watching, not a proven edge. On indices the same 1-month wait does not help (5.9-6.4 %/yr).
4. **Nothing here beats buy-and-hold on return.** The equal-weight top 100 makes 12.8 % and the S&P 500 10.1 %. The useful result is drawdowns of −18 to −25 % against −55 % for the index.
5. **Current state (2026-11-03):** for the asked stock rule (no filter) 11 recent signals are still in their 2-month wait with the MACD still > 0, and each is bought if that still holds at its check date: PLTR, SMCI and QCOM (from 11 Nov), CRM (18 Nov), NOW (25 Nov), DIS (2 Dec), META (9 Dec), PG and ABT (23 Dec), ACN and LIN (30 Dec). The wait-1-month S&P > 100-day book holds MRK (+37 %), UNP (+36 %), DELL (+109 %), JPM (+9 %) and PFE (+4 %). The S&P is below its 100-day average, so it makes no new buys for now. The asked index book holds only XLK (−7 %). These are backtest model states, not investment advice.

Reproduce: `python scripts/delayed_entry_study.py indices && python scripts/delayed_entry_study.py stocks && python scripts/delayed_entry_study.py stocks-wait1m && python scripts/delayed_entry_charts.py`.

---

## Holding period 3 vs **6** vs 12 months (S&P 500 50-day filter, MACD signal, 1 % stop)

Scripts: the same `scripts/indices_ma50_study.py` and `scripts/stocks_ma50_study.py`, now with a 6-month hold (time exit at the first open ≥ entry + 182 days) in the grid; results in `results/indices_ma50/` and `results/stocks_ma50/`. Everything else is unchanged: the weekly MACD up-phase signal, buys and re-buys only while the S&P 500 is above its 50-day average, the 1 % stop with re-entry at the entry price, and the exit after a weekly MACD < 0 close. After a time exit an asset can only be bought again on a new MACD up-phase.

**27 DM indices + US sectors, max 3, 1990-2026** (CAGR · max DD · Sharpe · average invested):

| | 3 months | **6 months** | 1 year |
|---|---|---|---|
| **S&P > 50-day, 1 % stop** | 4.1 % · −14 % · 0.70 · 30 % | **5.2 % · −25 % · 0.67 · 43 %** | 7.0 % · −26 % · 0.75 · 58 % |
| S&P > 50-day, no stop | 5.1 % · −20 % · 0.67 | 6.0 % · −21 % · 0.66 | 8.1 % · −25 % · 0.77 |
| S&P > 100-day, no stop | 4.8 % · −17 % · 0.66 | 6.2 % · −25 % · 0.69 | **8.8 % · −20 % · 0.85** |
| No filter, no stop | 5.3 % · −20 % · 0.66 | 6.4 % · −22 % · 0.67 | 8.4 % · −24 % · 0.80 |
| *16 DM indices only, S&P > 50d, 1 % stop* | 3.3 % · −12 % · 0.65 | 4.5 % · −17 % · 0.66 | 6.0 % · −21 % · 0.71 |
| *11 US sectors only, no filter, no stop* | 3.6 % · −14 % · 0.56 | **5.2 % · −16 % · 0.66** | 4.4 % · −24 % · 0.50 |

Random pick among same-day signals (50 draws): S&P 50-day, 6 months, 1 % stop averages 4.9 % / −24 % / 0.64, against 3.8 % / −15 % / 0.66 for 3 months and 6.8 % / −27 % / 0.73 for 1 year.

**Point-in-time top-100 US stocks, 1997-2026** (CAGR · max DD · Sharpe; random-pick mean in brackets):

| | 3 months | **6 months** | 1 year |
|---|---|---|---|
| **S&P > 50-day, 1 % stop, 10 stocks** | 6.1 % · −24 % · 0.69 (5.7 % · −27 % · 0.66) | **6.0 % · −22 % · 0.59** (5.7 % · −23 % · 0.57) | 6.6 % · −32 % · 0.56 (5.8 % · −38 % · 0.51) |
| S&P > 50-day, 1 % stop, 20 stocks | 3.7 % · −19 % · 0.58 | 5.1 % · −17 % · 0.58 (5.2 % · −17 % · 0.60) | 6.4 % · −24 % · 0.61 |
| S&P > 100-day, 1 % stop, 20 stocks | 4.7 % · −15 % · 0.68 | 5.9 % · −18 % · 0.63 (6.0 % · −18 % · 0.66) | 6.7 % · −24 % · 0.61 |
| No filter, 1 % stop, 10 stocks | 7.5 % · −29 % · 0.73 | 7.9 % · −36 % · 0.66 (8.3 % · −33 % · 0.70) | 6.8 % · −45 % · 0.53 |
| **No filter, 1 % stop, 20 stocks** | 5.8 % · −22 % · 0.76 (5.9 % · −23 % · 0.77) | **7.8 % · −25 % · 0.76** (7.4 % · −25 % · 0.73) | 8.0 % · −36 % · 0.67 |
| S&P > 50-day, 1 % stop, 3 stocks | 4.8 % · −38 % · 0.42 | 2.9 % · −64 % · 0.26 | 3.0 % · −43 % · 0.27 |
| *Equal-weight PIT top 100 / S&P 500 TR* | | *12.8 % · −58 % · 0.67 / 10.1 % · −55 % · 0.60* | |

Selected years: indices S&P 50d + 1 % stop at 3 / 6 / 12 months: 2008 −5.8 / −6.2 / −6.2 %, 2009 +9.8 / +16.7 / +18.9 %, 2024 −1.3 / +6.4 / +20.8 %. Stocks, no filter + 1 % stop, 20 stocks, 3 / 6 months: 2008 −4.3 / −13.0 %, 2009 +8.6 / +7.8 %, 2024 +7.1 / +17.7 %.

**What to take from it**

1. **Indices + sectors: 6 months is not a sweet spot.** With the asked filter and stop, return rises almost linearly with the holding period (4.1 → 5.2 → 7.0 %/yr). The drawdown, however, jumps to nearly the 1-year level already at 6 months (−14 → −25 → −26 %). The 6-month Sharpe (0.67) is the lowest of the three, and the random picks confirm it. A 6-month exit still holds through the crash but cuts the trend before the payoff. **On the 27, keep the 1-year hold** (best: S&P > 100-day, no stop, 8.8 % / −20 % / 0.85; 0.91 with 5 slots). Use 3 months only if the lowest drawdown matters most.
2. **Exception: US sectors alone prefer 6 months.** 5.2 %/yr, −16 %, Sharpe 0.66, against 4.4 % / −24 % / 0.50 with a 1-year hold. Sector leadership rotates faster than country indices trend. DM indices alone still prefer 1 year.
3. **Stocks with the S&P 50-day filter: 6 months ≈ 3 months.** With 10 stocks it gives 6.0 % / −22 % / 0.59 (random 5.7 %), which is no better than 3 months on return and worse on Sharpe. With 20 stocks it adds return (5.1 % vs 3.7 %) at a similar drawdown (−17 %).
4. **Stocks: the best balance found so far is no filter, 6-month hold, 1 % stop, 20 stocks.** It makes **7.8 %/yr with −25 % max DD and Sharpe 0.76** (random 7.4 % / −25 % / 0.73). That is about 2 %/yr more than the 3-month version at the same Sharpe, and almost the 1-year return (8.0 %) with 11 points less drawdown. It is 60 % invested on average.
5. **Never run these with only 3 stocks.** With a filter and a 6-month hold the 3-stock books have max drawdowns of −64 to −85 %; a handful of trades decides everything.
6. **Current state (2026-11-03):** the S&P 500 is 1.6 % below its 50-day average, so all filtered books are frozen for new buys (the no-filter book keeps trading). The 6-month index book holds only XLF (until early January). The no-filter 6-month stock book (20 stocks) holds LLY (+40 %), V (+16 %), CRWD (+15 %), PFE (+12 %), MA (+10 %), ABT, PYPL, PLTR, PG and UNH; 10 more names are stopped out and wait to re-trigger at their entry prices. These are backtest model states, not investment advice.

---

## DM indices + US sectors: S&P 500 **50-day** filter + **3-month** holding period (MACD signal, 1-2 % stop)

Scripts: `scripts/indices_ma50_study.py` and `scripts/indices_ma50_charts.py`; results in `results/indices_ma50/`.

Rules: the single-stock test above, applied to the original 27 instruments (16 DM indices + 11 SPDR sectors, 1990-2026, price indices):
* buy a new weekly MACD up-phase at the next open only if the **S&P 500 closed above its 50-day average**;
* 1 % (or 2 %) stop below the entry, with re-entry at the entry price only while the S&P 500 is above its 50-day average;
* exit at the next open after a weekly MACD < 0 close or **after 3 months**;
* max 3 positions (also 5), 1/N of equity each, compounding, 3 bps per side.

Grid: filter (none / S&P 50-day / S&P 100-day / asset's own 50-day) × hold (3 months / 1 year; 6 months added in the section above) × stop (none / 1 % / 2 %) × max 3 / 5. Key variants are also run on the DM indices and sectors alone, plus 50 random-pick draws.

| 27 instruments, max 3, 1990-2026 (CAGR · max DD · Sharpe · avg invested) | 3-month hold | 1-year hold |
|---|---|---|
| **S&P > 50-day, 1 % stop (asked)** | **4.1 % · −14 % · 0.70 · 30 %** | 7.0 % · −26 % · 0.75 · 58 % |
| S&P > 50-day, 2 % stop | 4.1 % · −18 % · 0.67 · 33 % | 6.8 % · −29 % · 0.71 · 60 % |
| S&P > 50-day, no stop | 5.1 % · −20 % · 0.67 · 42 % | 8.1 % · −25 % · 0.77 · 66 % |
| S&P > 100-day, 1 % stop | 4.2 % · −14 % · 0.73 · 29 % | 7.4 % · −21 % · 0.79 · 57 % |
| **S&P > 100-day, no stop** | 4.8 % · −17 % · 0.66 · 39 % | **8.8 % · −20 % · 0.85 · 63 %** |
| No filter, 1 % stop | 4.5 % · −19 % · 0.70 · 34 % | 7.6 % · −27 % · 0.78 · 61 % |
| No filter, no stop | 5.3 % · −20 % · 0.66 · 45 % | 8.4 % · −24 % · 0.80 · 68 % |
| Asset's own 50-day, 1 % stop | 4.7 % · −20 % · 0.73 · 33 % | 7.4 % · −30 % · 0.77 · 60 % |
| *Max 5:* S&P > 50-day, 1 % stop / S&P > 100-day, no stop | 3.3 % · −12 % · 0.69 / 4.4 % · −12 % · 0.72 | 6.9 % · −21 % · 0.84 / **8.4 % · −18 % · 0.91** |
| *Equal-weight 27 buy & hold / S&P 500 (price)* | *9.7 % · −52 % · 0.68 / 8.6 % · −57 % · 0.55* | |

Random pick among same-day signals (50 draws, max 3, mean): asked 3.8 % / −15 % / 0.66; S&P 100-day, 1 year, no stop 8.7 % / −20 % / 0.85; S&P 50-day, 1 year, 1 % stop 6.8 % / −27 % / 0.73; no filter, 3 months, 1 % stop 4.2 % / −21 % / 0.66. The ranges are narrow (±0.3-0.5 %/yr), so the ranking doesn't depend on which signal gets the slot.

| Sub-universe, max 3 (CAGR · max DD · Sharpe) | S&P > 50d, 3 months, 1 % stop | No filter, 3 months, 1 % stop | S&P > 100d, 1 year, no stop | No filter, 1 year, 1 % stop |
|---|---|---|---|---|
| 16 DM indices | 3.3 % · −12 % · 0.65 | 4.1 % · −14 % · 0.73 | 6.3 % · −25 % · 0.68 | **6.9 % · −20 % · 0.76** |
| 11 US sectors | 1.6 % · −12 % · 0.36 | 2.1 % · −18 % · 0.42 | 4.6 % · −22 % · 0.53 | 3.3 % · −29 % · 0.42 |

Selected calendar years (27, max 3):

| Year | S&P 50d, 3 m, 1 % (asked) | S&P 50d, 3 m, no stop | S&P 100d, 1 y, no stop | MACD only, 1 y | EW 27 | S&P 500 |
|---|---|---|---|---|---|---|
| 2001 / 2002 | −2.7 / −2.9 % | −1.2 / +3.3 % | −10.6 / −5.2 % | −13.8 / −6.9 % | −17.0 / −24.1 % | −13.0 / −23.4 % |
| 2008 | −5.8 % | −11.4 % | −6.7 % | −14.1 % | −35.5 % | −38.5 % |
| 2009 | +9.8 % | +14.8 % | +24.0 % | +24.0 % | +29.8 % | +23.4 % |
| 2020 | +20.8 % | +22.0 % | +10.8 % | +25.2 % | +8.7 % | +16.3 % |
| 2022 | −3.7 % | −9.0 % | −5.5 % | −15.1 % | −10.8 % | −19.4 % |
| 2023 / 2024 / 2025 | +7.8 / −1.3 / +2.1 % | +10.7 / +3.1 / +3.0 % | +9.8 / +26.2 / +12.5 % | +22.7 / +15.4 / +13.4 % | +19.4 / +16.3 / +18.9 % | +24.2 / +23.3 / +16.4 % |

![indices ma50](results/indices_ma50/indices_ma50.png)

**What to take from it**

1. **On indices and sectors the 3-month hold roughly halves the return and does not improve the Sharpe.** The asked rules make **4.1 %/yr with a −14 % max drawdown and Sharpe 0.70**. The same filter with a 1-year hold makes 7.0 % / −26 % / 0.75, and the best index setup (S&P > 100-day, 1-year hold, no stop) makes **8.8 % / −20 % / 0.85**. Index trends are long and smooth. A 1-year trade averages +7 to +10 %, a 3-month trade only +2 to +3 %, and the asked book is in cash 70 % of the time. Single stocks were different: there, cutting at 3 months raised the Sharpe from 0.58 to 0.71 because stock up-trends fail more often.
2. **The drawdown cut is real but bought with return.** −14 % is the lowest drawdown of any index variant with max 3; with max 5 it falls to about −11 to −12 %. Bad years are mild (2008 −5.8 %, 2022 −3.7 %), but so are good ones (2024 −1.3 %, 2025 +2.1 %). As a stand-alone strategy it earns less than half of buy-and-hold (9.7 % for the equal-weight 27). It only makes sense as a sleeve that leaves 70 % of the capital free for something else.
3. **The 50-day average is again a little worse than the 100-day** (1-year hold: 8.1 % vs 8.8 % without stop, 7.0 % vs 7.4 % with the 1 % stop; random picks agree). Keep the 100-day.
4. **The stops still don't help on the 27.** With a 1-year hold the 1 % stop costs 0.8-1.5 %/yr. With a 3-month hold it trims the drawdown (−20 → −14 %) but also the return (5.1 → 4.1 %). This matches every earlier index test; the 1 % stop only paid off on single stocks.
5. **A new finding: 5 slots instead of 3 improves the best index setup.** S&P > 100-day, 1-year hold, no stop with **max 5 gives 8.4 %/yr, −18 % max DD and Sharpe 0.91**, the best risk-adjusted result in the project. With max 3 it gives 8.8 % / −20 % / 0.85.
6. **DM indices alone:** the asked rules give 3.3 % / −12 %. The best DM-only version is still no filter, 1-year hold, 1 % stop (6.9 % / −20 % / 0.76); a US filter says less about Europe and Asia. **US sectors alone** are weak in every version (1.6-4.6 %/yr).
7. **Current state (2026-11-03):** the S&P 500 is 1.6 % below its 50-day average, so the 50-day filter is **OFF**. The asked book is **flat**: all its trades have already hit the 3-month exit or the stop. The 100-day / 1-year book still holds XLB (+17.8 %) and the Nasdaq 100 (+12.4 %). These are backtest model states, not investment advice.

Reproduce: `python scripts/indices_ma50_study.py && python scripts/indices_ma50_charts.py`.

---

## 100 single US stocks: S&P 500 **50-day** filter + **3-month** holding period (MACD signal, 1-2 % stop)

Scripts: `scripts/stocks_ma50_study.py` and `scripts/stocks_ma50_charts.py`; results in `results/stocks_ma50/`.

Rules: same as the section below (point-in-time S&P 500 top 100, weekly MACD up-phase signal, 1 % / 2 % stop with re-entry at the entry price, exit at the next open after a weekly MACD < 0 close, 1/N of equity per stock), with two changes:
* the regime filter is the **S&P 500 above its 50-day average** (was 100-day). It gates the entry and every re-entry after a stop;
* the **time exit is after 3 months** (the first open ≥ entry + 91 days; was 1 year). After a time exit the stock can only be bought again on a new MACD up-phase.

To separate the two changes, every combination of filter (none / S&P 50-day / S&P 100-day / stock's own 50-day) × holding period (3 months / 1 year; 6 months added in the section above) × stop (none / 1 % / 2 %) × max 3 / 10 / 20 stocks was run, plus 20 random-pick draws for the key ones.

| Point-in-time top 100, 1997-2026 (CAGR · max DD · Sharpe) | max 3 | **max 10** | max 20 |
|---|---|---|---|
| **S&P > 50-day, 3 months, 1 % stop (asked)** | 4.8 % · −38 % · 0.42 | **6.1 % · −24 % · 0.69** | 3.7 % · −19 % · 0.58 |
| S&P > 50-day, 3 months, 2 % stop | 3.1 % · −54 % · 0.28 | 5.2 % · −30 % · 0.58 | 3.0 % · −26 % · 0.45 |
| S&P > 50-day, 3 months, no stop | 5.9 % · −58 % · 0.39 | 7.9 % · −38 % · 0.65 | 4.6 % · −34 % · 0.50 |
| S&P > 50-day, 1 year, 1 % stop | 3.0 % · −43 % · 0.27 | 6.6 % · −32 % · 0.56 | 6.4 % · −24 % · 0.61 |
| S&P > 100-day, 3 months, 1 % stop | 5.5 % · −35 % · 0.45 | 6.5 % · −26 % · **0.71** | 4.7 % · **−15 %** · 0.68 |
| *S&P > 100-day, 1 year, 1 % stop (previous best)* | 6.3 % · −50 % · 0.41 | *8.4 % · −34 % · 0.66* | 6.7 % · −24 % · 0.61 |
| **No filter, 3 months, 1 % stop** | 9.7 % · −42 % · 0.64 | 7.5 % · −29 % · **0.73** | 5.8 % · −22 % · **0.76** |
| No filter, 3 months, no stop | **10.7 %** · −55 % · 0.58 | **8.8 %** · −39 % · 0.64 | 6.4 % · −40 % · 0.60 |
| Stock's own 50-day, 3 months, 1 % stop | 8.3 % · −53 % · 0.58 | 5.9 % · −31 % · 0.61 | 5.0 % · −24 % · 0.69 |
| *MACD only, no filter, no stop, 1 year* | 8.7 % · −54 % · 0.47 | *6.8 % · −46 % · 0.47* | 8.3 % · −43 % · 0.59 |
| *Equal-weight PIT top 100 / S&P 500 TR* | | *12.8 % · −58 % · 0.67 / 10.1 % · −55 % · 0.60* | |

Average invested: 3-month versions with the 1 % stop are only **33-61 % invested** (stops plus a short hold leave cash idle), against 62-77 % for 1-year holds with the stop and 86-93 % for MACD only.

**Robustness: random pick among same-day signals, 20 draws** (mean, 5-95 % range):

| | 10 stocks: CAGR | Max DD | Sharpe | 20 stocks: CAGR | Max DD | Sharpe |
|---|---|---|---|---|---|---|
| **S&P 50-day, 3 months, 1 % stop** | 5.7 % (5.3-6.1) | −27 % | 0.66 | 3.8 % (3.7-3.9) | −19 % | 0.59 |
| S&P 100-day, 3 months, 1 % stop | 6.3 % (5.9-6.8) | −25 % | 0.71 | 4.7 % (4.6-4.9) | **−15 %** | 0.70 |
| S&P 50-day, 1 year, 1 % stop | 5.8 % (4.8-6.6) | −38 % | 0.51 | 6.3 % (6.0-6.6) | −27 % | 0.60 |
| S&P 100-day, 1 year, 1 % stop | 7.0 % (6.2-7.6) | −35 % | 0.58 | 6.5 % (6.0-7.0) | −26 % | 0.61 |
| **No filter, 3 months, 1 % stop** | 6.9 % (6.4-7.6) | −26 % | 0.70 | 5.9 % (5.7-6.0) | −23 % | **0.77** |
| No filter, 3 months, no stop | **8.5 %** (8.0-9.4) | −38 % | 0.63 | 6.4 % (6.2-6.7) | −41 % | 0.61 |
| MACD only, 1 year, no stop | 7.4 % (6.3-8.6) | −47 % | 0.50 | 7.8 % (7.0-8.2) | −42 % | 0.57 |

Selected calendar years (10 stocks unless noted):

| Year | S&P 50d, 3 m, 1 % | No filter, 3 m, 1 % | S&P 100d, 1 y, 1 % | MACD only, 1 y | EW top 100 | S&P 500 TR |
|---|---|---|---|---|---|---|
| 2001 / 2002 | −3.5 / −10.1 % | −15.9 / −12.5 % | −7.6 / −11.5 % | −27.1 / −24.2 % | −5.8 / −22.5 % | −10.9 / −23.4 % |
| 2008 | **−3.3 %** | −6.0 % | −5.3 % | −29.6 % | −41.1 % | −39.6 % |
| 2009 | +2.0 % | +5.9 % | +16.9 % | +15.6 % | +53.9 % | +32.2 % |
| 2020 | +16.7 % | +17.0 % | +11.3 % | +16.0 % | +18.7 % | +16.4 % |
| 2022 | −8.9 % | **−4.4 %** | −17.8 % | −17.0 % | −13.8 % | −18.1 % |
| 2023 / 2024 / 2025 | +7.1 / +6.6 / +20.5 % | +12.2 / +10.3 / +18.4 % | +11.0 / +14.0 / +9.9 % | +5.6 / +5.8 / +3.7 % | +24.2 / +18.9 / +21.9 % | +26.3 / +26.9 / +17.5 % |

On today's top 100 (biased, 1990-2026, 10 stocks) the asked rules make 9.7 %/yr with −23 % DD and Sharpe 1.04, against 16.6 % / −23 % / 1.11 with the 100-day filter and a 1-year hold. A 3-month hold cuts off the long winning trends that this biased list is full of.

![stocks ma50](results/stocks_ma50/stocks_ma50.png)

**What to take from it**

1. **The asked version (S&P > 50-day, 3-month hold, 1 % stop) is a low-risk, low-return book.** With 10 stocks it makes **6.1 %/yr with a −24 % max drawdown and Sharpe 0.69**. The random-pick mean is 5.7 % / −27 % / 0.66, with a narrow range: more trades means less luck. That is a better drawdown and Sharpe than the 1-year version, but about 2 %/yr less return than the earlier best (8.4 %; 7.0 % on random picks). With 20 stocks it falls to 3.7 %/yr, because the money sits in cash about two thirds of the time.
2. **The 3-month hold drives the result; the 50-day average doesn't.** For the same filter and stop, going from 1 year to 3 months cuts the drawdown by about 10 points (−35 → −25 % at 10 stocks on random picks) and raises the Sharpe from about 0.58 to 0.71. It costs 0.5-1 %/yr. The 3-month exit takes profits before the MACD turns, and over 70 % of trades end on the time exit. It also misses the big rebound years: 2009 made only +2 % against +17 % with a 1-year hold.
3. **The 50-day average is slightly worse than the 100-day in every pairing:** 6.1 vs 6.5 %/yr and Sharpe 0.69 vs 0.71 at 3 months, and 6.6 vs 8.4 %/yr at 1 year. The random picks agree. The 50-day line is probably too fast: it is crossed more often, so more good re-entries are blocked. If you use a market filter, keep the 100-day.
4. **With a 3-month hold and a 1 % stop the S&P filter is almost redundant.** The best risk-adjusted stock book in this whole project is **no filter, 3-month hold, 1 % stop**. It makes 7.5 %/yr / −29 % / Sharpe 0.73 with 10 stocks, and **5.8 %/yr / −22 % / Sharpe 0.76** with 20; random-pick Sharpe is 0.70 and 0.77. The short hold plus the 1 % stop already keep you out of bear markets (2008 −6 %, 2022 −4 %), so the filter mostly removes good trades.
5. **The 2 % stop is again worse than 1 %**, and the stock's own 50-day filter again adds nothing.
6. **None of these beats buy-and-hold on return** (S&P 500 TR 10.1 %, equal-weight top 100 12.8 %). Their value is the low drawdown at low exposure. Because the 3-month book is only 40-55 % invested, it combines well with another strategy (e.g. the index/sector MACD book) on the same capital. Alternatively, size it up about 1.5× to reach index-like return with roughly −35 to −40 % drawdown; that is an estimate, not simulated.
7. **Current state (2026-11-03):** the S&P 500 (7,569) is **1.6 % below its 50-day average (7,693)**, so the 50-day filter is **OFF**: no new buys or re-entries until the S&P closes above it. The asked 10-stock book holds TMO (+19.9 %), MA (+9.7 %) and PYPL (+2.9 %) until their 3-month exits (mid/late November). DASH, MSFT and CRM are stopped out and wait for the filter. These are backtest model states, not investment advice.

Reproduce: `python scripts/stocks_ma50_study.py && python scripts/stocks_ma50_charts.py`.

---

## 100 single US stocks: S&P 500 (or own-stock) 100-day filter + weekly-MACD signal + 1-2 % stop

Scripts: `scripts/stocks_regime_study.py` and `scripts/stocks_regime_charts.py`; results in `results/stocks_regime/`.

Rules:
* **Universe (main):** the point-in-time S&P 500 top 100 by trailing dollar volume, rebuilt every month (same data as the survivorship-bias section below). The reference case is today's top 100, which is survivorship-biased and runs from 1990.
* **Entry:** a new weekly MACD up-phase in the stock (MACD and signal both turn > 0), bought at the next open **only if the S&P 500 closed above its 100-day average** on the signal day.
* **Alternative filter:** the **stock's own 100-day average** replaces the S&P 500's. The stock must close above its own 100-day average on the signal day and before each re-entry. A third version requires both.
* **Stop:** 1 % (or 2 %) below the entry price E0. After a stop, **re-buy at E0, but only while the filter is on**. This is the conditional re-entry, any number of times.
* **Exit:** the stock's weekly MACD < 0 (sell at the next open) or after 1 year.
* **Portfolio:** max 3 / 10 / 20 stocks at once, 1/N of equity each, cash-capped (no leverage), compounding, 3 bps per side. When several signals appear on the same day, the strongest MACD (MACD/price) gets the slot.

| Point-in-time top 100, 1997-2026 | max 3 stocks | max 10 stocks | max 20 stocks |
|---|---|---|---|
| MACD only (no filter, no stop) | 8.7 % · −54 % · 0.47 | 6.8 % · −46 % · 0.47 | 8.3 % · −43 % · 0.59 |
| + S&P > 100-day filter | 4.5 % · −65 % · 0.31 | 8.1 % · −44 % · 0.56 | 7.7 % · −36 % · 0.59 |
| + 1 % stop & re-entry (no filter) | **9.1 %** · −46 % · 0.53 | 6.8 % · −45 % · 0.53 | 8.0 % · −36 % · **0.67** |
| **+ S&P filter + 1 % stop, conditional re-entry** | 6.3 % · −50 % · 0.41 | **8.4 % · −34 % · 0.66** (IS 6.3 / OOS 10.8) | 6.7 % · **−24 %** · 0.61 |
| + S&P filter + 2 % stop, conditional re-entry | 5.8 % · −50 % · 0.39 | 7.8 % · −36 % · 0.61 | 6.5 % · −26 % · 0.59 |
| + **stock > its own 100-day avg** filter, no stop | 6.2 % · −64 % · 0.37 | 6.0 % · −45 % · 0.42 | 8.1 % · −42 % · 0.58 |
| + **own-stock filter + 1 % stop**, conditional re-entry | 6.1 % · −56 % · 0.40 | 5.6 % · −35 % · 0.46 | 7.5 % · −34 % · 0.64 |
| + own-stock filter + 2 % stop, conditional re-entry | 4.9 % · −62 % · 0.34 | 4.6 % · −41 % · 0.39 | 6.7 % · −39 % · 0.58 |
| + S&P **and** own-stock filter + 1 % stop | 5.0 % · −51 % · 0.35 | 8.1 % · −35 % · 0.64 | 6.5 % · −24 % · 0.60 |
| *Equal-weight buy & hold of the PIT top 100* | | *12.8 % · −58 % · 0.67* | |
| *S&P 500 total return* | | *10.1 % · −55 % · 0.60* | |

Each cell is CAGR · max drawdown · Sharpe.

**Robustness: random pick among same-day signals (20 draws, point-in-time).** The table above gives the slot to the strongest MACD when several stocks signal on the same day. With a random choice instead:

| 20 random draws, 1997-2026 | CAGR mean (5-95 %) | Max DD mean (5-95 %) | Sharpe mean |
|---|---|---|---|
| 10 stocks, MACD only | 7.4 % (6.5 to 8.4) | −46 % (−49 to −44) | 0.51 |
| **10 stocks, S&P filter + 1 % stop** | 6.9 % (6.3 to 7.9) | **−35 % (−40 to −31)** | **0.58** |
| 20 stocks, MACD only | 7.8 % (7.0 to 8.5) | −42 % (−44 to −40) | 0.57 |
| **20 stocks, S&P filter + 1 % stop** | 6.7 % (6.3 to 7.0) | **−26 % (−28 to −24)** | **0.62** |
| 10 stocks, own-stock filter + 1 % stop | 6.1 % (5.2 to 7.4) | −38 % (−42 to −33) | 0.50 |
| 20 stocks, own-stock filter + 1 % stop | 7.2 % (6.8 to 7.7) | −32 % (−34 to −29) | 0.63 |
| 10 stocks, S&P + own-stock filter + 1 % stop | 6.7 % (5.8 to 7.5) | −35 % (−39 to −30) | 0.57 |
| 20 stocks, S&P + own-stock filter + 1 % stop | 6.4 % (6.0 to 6.8) | −27 % (−28 to −24) | 0.60 |

So the **drawdown cut is robust** (−11 to −16 points in every draw), and Sharpe is a bit better. **The return gain is not**: on average the filter + stop costs 0.5-1 %/yr, and the 8.4 % headline sits at the lucky end of the range.

| *Today's top 100 (biased), 1990-2026* | max 3 | max 10 | max 20 |
|---|---|---|---|
| MACD only | 21.3 % · −75 % | 20.7 % · −53 % | 19.3 % · −41 % |
| 1 % stop, no filter | 24.5 % · −51 % | 22.1 % · −39 % | 18.8 % · −26 % |
| S&P filter + 1 % stop | 18.9 % · −43 % | 16.6 % · −23 % | 15.3 % · −18 % |
| S&P filter + 2 % stop | 18.0 % · −47 % | 15.9 % · −26 % | 14.7 % · −22 % |
| Own-stock filter + 1 % stop | 24.7 % · −50 % | 20.2 % · −40 % | 17.7 % · −28 % |
| S&P + own-stock filter + 1 % stop | 17.5 % · −49 % | 15.7 % · −24 % | 15.1 % · −19 % |

Selected calendar years (point-in-time, max 10 unless noted):

| Year | MACD only | S&P filter + 1 % stop | same, 20 stocks | EW top 100 | S&P 500 TR |
|---|---|---|---|---|---|
| 2001 | −26.4 % | −6.5 % | −7.3 % | −5.8 % | −10.9 % |
| 2002 | −25.1 % | −12.5 % | −10.0 % | −22.5 % | −23.4 % |
| 2008 | −30.2 % | **−5.6 %** | −5.0 % | −41.1 % | −39.6 % |
| 2009 | +16.3 % | +17.4 % | +17.4 % | +53.9 % | +32.2 % |
| 2020 | +12.7 % | +10.3 % | +17.1 % | +18.7 % | +16.4 % |
| 2022 | −17.0 % | −17.8 % | −15.0 % | −13.8 % | −18.1 % |
| 2023-2025 | +5.6 / +6.5 / +4.1 % | +11.0 / +14.4 / +11.2 % | +15.4 / +19.8 / +3.6 % | +24.2 / +18.9 / +21.9 % | +26.3 / +26.9 / +17.5 % |

![stocks regime](results/stocks_regime/stocks_regime.png)

**What to take from it**

1. **On single stocks the S&P filter + 1 % stop is a drawdown tool, and it works.** With 10 stocks the full rule set (S&P > 100-day filter, 1 % stop, re-entry only while the S&P is above its average) gives **8.4 %/yr, max DD −34 % and Sharpe 0.66**, against 6.8 % / −46 % / 0.47 for MACD alone. Out of sample (2013-2026) it makes 10.8 %/yr. The random-pick test shows that the **drawdown cut (about −11 points) is real**, while the extra return is not (6.9 % vs 7.4 % on average). The filter mainly avoids bear markets: 2008 was −5.6 % instead of −30 %, and 2001-02 −6.5 % / −12.5 % instead of −26 % / −25 %.
2. **With 20 stocks you get the lowest drawdown, −24 %** (vs −55 % for the S&P 500 and −58 % for the equal-weight top 100), at 6.7 %/yr and Sharpe 0.61. That is the most defensive version.
3. **With 3 stocks the filter hurts** (4.5-6.3 %/yr, DD −50 to −65 %). Three positions are too few: a handful of trades decides the result. The earlier random-pick test already showed that 3-stock books range from 2 to 10 %/yr on luck alone.
4. **1 % beats 2 %** in every case, by 0.2-0.7 %/yr with a similar or smaller drawdown. On stocks a campaign is stopped out on average about 4 times (1 % stop) or 2.6 times (2 % stop), and the stop + re-entry works as a "be in only when price is above my entry" rule.
5. **It still does not beat buying and holding the index on return.** 8.4 %/yr is below the S&P 500 TR (10.1 %) and the equal-weight top 100 (12.8 %). The money goes back in the strong rebound years: 2009 +17 % vs +54 % for EW, and 2023-25 also lags. What you get is **half the index drawdown at a similar Sharpe** (0.66 vs 0.60-0.67). Use it as a risk-controlled stock book, not as an alpha engine. On the biased today's-100 universe the filter also lowers CAGR (22.1 → 16.6 % at max 10) while halving the drawdown (−39 → −23 %). It is the same trade-off.
6. **The stock's own 100-day average is the wrong filter: it adds nothing over the 1 % stop alone.** 95 % of the MACD signals already have the stock above its own 100-day average, because a fresh weekly MACD up-phase almost always means the price has recovered above it. So the entry filter removes only 5 % of signals (trades at max 20: 983 → 947). The S&P filter removes 17 %. With the 1 % stop, the own-stock filter gives 5.6 % / −35 % / Sharpe 0.46 at 10 stocks (random-pick mean 6.1 % / −38 %) and 7.5 % / −34 % / 0.64 at 20 stocks. Those are about the same as the 1 % stop with no filter (6.8 % / −45 % and 8.0 % / −36 %) and clearly worse than the S&P filter on drawdown (−24 % at 20 stocks). The reason is that **the S&P filter carries market-level information a single stock doesn't have.** In a bear market (2001-02, 2008) many stocks still start new MACD up-phases above their own average and then fail. The S&P filter skips those trades; the own-stock filter takes them. Using both is no better than the S&P alone (8.1 % / −35 % at 10 stocks, 6.5 % / −24 % at 20). **Keep the S&P 500 filter; drop the own-stock MA filter.**
7. **Current state (2026-11-03):** the S&P 500 is 0.7 % below its 100-day average, so **the filter is OFF: no new stock buys and no re-entries after stops** until the S&P closes back above about 7,620. The 10-stock book still holds MRK (+45.8 %), PM (+20.8 %), V (+16.1 %), CRWD (+14.5 %), ETN (−11.6 %) and UNH (−8.8 %) under their own 1 % stop / MACD / 1-year rules. VZ, HOOD and DASH are stopped out and wait for the S&P to recover before re-entry at their entry price. With the own-stock filter the book would differ: it holds MRK, PM, JPM, UNH, ABBV, PYPL and PLTR. VZ, DASH and NOW are stopped out and below their own 100-day average, so they cannot be re-bought yet. These are backtest model states, not investment advice.

Reproduce: `python scripts/stocks_regime_study.py && python scripts/stocks_regime_charts.py`.

---

## Short leg on the WORST weekly-MACD profile (27 DM indices + US sectors)

Scripts: `scripts/worst_short_study.py` and `scripts/worst_short_charts.py`; results in `results/worst_short/`.

**How "worst MACD profile" is measured.** A raw MACD isn't comparable across assets, because it is in index points. So each week every asset gets four candidate scores; lower = worse:

| Score | Formula | What a very negative value means |
|---|---|---|
| depth | MACD / price | the 12-week average is far below the 26-week average, i.e. a deep downtrend |
| depth_vol | MACD / (price × 26-week volatility) | the same depth measured in the asset's own weekly swings, so quiet utilities and volatile Hang Seng compare fairly |
| accel | (MACD − signal) / price | negative histogram: the downtrend is **still accelerating** |
| **composite** | average cross-sectional rank of depth_vol and accel_vol | **deep in σ terms AND still getting worse.** This is the "worst profile" chosen in-sample (1990-2012) |

**Short leg rules:**
* Each week, short the **3 worst** assets that are also in a downtrend (MACD and signal below 0), at the next open.
* Cover when MACD turns above 0, when the asset leaves the worst 6, or after 1 year.
* 1/3 of equity per short, no leverage.

| 1990-2026 | Trades | Win % | Avg trade | CAGR (in / out of sample) | Max DD | Sharpe |
|---|---|---|---|---|---|---|
| **Short the 3 worst — composite (chosen)** | 337 | 34 % | −1.1 % | **−3.9 %** (−1.1 / −8.4) | **−83 %** | −0.21 |
| Short the 3 worst — depth / depth_vol / accel | 213-299 | 28-32 % | −1.5 to −2.1 % | −4.8 to −5.1 % | −86 to −88 % | −0.26 to −0.30 |
| Short only the single worst / the 5 worst | 161 / 389 | 39 / 33 % | | −4.8 / −3.9 % | −88 / −81 % | −0.14 / −0.25 |
| *Long the 3 best profiles (mirror image, depth_vol)* | 269 | 55 % | +4.4 % | 9.4 % (8.6 / 10.6) | −40 % | 0.68 |
| *Contrarian: BUY the 3 worst profiles, sell when MACD > 0* | 214-340 | **66-72 %** | +1.0 to +2.0 % | 2.2-3.0 % | −61 to −72 % | 0.21-0.26 |
| *Long: new MACD up-phase, max 3 (earlier rules)* | 133 | 48 % | +7.8 % | **8.4 %** | **−24 %** | **0.80** |
| Earlier long + 50 % worst-short overlay | – | – | – | 6.8 % | −21.5 % | 0.64 |
| Earlier long + 100 % worst-short overlay | – | – | – | 4.6 % | −34.5 % | 0.37 |
| 50 / 50 earlier long + worst short | – | – | – | 2.6 % | −17.7 % | 0.37 |
| *Equal-weight buy & hold of the 27* | – | – | – | 9.7 % | −52 % | 0.68 |

![worst short](results/worst_short/worst_short.png)

**What to take from it (and what "worst MACD profile" means)**

1. **The worst profile is a stretched, still-falling market, and those usually bounce.** An asset that is deep below its 26-week trend and still accelerating down is *oversold*. Buying the 3 worst profiles wins **66-72 %** of the time. Shorting them therefore loses: −4 to −5 %/yr, with a −83 % to −88 % drawdown. That is the same mean-reversion this project started from (DeMark 9 after a sell-off).
2. **The short leg is crash insurance, not an alpha source.** It made money in only 9 of 36 years, but those are the crashes: **+55 % in 2008, +28 % in 2002, +21 % in 2000, +8 % in 2018**. It loses steadily in normal years and gets hit hardest in V-shaped rebounds: −27 % in 2020, −22 % in 2023, −20 % in 2019 and 2025.
3. **As an overlay it costs more than it saves.** Adding a 50 % worst-profile short to the long strategy lowers the max drawdown only from −24 % to −21.5 %, but cuts CAGR from 8.4 % to 6.8 % and Sharpe from 0.80 to 0.64. A full-size overlay is worse. The long leg's own MACD < 0 exit already takes you to cash in bear markets, which is cheaper protection.
4. **Use the MACD profile the other way round.** The *best* profile (highest depth_vol) is a decent long rotation: 9.4 %/yr, Sharpe 0.68, −40 % DD. The earlier rule (buy a new up-phase) is still the best long: Sharpe 0.80, −24 % DD.
5. **If you still want a short leg:** keep it small and use it only in a market-wide downtrend (e.g. when most of the 27 have MACD < 0). It only pays when the whole market is falling, not when one sector is.

**Worst MACD profiles right now** (week ending 2026-10-30; composite rank, 1 = worst):

| Rank | Asset | MACD % of price | MACD in σ | Histogram % | Downtrend (both lines < 0) | Reading |
|---|---|---|---|---|---|---|
| 1 | XLI Industrials | −0.62 % | −0.40 | −1.16 % | no (signal still > 0) | fresh roll-over, falling fast but not yet a confirmed downtrend |
| 2 | **CAC 40** | −1.14 % | −0.74 | −0.80 % | **yes** | the worst *confirmed* downtrend, still accelerating. **Short held since 2026-10-26 (−2.6 %)** |
| 4 | XLC Communication Services | −1.54 % | −0.68 | −0.83 % | yes | deep and accelerating; just outside the worst 3 |
| 4 | FTSE MIB / Russell 2000 | +0.59 % / +0.17 % | +0.33 / +0.09 | −1.33 % / −1.27 % | no | still in up-trends, but momentum fading fast |
| 6 | Hang Seng | −1.85 % | −0.76 | −0.75 % | yes | the deepest downtrend in σ terms |
| 12 | XLU Utilities | −1.34 % | −0.57 | +0.04 % | yes | deep but already stabilising (histogram turned up) |

These are backtest model states, not investment advice.

Reproduce: `python scripts/worst_short_study.py && python scripts/worst_short_charts.py`.

---

## US stocks without survivorship bias: point-in-time S&P 500 membership

Scripts: `scripts/sp500_pit_data.py`, `scripts/sp500_pit_fix.py` and `scripts/sp500_pit_study.py`; results in `results/sp500_pit/`.

* **Membership:** daily S&P 500 constituents since 1996 from [fja05680/sp500](https://github.com/fja05680/sp500), based on Andreas Clenow's list. 1,209 tickers have ever been members.
* **Size ranking:** each month the **100 largest members by trailing 1-year average dollar volume** form the tradable list. Historical market caps aren't freely available, so dollar volume stands in for size. A MACD signal counts only if the stock is on that month's list.
* **Same rules as before:** MACD < 0 stop, 1-year exit, 1/N of equity per position, cash-capped. A stock whose price history ends mid-trade (delisted or acquired) is closed at its last price.
* **Remaining bias:** Yahoo only keeps listed stocks. With renames mapped (FB→META, ANTM→ELV, UTX→RTX, BK→BNY, MMC→MRSH, …), 785 of 1,209 tickers have data. Member coverage is 38 % in 1996, 47 % in 2000, 61 % in 2008, 74 % in 2015 and 98 % in 2026. The missing names are mostly bankruptcies and takeovers (Lehman, WorldCom, Enron, Bear Stearns, Wachovia, Time Warner, …), so these results are **still somewhat too optimistic**, especially before 2010. Fully clean data needs a paid source (Norgate, CRSP, EOD Data).

| 1997-2026, compounded | **Point-in-time top 100**: CAGR | Max DD | Sharpe | *Today's top 100 (biased)*: CAGR | Max DD |
|---|---|---|---|---|---|
| MACD signal, max 3 (asked rules) | **8.7 %** (IS 7.4 / OOS 9.9) | −54 % | 0.47 | *20.8 %* | *−75 %* |
| MACD signal, max 10 | 6.8 % | −46 % | 0.47 | *19.3 %* | *−53 %* |
| MACD signal, max 20 | 8.3 % | −43 % | 0.59 | *18.2 %* | *−41 %* |
| 1 % stop + re-entry, max 3 | 9.1 % | −46 % | 0.53 | *24.5 %* | *−51 %* |
| 1 % stop + re-entry, max 10 | 6.8 % | −45 % | 0.53 | *20.8 %* | *−39 %* |
| **1 % stop + re-entry, max 20** | 8.0 % | **−36 %** | **0.67** | – | – |
| Pyramid up 1 %, 5 adds, max 3 / max 10 | 8.2 % / 6.5 % | −51 % / −43 % | 0.47 | – | – |
| Martingale ladder ×2, max 3 / max 10 | 3.9 % / 3.1 % | −42 % / −35 % | 0.30 | – | – |
| Max 3, random pick among same-day signals (20 draws) | 5.0 % (2.0-10.1) | −63 % | 0.33 | – | – |
| *Equal-weight buy & hold of the point-in-time top 100* | **12.8 %** | −58 % | **0.67** | *20.3 % (today's 100)* | *−47 %* |
| *S&P 500 total return* | **10.1 %** | −55 % | 0.60 | | |

![pit](results/sp500_pit/equity_pit.png)

**What to take from it**

1. **Survivorship bias explained almost all of the earlier stock result.** Picking from stocks that were really in the S&P 500 at the time, the 3-stock MACD strategy drops from **20.8 % to 8.7 %/yr** over the same 1997-2026 window. Even that is still flattered by the missing bankruptcies.
2. **On US large caps the MACD strategy does not beat buy & hold.** It made 7-9 %/yr, against 10.1 % for the S&P 500 and 12.8 % for an equal-weight top 100. The 3-stock version is also luck-dependent: a random pick among same-day signals gives 2-10 %/yr.
3. **The only redeeming setup is 20 stocks with the 1 % stop + re-entry.** It makes 8.0 %/yr with a **−36 %** max drawdown (vs −55 % for the S&P 500) and Sharpe 0.67, about the same as the equal-weight index. That is a risk-reduction tool, not an alpha source.
4. **Ladder / martingale remains the worst** (3-4 %/yr), and pyramiding is neutral. Same as on indices.
5. **Practical conclusion:** the weekly-MACD idea works better on diversified indices and sectors (8.4 %/yr, −24 % DD, Sharpe 0.80) than on single stocks. On stocks it mostly cuts the drawdown and gives up return.

---

## Short leg: shorting DM indices when the weekly MACD turns below zero

Scripts: `scripts/macd_short_study.py`, chart `scripts/pit_short_charts.py`; results in `results/macd_short/`. This mirrors the long strategy on the 16 DM indices:

* **Short** at the next open when the weekly MACD and signal both turn below 0.
* **Cover** when the weekly MACD goes back above 0, or after 1 year. Tested with and without a **1 % stop above the entry plus re-entry**: re-short when price falls back to the entry.
* **Max 3 shorts**, 1/3 of equity each.
* Shorts are simulated with the long engine on prices mirrored around the entry. This is exact per unit and cross-checked against hand calculations. Index futures carry is not modelled.

| 1990-2026, 16 DM indices, max 3 | Trades | Win % | CAGR (in / out of sample) | Max DD | Sharpe |
|---|---|---|---|---|---|
| **Short leg, MACD stop, 1 year** | 135 | 23 % | **−3.2 %** (−0.8 / −7.1) | **−76 %** | −0.24 |
| Short leg + 1 % stop & re-entry | 135 | 17 % | −0.4 % (+1.4 / −3.3) | −51 % | 0.00 |
| Short + 1 % stop & re-entry, target −20 %, 1 year (best cell) | 147 | 23 % | +0.5 % (+2.5 / −2.7) | −42 % | 0.10 |
| Short leg on all 27 (indices + sectors) | 156 | 24 % | −2.9 % | −72 % | −0.18 |
| *Long leg, same 16 DM indices, MACD stop* | 125 | 46 % | **6.9 %** | −23 % | 0.71 |
| *Long leg + 1 % stop & re-entry* | 125 | 41 % | 6.9 % | −20 % | **0.76** |
| 50 / 50 long + short (both with 1 % stop) | – | – | 3.4 % | −15 % | 0.59 |
| Long 100 % + short overlay 100 % (both with 1 % stop) | – | – | 6.6 % | −29 % | 0.59 |
| *Equal-weight DM indices buy & hold* | – | – | 8.6 % | −55 % | 0.61 |

![short](results/macd_short/equity_short.png)

**What to take from it**

1. **The short leg loses money over time.** It does pay in real bear markets: +30 % in 2002, +41 % in 2008, +6-8 % in 2000-01 and 2011. But most MACD < 0 phases are just corrections inside a rising market. 89 % of shorts are stopped by the MACD turning back up, at about −5 % each.
2. **Rebounds are brutal for a slow weekly signal.** The worst shorts were opened right at the lows: Russell 2000 at the March 2020 bottom lost −47 %, and FTSE 100 in March 2020 lost −22 %. 2020 alone cost the short book −30 %.
3. **The 1 % stop & re-entry halves the damage** (−0.4 %/yr instead of −3.2 %, DD −51 % instead of −76 %) **but does not make it profitable.** Out-of-sample (2013-2026) every short variant lost money.
4. **Adding the short leg makes the long strategy worse.** The legs are negatively correlated (−0.16 to −0.25). 50/50 cuts the drawdown to −15 % but also cuts return to 3.4 % (Sharpe 0.59 vs 0.76 long-only). Long + short overlay is 6.6 %/yr with Sharpe 0.59.
5. **If you want downside protection,** the long leg's own MACD exit already moves you to cash in bear markets. A short leg on a slow weekly signal is not worth carrying. If anything, use it only as a small hedge with the 1 % stop.

**Short book live now (2026-11-03):**
* Short **Hang Seng** since 2026-06-22: +1.2 %, or −0.9 % with the 1 % stop after 2 stop-outs.
* Short **CAC 40** since 2026-10-26: −2.6 %; with the 1 % stop it is flat, waiting to re-short at the entry.
* These are the only two DM indices with both weekly MACD lines below 0. These are backtest model states, not investment advice.

---

## The same MACD tests on the 100 biggest US stocks

Universe (`scripts/us100_universe.py`): today's 100 largest S&P 500 companies by market cap (Yahoo Finance, Nov 2026), one share class each, from Apple ($5.1tn) to #100 at $123bn. Daily data is dividend- and split-adjusted, from 1990 or the listing date. Rules are the same as the index study: buy at the next open when the weekly MACD and signal both turn > 0, exit on MACD < 0 or after 1 year, 1/N of equity per position, no leverage. Script: `scripts/us100_study.py`; results in `results/us100/`.

> **Big caveat: survivorship bias.** These are *today's* winners: Nvidia, Tesla, Vertex, Palantir and so on. Any backtest on them back to 1990 looks great, so the fair yardstick is **buy & hold of the same 100 stocks**, which has the same bias.

| 1990-2026, compounded | Positions | CAGR (in / out of sample) | Max DD | Sharpe | Invested |
|---|---|---|---|---|---|
| **MACD signal, max 3 stocks (asked rules)** | 201 | **21.3 %** (17.7 / 27.6) | **−75 %** | 0.85 | 91 % |
| MACD signal, max 5 | 325 | 19.9 % | −61 % | 0.91 | 91 % |
| MACD signal, max 10 | 607 | 20.7 % (23.3 / 16.2) | −53 % | 1.07 | 89 % |
| MACD signal, max 20 | 1,131 | 19.3 % (19.8 / 18.3) | −41 % | 1.15 | 85 % |
| **+ 1 % stop, re-entry at first entry, max 3** | 201 | **24.5 %** (23.7 / 25.7) | −51 % | 1.02 | 76 % |
| **+ 1 % stop, re-entry at first entry, max 10** | 608 | 22.1 % (25.5 / 16.4) | **−39 %** | **1.25** | 77 % |
| Pyramid up, 1 % step, 5 adds, max 3 / max 10 | 201 / 608 | 21.6 % / 19.9 % | −61 % / −50 % | 0.89 / 1.08 | 83 % / 81 % |
| Martingale ladder ×2, 1 % step, max 3 / max 10 | 201 / 616 | 13.5 % / 12.7 % | −72 % / −46 % | 0.69 / 0.87 | 50 % |
| Same rules, max 3, random pick among same-day signals (30 draws) | – | 16.0 % (10.6-24.1) | −62 % (−50 to −73) | 0.75 (0.55-1.03) | – |
| *Equal-weight buy & hold of the same 100 stocks* | – | **22.0 %** (21.4 / 22.7) | **−47 %** | **1.13** | 100 % |
| *S&P 500 total return* | – | 10.8 % | −55 % | 0.66 | 100 % |

![us100](results/us100/equity_us100.png)

**What to take from it**

1. **The 20 %+ returns come from the stock list, not the signal.** Just holding the same 100 stocks made 22 %/yr with Sharpe 1.13. The asked rules (max 3) made 21 %/yr with a **−75 % drawdown**: 2000-02 wiped out three quarters of the account, and the drawdown from the Nov 2000 peak bottomed only in July 2009. Against the right yardstick the plain MACD strategy adds nothing.
2. **The weekly MACD is too slow for single stocks.** Individual stocks crash far faster than indices. Trades lost **−53 %** (Intuitive Surgical 2001), −41 % (Capital One 2002), −36 % (Nvidia 2001) and −32 % (Gilead 2000) before the weekly MACD turned negative. With only 3 positions, a few of those sink the account.
3. **Which 3 stocks you hold is mostly luck.** Picking randomly among same-day signals gives anywhere from 10.6 % to 24.1 %/yr (mean 16 %). The 21 % comes largely from a few giant winners: Vertex +391 % in 1999-2000, Tesla, Amphenol, Merck. The take-profit grid is noisy for the same reason.
4. **On stocks the 1 % stop with re-entry *does* help, unlike on indices.** It cuts the crashing stocks early and re-buys if they recover:
   * Max 3: 24.5 %/yr with DD −51 % instead of −75 %.
   * Max 10: 22.1 %/yr, **DD −39 %, Sharpe 1.25**. This is the only setup that beats buy & hold of the same stocks on risk (−39 % vs −47 %, Sharpe 1.25 vs 1.13).
   * Caveat: the max 10 version earned only 16.4 %/yr in 2013-2026, versus 22.7 % for buy & hold.
5. **More positions are safer:** 3 → 10 → 20 stocks moves the drawdown from −75 % → −53 % → −41 % at about the same return. Pyramiding is about neutral, as on indices. The martingale ladder is clearly worse (12-14 %/yr).
6. **What to use on stocks:** hold **10-20 names**, not 3. **Add the 1 % stop with re-entry at the first entry price.** Judge it against buy & hold of the same list, not against the S&P 500. To remove the survivorship bias you would need point-in-time index membership (e.g. a paid S&P constituents history).

**Live (asked rules, max 3, 2026-11-03):** Merck (+50 % since 2025-11-24), Eli Lilly (+41 % since 2026-05-18), Visa (+18 % since 2026-07-20). 66 of the 100 stocks have both weekly MACD lines above 0 right now. These are backtest model states, not investment advice.

*Sizing note:* this study caps each new position at the cash not tied up in open positions, so there is no hidden leverage. The same fix applied to the index study changes it only marginally: base 8.5 % → 8.4 %/yr, DD −25.5 % → −24.2 %, Sharpe 0.79 → 0.80.

Reproduce: `python scripts/us100_universe.py && python scripts/us100_data.py && python scripts/us100_study.py && python scripts/us100_charts.py`.

---

## Weekly-MACD strategy: pyramiding up (1 unit, +1 unit every 1 % up)

Same signal, MACD < 0 stop, 3 slots and compounding as above (`scripts/macd_pyramid_study.py`, results in `results/macd_pyramid/`).
* Start with **1 unit** at the first entry E0.
* Add **+1 unit on a buy-stop every 1 % above E0** (E0 × 1.01, × 1.01², …), up to K adds.
* The K+1 units together equal the slot's 1/3 of equity, so there is no leverage.
* Everything is closed on MACD < 0 or at the take-profit (same time × level grid as before).

| 1-year exit, no level | Avg units bought | Win % | Avg campaign | Winners / losers avg | Worst campaign | CAGR (in / out of sample) | Max DD | Sharpe | Invested |
|---|---|---|---|---|---|---|---|---|---|
| **All-in at entry (base)** | 1 | 48 % | +7.8 % | +22.3 % / −5.5 % | −12.8 % | **8.5 %** (7.4 / 10.3) | −26 % | **0.79** | 69 % |
| Pyramid, 3 adds | 3.4 | 45 % | +7.3 % | | −14.2 % | 8.1 % (7.0 / 9.9) | −25 % | 0.79 | 64 % |
| Pyramid, 5 adds | 4.7 | 45 % | +7.0 % | | −15.0 % | 7.7 % (6.6 / 9.6) | −25 % | 0.78 | 61 % |
| Pyramid, 10 adds | 7.6 | 42 % | +6.0 % | +18.9 % / −3.4 % | −17.0 % | 6.7 % (5.6 / 8.4) | −22 % | 0.73 | 54 % |
| Pyramid, 20 adds | 11.8 | 38 % | +4.5 % | | −15.7 % | 4.9 % (4.1 / 6.3) | −18 % | 0.65 | 40 % |
| Pyramid, 40 adds | 14.2 | 38 % | +2.7 % | | −8.1 % | 3.1 % | −9 % | 0.61 | 23 % |
| Pyramid, 2 % step, 10 adds | 6.2 | 38 % | +4.5 % | | −15.8 % | 4.9 % | −18 % | 0.66 | 40 % |

![pyramid](results/macd_pyramid/macd_pyramid.png)

**What to take from it**

1. **Pyramiding up does not improve the strategy.** Every add lowers CAGR and Sharpe: 0.79 → 0.78 → 0.73 → 0.65 for 0 / 5 / 10 / 20 adds. A small pyramid (3-5 adds) is about the same as the base; a large one is clearly worse.
2. **Why:**
   * It does cut the failed trades: the average MACD-stop loss falls from −4.4 % to −3.2 % with 10 adds.
   * But it cuts the winners more, from +26 % to +20 % on 1-year exits, because the extra units are bought higher.
   * And when a strong trend finally rolls over, the position is fully loaded at the top before the weekly MACD stop fires. That makes the worst campaign *worse* (−17 % vs −13 %).
   * Return per dollar invested is unchanged (about 12.3 % for every variant), so pyramiding is just a slower way of getting in.
3. **Take-profit:** the pattern is the same as before. A long hold (2 years / none) with no target gives the most return (8.0-8.2 % with 10 adds). The best Sharpe cells (0.81 at 3 months / +10 %) only invest 8-16 % of the money, so they earn 1-3 %/yr. You would need leverage to make them useful, and leveraged they end up no better than the base.
4. **Bottom line:** keep buying the full position at the signal. If you want a gentler ramp-in, 3 adds of 1 % costs almost nothing (8.1 % vs 8.5 % CAGR, same Sharpe).

Reproduce: `python scripts/macd_pyramid_study.py && python scripts/macd_pyramid_charts.py`.

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
  macd_variants_study.py  1 % stop + re-entry, 1 % ladder / martingale, take-profit grid -> results/macd_variants/
  macd_variants_charts.py its chart
  macd_pyramid_study.py   pyramiding up (+1 unit every 1 % up) -> results/macd_pyramid/
  macd_pyramid_charts.py  its chart
  us100_universe.py / us100_data.py / us100_study.py / us100_charts.py
                   the same MACD tests on the 100 biggest US stocks -> data/us100/, results/us100/
  sp500_pit_data.py / sp500_pit_fix.py / sp500_pit_study.py
                   point-in-time S&P 500 top 100 (less survivorship bias) -> data/sp500_pit/, results/sp500_pit/
  macd_short_study.py  short leg on DM indices (MACD < 0), combined long/short -> results/macd_short/
  pit_short_charts.py  charts for both
  worst_short_study.py / worst_short_charts.py
                   short leg on the worst weekly-MACD profile of the 27, contrarian test, overlays -> results/worst_short/
  macd_regime_study.py / macd_regime_charts.py
                   MACD long only when the S&P 500 is above its 100-day average (+ exits, re-entry, 50/200d) -> results/macd_regime/
  stocks_regime_study.py / stocks_regime_charts.py
                   100 single stocks (point-in-time and today's top 100): S&P or own-stock 100-day filter + MACD + 1-2 % stop -> results/stocks_regime/
  stocks_ma50_study.py / stocks_ma50_charts.py
                   same with the S&P 50-day filter and a 3-month hold (filter x hold x stop grid) -> results/stocks_ma50/
  indices_ma50_study.py / indices_ma50_charts.py
                   S&P 50-day filter + 3-month hold on the 27 DM indices + sectors (filter x hold x stop x max 3/5) -> results/indices_ma50/
  delayed_entry_study.py / delayed_entry_charts.py
                   wait 1-3 months after the MACD signal, buy if the MACD stayed > 0, hold the rest of the year -> results/delayed_entry/
  combo_kelly_study.py / combo_kelly_charts.py
                   best index book + best stock book, T-bills on idle cash, Kelly / leverage vs Calmar -> results/combo_kelly/
  drawdown_study.py / drawdown_charts.py
                   drawdown depth, dates and time under water of the best books and the combination -> results/drawdowns/
strategy/grid.py   the grid engine (levels, LIFO units, starting size j0)
strategy/macd_engine.py  campaign engine for the MACD strategy (base / 1 % stop + re-entry / ladder / pyramid, time + level TP)
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
