# Methodology: Smart Trend Indicator (5-State Regime Model)

This document is the research backing for `scripts/trend_classifier.py`. It
explains *why* each indicator was chosen, *how* they're combined, and how to
tune the system.

## 1. Research summary

Production-grade "smart trend" tools (the class of indicator this skill is
modeled on) do not use a single oscillator. They stack complementary indicator
families, each responsible for a different job, then merge them with a
weighted/composite score and a state machine:

- **Trend backbone**: fast/slow EMAs establish primary direction; some tools
  add Ichimoku Cloud position and/or Supertrend for a second directional
  opinion and noise reduction.
- **Strength & volatility filter**: ADX (Average Directional Index) confirms
  whether a trend has enough conviction to be called a "trend" at all; ATR
  (Average True Range) confirms whether volatility is expanding (trending) or
  contracting (consolidating/sideways).
- **Momentum zones**: RSI is bucketed into bands (not just a single 70/30
  cross) to classify Overbought / bullish momentum / neutral / bearish
  momentum / Oversold.
- **State machine with minimum hold bars**: to stop the classification from
  flipping every bar (a "whipsaw"), the new state must remain valid for a
  minimum number of bars before it replaces the previous one.

A key nuance surfaced across multiple sources: RSI thresholds should be read
**in the context of the prevailing trend**, not in isolation. In a strong
uptrend, RSI can stay "overbought" (>70) for a long time without reversing —
that's healthy trend strength, not automatically a sell signal. Conversely,
RSI dipping to oversold *during* an uptrend is often a pullback/continuation
setup, not a reversal. This is why `trend_score` (direction) is computed
**before** RSI is applied, and RSI is used to add nuance on top of the
direction rather than to override it. Several tools explicitly recommend
attaching a moving-average-based support/resistance check alongside RSI so
that extreme readings aren't treated as automatic reversal signals in a
strong trend.

For sideways/consolidation detection specifically, the standard combination
found across multiple independent implementations is **ADX below ~20** (weak
trend strength) together with **ATR below its own moving average** (volatility
contracting) — both must agree that the market lacks conviction before the
regime is called Sideways.

## 2. Indicator definitions used

All are computed with standard formulas over OHLC data:

- **EMA(n)** — exponential moving average of `close`, span `n`.
  - `ema_fast = EMA(9)`, `ema_slow = EMA(21)`, `ema_trend = EMA(50)`
- **RSI(14)** — Wilder's Relative Strength Index over `close`, period 14.
- **ADX(14)** — Wilder's Average Directional Index (uses `+DI`/`-DI`), period 14.
- **ATR(14)** — Wilder's Average True Range over `high/low/close`, period 14,
  compared against `ATR_MA(20)` (simple moving average of ATR) to gauge
  whether volatility is expanding or contracting.
- **Supertrend(10, 3)** — ATR-based trailing stop/flip line; used as a binary
  direction confirmation (price above line = bullish bias, below = bearish
  bias) to corroborate the EMA backbone and reduce false flips.

## 3. Composite scoring

### 3.1 Trend score (direction, -1 / 0 / +1)

```
bullish_votes = 0
bearish_votes = 0

if ema_fast > ema_slow > ema_trend: bullish_votes += 1
if ema_fast < ema_slow < ema_trend: bearish_votes += 1

if close > supertrend_line: bullish_votes += 1
else: bearish_votes += 1

if bullish_votes >= 2: trend_score = +1
elif bearish_votes >= 2: trend_score = -1
else: trend_score = 0        # EMA stack and Supertrend disagree -> mixed/neutral
```

Using "votes" from two independent methods (EMA stack ordering + Supertrend
side) rather than a single crossover reduces false trend flips from a single
noisy indicator disagreeing with the others.

### 3.2 Strength / volatility filter

```
adx_weak      = ADX < adx_sideways_threshold     # default threshold: 20
atr_contract  = ATR < ATR_MA(20)                 # volatility below its own average
strength_weak = adx_weak and atr_contract
```

`strength_weak = True` means the market currently lacks both directional
conviction (ADX) and expanding volatility (ATR) — the two hallmarks of a
genuine trend are both absent, so the bar is a strong Sideways candidate
regardless of what the EMA stack says.

### 3.3 Momentum zone (RSI bands)

```
if RSI >= 70: momentum = "overbought"
elif RSI >= 50: momentum = "bullish"
elif RSI > 30: momentum = "bearish"
else: momentum = "oversold"

neutral_band = 40 <= RSI <= 60   # supports Sideways when trend/strength are also neutral
```

### 3.4 Final candidate state (decision order — first match wins)

```
if strength_weak and neutral_band and trend_score == 0:
    candidate = SIDEWAYS
elif trend_score >= 1 and momentum == "overbought":
    candidate = OVERBOUGHT
elif trend_score >= 1:
    candidate = UPTREND
elif trend_score <= -1 and momentum == "oversold":
    candidate = OVERSOLD
elif trend_score <= -1:
    candidate = DOWNTREND
else:
    candidate = SIDEWAYS
```

Rationale for the ordering: the "genuinely no conviction" Sideways check runs
first because it's the strongest, most specific condition (both strength AND
momentum AND direction agree there's nothing happening). After that, extremes
(Overbought/Oversold) are only assigned *within* an already-established trend
direction — matching the research finding that overbought/oversold readings
mean something different depending on whether they occur with or against the
prevailing trend. A bearish RSI reading with no established downtrend just
falls through to Sideways rather than being mislabeled Oversold.

### 3.5 State machine (hysteresis / minimum hold bars)

```
def apply_hysteresis(candidate, prev_state, bars_in_state, min_hold_bars=3):
    if prev_state is None:
        return candidate, 1
    if candidate == prev_state:
        return candidate, bars_in_state + 1
    if bars_in_state < min_hold_bars:
        # Not held long enough yet to "earn" a flip; stay in previous state
        return prev_state, bars_in_state + 1
    return candidate, 1
```

This prevents the label from oscillating rapidly bar-to-bar when the
composite score is right at a boundary. `min_hold_bars` is the main "how
reactive vs. how stable" tuning knob (see SKILL.md tuning guide).

## 4. Close-only fallback mode

If only `close` prices are available (no OHLC):
- `high = low = close` is used, which makes ATR degrade to the average
  absolute bar-to-bar change (still usable as a rough volatility proxy, just
  noisier — true ATR needs the intraday range).
- ADX becomes less reliable without real highs/lows; the script will emit a
  warning and, in this mode, gives ADX less weight by requiring **both** the
  EMA-vote mixed condition *and* an ATR contraction before calling Sideways,
  rather than trusting ADX alone.
- Supertrend also degrades slightly (same high=low=close substitution) but
  remains directionally useful.

Recommendation to the user: whenever possible, use real OHLC data — it
meaningfully improves ADX/ATR/Supertrend accuracy over close-only series.

## 5. Combining with other indicators (extending this skill)

The scoring system is modular — the `trend_classifier.py` functions
(`compute_ema`, `compute_rsi`, `compute_adx`, `compute_atr`,
`compute_supertrend`) can be swapped or supplemented. Natural extensions
found in the research:

- **Bollinger Bands**: add a rule that Overbought/Oversold requires price to
  also be at/beyond the upper/lower band, for stricter extremes.
- **Ichimoku Cloud**: add "price above/below cloud" as a third directional
  vote alongside EMA-stack and Supertrend for even more false-flip
  resistance.
- **Volume / Money Flow Index (MFI)**: corroborate Overbought/Oversold with
  volume-backed momentum instead of price-only RSI.
- **Multi-timeframe confirmation**: run the same classifier on a higher
  timeframe (e.g. 4H when trading 1H) and only accept Uptrend/Downtrend
  labels on the lower timeframe when the higher timeframe agrees — this is a
  commonly cited technique for filtering out lower-timeframe noise.

## 6. Sources consulted

- TradingView — "Smart Trend Indicator" (EMA backbone + Ichimoku + Heikin
  Ashi/Supertrend + Pivot/ATR filters + RSI zones + composite scoring + state
  machine with minimum hold bars; 5-state regime model identical in spirit to
  this skill).
- TradingView — "Smart Buy/Sell Signal Indicator" (Supertrend + Bollinger
  Bands for OB/OS + RSI momentum confirmation + ADX strength filter combined
  as layered confirmation).
- TradingView (India) — "Sideways" indicator (RSI + ADX combination for
  sideways detection; RSI-band mapping of >50 to uptrend bias, <50 to
  downtrend bias, 40-60 to sideways).
- quivofx — "Smart Trend Indicator" (trend line + band structure; buy setups
  = uptrend + oversold band, sell setups = downtrend + overbought band).
- MQL5 Market — "Smart Trend Professional" (EMA stack ordering vs a trend
  EMA + RSI healthy-momentum zone + Stochastic entry timing).
- Charles Schwab — "Identifying Trend Reversals with RSI" and "Technical
  Indicators: 3 Trading Traps to Avoid" (RSI 70/30 conventions, and the
  importance of confirming RSI extremes with a moving average / trend
  context rather than trading them in isolation).
- FOREX.com — "Trend Trading: Strategies, Indicators and Examples" (Bollinger
  Band basis for OB/OS, swing-high/low based uptrend/downtrend/sideways
  definitions).

## 7. Default parameters (all overridable via function args / CLI flags)

| Parameter | Default |
|---|---|
| `ema_fast` | 9 |
| `ema_slow` | 21 |
| `ema_trend` | 50 |
| `rsi_period` | 14 |
| `rsi_overbought` | 70 |
| `rsi_oversold` | 30 |
| `rsi_neutral_low` | 40 |
| `rsi_neutral_high` | 60 |
| `adx_period` | 14 |
| `adx_sideways_threshold` | 20 |
| `atr_period` | 14 |
| `atr_ma_period` | 20 |
| `supertrend_period` | 10 |
| `supertrend_multiplier` | 3.0 |
| `min_hold_bars` | 3 |
