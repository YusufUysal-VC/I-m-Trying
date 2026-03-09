"""
Plotly chart generation for interactive candlestick charts with technical indicators.
Returns HTML div strings for embedding in the report.
"""

import logging

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .indicators import IndicatorResult

logger = logging.getLogger(__name__)

DARK_BG = "#1a1a2e"
DARK_GRID = "#2a2a4a"
DARK_TEXT = "#e0e0e0"


def build_chart(df: pd.DataFrame, symbol: str, timeframe: str,
                indicators: IndicatorResult) -> str:
    """
    Build a complete interactive chart with:
    - Candlestick (OHLC)
    - EMA 20/50/200
    - Bollinger Bands
    - Support/Resistance lines
    - MACD subpanel
    - RSI subpanel

    Returns HTML div string.
    """
    if df is None or df.empty:
        return f'<div class="chart-error">Grafik verisi bulunamadı: {symbol} [{timeframe}]</div>'

    try:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=("", "MACD", "RSI"),
        )

        dates = df.index

        # 1. Candlestick
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
            ),
            row=1, col=1,
        )

        # 2. EMAs
        if indicators.ema20_series is not None:
            fig.add_trace(
                go.Scatter(x=dates, y=indicators.ema20_series, name="EMA 20",
                           line=dict(color="#74b9ff", width=1)),
                row=1, col=1,
            )
        if indicators.ema50_series is not None:
            fig.add_trace(
                go.Scatter(x=dates, y=indicators.ema50_series, name="EMA 50",
                           line=dict(color="#fdcb6e", width=1)),
                row=1, col=1,
            )
        if indicators.ema200_series is not None:
            fig.add_trace(
                go.Scatter(x=dates, y=indicators.ema200_series, name="EMA 200",
                           line=dict(color="#d63031", width=1.5)),
                row=1, col=1,
            )

        # 3. Bollinger Bands
        if indicators.bb_series is not None:
            bb = indicators.bb_series.dropna()
            if not bb.empty:
                bb_cols = bb.columns.tolist()
                # BBL, BBM, BBU are first 3 columns
                fig.add_trace(
                    go.Scatter(x=bb.index, y=bb.iloc[:, 2], name="BB Üst",
                               line=dict(color="rgba(116, 185, 255, 0.3)", width=1)),
                    row=1, col=1,
                )
                fig.add_trace(
                    go.Scatter(x=bb.index, y=bb.iloc[:, 0], name="BB Alt",
                               line=dict(color="rgba(116, 185, 255, 0.3)", width=1),
                               fill="tonexty", fillcolor="rgba(116, 185, 255, 0.08)"),
                    row=1, col=1,
                )

        # 4. Support lines
        for level in indicators.support_levels:
            fig.add_hline(
                y=level.price, row=1, col=1,
                line=dict(color="#00b894", width=1, dash="dash"),
                annotation_text=f"S: {level.price:.4g}",
                annotation_position="left",
                annotation_font_color="#00b894",
                annotation_font_size=10,
            )

        # 5. Resistance lines
        for level in indicators.resistance_levels:
            fig.add_hline(
                y=level.price, row=1, col=1,
                line=dict(color="#d63031", width=1, dash="dash"),
                annotation_text=f"R: {level.price:.4g}",
                annotation_position="left",
                annotation_font_color="#d63031",
                annotation_font_size=10,
            )

        # 6. MACD subpanel
        if indicators.macd_series is not None:
            macd = indicators.macd_series.dropna()
            if not macd.empty:
                macd_cols = macd.columns.tolist()
                # MACD line
                fig.add_trace(
                    go.Scatter(x=macd.index, y=macd.iloc[:, 0], name="MACD",
                               line=dict(color="#74b9ff", width=1)),
                    row=2, col=1,
                )
                # Signal line
                fig.add_trace(
                    go.Scatter(x=macd.index, y=macd.iloc[:, 1], name="Signal",
                               line=dict(color="#fdcb6e", width=1)),
                    row=2, col=1,
                )
                # Histogram
                hist_colors = ["#00b894" if v >= 0 else "#d63031" for v in macd.iloc[:, 2]]
                fig.add_trace(
                    go.Bar(x=macd.index, y=macd.iloc[:, 2], name="Histogram",
                           marker_color=hist_colors, opacity=0.6),
                    row=2, col=1,
                )

        # 7. RSI subpanel
        if indicators.rsi_series is not None:
            rsi = indicators.rsi_series.dropna()
            if not rsi.empty:
                fig.add_trace(
                    go.Scatter(x=rsi.index, y=rsi, name="RSI",
                               line=dict(color="#a29bfe", width=1.5)),
                    row=3, col=1,
                )
                # 30/70 reference lines
                fig.add_hline(y=70, row=3, col=1,
                              line=dict(color="#d63031", width=0.5, dash="dot"))
                fig.add_hline(y=30, row=3, col=1,
                              line=dict(color="#00b894", width=0.5, dash="dot"))
                fig.add_hline(y=50, row=3, col=1,
                              line=dict(color="#636e72", width=0.5, dash="dot"))

                # Colored zones
                fig.add_hrect(y0=70, y1=100, row=3, col=1,
                              fillcolor="rgba(214, 48, 49, 0.1)", line_width=0)
                fig.add_hrect(y0=0, y1=30, row=3, col=1,
                              fillcolor="rgba(0, 184, 148, 0.1)", line_width=0)

        # Layout
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor=DARK_BG,
            plot_bgcolor=DARK_BG,
            font=dict(color=DARK_TEXT, family="system-ui, -apple-system, sans-serif"),
            height=700,
            margin=dict(l=60, r=20, t=30, b=30),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(size=10),
            ),
            xaxis_rangeslider_visible=False,
            hovermode="x unified",
        )

        # Range selector on main chart
        fig.update_xaxes(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1A", step="month", stepmode="backward"),
                    dict(count=3, label="3A", step="month", stepmode="backward"),
                    dict(count=6, label="6A", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(label="Tümü", step="all"),
                ]),
                bgcolor=DARK_BG,
                activecolor="#2a2a4a",
                font=dict(color=DARK_TEXT),
            ),
            row=1, col=1,
        )

        # Grid styling
        for row in range(1, 4):
            fig.update_xaxes(gridcolor=DARK_GRID, row=row, col=1)
            fig.update_yaxes(gridcolor=DARK_GRID, row=row, col=1)

        # RSI y-axis range
        fig.update_yaxes(range=[0, 100], row=3, col=1)

        return fig.to_html(full_html=False, include_plotlyjs=False)

    except Exception as e:
        logger.error(f"Chart build failed for {symbol} [{timeframe}]: {e}")
        return f'<div class="chart-error">Grafik oluşturulamadı: {symbol} [{timeframe}] — {e}</div>'
