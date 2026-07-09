# 1-7 Scoring Rubric — Freshness, Strength, Explosiveness

Score each dimension independently. Do not let a high score on one dimension pull up your estimate
of another — a zone can be very Fresh but weak (Strength 2) if the leg-out was unconvincing.

---

## Freshness (has the zone been "spent")?

| Score | Criteria |
|---|---|
| 7 | Zero touches since formation, and formed recently (within the recent ~20-30% of the visible chart / a small number of ATR-normalized bars ago). Fully virgin, still "current." |
| 6 | Zero touches, but formed further back in the data — still virgin, slightly discount for age/uncertainty about intervening off-chart activity. |
| 5 | Zero touches, formed long ago relative to the visible window (low confidence it's still relevant, but technically untested). |
| 4 | One touch, clean wick-only rejection (price entered the zone and closed back outside it same or next bar). |
| 3 | One touch with a deeper probe (closed inside the zone briefly before reversing) — meaningful order absorption occurred. |
| 2 | Two or more touches with rejections, or one touch that closed partway through the zone without full invalidation. |
| 1 | Repeatedly touched, or a candle has closed through the far boundary — functionally mitigated. Report the score but flag status as "Mitigated" and exclude from fresh-zone trade ideas. |

## Strength (size of the imbalance: leg-out vs. base/leg-in)

Composite of: leg-out size relative to ATR/local average range, number of strong consecutive
leg-out candles, base tightness (fewer/smaller-bodied base candles score higher), and volume
multiple at the leg-out if volume data exists.

| Score | Criteria |
|---|---|
| 7 | Leg-out ≥3x local average range (or a clear gap), 3+ consecutive strong same-direction candles, tight 1-2 candle base, volume (if available) ≥3x average. |
| 6 | Leg-out ~2.5-3x average, 2-3 strong candles, base ≤3 candles, volume ≥2x if available. |
| 5 | Leg-out ~2-2.5x average, base ≤3 candles, decent follow-through. |
| 4 | Leg-out ~1.5-2x average, single strong candle or two moderate ones, base 3-4 candles. |
| 3 | Leg-out ~1.2-1.5x average, base 4-5 candles, some hesitation visible in the departure. |
| 2 | Leg-out only marginally larger than base candles, wide base (5-6 candles). |
| 1 | Leg-out barely distinguishable from surrounding noise, base >6 candles — borderline invalid zone; consider excluding entirely rather than scoring it 1. |

## Explosiveness (speed of departure, independent of total size)

Composite of: how many bars it took to clear a fixed multiple (~2x ATR) of distance from the zone,
size of the *first* leg-out candle specifically relative to the base, and presence of a gap.

| Score | Criteria |
|---|---|
| 7 | Gap away from the base, or ≥2x ATR cleared within 1 bar. No hesitation whatsoever. |
| 6 | ≥2x ATR cleared within 2 bars, first leg-out candle alone is large relative to the base. |
| 5 | ≥2x ATR cleared within 3 bars, minimal pullback/wick back toward the base along the way. |
| 4 | Clear, steady move away over 3-5 bars, no full retracement back into the base during the move. |
| 3 | Move away over 5-8 bars with one shallow pullback toward the zone. |
| 2 | Slow drift away over many bars with repeated wicks back toward the zone. |
| 1 | Price barely leaves the zone / lingers nearby for an extended period before any real separation. |

---

## Worked example

A daily chart shows 4 down candles (Drop leg-in) into 2 small-bodied overlapping candles (tight
base) into a gap-up candle that closes near its high, followed by 2 more strong up candles, all on
elevated volume, and price has not returned to the base since:

- Pattern: **Drop-Base-Rally (DBR)** → demand zone (reversal).
- Freshness: **7** (virgin, recent).
- Strength: **7** (gap, 3 strong candles, 2-candle base, high volume).
- Explosiveness: **7** (gap + immediate follow-through).
- Overall: **7** — textbook fresh, high-conviction reversal zone.

Contrast: same pattern shape, but the base is 5 candles wide, the leg-out is a single moderate
candle with no gap, and price has already wicked into the zone once and rejected:

- Freshness: **4** (one clean touch).
- Strength: **3** (wide base, unremarkable leg-out).
- Explosiveness: **3** (slow separation, one pullback).
- Overall: **~3.5** — a marginal, lower-conviction zone; mention it but don't oversell it.

## Notes on data-poor situations

- **No volume data** (common for spot forex/CFDs): drop the volume component and re-weight
  Strength using range/candle-size factors only — say so explicitly in your output.
- **Thin/illiquid scrips**: wide natural candle ranges can inflate apparent Strength/Explosiveness;
  sanity-check against the scrip's own historical ATR, not a generic threshold.
- **Very short data window**: if you can't see enough history to judge Freshness properly (e.g.
  only 20 bars provided), say so and treat the Freshness score as provisional.