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
        if avg_vol_5 <= vol_sma50 * 1.2:
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
                if vol_flag <= vol_pole * 0.85:
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
            
            # Force evaluate inside bar if combo mode is selected, regardless of checkbox
            check_inside = True if combo_mode == "Require Inside Bar INSIDE a Base" else pat_config.get("inside")
            has_inside = detect_inside_bar(df) if check_inside else False
            
            has_flat = detect_flat_base(df) if pat_config.get("flat") else False
            has_flag = detect_bull_flag(df) if pat_config.get("flag") else False
            
            detected = []
            if has_inside and (pat_config.get("inside") or combo_mode == "Require Inside Bar INSIDE a Base"):
                detected.append("🎯 NR14 Inside")
            if has_flat: detected.append("📐 Flat Base")
            if has_flag: detected.append("🚩 Bull Flag")
                
            # Apply strict COMBO logic
            if combo_mode == "Require Inside Bar INSIDE a Base":
                # Ensure at least one of the selected bases is present
                base_present = (has_flat and pat_config.get("flat")) or (has_flag and pat_config.get("flag"))
                if has_inside and base_present:
                    bases_only = [d for d in detected if d != "🎯 NR14 Inside"]
                    pattern_results[tv_sym] = " | ".join(bases_only) + " + 🎯 Inside Bar"
                else:
                    pattern_results[tv_sym] = ""
            else:
                pattern_results[tv_sym] = " | ".join(detected) if detected else ""

    # Map the results back to the dataframe
    df_screener["TV_Symbol"] = df_screener["exchange"] + ":" + df_screener["name"]
    df_screener["Detected_Pattern"] = df_screener["TV_Symbol"].map(pattern_results).fillna("")
    
    # Filter the screener dataframe down to ONLY stocks that hit at least one selected pattern
    if any(pat_config.values()) or combo_mode == "Require Inside Bar INSIDE a Base":
        df_screener = df_screener[df_screener["Detected_Pattern"] != ""]
        
    return df_screener
