#!/usr/bin/env python3
"""
detect_zones.py — Mechanically detect and score supply/demand zones from OHLC data.

WHAT IT DOES
    1. Classifies each candle as Rally / Drop / Base relative to local volatility (ATR).
    2. Scans for Leg-in -> Base(1-6 candles) -> Leg-out sequences.
    3. Classifies each found zone as RBR / RBD / DBR / DBD.
    4. Scores each zone 1-7 on Freshness, Strength, Explosiveness (see
       references/scoring_rubric.md in this skill for the exact criteria this implements).
    5. Tracks touches since formation to set Freshness / status (Fresh / Tested / Mitigated).
    6. Prints a results table (and optionally writes CSV/JSON).

EXPECTED INPUT CSV COLUMNS (case-insensitive, order doesn't matter):
    date/datetime/time  (optional but recommended)
    open, high, low, close
    volume  (optional — if absent, Strength scoring drops the volume component)

USAGE
    python detect_zones.py path/to/ohlc.csv
    python detect_zones.py path/to/ohlc.csv --max-base 6 --leg-out-atr 1.5 --out zones.csv
    python detect_zones.py path/to/ohlc.csv --json zones.json

    As a library:
        from detect_zones import detect_zones
        import pandas as pd
        df = pd.read_csv("ohlc.csv")
        zones = detect_zones(df)   # returns a pandas DataFrame, one row per zone

NOTES
    - This is a heuristic, transparent implementation of the rules in
      references/zone_identification.md and references/scoring_rubric.md — it is meant to remove
      hindsight bias and give reproducible numbers, not to be a black-box "signal generator."
      Always sanity-check flagged zones against the chart, especially near the edges of the data.
    - Designed to run on any single timeframe's OHLC data; run it once per timeframe for a
      multi-timeframe analysis and reconcile manually per the skill's Step 1 guidance.
"""

import argparse
import sys
import json
import numpy as np
import pandas as pd


REQUIRED_COLS = ["open", "high", "low", "close"]


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    rename_map = {}
    for c in df.columns:
        if c in ("date", "datetime", "time", "timestamp"):
            rename_map[c] = "date"
    df = df.rename(columns=rename_map)
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required column(s): {missing}. Found columns: {list(df.columns)}")
    if "date" not in df.columns:
        df["date"] = df.index.astype(str)
    if "volume" not in df.columns:
        df["volume"] = np.nan
    return df.reset_index(drop=True)


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([
        (high - low).abs(),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period, min_periods=max(2, period // 2)).mean()
    atr = atr.bfill()
    return atr


def _classify_candles(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    body = (df["close"] - df["open"]).abs()
    rng = (df["high"] - df["low"]).replace(0, np.nan)
    avg_body = body.rolling(15, min_periods=5).mean().bfill()

    direction = np.where(df["close"] > df["open"], "up",
                 np.where(df["close"] < df["open"], "down", "flat"))
    body_ratio = (body / rng).fillna(0)

    is_base = (body < 0.5 * avg_body) | (body_ratio < 0.35)
    kind = np.where(is_base, "base",
             np.where(direction == "up", "rally",
               np.where(direction == "down", "drop", "base")))

    df["direction"] = direction
    df["body"] = body
    df["range"] = rng.fillna(0)
    df["is_base"] = is_base
    df["kind"] = kind
    return df


def detect_zones(df: pd.DataFrame, max_base: int = 6, leg_out_atr_mult: float = 1.5,
                  min_leg_candles: int = 2) -> pd.DataFrame:
    """
    Detect supply/demand zones in an OHLC(V) DataFrame.

    Parameters
    ----------
    df : DataFrame with columns open, high, low, close, (volume, date optional)
    max_base : maximum consecutive base candles allowed to still count as a "base" (default 6)
    leg_out_atr_mult : minimum leg-out move, as a multiple of ATR, to count as a valid departure
    min_leg_candles : minimum consecutive same-direction candles to count as a leg-in

    Returns
    -------
    DataFrame, one row per detected zone, with columns:
        type, pattern, zone_top, zone_bottom, base_start_idx, base_end_idx,
        base_start_date, base_end_date, freshness, strength, explosiveness, overall,
        touches, status
    """
    df = _normalize_columns(df)
    df["atr"] = _atr(df)
    df = _classify_candles(df)

    n = len(df)
    zones = []
    i = 1
    while i < n - min_leg_candles:
        # find a leg-in: min_leg_candles consecutive same-direction non-base candles ending at i-1
        j = i
        leg_kinds = []
        while j < n and df["kind"].iloc[j] in ("rally", "drop"):
            leg_kinds.append(df["kind"].iloc[j])
            j += 1
        if len(leg_kinds) < min_leg_candles:
            i += 1
            continue
        leg_in_dir = leg_kinds[-1]  # direction right before the base
        leg_in_end = j - 1

        # find base: 1..max_base consecutive base candles
        b0 = j
        b1 = b0
        while b1 < n and df["kind"].iloc[b1] == "base" and (b1 - b0) < max_base:
            b1 += 1
        if b1 == b0:
            i = leg_in_end + 1
            continue
        base_start, base_end = b0, b1 - 1

        # find leg-out starting at b1
        if b1 >= n:
            break
        leg_out_dir = df["kind"].iloc[b1]
        if leg_out_dir not in ("rally", "drop"):
            i = base_end + 1
            continue

        atr_at_base = df["atr"].iloc[base_end]
        if atr_at_base == 0 or np.isnan(atr_at_base):
            i = base_end + 1
            continue

        # measure leg-out displacement over next up to 3 candles from base_end
        look = min(b1 + 3, n)
        if leg_out_dir == "rally":
            leg_out_extreme = df["high"].iloc[b1:look].max()
            base_ref = df[["open", "close"]].iloc[base_start:base_end + 1].values.max()
            leg_out_move = leg_out_extreme - base_ref
        else:
            leg_out_extreme = df["low"].iloc[b1:look].min()
            base_ref = df[["open", "close"]].iloc[base_start:base_end + 1].values.min()
            leg_out_move = base_ref - leg_out_extreme

        if leg_out_move < leg_out_atr_mult * atr_at_base:
            i = base_end + 1
            continue  # not explosive enough — skip, don't mark a zone

        # valid zone found — classify pattern
        if leg_in_dir == "rally" and leg_out_dir == "rally":
            pattern, ztype = "RBR", "demand"
        elif leg_in_dir == "rally" and leg_out_dir == "drop":
            pattern, ztype = "RBD", "supply"
        elif leg_in_dir == "drop" and leg_out_dir == "rally":
            pattern, ztype = "DBR", "demand"
        else:
            pattern, ztype = "DBD", "supply"

        base_slice = df.iloc[base_start:base_end + 1]
        if ztype == "demand":
            zone_bottom = base_slice["low"].min()
            zone_top = base_slice[["open", "close"]].values.max()
        else:
            zone_top = base_slice["high"].max()
            zone_bottom = base_slice[["open", "close"]].values.min()

        # --- scoring ---
        base_len = base_end - base_start + 1
        avg_range = df["range"].iloc[max(0, base_start - 15):base_start].mean()
        avg_range = avg_range if avg_range and not np.isnan(avg_range) else df["range"].mean()

        # Strength
        size_mult = leg_out_move / atr_at_base if atr_at_base else 0
        consec = 0
        k = b1
        while k < n and df["kind"].iloc[k] == leg_out_dir:
            consec += 1
            k += 1
        vol_ratio = np.nan
        if df["volume"].notna().any():
            base_vol_avg = df["volume"].iloc[max(0, base_start - 15):base_start].mean()
            leg_vol = df["volume"].iloc[b1:min(b1 + 2, n)].mean()
            if base_vol_avg and not np.isnan(base_vol_avg) and base_vol_avg > 0:
                vol_ratio = leg_vol / base_vol_avg

        strength = 1
        if size_mult >= 3 and consec >= 3 and base_len <= 2:
            strength = 7
        elif size_mult >= 2.5 and consec >= 2 and base_len <= 3:
            strength = 6
        elif size_mult >= 2.0 and base_len <= 3:
            strength = 5
        elif size_mult >= 1.5:
            strength = 4
        elif size_mult >= 1.2 and base_len <= 5:
            strength = 3
        elif base_len <= 6:
            strength = 2
        if not np.isnan(vol_ratio):
            if vol_ratio >= 3:
                strength = min(7, strength + 1)
            elif vol_ratio < 1:
                strength = max(1, strength - 1)

        # Explosiveness — bars to clear 2x ATR, gap check
        gap = False
        if leg_out_dir == "rally":
            gap = df["open"].iloc[b1] > df["high"].iloc[b1 - 1]
        else:
            gap = df["open"].iloc[b1] < df["low"].iloc[b1 - 1]
        target = 2 * atr_at_base
        bars_to_clear = None
        cum = 0
        for k2 in range(b1, min(b1 + 8, n)):
            if leg_out_dir == "rally":
                cum = max(cum, df["high"].iloc[k2] - base_ref)
            else:
                cum = max(cum, base_ref - df["low"].iloc[k2])
            if cum >= target:
                bars_to_clear = k2 - b1 + 1
                break

        if gap or (bars_to_clear is not None and bars_to_clear <= 1):
            explosiveness = 7
        elif bars_to_clear is not None and bars_to_clear <= 2:
            explosiveness = 6
        elif bars_to_clear is not None and bars_to_clear <= 3:
            explosiveness = 5
        elif bars_to_clear is not None and bars_to_clear <= 5:
            explosiveness = 4
        elif bars_to_clear is not None and bars_to_clear <= 8:
            explosiveness = 3
        else:
            explosiveness = 2

        # Freshness — touches since formation (closes back into the zone after formation)
        touches = 0
        mitigated = False
        after = df.iloc[look:]
        for _, row in after.iterrows():
            lo, hi, close_ = row["low"], row["high"], row["close"]
            entered = not (hi < zone_bottom or lo > zone_top)
            if entered:
                touches += 1
                closed_through = (ztype == "demand" and close_ < zone_bottom) or \
                                  (ztype == "supply" and close_ > zone_top)
                if closed_through:
                    mitigated = True
                    break
        recency = (n - 1 - base_end) / max(1, n)  # 0 = just formed, ~1 = formed at start of data
        if mitigated:
            freshness = 1
            status = "Mitigated"
        elif touches == 0:
            freshness = 7 if recency < 0.3 else (6 if recency < 0.6 else 5)
            status = "Fresh"
        elif touches == 1:
            freshness = 4
            status = "Tested (1x)"
        else:
            freshness = 2
            status = f"Tested ({touches}x)"

        overall = round((freshness + strength + explosiveness) / 3 * 2) / 2

        zones.append({
            "type": ztype,
            "pattern": pattern,
            "zone_top": round(float(zone_top), 4),
            "zone_bottom": round(float(zone_bottom), 4),
            "base_start_date": df["date"].iloc[base_start],
            "base_end_date": df["date"].iloc[base_end],
            "base_candles": base_len,
            "freshness": freshness,
            "strength": strength,
            "explosiveness": explosiveness,
            "overall": overall,
            "touches": touches,
            "status": status,
        })

        i = b1 + 1  # continue scanning after this zone's leg-out

    return pd.DataFrame(zones)


def main():
    ap = argparse.ArgumentParser(description="Detect and score supply/demand zones from OHLC CSV data.")
    ap.add_argument("csv_path", help="Path to OHLC(V) CSV file")
    ap.add_argument("--max-base", type=int, default=6, help="Max consecutive base candles (default 6)")
    ap.add_argument("--leg-out-atr", type=float, default=1.5,
                     help="Min leg-out move as multiple of ATR to count as valid (default 1.5)")
    ap.add_argument("--out", help="Optional path to write results as CSV")
    ap.add_argument("--json", dest="json_out", help="Optional path to write results as JSON")
    args = ap.parse_args()

    try:
        df = pd.read_csv(args.csv_path)
    except Exception as e:
        print(f"Failed to read CSV: {e}", file=sys.stderr)
        sys.exit(1)

    zones = detect_zones(df, max_base=args.max_base, leg_out_atr_mult=args.leg_out_atr)

    if zones.empty:
        print("No valid supply/demand zones detected with current thresholds. "
              "Try lowering --leg-out-atr or check the input data.")
        return

    zones = zones.sort_values("base_end_date")
    with pd.option_context("display.max_rows", None, "display.width", 160):
        print(zones.to_string(index=False))

    if args.out:
        zones.to_csv(args.out, index=False)
        print(f"\nSaved CSV -> {args.out}")
    if args.json_out:
        zones.to_json(args.json_out, orient="records", indent=2)
        print(f"Saved JSON -> {args.json_out}")


if __name__ == "__main__":
    main()