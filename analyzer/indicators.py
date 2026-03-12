import pandas_ta as ta
import pandas as pd


def calculate_all(df):
    """Calculate all technical indicators on a DataFrame."""
    if df is None or df.empty or len(df) < 20:
        return df

    close = df['Close']

    # RSI (14)
    rsi_result = ta.rsi(close, length=14)
    if rsi_result is not None:
        df['rsi'] = rsi_result

    # MACD (12, 26, 9)
    try:
        macd_result = ta.macd(close, fast=12, slow=26, signal=9)
        if macd_result is not None and not macd_result.empty:
            cols = list(macd_result.columns)
            print(f"[DEBUG] MACD columns: {cols}")
            # Assign by column order: MACD line, histogram, signal
            # pandas-ta returns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            for col in cols:
                col_upper = col.upper()
                if 'MACDH' in col_upper:
                    df['macd_hist'] = macd_result[col]
                elif 'MACDS' in col_upper:
                    df['macd_signal'] = macd_result[col]
                elif 'MACD' in col_upper:
                    df['macd'] = macd_result[col]
    except Exception as e:
        print(f"[HATA] MACD hesaplama: {e}")

    # Bollinger Bands (20, 2)
    try:
        bb_result = ta.bbands(close, length=20, std=2)
        if bb_result is not None and not bb_result.empty:
            cols = list(bb_result.columns)
            print(f"[DEBUG] BBands columns: {cols}")
            for col in cols:
                col_upper = col.upper()
                if 'BBU' in col_upper:
                    df['bb_upper'] = bb_result[col]
                elif 'BBM' in col_upper:
                    df['bb_mid'] = bb_result[col]
                elif 'BBL' in col_upper:
                    df['bb_lower'] = bb_result[col]
    except Exception as e:
        print(f"[HATA] BBands hesaplama: {e}")

    # Moving Averages
    if len(df) >= 20:
        df['ema20'] = ta.ema(close, length=20)
        df['sma20'] = ta.sma(close, length=20)
    if len(df) >= 50:
        df['ema50'] = ta.ema(close, length=50)
    if len(df) >= 200:
        df['ema200'] = ta.ema(close, length=200)

    # Volume EMA
    if 'Volume' in df.columns and df['Volume'].sum() > 0:
        df['vol_ema20'] = ta.ema(df['Volume'], length=20)
    else:
        df['vol_ema20'] = 0

    return df
