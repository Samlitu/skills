---
name: supply-demand-trading-zones
description: Analyze a scrip/stock/forex/crypto price chart (OHLC data or chart image) to (1) identify supply and demand zones, (2) classify the base pattern that formed each zone as Rally-Base-Rally (RBR), Rally-Base-Drop (RBD), Drop-Base-Rally (DBR), or Drop-Base-Drop (DBD), and (3) score each zone 1-7 on Freshness, Strength, and Explosiveness to produce an overall trade-quality rating. Use this skill whenever the user mentions "supply and demand zones," "supply zone," "demand zone," "RBR/RBD/DBR/DBD," "rally base rally," "drop base rally," "base candles," "institutional footprint," "zone freshness/strength," or asks you to mark up, grade, or rate zones on a scrip/stock/forex/crypto chart — even if they just paste OHLC data or upload a chart image and ask "find the zones" or "where should I buy/sell this." Also use it to review or grade a zone the user has already drawn.
---

# Supply and Demand Trading Zones

A systematic, rules-based workflow for finding institutional supply/demand zones on a price
chart, classifying the leg-in/base/leg-out pattern that created each zone, and grading zone
quality on a 1-7 scale across three dimensions: **Freshness**, **Strength**, and **Explosiveness**.

This skill is for technical/price-action analysis education and research. It does not predict
outcomes or constitute investment advice — always say so plainly when presenting results, and
note that zones are probability tools, not guarantees.

## When to use this

- User uploads/pastes OHLC data (CSV, screenshot of a chart, TradingView export, broker export) for a
  scrip/stock/pair/crypto and wants zones identified or graded.
- User uploads a chart image and asks to mark up supply/demand zones visually.
- User wants to know if a zone is "fresh," "strong," or tradeable.
- User wants a watchlist of scrips scored by zone quality.

## Core concepts (read this before doing anything)

Supply and demand zones are **not** the same as support/resistance. Support/resistance levels get
*stronger* with repeated touches; supply/demand zones get *weaker* with repeated touches, because
each revisit consumes the unfilled institutional orders left behind. A zone is defined by the
**explosive move that left it**, not by how many times price has bounced there.

Every zone has three structural parts:

1. **Leg-in** — the move going *into* the base (a Rally = 2+ same-direction bullish candles, or a
   Drop = 2+ same-direction bearish candles).
2. **Base** — 1-6 candles of consolidation/indecision (small bodies, overlapping ranges, low
   directional conviction) where institutional orders are believed to accumulate. Tighter and
   shorter bases (1-3 candles) are stronger than wide, long bases (6+ candles).
3. **Leg-out** — the move *out* of the base. This is the "departure" — it must be visibly more
   explosive than the leg-in (larger bodies, often a gap, ideally rising participation/volume) for
   the zone to be worth marking at all. A weak, choppy leg-out is not a valid zone — skip it.

The zone itself is drawn as a rectangle covering the base candles only: from the base's extreme
wick to the base's opposite-side body extreme (top of the highest body / bottom of the lowest body
inside the base). It is **not** the leg-in or leg-out candles.

Full detection and drawing rules, plus worked examples, are in `references/zone_identification.md`
— read it before doing manual (image-based) zone marking for the first time in a conversation.

## Step 1 — Identify supply and demand zones

**Demand zone**: forms below current price. Leg-out is a Rally. Origin of buy-side imbalance.
**Supply zone**: forms above current price. Leg-out is a Drop. Origin of sell-side imbalance.

Workflow:

1. **Get the data.** If the user gave OHLC data (CSV/table/pasted values), use
   `scripts/detect_zones.py` — it is far more reliable than eyeballing and gives reproducible,
   numeric output. If the user only gave a chart image, do it visually using the rules in
   `references/zone_identification.md`, moving right-to-left from the current price bar looking for
   the nearest un-mitigated base-with-explosive-departure in each direction.
2. **Establish higher-timeframe bias first if multiple timeframes/enough data are available**
   (uptrend → prioritize demand zones for longs; downtrend → prioritize supply zones for shorts;
   counter-trend zones are lower probability — flag them as such).
3. **Mark every valid zone** you find within the visible/available data, not just the nearest one.
   For each zone capture: direction (supply/demand), price range (top/bottom), the bar index or
   date range of the base, and whether price has returned to it since (touch count) — untouched =
   "fresh," 1 touch = "tested," touched-and-closed-through = "mitigated/invalidated" (exclude
   mitigated zones from trade consideration but you can still mention them).
4. Discard candidate bases whose leg-out is not clearly stronger than the leg-in — these are just
   noise/consolidation, not real zones.

## Step 2 — Classify the pattern (RBR / RBD / DBR / DBD)

Use leg-in direction + leg-out direction:

| Leg-in | Leg-out | Pattern | Zone type | Character |
|---|---|---|---|---|
| Rally | Rally | **RBR** — Rally-Base-Rally | Demand (continuation) | Trend continuation in an uptrend. Weaker than DBR on average — smaller institutional positions typically built mid-trend. |
| Rally | Drop | **RBD** — Rally-Base-Drop | Supply (reversal) | Bearish reversal signature; found at market tops. Generally the strongest supply pattern. |
| Drop | Rally | **DBR** — Drop-Base-Rally | Demand (reversal) | Bullish reversal signature; found at market bottoms. Generally the strongest demand pattern. |
| Drop | Drop | **DBD** — Drop-Base-Drop | Supply (continuation) | Trend continuation in a downtrend. Weaker than RBD on average. |

Rules of thumb to pass on to the user:
- **Reversal patterns (RBD, DBR) > continuation patterns (RBR, DBD)** in average reaction quality,
  because reversal zones mark a genuine change in who's in control, not just a pause.
- Continuation zones (RBR/DBD) are still tradeable — they tend to act as good stop-and-reverse or
  add-to-trend entries — just size/expect them as the weaker sibling of their reversal counterpart.
- Never label a pattern from leg-in/leg-out alone without confirming the base actually consolidated
  (overlapping small-bodied candles) — a "V-shaped" spike with no real pause is not a base.

`scripts/detect_zones.py` outputs this classification automatically per zone. For image-based
analysis, walk left from the base to find the leg-in and right from the base to find the leg-out,
and apply the table above.

## Step 3 — Rate each zone 1-7 on Freshness, Strength, Explosiveness

Score every valid zone found in Step 1 on all three dimensions independently, 1 (worst) to 7 (best).
Full rubric with worked criteria is in `references/scoring_rubric.md` — read it before scoring by
hand. Summary:

**Freshness (1-7)** — has price come back and eaten into the resting orders?
- 7 = never touched since formation (fully virgin), formed recently
- 5-6 = never touched, but formed a while ago (some natural decay assumed)
- 3-4 = touched once with a clean wick rejection (partial absorption)
- 2 = touched 2+ times, or one touch that closed partway into the zone
- 1 = repeatedly touched / body-closed through part of the zone (functionally mitigated — flag as
  invalid for a fresh-zone trade thesis even though you still report the score)

**Strength (1-7)** — how imbalanced was the leg-out vs. the base/leg-in?
- Driven by: leg-out move size relative to ATR/average range, number of consecutive same-direction
  leg-out candles, presence of a gap away from the base, volume spike if volume data is available,
  and tightness of the base (fewer, smaller-bodied base candles = stronger).
- 7 = large gap or 3+ powerful same-direction candles, tight 1-2 candle base, volume/size multiple
  ≥3x the local average
- 4 = solid single strong candle leg-out, base of 3-4 candles, ~1.5-2x average size
- 1 = leg-out only marginally bigger than surrounding noise, wide/long base (6+ candles)

**Explosiveness (1-7)** — how *fast* did price leave, independent of total size?
- Driven by: how few bars it took to travel a fixed multiple of ATR away from the zone, the size of
  just the *first* leg-out candle relative to the base candles, and any gap.
- 7 = price clears 2x+ ATR away within 1-2 bars of leaving the base, often via a gap
- 4 = steady clear move away over 3-5 bars, no hesitation back into the base
- 1 = price drifts away slowly over many bars, repeatedly wicking back toward the base

**Overall zone score** = round(average of the three, to nearest 0.5), reported alongside the three
sub-scores — never collapse to a single number without also showing the breakdown, since a trader
may care about one dimension more than another (e.g., a scalper cares more about Explosiveness, a
swing trader more about Freshness).

## Output format

For chart/data analysis requests, default to a table, one row per zone, sorted by proximity to
current price:

| # | Type | Pattern | Zone range | Base date/bars | Freshness | Strength | Explosiveness | Overall | Status |
|---|---|---|---|---|---|---|---|---|---|

Follow the table with 1-2 sentences per zone flagging anything a mechanical score can't capture
(e.g., "this DBR zone sits inside a larger daily supply zone — countertrend, treat cautiously").

If the user uploaded a chart image and a visual markup would help, use the Visualizer to draw the
zones as colored rectangles over a reconstruction of the price action, or annotate a copy of their
image if you have image-editing tools available — a table alone often isn't enough for "show me
the zones on the chart" requests.

Always close with a short, plain note that this is a probability-based technical framework, not a
guarantee, and that position sizing/stop placement is the user's own risk decision.

## Using the detection script

`scripts/detect_zones.py` takes a CSV of OHLC(V) data and prints/saves the zone table above,
computed mechanically (ATR-based leg-out threshold, base = low-momentum candles, freshness from
touch-count since formation). See the script's `--help` and the docstring at the top of the file
for the CSV column names it expects and the tunable parameters (base max length, ATR multiple for a
valid leg-out, lookback window). Prefer this script over manual eyeballing whenever OHLC data is
available — it removes hindsight bias and is exactly reproducible.

## Reference files

- `references/zone_identification.md` — detailed base/leg-in/leg-out rules, how to draw zone
  boundaries, multi-timeframe approach, invalidation/mitigation rules, worked chart examples.
- `references/scoring_rubric.md` — full 1-7 criteria tables for Freshness, Strength, Explosiveness
  with worked examples and edge cases (gaps, low-volume markets, thin scrips).