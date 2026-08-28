import pandas as pd
import numpy as np

def detect_inside_bar(df):
    if len(df) < 15: return False
    h = df['High']
    l = df['Low']
    c = df['Close']
    v = df['Volume']
    
    # 1. Inside Bar Check (Strict)
    if h.iloc[-1] <= h.iloc[-2] and l.iloc[-1] >= l.iloc[-2]:
        # 2. Daily Range < ATR14
        tr1 = h - l
        tr2 = (h - c.shift(1)).abs()
        tr3 = (l - c.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr14 = tr.rolling(14).mean().iloc[-1]
        rng = h.iloc[-1] - l.iloc[-1]
        
        if rng < atr14:
            # 3. Volume Dry Up (Current Vol <= 50 SMA)
            vol_sma50 = v.rolling(50).mean().iloc[-1]
            if v.iloc[-1] <= vol_sma50:
                return True
    return False

def detect_flat_base(df):
    if len(df) < 50: return False
    h = df['High']
    l = df['Low']
    v = df['Volume']
    
    period = 15 # Check last 15 days (10+ bars rule)
    h_period = h.iloc[-period:]
    l_period = l.iloc[-period:]
    max_h = h_period.max()
    min_l = l_period.min()
    
    # Range bound within 15%
    if min_l > 0 and (max_h - min_l) / min_l <= 0.15:
        # VDU: Average volume of last 3 days <= 50 Vol SMA
        avg_vol_3 = v.iloc[-3:].mean()
        vol_sma50 = v.rolling(50).mean().iloc[-1]
        if avg_vol_3 <= vol_sma50:
            return True
    return False

def detect_bull_flag(df):
    if len(df) < 50: return False
    h = df['High']
    l = df['Low']
    v = df['Volume']
    
    # 1. Find Pole (Max High in last 30 days)
    h_30 = h.iloc[-30:]
    pole_top_idx = h_30.idxmax()
    pole_top = h_30[pole_top_idx]
    
    pre_pole = h.loc[:pole_top_idx].iloc[-15:]
    if len(pre_pole) < 2: return False
    pole_start = pre_pole.min()
    
    # 2. Pole magnitude >= 20%
    if pole_start > 0 and (pole_top - pole_start) / pole_start >= 0.20:
        flag_data = h.loc[pole_top_idx:]
        flag_len = len(flag_data) - 1
        
        # 3. Flag Duration (3 to 15 bars)
        if 3 <= flag_len <= 15:
            flag_low = l.loc[pole_top_idx:].min()
            ret_pct = (pole_top - flag_low) / (pole_top - pole_start)
            
            # 4. Retracement <= 38.2%
            if ret_pct <= 0.382:
                vol_pole = v.loc[:pole_top_idx].iloc[-10:].mean()
                vol_flag = v.loc[pole_top_idx:].mean()
                
                # 5. Sharp Volume Decline in Flag vs Pole
                if vol_flag <= vol_pole * 0.75:
                    return True
    return False

def detect_vcp(df):
    if len(df) < 60: return False
    h = df['High']
    l = df['Low']
    v = df['Volume']
    
    h_60 = h.iloc[-60:]
    l_60 = l.iloc[-60:]
    
    # 1. Pivot Detection: Find local peak highs
    peaks = h_60[(h_60 == h_60.rolling(5, center=True).max())]
    
    if len(peaks) >= 2:
        depths = []
        peak_dates = peaks.index.tolist()
        
        # Calculate depth of each swing
        for i in range(len(peak_dates)-1):
            p1 = peak_dates[i]
            p2 = peak_dates[i+1]
            trough = l_60.loc[p1:p2].min()
            depth = (h_60[p1] - trough) / h_60[p1]
            depths.append(depth)
            
        last_trough = l_60.loc[peak_dates[-1]:].min()
        last_depth = (h_60[peak_dates[-1]] - last_trough) / h_60[peak_dates[-1]]
        depths.append(last_depth)
        
        # Filter out tiny noise fluctuations
        depths = [d for d in depths if d > 0.015]
        
        # 2. Check Contraction Sequence
        if len(depths) >= 2:
            is_contracting = True
            for i in range(1, len(depths)):
                # Allow a tiny 5% mathematical margin of error, but sequence must be mostly contracting
                if depths[i] > depths[i-1] * 1.05: 
                    is_contracting = False
                    break
            
            # 3. Final Contraction Depth <= 6% & Vol Dry Up
            if is_contracting and depths[-1] <= 0.06:
                vol_sma50 = v.rolling(50).mean().iloc[-1]
                if v.iloc[-3:].mean() <= vol_sma50:
                    return True
    return False

def run_pattern_engine(df_screener, pat_config):
    from modules.data import fetch_historical_data_yf
    
    # Format symbols for yfinance engine
    symbols = df_screener["exchange"] + ":" + df_screener["name"]
    data_dict, sym_map = fetch_historical_data_yf(symbols.tolist())
    
    if not data_dict:
        df_screener["Detected_Pattern"] = ""
        return df_screener
        
    pattern_results = {}
    
    for yf_t, tv_sym in sym_map.items():
        if yf_t not in data_dict:
            pattern_results[tv_sym] = ""
            continue
            
        df = data_dict[yf_t]
        
        detected = []
        if pat_config.get("inside") and detect_inside_bar(df):
            detected.append("🎯 NR14 Inside")
        if pat_config.get("flat") and detect_flat_base(df):
            detected.append("📐 Flat Base")
        if pat_config.get("flag") and detect_bull_flag(df):
            detected.append("🚩 Bull Flag")
        if pat_config.get("vcp") and detect_vcp(df):
            detected.append("🌪️ VCP")
            
        pattern_results[tv_sym] = " | ".join(detected)
        
    df_screener["TV_Symbol"] = df_screener["exchange"] + ":" + df_screener["name"]
    df_screener["Detected_Pattern"] = df_screener["TV_Symbol"].map(pattern_results).fillna("")
    
    # Filter the screener dataframe down to ONLY stocks that hit at least one selected pattern
    if any(pat_config.values()):
        df_screener = df_screener[df_screener["Detected_Pattern"] != ""]
        
    return df_screener
