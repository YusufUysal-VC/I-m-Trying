import pandas_ta as ta


def calculate_all(df):
    """Calculate all technical indicators on a DataFrame."""
    if df is None or df.empty or len(df) < 20:
        return df

    # RSI (14)
    df['rsi'] = ta.rsi(df['Close'], length=14)

    # MACD (12, 26, 9)
    macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
    if macd is not None:
        df['macd'] = macd.iloc[:, 0]
        df['macd_signal'] = macd.iloc[:, 1]
        df['macd_hist'] = macd.iloc[:, 2]

    # Bollinger Bands (20, 2)
    bb = ta.bbands(df['Close'], length=20, std=2)
    if bb is not None:
        df['bb_upper'] = bb.iloc[:, 2]
        df['bb_mid'] = bb.iloc[:, 1]
        df['bb_lower'] = bb.iloc[:, 0]

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
