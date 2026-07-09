"""
Smart Trend Indicator — plot_trend_chart.py

Renders a color-coded candlestick or line chart from a CSV already labeled by
trend_classifier.py (must contain: close, state, color; open/high/low needed
for candlestick mode).

Color code:
    Oversold    -> dark red   (#8B0000)
    Downtrend   -> red        (#FF0000)
    Sideways    -> black      (#000000)
    Uptrend     -> green      (#008000)
    Overbought  -> dark green (#004d00)

Usage:
    python plot_trend_chart.py --input labeled.csv --output trend_chart.png --chart-type candlestick
    python plot_trend_chart.py --input labeled.csv --output trend_chart.png --chart-type line
"""

import argparse
import sys

import matplotlib
matplotlib.use("Agg")  # headless-safe backend
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D
import pandas as pd

STATE_ORDER = ["Overbought", "Uptrend", "Sideways", "Downtrend", "Oversold"]
STATE_COLORS = {
    "Oversold": "#8B0000",
    "Downtrend": "#FF0000",
    "Sideways": "#000000",
    "Uptrend": "#008000",
    "Overbought": "#004d00",
}


def _load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.columns = [str(c).strip().lower() for c in df.columns]
    required = {"close", "state"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input file is missing required column(s): {missing}")
    return df


def plot_candlestick(df: pd.DataFrame, ax, width=0.6):
    x = range(len(df))
    for i, (_, row) in zip(x, df.iterrows()):
        color = STATE_COLORS.get(row["state"], "#888888")
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]
        ax.plot([i, i], [l, h], color=color, linewidth=1)
        lower = min(o, c)
        height = max(abs(c - o), 1e-9)
        ax.add_patch(
            Rectangle((i - width / 2, lower), width, height,
                      facecolor=color, edgecolor=color)
        )
    ax.set_xlim(-1, len(df))


def plot_line(df: pd.DataFrame, ax):
    """Draw the close-price line as colored segments matching each bar's state."""
    x = list(range(len(df)))
    closes = df["close"].values
    states = df["state"].values
    for i in range(len(df) - 1):
        color = STATE_COLORS.get(states[i], "#888888")
        ax.plot(x[i:i + 2], closes[i:i + 2], color=color, linewidth=2)
    ax.set_xlim(-1, len(df))


def _legend_handles():
    return [
        Line2D([0], [0], color=STATE_COLORS[s], lw=4, label=s)
        for s in STATE_ORDER
    ]


def render(df: pd.DataFrame, chart_type: str, output_path: str, title: str = "Smart Trend Indicator"):
    fig, ax = plt.subplots(figsize=(14, 7))

    if chart_type == "candlestick":
        if not all(c in df.columns for c in ("open", "high", "low")):
            raise ValueError("Candlestick chart requires open/high/low columns; use --chart-type line instead.")
        plot_candlestick(df, ax)
    elif chart_type == "line":
        plot_line(df, ax)
    else:
        raise ValueError("chart_type must be 'candlestick' or 'line'")

    n = len(df)
    step = max(1, n // 12)
    tick_positions = list(range(0, n, step))
    tick_labels = [df.index[i].strftime("%Y-%m-%d") if hasattr(df.index[i], "strftime") else str(df.index[i])
                   for i in tick_positions]
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=45, ha="right")

    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("Price")
    ax.legend(handles=_legend_handles(), loc="upper left", title="Trend State", framealpha=0.9)
    ax.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Render a color-coded Smart Trend Indicator chart")
    parser.add_argument("--input", required=True, help="Labeled CSV from trend_classifier.py")
    parser.add_argument("--output", required=True, help="Output image path (e.g. trend_chart.png)")
    parser.add_argument("--chart-type", choices=["candlestick", "line"], default=None,
                         help="Defaults to candlestick if OHLC present, else line")
    parser.add_argument("--title", default="Smart Trend Indicator")
    args = parser.parse_args()

    df = _load(args.input)

    chart_type = args.chart_type
    if chart_type is None:
        chart_type = "candlestick" if all(c in df.columns for c in ("open", "high", "low")) else "line"

    render(df, chart_type, args.output, args.title)
    print(f"Saved {chart_type} chart to {args.output}")


if __name__ == "__main__":
    sys.exit(main())
