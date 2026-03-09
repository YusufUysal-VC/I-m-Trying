"""
chart_builder.py — Plotly chart generation for market analysis reports.
Returns HTML div strings for embedding in single-file HTML reports.
Each chart: candlestick + EMA overlays + Bollinger Bands + S/R lines + MACD + RSI subpanels.
"""

import logging
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Dark theme colors
THEME = {
    "bg": "#1a1a2e",
    "paper": "#16213e",
    "grid": "#2a2a4a",
    "text": "#e0e0e0",
    "ema20": "#4fc3f7",
    "ema50": "#ffb74d",
    "ema200": "#ef5350",
    "bb_fill": "rgba(100,181,246,0.15)",
    "bb_line": "rgba(100,181,246,0.5)",
    "support": "#00b894",
    "resistance": "#d63031",
    "macd_line": "#4fc3f7",
    "macd_signal": "#ffb74d",
    "macd_hist_pos": "#00b894",
    "macd_hist_neg": "#d63031",
    "rsi_line": "#ce93d8",
    "rsi_ob": "rgba(213,0,0,0.15)",
    "rsi_os": "rgba(0,184,148,0.15)",
}


def build_chart(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    support_levels: list,
    resistance_levels: list,
) -> str:
    """
    Build an interactive Plotly chart and return it as an HTML div string.

    Args:
        df: OHLCV DataFrame with computed indicator columns (EMA_20, EMA_50, etc.)
        symbol: Ticker symbol for labeling
        timeframe: Timeframe label (e.g., "Günlük")
        support_levels: List of {"price": float, "strength": str} dicts
        resistance_levels: List of {"price": float, "strength": str} dicts

    Returns:
        HTML div string (Plotly chart, no full HTML)
    """
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError:
        logger.error("plotly not installed")
        return "<div>Grafik yüklenemedi (plotly kurulu değil)</div>"

    if df is None or len(df) < 5:
        return "<div class='chart-unavailable'>Grafik için yeterli veri yok.</div>"

    # Prepare data
    dates = df.index
    has_macd = "MACD" in df.columns and "MACD_signal" in df.columns
    has_rsi = "RSI" in df.columns

    # Row heights
    row_count = 1 + (1 if has_macd else 0) + (1 if has_rsi else 0)
    if row_count == 3:
        row_heights = [0.6, 0.2, 0.2]
    elif row_count == 2:
        row_heights = [0.7, 0.3]
    else:
        row_heights = [1.0]

    subplot_titles = [f"{symbol} — {timeframe}"]
    if has_macd:
        subplot_titles.append("MACD")
    if has_rsi:
        subplot_titles.append("RSI (14)")

    fig = make_subplots(
        rows=row_count,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # === ROW 1: Candlestick + EMAs + Bollinger Bands ===
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="OHLC",
            increasing_line_color="#00b894",
            decreasing_line_color="#d63031",
            increasing_fillcolor="#00b894",
            decreasing_fillcolor="#d63031",
            showlegend=False,
        ),
        row=1, col=1,
    )

    # Bollinger Bands (shaded area)
    if "BB_upper" in df.columns and "BB_lower" in df.columns:
        # Upper band
        fig.add_trace(
            go.Scatter(
                x=dates, y=df["BB_upper"],
                mode="lines",
                line=dict(color=THEME["bb_line"], width=1, dash="dot"),
                name="BB Üst",
                showlegend=False,
            ),
            row=1, col=1,
        )
        # Lower band (fill to upper)
        fig.add_trace(
            go.Scatter(
                x=dates, y=df["BB_lower"],
                mode="lines",
                line=dict(color=THEME["bb_line"], width=1, dash="dot"),
                fill="tonexty",
                fillcolor=THEME["bb_fill"],
                name="BB Alt",
                showlegend=False,
            ),
            row=1, col=1,
        )
        # Middle band
        if "BB_middle" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df["BB_middle"],
                    mode="lines",
                    line=dict(color="rgba(100,181,246,0.4)", width=1),
                    name="BB Orta",
                    showlegend=False,
                ),
                row=1, col=1,
            )

    # EMAs
    ema_configs = [
        ("EMA_20", THEME["ema20"], "EMA 20", 1.5),
        ("EMA_50", THEME["ema50"], "EMA 50", 1.5),
        ("EMA_200", THEME["ema200"], "EMA 200", 2.0),
    ]
    for col_name, color, label, width in ema_configs:
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df[col_name],
                    mode="lines",
                    line=dict(color=color, width=width),
                    name=label,
                    showlegend=True,
                ),
                row=1, col=1,
            )

    # Support levels (dashed green)
    for s in support_levels[:3]:
        sp = s["price"]
        fig.add_hline(
            y=sp,
            line=dict(color=THEME["support"], width=1, dash="dash"),
            annotation_text=f"Destek {_fmt_price(sp)} ({s.get('strength', '')})",
            annotation_position="left",
            annotation_font_color=THEME["support"],
            annotation_font_size=10,
            row=1, col=1,
        )

    # Resistance levels (dashed red)
    for r in resistance_levels[:3]:
        rp = r["price"]
        fig.add_hline(
            y=rp,
            line=dict(color=THEME["resistance"], width=1, dash="dash"),
            annotation_text=f"Direnç {_fmt_price(rp)} ({r.get('strength', '')})",
            annotation_position="right",
            annotation_font_color=THEME["resistance"],
            annotation_font_size=10,
            row=1, col=1,
        )

    # === MACD Panel ===
    current_row = 2
    if has_macd:
        if "MACD_hist" in df.columns:
            hist_colors = [
                THEME["macd_hist_pos"] if v >= 0 else THEME["macd_hist_neg"]
                for v in df["MACD_hist"].fillna(0)
            ]
            fig.add_trace(
                go.Bar(
                    x=dates,
                    y=df["MACD_hist"],
                    marker_color=hist_colors,
                    name="MACD Histogram",
                    showlegend=False,
                ),
                row=current_row, col=1,
            )
        fig.add_trace(
            go.Scatter(
                x=dates, y=df["MACD"],
                mode="lines",
                line=dict(color=THEME["macd_line"], width=1.5),
                name="MACD",
                showlegend=False,
            ),
            row=current_row, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=dates, y=df["MACD_signal"],
                mode="lines",
                line=dict(color=THEME["macd_signal"], width=1.5),
                name="Signal",
                showlegend=False,
            ),
            row=current_row, col=1,
        )
        # Zero line
        fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.3)", width=1), row=current_row, col=1)
        current_row += 1

    # === RSI Panel ===
    if has_rsi:
        # RSI colored zones
        fig.add_hrect(
            y0=70, y1=100,
            fillcolor=THEME["rsi_ob"],
            line_width=0,
            row=current_row, col=1,
        )
        fig.add_hrect(
            y0=0, y1=30,
            fillcolor=THEME["rsi_os"],
            line_width=0,
            row=current_row, col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=dates, y=df["RSI"],
                mode="lines",
                line=dict(color=THEME["rsi_line"], width=1.5),
                name="RSI",
                showlegend=False,
            ),
            row=current_row, col=1,
        )
        # Reference lines
        for level in [30, 50, 70]:
            fig.add_hline(
                y=level,
                line=dict(color="rgba(255,255,255,0.25)", width=1, dash="dot"),
                row=current_row, col=1,
            )

    # === Layout ===
    fig.update_layout(
        height=700,
        paper_bgcolor=THEME["paper"],
        plot_bgcolor=THEME["bg"],
        font=dict(color=THEME["text"], size=11),
        margin=dict(l=60, r=80, t=40, b=20),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
    )

    # Apply dark theme to all axes
    axis_style = dict(
        gridcolor=THEME["grid"],
        zerolinecolor=THEME["grid"],
        linecolor=THEME["grid"],
        tickfont=dict(color=THEME["text"]),
    )
    for i in range(1, row_count + 1):
        fig.update_xaxes(row=i, col=1, **axis_style)
        fig.update_yaxes(row=i, col=1, **axis_style)

    # Range selector buttons on main chart
    fig.update_xaxes(
        row=1, col=1,
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1A", step="month", stepmode="backward"),
                dict(count=3, label="3A", step="month", stepmode="backward"),
                dict(count=6, label="6A", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all", label="Tümü"),
            ],
            bgcolor=THEME["paper"],
            activecolor="#4a4a7a",
            font=dict(color=THEME["text"]),
            x=0,
            y=1.02,
        ),
        type="date",
    )

    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"displayModeBar": True, "responsive": True},
    )


def _fmt_price(price: float) -> str:
    if price >= 1000:
        return f"{price:,.0f}"
    elif price >= 10:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.3f}"
    else:
        return f"{price:.4f}"
