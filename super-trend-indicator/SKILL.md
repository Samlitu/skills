---
name: smart-trend-indicator
description: Classifies every candle/bar of a price series (OHLC or close-only) into one of five market-regime states — Oversold, Downtrend, Sideways, Uptrend, Overbought — using a multi-factor composite score (EMA trend backbone, ADX strength, ATR volatility filter, RSI momentum zones) with a state-machine to prevent whipsaws. Use this skill whenever the user asks to identify trend/regime for a chart, wants a "smart trend indicator," asks to label candles as overbought/oversold/uptrend/downtrend/sideways, wants a color-coded trend chart, or wants to combine RSI/ADX/EMA/ATR/Supertrend indicators into one trend signal. Also trigger for requests like "classify this stock's trend over time," "plot trend regimes on my chart," or "build/update a trend-regime indicator skill." Works with CSV/uploaded OHLCV data or ad-hoc price series.
---

# Smart Trend Indicator

A multi-factor **regime classification** system that labels every timestamp of a
price series into exactly one of five states, and renders a color-coded chart.

| State | Meaning | Color | Hex |
|---|---|---|---|
| (a) Oversold | Strong down-move has stretched too far, reversal risk up | Dark Red | `#8B0000` |
| (b) Downtrend | Price trending down with strength | Red | `#FF0000` |
| (c) Sideways | No clear directional edge / consolidation | Black | `#000000` |
| (d) Uptrend | Price trending up with strength | Green | `#008000` |
| (e) Overbought | Strong up-move has stretched too far, reversal risk down | Dark Green | `#004d00` |

This mirrors how professional "smart trend" tools on TradingView/MT4 work: they
never rely on one indicator alone. They build an **EMA trend backbone**, confirm
strength/volatility with **ADX + ATR**, and use **RSI zones** to detect the
overbought/oversold extremes layered on top of the trend bias. A **state
machine** with minimum hold bars prevents rapid flip-flopping ("whipsaws")
between labels. See `references/methodology.md` for the full research writeup
and citations.

## When to use this skill

Trigger this skill whenever the user wants to:
- Label each bar/candle of a chart with a trend regime (the 5 states above)
- Build, run, or explain a "Smart Trend Indicator"
- Combine RSI/EMA/ADX/ATR/Supertrend into a single trend signal
- Produce a color-coded trend/regime chart (candlestick or line)
- Backtest or eyeball how a stock/crypto/forex pair moved through
  trend regimes over time

## Inputs this skill expects

Ask the user for (or infer from an uploaded file):
1. **Price data**: a CSV with at least `date/time, close` columns; ideally also
   `open, high, low, volume` for a proper candlestick chart and for ADX/ATR
   (which need high/low). If only close is available, the script falls back to
   close-only approximations (see "Close-only mode" in methodology.md).
2. **Timeframe context** (optional): daily/hourly/intraday — used only for
   labeling the chart axis, the math is timeframe-agnostic.
3. **Chart type**: candlestick or line (default: candlestick if OHLC present,
   otherwise line).
4. **Sensitivity** (optional): "more reactive" vs "more stable" — maps to the
   `min_hold_bars` and threshold parameters (see below).

If the user hasn't provided a file, ask them to upload a CSV, or offer to fetch
example data if a connector/web tool is available (e.g. a market-data MCP).

## Workflow

1. **Load data** into a pandas DataFrame with a datetime index and (ideally)
   `open, high, low, close, volume` columns.
2. **Run the classifier**: call `scripts/trend_classifier.py` (as a library or
   CLI) to compute indicators and assign one of the 5 states per row, plus its
   color hex code.
3. **Plot the chart**: call `scripts/plot_trend_chart.py` to render a
   candlestick or line chart with each bar/segment colored by its state, and a
   legend.
4. **Summarize** for the user: current state, how long it has held, the last
   state transition, and a brief plain-English rationale (e.g. "ADX rose above
   25 and price closed above both EMAs and the Supertrend line, so the regime
   flipped from Sideways to Uptrend on <date>").
5. **Offer refinements**: sensitivity tuning, exporting the labeled CSV,
   annotating specific transitions, or combining with a second symbol.

## Quick usage (CLI)

```bash
# Classify a CSV of OHLCV data and print a summary + write a labeled CSV
python scripts/trend_classifier.py --input data.csv --output labeled.csv

# Render the color-coded candlestick chart (PNG) from the labeled CSV
python scripts/plot_trend_chart.py --input labeled.csv --output trend_chart.png --chart-type candlestick
```

Or import directly in Python:

```python
from scripts.trend_classifier import classify_trend
import pandas as pd

df = pd.read_csv("data.csv", parse_dates=["date"], index_col="date")
labeled = classify_trend(df)   # adds columns: state, color, score, adx, atr, rsi, ema_fast, ema_slow, ema_trend
```

## Composite methodology (summary)

The classifier combines four layers (full detail + rationale in
`references/methodology.md`):

1. **Trend backbone (direction)** — EMA(9) vs EMA(21) vs EMA(50), plus a
   Supertrend confirmation. Produces a `trend_score` of -1 (bearish), 0
   (mixed), or +1 (bullish).
2. **Strength/volatility filter** — ADX(14) and an ATR(14) vs its 20-period
   average. Low ADX + contracting ATR ⇒ market lacks the conviction to be
   trending ⇒ candidate for Sideways regardless of what EMAs say.
3. **Momentum zone (RSI)** — RSI(14) placed into bands: `<=30` oversold,
   `30-50` bearish momentum, `50-70` bullish momentum, `>=70` overbought,
   `40-60` neutral band that supports Sideways.
4. **State machine** — combines the three signals above into one of the 5
   states, then enforces a `min_hold_bars` (default 3) so the label doesn't
   flip on every single bar — it must sustain the new regime's conditions for
   several bars before switching (hysteresis), exactly like production
   trend-regime tools do it.

Decision order per bar (first match wins) — see methodology.md for full pseudo-code:

```
if ADX < 20 and 40 <= RSI <= 60 and |trend_score| < 1:
    candidate = SIDEWAYS
elif trend_score >= 1 and RSI >= 70:
    candidate = OVERBOUGHT
elif trend_score >= 1:
    candidate = UPTREND
elif trend_score <= -1 and RSI <= 30:
    candidate = OVERSOLD
elif trend_score <= -1:
    candidate = DOWNTREND
else:
    candidate = SIDEWAYS

state = apply_hysteresis(candidate, previous_state, min_hold_bars)
```

## Files in this skill

```
smart-trend-indicator/
├── SKILL.md                        (this file)
├── scripts/
│   ├── trend_classifier.py         core indicator math + 5-state classification + state machine
│   └── plot_trend_chart.py         color-coded candlestick/line chart renderer (matplotlib)
├── references/
│   └── methodology.md              full research write-up: sources, thresholds, combination logic,
│                                    close-only fallback, tuning guide, worked example
└── assets/
    └── sample_data.csv             small synthetic OHLCV sample for smoke-testing the scripts
```

## Tuning guide (quick reference)

| Want... | Change |
|---|---|
| Fewer, more stable regime flips | increase `min_hold_bars` (e.g. 5-8) |
| More reactive to fast reversals | decrease `min_hold_bars` (e.g. 1-2), tighten RSI bands to 35/65 |
| Wider Sideways zone | raise ADX sideways threshold (e.g. 25) and widen RSI neutral band to 35-65 |
| Stricter Overbought/Oversold | raise/lower RSI extreme thresholds to 75/25 |

Full parameter list and defaults are documented at the top of
`scripts/trend_classifier.py`.
