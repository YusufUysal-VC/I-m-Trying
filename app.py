import json
import os
import math
import threading
import webbrowser
from pathlib import Path
from datetime import datetime

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analyzer.data_fetcher import fetch_data, safe_fetch, save_to_cache, load_from_cache, TIMEFRAMES
from analyzer.indicators import calculate_all
from analyzer.support_resistance import find_levels
from analyzer.trend_score import calculate_trend_score
from analyzer.signal_engine import generate_signal
from analyzer.narrative import detect_narrative, create_action_plan

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).parent
WATCHLIST_FILE = BASE_DIR / 'watchlist.json'
CACHE_DIR = BASE_DIR / 'cache'
CACHE_DIR.mkdir(exist_ok=True)
PORTFOLIO_FILE = BASE_DIR / 'portfolio.json'

last_update_time = None


def load_watchlist():
    with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_portfolio():
    if PORTFOLIO_FILE.exists():
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_portfolio(data):
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _safe_val(series, idx=-1, default=0):
    try:
        val = series.iloc[idx]
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        return float(val)
    except (IndexError, KeyError, TypeError):
        return default


def extract_indicators(df):
    """Extract latest indicator values from DataFrame."""
    if df is None or df.empty:
        return {}

    price = _safe_val(df['Close'])
    return {
        'price': price,
        'open': _safe_val(df['Open']),
        'high': _safe_val(df['High']),
        'low': _safe_val(df['Low']),
        'volume': _safe_val(df['Volume']),
        'rsi': _safe_val(df.get('rsi', None)) if 'rsi' in df.columns else 50,
        'macd': _safe_val(df.get('macd', None)) if 'macd' in df.columns else 0,
        'macd_signal': _safe_val(df.get('macd_signal', None)) if 'macd_signal' in df.columns else 0,
        'macd_hist': _safe_val(df.get('macd_hist', None)) if 'macd_hist' in df.columns else 0,
        'prev_macd_hist': _safe_val(df['macd_hist'], -2) if 'macd_hist' in df.columns and len(df) > 1 else 0,
        'bb_upper': _safe_val(df.get('bb_upper', None)) if 'bb_upper' in df.columns else price * 1.02,
        'bb_mid': _safe_val(df.get('bb_mid', None)) if 'bb_mid' in df.columns else price,
        'bb_lower': _safe_val(df.get('bb_lower', None)) if 'bb_lower' in df.columns else price * 0.98,
        'ema20': _safe_val(df.get('ema20', None)) if 'ema20' in df.columns else price,
        'ema50': _safe_val(df.get('ema50', None)) if 'ema50' in df.columns else price,
        'ema200': _safe_val(df.get('ema200', None)) if 'ema200' in df.columns else price,
        'sma20': _safe_val(df.get('sma20', None)) if 'sma20' in df.columns else price,
        'vol_ema20': _safe_val(df.get('vol_ema20', None)) if 'vol_ema20' in df.columns else 0,
        'prev_ema20': _safe_val(df['ema20'], -2) if 'ema20' in df.columns and len(df) > 1 else 0,
        'prev_ema50': _safe_val(df['ema50'], -2) if 'ema50' in df.columns and len(df) > 1 else 0,
    }


def analyze_symbol(symbol, tf='3A'):
    """Full analysis for a single symbol."""
    try:
        tf_config = TIMEFRAMES.get(tf, TIMEFRAMES['3A'])
        df = safe_fetch(symbol, tf_config['period'], tf_config['interval'])

        if df is None or (hasattr(df, 'empty') and df.empty) or len(df) < 5:
            cached = load_from_cache(symbol)
            if cached:
                return cached
            return {'error': f'Yetersiz veri: {symbol}', 'symbol': symbol}

        df = calculate_all(df)
        indicators = extract_indicators(df)

        levels = find_levels(df)
        support_levels = levels['support']
        resistance_levels = levels['resistance']

        indicators['resistance_1'] = resistance_levels[0] if resistance_levels else indicators['price'] * 1.05
        indicators['volume_ratio'] = (
            indicators['volume'] / indicators['vol_ema20']
            if indicators['vol_ema20'] > 0 else 1
        )

        trend_score = calculate_trend_score(df, indicators)
        signal = generate_signal(
            trend_score,
            indicators['rsi'],
            indicators['price'],
            indicators['bb_upper'],
            indicators['bb_lower'],
            indicators['ema50']
        )

        narrative = detect_narrative(indicators)
        action_plan = create_action_plan(
            signal, support_levels, resistance_levels,
            indicators['price'], narrative
        )

        # Price change calculation
        if len(df) > 1:
            prev_close = _safe_val(df['Close'], -2)
            if prev_close > 0:
                change = indicators['price'] - prev_close
                change_pct = (change / prev_close) * 100
            else:
                change = 0
                change_pct = 0
        else:
            change = 0
            change_pct = 0

        result = {
            'symbol': symbol,
            'price': round(indicators['price'], 2),
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'indicators': {
                'rsi': round(indicators['rsi'], 2),
                'macd': round(indicators['macd'], 4),
                'macd_signal': round(indicators['macd_signal'], 4),
                'macd_hist': round(indicators['macd_hist'], 4),
                'ema20': round(indicators['ema20'], 2),
                'ema50': round(indicators['ema50'], 2),
                'ema200': round(indicators['ema200'], 2),
                'bb_upper': round(indicators['bb_upper'], 2),
                'bb_mid': round(indicators['bb_mid'], 2),
                'bb_lower': round(indicators['bb_lower'], 2),
            },
            'support': [round(s, 2) for s in support_levels],
            'resistance': [round(r, 2) for r in resistance_levels],
            'trend_score': trend_score,
            'signal': signal,
            'narrative': narrative,
            'action_plan': action_plan.to_dict(),
            'updated_at': datetime.now().strftime('%H:%M:%S')
        }

        save_to_cache(symbol, result)
        return result

    except Exception as e:
        cached = load_from_cache(symbol)
        if cached:
            return cached
        return {'error': str(e), 'symbol': symbol}


def _clean_series(df, col):
    """Return x (integer indices), y lists with NaN values removed."""
    if col not in df.columns:
        return [], []
    mask = df[col].notna()
    # Return integer positions (not datetime index) for gap-free x-axis
    positions = [i for i, m in enumerate(mask) if m]
    values = df[col][mask].tolist()
    return positions, values


def create_chart_json(symbol, tf='3A', show_rsi=False, show_macd=False,
                      show_sr=True, show_trend=False, show_volume=True, theme='dark'):
    """Create Plotly chart JSON for a symbol and timeframe."""
    try:
        tf_config = TIMEFRAMES.get(tf, TIMEFRAMES['3A'])
        df = safe_fetch(symbol, tf_config['period'], tf_config['interval'])

        if df is None or (hasattr(df, 'empty') and df.empty):
            return None

        # Ensure we have enough data
        if len(df) < 5:
            return None

        df = calculate_all(df)
        levels = find_levels(df)

        # Remove timezone info
        try:
            df.index = df.index.tz_localize(None)
        except TypeError:
            pass  # Already tz-naive

        # Drop rows where OHLC has NaN
        ohlc_mask = df['Open'].notna() & df['Close'].notna() & df['High'].notna() & df['Low'].notna()
        df = df[ohlc_mask]

        if len(df) < 10:
            return json.dumps({'data': [], 'layout': {}, 'error': 'Yetersiz veri'})

        # Use sequential integer index to eliminate weekend/holiday gaps
        x_dates = list(range(len(df)))
        # Format labels: include time for intraday timeframes
        intraday = tf in ('1G', '1H', '1A')
        if intraday:
            date_labels = [d.strftime('%H:%M') if hasattr(d, 'strftime') else str(d) for d in df.index.tolist()]
        else:
            date_labels = [d.strftime('%d %b') if hasattr(d, 'strftime') else str(d) for d in df.index.tolist()]

        # Theme colors
        is_light = theme == 'light'
        paper_bg = '#ffffff' if is_light else '#0a0e17'
        plot_bg = '#f8f9fa' if is_light else '#0d1117'
        font_color = '#1a1a2e' if is_light else '#c9d1d9'
        grid_color = 'rgba(0,0,0,0.06)' if is_light else 'rgba(255,255,255,0.05)'

        # Dynamic subplot layout using weights
        panels = ['price']
        panel_weights = {'price': 5}
        subplot_titles = ['']

        if show_volume and 'Volume' in df.columns:
            panels.append('volume')
            panel_weights['volume'] = 1
            subplot_titles.append('')
        if show_rsi:
            panels.append('rsi')
            panel_weights['rsi'] = 1.5
            subplot_titles.append('RSI')
        if show_macd:
            panels.append('macd')
            panel_weights['macd'] = 1.5
            subplot_titles.append('MACD')

        num_rows = len(panels)
        total_weight = sum(panel_weights[p] for p in panels)
        row_heights = [panel_weights[p] / total_weight for p in panels]

        fig = make_subplots(
            rows=num_rows, cols=1,
            shared_xaxes=True,
            row_heights=row_heights,
            vertical_spacing=0.03,
            subplot_titles=subplot_titles
        )

        # ── Panel 1: Candlestick ──
        fig.add_trace(go.Candlestick(
            x=x_dates,
            open=df['Open'].tolist(),
            high=df['High'].tolist(),
            low=df['Low'].tolist(),
            close=df['Close'].tolist(),
            increasing=dict(line=dict(color='#00ff88'), fillcolor='#00ff88'),
            decreasing=dict(line=dict(color='#ff4444'), fillcolor='#ff4444'),
            name='Fiyat'
        ), row=1, col=1)

        # EMAs — only plot with cleaned (no NaN) data
        for col, color, width, label in [
            ('ema20', '#00aaff', 1, 'EMA20'),
            ('ema50', '#ffaa00', 1.5, 'EMA50'),
            ('ema200', '#ff4444', 2, 'EMA200'),
        ]:
            cx, cy = _clean_series(df, col)
            if len(cx) > 10:
                fig.add_trace(go.Scatter(x=cx, y=cy,
                    line=dict(color=color, width=width), name=label), row=1, col=1)

        # Bollinger Bands
        bx_u, by_u = _clean_series(df, 'bb_upper')
        bx_l, by_l = _clean_series(df, 'bb_lower')
        if len(bx_u) > 10:
            fig.add_trace(go.Scatter(x=bx_u, y=by_u,
                line=dict(color='rgba(150,150,150,0.5)', width=1),
                name='BB Üst', fill=None), row=1, col=1)
            fig.add_trace(go.Scatter(x=bx_l, y=by_l,
                line=dict(color='rgba(150,150,150,0.5)', width=1),
                name='BB Alt', fill='tonexty',
                fillcolor='rgba(150,150,150,0.1)'), row=1, col=1)

        # ── Panel: Volume (if enabled) ──
        vol_row = panels.index('volume') + 1 if 'volume' in panels else None
        if vol_row and 'Volume' in df.columns:
            vol_data = df['Volume'].tolist()
            vol_colors = ['#00ff8866' if c >= o else '#ff444466'
                          for c, o in zip(df['Close'], df['Open'])]
            fig.add_trace(go.Bar(
                x=x_dates, y=vol_data,
                marker_color=vol_colors, name='Hacim',
                showlegend=False
            ), row=vol_row, col=1)
            fig.update_yaxes(showticklabels=False, row=vol_row, col=1)

        # Support/Resistance lines (toggleable)
        if show_sr:
            for s in levels['support'][:3]:
                fig.add_hline(y=s, line_dash='dash', line_color='rgba(0,255,136,0.5)',
                              line_width=1, row=1, col=1)
            for r in levels['resistance'][:3]:
                fig.add_hline(y=r, line_dash='dash', line_color='rgba(255,68,68,0.5)',
                              line_width=1, row=1, col=1)

        # Trend line (toggleable) — connect first and last significant lows/highs
        if show_trend and len(df) >= 10:
            import numpy as np
            closes = df['Close'].values
            n = len(closes)
            x_idx = np.arange(n)
            # Linear regression on close prices for trend direction
            slope, intercept = np.polyfit(x_idx, closes, 1)
            trend_y = [intercept + slope * i for i in range(n)]
            fig.add_trace(go.Scatter(
                x=list(range(n)), y=trend_y,
                line=dict(color='rgba(234,179,8,0.6)', width=2, dash='dot'),
                name='Trend', showlegend=True
            ), row=1, col=1)

        # Y-axis: readable tick intervals (~8 ticks)
        price_min = df['Low'].min()
        price_max = df['High'].max()
        price_range = price_max - price_min
        if price_range > 0:
            raw_tick = price_range / 8
            magnitude = 10 ** math.floor(math.log10(raw_tick))
            nice_ticks = [1, 2, 2.5, 5, 10]
            dtick = magnitude * min(nice_ticks, key=lambda x: abs(x * magnitude - raw_tick))
            fig.update_yaxes(dtick=dtick, row=1, col=1)

        # ── Panel: RSI (if enabled) ──
        if show_rsi:
            rsi_row = panels.index('rsi') + 1
            rx, ry = _clean_series(df, 'rsi')
            if len(rx) > 5:
                fig.add_trace(go.Scatter(x=rx, y=ry,
                    line=dict(color='#aa44ff', width=1.5), name='RSI'), row=rsi_row, col=1)
            fig.add_hline(y=70, line_dash='dash', line_color='rgba(255,68,68,0.6)',
                          line_width=1, row=rsi_row, col=1)
            fig.add_hline(y=30, line_dash='dash', line_color='rgba(0,255,136,0.6)',
                          line_width=1, row=rsi_row, col=1)
            fig.update_yaxes(range=[0, 100], row=rsi_row, col=1)

        # ── Panel: MACD (if enabled) ──
        if show_macd:
            macd_row = panels.index('macd') + 1
            mx_h, my_h = _clean_series(df, 'macd_hist')
            if len(mx_h) > 5:
                colors = ['#00ff88' if v >= 0 else '#ff4444' for v in my_h]
                fig.add_trace(go.Bar(x=mx_h, y=my_h,
                    marker_color=colors, name='MACD Hist'), row=macd_row, col=1)

            mx, my = _clean_series(df, 'macd')
            if len(mx) > 5:
                fig.add_trace(go.Scatter(x=mx, y=my,
                    line=dict(color='#00aaff', width=1.5), name='MACD'), row=macd_row, col=1)

            ms, msy = _clean_series(df, 'macd_signal')
            if len(ms) > 5:
                fig.add_trace(go.Scatter(x=ms, y=msy,
                    line=dict(color='#ffaa00', width=1), name='Sinyal'), row=macd_row, col=1)

        # ── Layout ──
        chart_height = 550 if num_rows == 1 else 650

        # Build tick values/labels for ~12 evenly spaced date labels
        num_ticks = min(12, len(x_dates))
        tick_step = max(1, len(x_dates) // num_ticks)
        tick_vals = list(range(0, len(x_dates), tick_step))
        tick_text = [date_labels[i] for i in tick_vals]

        fig.update_layout(
            template='plotly_dark' if not is_light else 'plotly_white',
            paper_bgcolor=paper_bg,
            plot_bgcolor=plot_bg,
            font=dict(family='Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif', size=12, color=font_color),
            xaxis_rangeslider_visible=False,
            showlegend=True,
            legend=dict(
                bgcolor='rgba(0,0,0,0)',
                font=dict(size=11),
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            margin=dict(l=65, r=15, t=30, b=40),
            height=chart_height
        )

        # Hide range sliders for all x-axes
        for i in range(1, num_rows + 1):
            axis_name = f'xaxis{i}_rangeslider_visible' if i > 1 else 'xaxis_rangeslider_visible'
            fig.update_layout(**{axis_name: False})

        fig.update_xaxes(gridcolor=grid_color, showgrid=True)
        fig.update_yaxes(gridcolor=grid_color, showgrid=True)

        # Only show x-axis tick labels on the bottom panel, using date labels
        for i in range(1, num_rows + 1):
            fig.update_xaxes(
                showticklabels=(i == num_rows),
                tickvals=tick_vals if i == num_rows else None,
                ticktext=tick_text if i == num_rows else None,
                row=i, col=1
            )

        return fig

    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


def score_opportunity(analysis):
    """Score each instrument for opportunity ranking."""
    score = 0
    ts = analysis.get('trend_score', 0)
    rr = analysis.get('action_plan', {}).get('rr_orani', 0)
    signal = analysis.get('signal', {}).get('signal', 'NÖTR')

    if signal in ('AL', 'SAT'):
        score += 40
    elif signal == 'İZLE':
        score += 20

    score += abs(ts) * 0.3
    score += min(rr * 10, 30)

    analysis['opportunity_score'] = round(score, 1)
    return analysis


# ─── ROUTES ───────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/watchlist')
def get_watchlist():
    return jsonify(load_watchlist())


@app.route('/api/watchlist/add', methods=['POST'])
def add_to_watchlist():
    data = request.json
    symbol = data.get('symbol', '').strip()
    name = data.get('name', '').strip()
    category = data.get('category', 'BIST')

    if not symbol or not name:
        return jsonify({'error': 'Symbol ve name gerekli'}), 400

    watchlist = load_watchlist()
    if category not in watchlist:
        watchlist[category] = []

    # Check duplicate
    for inst in watchlist[category]:
        if inst['symbol'] == symbol:
            return jsonify({'error': 'Bu enstrüman zaten listede'}), 400

    watchlist[category].append({'symbol': symbol, 'name': name})
    save_watchlist(watchlist)
    return jsonify({'success': True})


@app.route('/api/watchlist/remove', methods=['POST'])
def remove_from_watchlist():
    data = request.json
    symbol = data.get('symbol', '').strip()

    if not symbol:
        return jsonify({'error': 'Symbol gerekli'}), 400

    watchlist = load_watchlist()
    for category in watchlist:
        watchlist[category] = [i for i in watchlist[category] if i['symbol'] != symbol]
    save_watchlist(watchlist)
    return jsonify({'success': True})


@app.route('/api/analyze/<path:symbol>')
def analyze(symbol):
    tf = request.args.get('tf', '3A')
    result = analyze_symbol(symbol, tf)
    return jsonify(result)


@app.route('/api/analyze/all')
def analyze_all_endpoint():
    watchlist = load_watchlist()
    results = []
    for category, instruments in watchlist.items():
        for inst in instruments:
            cached = load_from_cache(inst['symbol'])
            if cached and 'error' not in cached:
                cached['category'] = category
                cached['name'] = inst['name']
                results.append(cached)
            else:
                analysis = analyze_symbol(inst['symbol'])
                if 'error' not in analysis:
                    analysis['category'] = category
                    analysis['name'] = inst['name']
                    results.append(analysis)
    return jsonify({
        'results': results,
        'updated_at': last_update_time or datetime.now().strftime('%H:%M:%S')
    })


@app.route('/api/chart/<path:symbol>/<tf>')
def chart(symbol, tf):
    show_rsi = request.args.get('rsi', '0') == '1'
    show_macd = request.args.get('macd', '0') == '1'
    show_sr = request.args.get('sr', '1') == '1'
    show_trend = request.args.get('trend', '0') == '1'
    show_volume = request.args.get('vol', '1') == '1'
    theme = request.args.get('theme', 'dark')
    fig = create_chart_json(symbol, tf, show_rsi=show_rsi, show_macd=show_macd,
                            show_sr=show_sr, show_trend=show_trend,
                            show_volume=show_volume, theme=theme)
    if fig is None:
        return '<div style="color:#888;text-align:center;padding:40px;">Grafik yüklenemedi</div>'
    chart_html = fig.to_html(
        full_html=True,
        include_plotlyjs='cdn',
        config={'responsive': True, 'displayModeBar': False}
    )
    return app.response_class(
        response=chart_html,
        status=200,
        mimetype='text/html'
    )


@app.route('/api/opportunities')
def opportunities():
    watchlist = load_watchlist()
    all_analyses = []
    for category, instruments in watchlist.items():
        for inst in instruments:
            cached = load_from_cache(inst['symbol'])
            if cached and 'error' not in cached:
                cached['category'] = category
                cached['name'] = inst['name']
                all_analyses.append(cached)

    actionable = [a for a in all_analyses if a.get('signal', {}).get('signal') in ('AL', 'SAT', 'İZLE')]
    scored = [score_opportunity(a) for a in actionable]
    top = sorted(scored, key=lambda x: x.get('opportunity_score', 0), reverse=True)[:5]
    return jsonify(top)


@app.route('/api/ticker')
def ticker():
    watchlist = load_watchlist()
    items = []
    for category, instruments in watchlist.items():
        for inst in instruments:
            cached = load_from_cache(inst['symbol'])
            if cached and 'error' not in cached:
                items.append({
                    'symbol': inst['symbol'],
                    'name': inst['name'],
                    'price': cached.get('price', 0),
                    'change_pct': cached.get('change_pct', 0)
                })
    return jsonify(items)


# ─── PORTFOLIO ────────────────────────────────────────────

@app.route('/api/portfolio')
def get_portfolio():
    positions = load_portfolio()
    total_cost = 0
    total_current = 0
    for pos in positions:
        cached = load_from_cache(pos['symbol'])
        pos['current_price'] = cached.get('price', 0) if cached else 0
        cost = pos['buy_price'] * pos['quantity']
        current = pos['current_price'] * pos['quantity']
        pos['pnl'] = round(current - cost, 2)
        pos['pnl_pct'] = round((current - cost) / cost * 100, 2) if cost > 0 else 0
        total_cost += cost
        total_current += current
    return jsonify({
        'positions': positions,
        'total_cost': round(total_cost, 2),
        'total_current': round(total_current, 2),
        'total_pnl': round(total_current - total_cost, 2),
        'total_pnl_pct': round((total_current - total_cost) / total_cost * 100, 2) if total_cost > 0 else 0
    })


@app.route('/api/portfolio/add', methods=['POST'])
def add_portfolio():
    data = request.json
    symbol = data.get('symbol', '').strip()
    buy_price = float(data.get('buy_price', 0))
    quantity = float(data.get('quantity', 0))
    if not symbol or buy_price <= 0 or quantity <= 0:
        return jsonify({'error': 'Geçerli sembol, fiyat ve miktar gerekli'}), 400
    positions = load_portfolio()
    positions.append({
        'symbol': symbol,
        'buy_price': buy_price,
        'quantity': quantity,
        'date': data.get('date', datetime.now().strftime('%Y-%m-%d'))
    })
    save_portfolio(positions)
    return jsonify({'success': True})


@app.route('/api/portfolio/remove', methods=['POST'])
def remove_portfolio():
    data = request.json
    idx = int(data.get('index', -1))
    positions = load_portfolio()
    if 0 <= idx < len(positions):
        positions.pop(idx)
        save_portfolio(positions)
        return jsonify({'success': True})
    return jsonify({'error': 'Geçersiz index'}), 400


# ─── SCHEDULER ────────────────────────────────────────────

scheduler = BackgroundScheduler()


def auto_update():
    global last_update_time
    with app.app_context():
        watchlist = load_watchlist()
        for category, instruments in watchlist.items():
            for inst in instruments:
                try:
                    analysis = analyze_symbol(inst['symbol'])
                    save_to_cache(inst['symbol'], analysis)
                except Exception as e:
                    print(f"[HATA] {inst['symbol']}: {e}")
        last_update_time = datetime.now().strftime('%H:%M:%S')
        print(f"[GÜNCELLEME] Tüm veriler güncellendi: {last_update_time}")


scheduler.add_job(auto_update, 'interval', minutes=5, id='auto_update')
scheduler.start()


# ─── MAIN ─────────────────────────────────────────────────

if __name__ == '__main__':
    def open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open('http://localhost:5001')

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=False)
