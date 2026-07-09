"""
Smart Trend Indicator — trend_classifier.py

Classifies every bar of an OHLC(V) price series into one of five regime
states:
    (a) Oversold    - dark red   (#8B0000)
    (b) Downtrend   - red        (#FF0000)
    (c) Sideways    - black      (#000000)
    (d) Uptrend     - green      (#008000)
    (e) Overbought  - dark green (#004d00)

See ../references/methodology.md for the full research write-up behind the
scoring/state-machine logic implemented here.

Usage (CLI):
    python trend_classifier.py --input data.csv --output labeled.csv

Usage (library):
    from trend_classifier import classify_trend
    labeled_df = classify_trend(df)   # df needs a datetime index + close
                                       # (open/high/low/volume optional but recommended)
"""

import argparse
import sys
import warnings

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Color / state constants
# ---------------------------------------------------------------------------

STATE_OVERSOLD = "Oversold"
STATE_DOWNTREND = "Downtrend"
STATE_SIDEWAYS = "Sideways"
STATE_UPTREND = "Uptrend"
STATE_OVERBOUGHT = "Overbought"

STATE_COLORS = {
    STATE_OVERSOLD: "#8B0000",     # dark red
    STATE_DOWNTREND: "#FF0000",    # red
    STATE_SIDEWAYS: "#000000",     # black
    STATE_UPTREND: "#008000",      # green
    STATE_OVERBOUGHT: "#004d00",   # dark green
}

DEFAULT_PARAMS = dict(
    ema_fast=9,
    ema_slow=21,
    ema_trend=50,
    rsi_period=14,
    rsi_overbought=70,
    rsi_oversold=30,
    rsi_neutral_low=40,
    rsi_neutral_high=60,
    adx_period=14,
    adx_sideways_threshold=20,
    atr_period=14,
    atr_ma_period=20,
    supertrend_period=10,
    supertrend_multiplier=3.0,
    min_hold_bars=3,
)


# ---------------------------------------------------------------------------
# Indicator building blocks
# ---------------------------------------------------------------------------

def compute_ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _wilder_smooth(series: pd.Series, period: int) -> pd.Series:
    """Wilder's smoothing (used by RSI/ADX/ATR)."""
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = _wilder_smooth(gain, period)
    avg_loss = _wilder_smooth(loss, period)
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50.0)  # no data yet / flat market -> neutral
    return rsi


def compute_true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    tr.iloc[0] = high.iloc[0] - low.iloc[0]
    return tr


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = compute_true_range(high, low, close)
    return _wilder_smooth(tr, period)


def compute_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    plus_dm = pd.Series(plus_dm, index=high.index)
    minus_dm = pd.Series(minus_dm, index=high.index)

    tr = compute_true_range(high, low, close)
    atr = _wilder_smooth(tr, period).replace(0, np.nan)

    plus_di = 100 * _wilder_smooth(plus_dm, period) / atr
    minus_di = 100 * _wilder_smooth(minus_dm, period) / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    adx = _wilder_smooth(dx.fillna(0.0), period)
    return adx.fillna(0.0)


def compute_supertrend(
    high: pd.Series, low: pd.Series, close: pd.Series,
    period: int = 10, multiplier: float = 3.0,
) -> pd.Series:
    """Returns the Supertrend line only (used here purely as a directional vote)."""
    atr = compute_atr(high, low, close, period)
    hl2 = (high + low) / 2.0
    upper_basic = hl2 + multiplier * atr
    lower_basic = hl2 - multiplier * atr

    upper_band = upper_basic.copy()
    lower_band = lower_basic.copy()
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)  # 1 = bullish, -1 = bearish

    for i in range(len(close)):
        if i == 0:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
            continue

        if upper_basic.iloc[i] < upper_band.iloc[i - 1] or close.iloc[i - 1] > upper_band.iloc[i - 1]:
            upper_band.iloc[i] = upper_basic.iloc[i]
        else:
            upper_band.iloc[i] = upper_band.iloc[i - 1]

        if lower_basic.iloc[i] > lower_band.iloc[i - 1] or close.iloc[i - 1] < lower_band.iloc[i - 1]:
            lower_band.iloc[i] = lower_basic.iloc[i]
        else:
            lower_band.iloc[i] = lower_band.iloc[i - 1]

        if supertrend.iloc[i - 1] == upper_band.iloc[i - 1] and close.iloc[i] <= upper_band.iloc[i]:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
        elif supertrend.iloc[i - 1] == upper_band.iloc[i - 1] and close.iloc[i] > upper_band.iloc[i]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        elif supertrend.iloc[i - 1] == lower_band.iloc[i - 1] and close.iloc[i] >= lower_band.iloc[i]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        else:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1

    return supertrend


# ---------------------------------------------------------------------------
# Composite scoring + state machine
# ---------------------------------------------------------------------------

def _trend_score_row(ema_fast, ema_slow, ema_trend, close, supertrend_line):
    bullish_votes = 0
    bearish_votes = 0

    if ema_fast > ema_slow > ema_trend:
        bullish_votes += 1
    elif ema_fast < ema_slow < ema_trend:
        bearish_votes += 1

    if close > supertrend_line:
        bullish_votes += 1
    else:
        bearish_votes += 1

    if bullish_votes >= 2:
        return 1
    if bearish_votes >= 2:
        return -1
    return 0


def _candidate_state_row(trend_score, adx, atr, atr_ma, rsi, p):
    strength_weak = (adx < p["adx_sideways_threshold"]) and (atr < atr_ma)
    neutral_band = p["rsi_neutral_low"] <= rsi <= p["rsi_neutral_high"]

    if strength_weak and neutral_band and trend_score == 0:
        return STATE_SIDEWAYS
    if trend_score >= 1 and rsi >= p["rsi_overbought"]:
        return STATE_OVERBOUGHT
    if trend_score >= 1:
        return STATE_UPTREND
    if trend_score <= -1 and rsi <= p["rsi_oversold"]:
        return STATE_OVERSOLD
    if trend_score <= -1:
        return STATE_DOWNTREND
    return STATE_SIDEWAYS


def _apply_hysteresis(candidates: pd.Series, min_hold_bars: int) -> pd.Series:
    states = []
    prev_state = None
    bars_in_state = 0

    for candidate in candidates:
        if prev_state is None:
            state = candidate
            bars_in_state = 1
        elif candidate == prev_state:
            state = candidate
            bars_in_state += 1
        elif bars_in_state < min_hold_bars:
            state = prev_state
            bars_in_state += 1
        else:
            state = candidate
            bars_in_state = 1

        states.append(state)
        prev_state = state

    return pd.Series(states, index=candidates.index)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_trend(df: pd.DataFrame, **overrides) -> pd.DataFrame:
    """
    Classify every row of `df` into one of the 5 trend states.

    df must contain a `close` column (case-insensitive). If `open/high/low`
    are missing, they are synthesized from `close` (close-only fallback mode
    — see references/methodology.md section 4); a warning is emitted.

    Extra keyword args override any DEFAULT_PARAMS entry, e.g.:
        classify_trend(df, min_hold_bars=5, rsi_overbought=75)

    Returns a copy of df with added columns:
        ema_fast, ema_slow, ema_trend, rsi, adx, atr, atr_ma, supertrend,
        trend_score, state, color
    """
    p = {**DEFAULT_PARAMS, **overrides}

    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    if "close" not in df.columns:
        raise ValueError("Input data must contain a 'close' column.")

    close_only_mode = not all(c in df.columns for c in ("open", "high", "low"))
    if close_only_mode:
        warnings.warn(
            "No open/high/low columns found — falling back to close-only mode. "
            "ADX/ATR/Supertrend accuracy is reduced. See methodology.md section 4."
        )
        df["high"] = df["close"]
        df["low"] = df["close"]
        df["open"] = df["close"]

    close, high, low = df["close"], df["high"], df["low"]

    df["ema_fast"] = compute_ema(close, p["ema_fast"])
    df["ema_slow"] = compute_ema(close, p["ema_slow"])
    df["ema_trend"] = compute_ema(close, p["ema_trend"])
    df["rsi"] = compute_rsi(close, p["rsi_period"])
    df["atr"] = compute_atr(high, low, close, p["atr_period"])
    df["atr_ma"] = df["atr"].rolling(p["atr_ma_period"], min_periods=1).mean()
    df["adx"] = compute_adx(high, low, close, p["adx_period"])
    df["supertrend"] = compute_supertrend(
        high, low, close, p["supertrend_period"], p["supertrend_multiplier"]
    )

    df["trend_score"] = [
        _trend_score_row(ef, es, et, c, st)
        for ef, es, et, c, st in zip(
            df["ema_fast"], df["ema_slow"], df["ema_trend"], close, df["supertrend"]
        )
    ]

    candidates = pd.Series(
        [
            _candidate_state_row(ts, adx, atr, atr_ma, rsi, p)
            for ts, adx, atr, atr_ma, rsi in zip(
                df["trend_score"], df["adx"], df["atr"], df["atr_ma"], df["rsi"]
            )
        ],
        index=df.index,
    )

    df["state"] = _apply_hysteresis(candidates, p["min_hold_bars"]).values
    df["color"] = df["state"].map(STATE_COLORS)

    return df


def summarize(df: pd.DataFrame) -> str:
    """Human-readable summary of the current state and recent transitions."""
    if "state" not in df.columns:
        raise ValueError("Run classify_trend() first.")

    current_state = df["state"].iloc[-1]
    # bars held in the current state (walk backwards)
    bars_held = 1
    for s in df["state"].iloc[-2::-1]:
        if s == current_state:
            bars_held += 1
        else:
            break

    transitions = df["state"].ne(df["state"].shift()).cumsum()
    n_transitions = transitions.iloc[-1]

    last_row = df.iloc[-1]
    lines = [
        f"Current state: {current_state} ({STATE_COLORS[current_state]}) "
        f"— held for {bars_held} bar(s).",
        f"Latest RSI: {last_row['rsi']:.1f} | ADX: {last_row['adx']:.1f} | "
        f"ATR: {last_row['atr']:.4f} (MA: {last_row['atr_ma']:.4f}) | "
        f"trend_score: {last_row['trend_score']}",
        f"Total regime changes over the series: {int(n_transitions) - 1}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _find_datetime_column(df: pd.DataFrame):
    for candidate in ("date", "datetime", "timestamp", "time"):
        for col in df.columns:
            if col.strip().lower() == candidate:
                return col
    return None


def main():
    parser = argparse.ArgumentParser(description="Smart Trend Indicator classifier")
    parser.add_argument("--input", required=True, help="Path to input CSV (needs a close column; open/high/low recommended)")
    parser.add_argument("--output", required=True, help="Path to write the labeled CSV")
    parser.add_argument("--min-hold-bars", type=int, default=DEFAULT_PARAMS["min_hold_bars"])
    parser.add_argument("--rsi-overbought", type=float, default=DEFAULT_PARAMS["rsi_overbought"])
    parser.add_argument("--rsi-oversold", type=float, default=DEFAULT_PARAMS["rsi_oversold"])
    parser.add_argument("--adx-sideways-threshold", type=float, default=DEFAULT_PARAMS["adx_sideways_threshold"])
    args = parser.parse_args()

    raw = pd.read_csv(args.input)
    dt_col = _find_datetime_column(raw)
    if dt_col:
        raw[dt_col] = pd.to_datetime(raw[dt_col])
        raw = raw.set_index(dt_col).sort_index()
    else:
        warnings.warn("No date/datetime/timestamp column found — using row order as the index.")

    labeled = classify_trend(
        raw,
        min_hold_bars=args.min_hold_bars,
        rsi_overbought=args.rsi_overbought,
        rsi_oversold=args.rsi_oversold,
        adx_sideways_threshold=args.adx_sideways_threshold,
    )
    labeled.to_csv(args.output)

    print(f"Wrote {len(labeled)} labeled rows to {args.output}\n")
    print(summarize(labeled))


if __name__ == "__main__":
    sys.exit(main())
