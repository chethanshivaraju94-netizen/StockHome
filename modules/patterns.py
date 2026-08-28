import pandas as pd
import numpy as np

def detect_inside_bar(df):
    """Inside bar with daily range strictly less than ATR14, and volume <= 50 SMA."""
    if len(df) < 10: return False
    h = df['High']
    l = df['Low']
    c = df['Close']
    v = df['Volume']
    
    if h.iloc[-1] <= h.iloc[-2] and l.iloc[-1] >= l.iloc[-2]:
        tr1 = h - l
        tr2 = (h - c.shift(1)).abs()
        tr3 = (l - c.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = tr.rolling(14, min_periods=5).mean().iloc[-1]
        rng = h.iloc[-1] - l.iloc[-1]
        
        if rng < atr14:
            vol_sma50 = v.rolling(50, min_periods=15).mean().iloc[-1]
            if v.iloc[-1] <= vol_sma50:
                return True
    return False

def detect_flat_base(df):
    """10+ bars constrained within a tight 15% band with Volume Dry Up."""
    if len(df) < 20: return False
    h = df['High']
    l = df['Low']
    v = df['Volume']
    
    period = 15 
    h_period = h.iloc[-period:]
    l_period = l.iloc[-period:]
    max_h = h_period.max()
    min_l = l_period.min()
    
    if min_l > 0 and (max_h - min_l) / min_l <= 0.15:
        avg_vol_5 = v.iloc[-5:].mean()
        vol_sma50 = v.rolling(50, min_periods=15).mean().iloc[-1]
        if avg_vol_5 <= vol_sma50 * 1.1:
            return True
    return False

def detect_bull_flag(df):
    """Sharp pole >= 20% followed by tight retracement <= 38.2%."""
    if len(df) < 25: return False
    h = df['High']
    l = df['Low']
    v = df['Volume']
    
    h_30 = h.iloc[-30:]
    pole_top_idx = h_30.idxmax()
    pole_top = h_30[pole_top_idx]
    
    pre_pole = h.loc[:pole_top_idx].iloc[-15:]
    if len(pre_pole) < 2: return False
    pole_start = pre_pole.min()
    
    if pole_start > 0 and (pole_top - pole_start) / pole_start >= 0.20:
        flag_data = h.loc[pole_top_idx:]
        flag_len = len(flag_data) - 1
        
        if 3 <= flag_len <= 15:
            flag_low = l.loc[pole_top_idx:].min()
            ret_pct = (pole_top - flag_low) / (pole_top - pole_start)
            
            if ret_pct <= 0.382:
                vol_pole = v.loc[:pole_top_idx].iloc[-10:].mean()
                vol_flag = v.loc[pole_top_idx:].mean()
                if vol_flag <= vol_pole * 0.85: # 15% drop in volume required
                    return True
    return False

def detect_vcp(df):
    """Segment-based Depth Contraction: Left side is wide, right side tightens."""
    if len(df) < 45: return False
    h = df['High'].iloc[-60:]
    l = df['Low'].iloc[-60:]
    c = df['Close'].iloc[-60:]
    v = df['Volume'].iloc[-60:]
    
    base_high = h.max()
    curr_close = c.iloc[-1]
    
    # Must be trading near the top of the base (within 15%)
    if base_high <= 0 or (base_high - curr_close) / base_high > 0.15:
        return False
        
    # Split the base into 3 segments to check for volatility decreasing left-to-right
    seg1_h = h.iloc[:20].max()
    seg1_l = l.iloc[:20].min()
    d1 = (seg1_h - seg1_l) / seg1_h if seg1_h > 0 else 0
    
    seg2_h = h.iloc[20:40].max()
    seg2_l = l.iloc[20:40].min()
    d2 = (seg2_h - seg2_l) / seg2_h if seg2_h > 0 else 0
    
    seg3_h = h.iloc[40:].max()
    seg3_l = l.iloc[40:].min()
    d3 = (seg3_h - seg3_l) / seg3_h if seg3_h > 0 else 0
    
    # Minervini VCP Rule: Left side must be loose (>=6%), right side must be tight (<=10%)
    if max(d1, d2) >= 0.06 and d3 <= 0.10:
        # Successive contraction check (allow 25% margin of error for market noise)
        if d2 <= d1 * 1.25 and d3 <= max(d2, 0.04) * 1.25:
            vol_sma50 = v.rolling(50, min_periods=15).mean().iloc[-1]
            if v.iloc[-5:].mean() <= vol_sma50 * 1.2:
                return True
    return False

def run_pattern_engine(df_screener, pat_config, combo_mode):
    from modules.data import fetch_historical_data_yf
    
    symbols_tuple = tuple((df_screener["exchange"] + ":" + df_screener["name"]).tolist())
    data_dict, sym_map = fetch_historical_data_yf(symbols_tuple, period="3mo")
    
    pattern_results = {}
    
    if data_dict:
        for yf_t, tv_sym in sym_map.items():
            if yf_t not in data_dict:
                pattern_results[tv_sym] = ""
                continue
                
            df = data_dict[yf_t]
            
            has_inside = detect_inside_bar(df) if pat_config.get("inside") else False
            has_flat = detect_flat_base(df) if pat_config.get("flat") else False
            has_flag = detect_bull_flag(df) if pat_config.get("flag") else False
            has_vcp = detect_vcp(df) if pat_config.get("vcp") else False
            
            detected = []
            if has_inside: detected.append("🎯 NR14 Inside")
            if has_flat: detected.append("📐 Flat Base")
            if has_flag: detected.append("🚩 Bull Flag")
            if has_vcp: detected.append("🌪️ VCP")
                
            # Apply strict COMBO logic if requested by user
            if combo_mode == "Require Inside Bar INSIDE a Base":
                if has_inside and (has_flat or has_flag or has_vcp):
                    pattern_results[tv_sym] = " | ".join(detected)
                else:
                    pattern_results[tv_sym] = ""
            else:
                pattern_results[tv_sym] = " | ".join(detected) if detected else ""

    # Map the results back to the dataframe
    df_screener["TV_Symbol"] = df_screener["exchange"] + ":" + df_screener["name"]
    df_screener["Detected_Pattern"] = df_screener["TV_Symbol"].map(pattern_results).fillna("")
    
    # Filter the screener dataframe down to ONLY stocks that hit at least one selected pattern
    if any(pat_config.values()):
        df_screener = df_screener[df_screener["Detected_Pattern"] != ""]
        
    return df_screener
