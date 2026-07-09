# Zone Identification — Detailed Rules

## 1. Candle classification

Classify each candle relative to local volatility (use ATR(14) if OHLV data is available; if only
an image is available, use visual body/range size relative to the last ~20 candles):

- **Rally candle**: bullish (close > open), body ≥ ~50% of that candle's range, part of a
  same-direction sequence.
- **Drop candle**: bearish (close < open), same body/range condition.
- **Base candle**: small body relative to recent average (rule of thumb: body < 50% of the average
  body size of the preceding 10-20 candles), and/or overlapping range with its neighbors — the
  market is indecisive, not trending.

A "Rally" or "Drop" leg needs **at least 2 consecutive same-direction candles** to count as a real
leg (single-candle spikes are noise, not institutional legs-in/out — though a single very large
candle with a gap can substitute for the leg-out requirement, see Explosiveness scoring).

## 2. Finding the base

Scan for 1-6 consecutive base candles sandwiched between a leg-in and a leg-out. Practical
guidance:

- **1-3 base candles = tight base = strong zone.** This is the ideal case — it means the imbalance
  was so severe the market couldn't consolidate for long before resuming/reversing.
- **4-6 base candles = acceptable but weaker.** More time = more of the resting orders may have
  already been worked by the time the leg-out happens.
- **7+ candles of consolidation is not a base** — it's a range/consolidation zone in its own right.
  Don't force-fit it into the RBR/RBD/DBR/DBD framework; treat it as a separate range play if
  relevant, or skip it.

## 3. Confirming a valid leg-out

The leg-out must be *visibly* more aggressive than the leg-in and than the base's internal
volatility. Concretely, look for at least one of:

- A candle (or the sum of the first 2-3 leg-out candles) whose range is ≥ ~1.5-2x the base
  candles' average range.
- A gap away from the base (opening outside the prior candle's range).
- 2+ consecutive same-direction candles with minimal upper/lower wicks (strong closes near the
  extreme), indicating no absorption on the way out.

If the "leg-out" is just a slightly-larger-than-average candle that's still choppy or quickly
reverses, don't mark a zone — this is the single most common beginner mistake (over-marking zones
on ordinary noise).

## 4. Drawing zone boundaries

- **Demand zone (base before a Rally leg-out)**: bottom of the rectangle = lowest wick among the
  base candles; top of the rectangle = highest body (open/close, not wick) among the base candles.
- **Supply zone (base before a Drop leg-out)**: top of the rectangle = highest wick among the base
  candles; bottom of the rectangle = lowest body among the base candles.
- Do not include the leg-in or leg-out candles themselves in the rectangle — only the base.
- If a base candle has an unusually long wick that would make the zone very wide, it's acceptable
  to use the body extreme instead and treat the wick as an outlier — note this assumption to the
  user.

## 5. Multi-timeframe approach

1. On a higher timeframe (weekly/daily for swing analysis, 4H/1D for intraday context), establish
   overall trend bias and mark the 1-3 most significant, closest un-mitigated zones.
2. Drop to the timeframe the user actually trades and look for a DBR/RBD (reversal) pattern nested
   *inside* the higher-timeframe zone — this "zone within a zone" is the highest-conviction setup
   because it aligns institutional-level and execution-level order flow.
3. Countertrend zones (e.g., a demand zone found during an overall downtrend) should be explicitly
   flagged as lower-probability and, if scored, should have their Overall score annotated
   "(countertrend)".

## 6. Freshness / mitigation tracking

- **Fresh / virgin**: zero touches since formation. Highest-probability category.
- **Tested**: price has wicked into the zone and rejected (closed back outside) — the zone is
  weaker but still tradeable; each additional touch weakens it further.
- **Mitigated / invalidated**: a candle has *closed* through the far side of the zone (not just
  wicked). Treat the zone as consumed — remove it from active trade consideration. It's fine to
  still report it in a historical summary, but mark status clearly as "Mitigated."
- A mitigated supply zone that gets convincingly broken can flip into a demand zone going forward
  (flip zone) — mention this if relevant, but grade the flipped zone fresh, on its own merits, not
  by inheriting the old zone's scores.

## 7. Common mistakes to avoid when applying this skill

- Redrawing/nudging zone boundaries after the fact to fit a preferred narrative — lock the
  boundaries once drawn from the base candles.
- Marking a zone from a meandering/choppy departure (no real imbalance).
- Treating a zone as equally valid after several tests as it was when fresh — always downgrade
  Freshness with each touch.
- Ignoring higher-timeframe opposing zones sitting close by — always scan a wider window than just
  the immediate base.
- Forcing a classification (RBR/RBD/DBR/DBD) onto a structure that doesn't have a genuine base —
  if there's no consolidation, there's no zone.