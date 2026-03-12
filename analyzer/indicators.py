import pandas_ta as ta


def calculate_all(df):
    """Calculate all technical indicators on a DataFrame."""
    if df is None or df.empty or len(df) < 20:
        return df

    # RSI (14)
    df['rsi'] = ta.rsi(df['Close'], length=14)

    # MACD (12, 26, 9)
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        # Use explicit column names from pandas-ta
        for col in macd.columns:
            if col.startswith('MACD_') and not col.startswith('MACDh') and not col.startswith('MACDs'):
                df['macd'] = macd[col]
            elif col.startswith('MACDh'):
                df['macd_hist'] = macd[col]
            elif col.startswith('MACDs'):
                df['macd_signal'] = macd[col]

    # Bollinger Bands (20, 2)
    bb = ta.bbands(df['Close'], length=20, std=2)
    if bb is not None and not bb.empty:
        for col in bb.columns:
            if col.startswith('BBU'):
                df['bb_upper'] = bb[col]
            elif col.startswith('BBM'):
                df['bb_mid'] = bb[col]
            elif col.startswith('BBL'):
                df['bb_lower'] = bb[col]

    # Moving Averages
    df['ema20'] = ta.ema(df['Close'], length=20)
    df['ema50'] = ta.ema(df['Close'], length=50)
    df['ema200'] = ta.ema(df['Close'], length=200)
    df['sma20'] = ta.sma(df['Close'], length=20)

    # Volume EMA
    if 'Volume' in df.columns and df['Volume'].sum() > 0:
        df['vol_ema20'] = ta.ema(df['Volume'], length=20)
    else:
        df['vol_ema20'] = 0

    return df
