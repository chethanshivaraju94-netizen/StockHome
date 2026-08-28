import pandas as pd
import numpy as np
import streamlit as st


# ==========================================
# 0. GEOMETRIC REGRESSION & PIVOT HELPERS
# ==========================================
def extract_pivots_and_slopes(df, lookback=40):
    if len(df) < lookback:
        return None

    h = df['High'].iloc[-lookback:].values
    l = df['Low'].iloc[-lookback:].values
    c = df['Close'].iloc[-lookback:].values
    
    base_price = c[0]
    if base_price <= 0:
        return None

    high_idx = []
    low_idx = []
    for i in range(2, lookback - 2):
        if h[i] == max(h[i-2:i+3]):
            high_idx.append(i)
        if l[i] == min(l[i-2:i+3]):
            low_idx.append(i)

    if len(high_idx) < 2 or len(low_idx) < 2:
        return None

    x_h = np.array(high_idx)
    y_h = h[high_idx] / base_price
    slope_h, intercept_h = np.polyfit(x_h, y_h, 1)
    
    y_h_pred = slope_h * x_h + intercept_h
    ss_res_h = np.sum((y_h - y_h_pred) ** 2)
    ss_tot_h = np.sum((y_h - np.mean(y_h)) ** 2)
    r2_h = 1 - (ss_res_h / ss_tot_h) if ss_tot_h > 0 else 1.0

    x_l = np.array(low_idx)
    y_l = l[low_idx] / base_price
    slope_l, intercept_l = np.polyfit(x_l, y_l, 1)

    y_l_pred = slope_l * x_l + intercept_l
    ss_res_l = np.sum((y_l - y_l_pred) ** 2)
    ss_tot_l = np.sum((y_l - np.mean(y_l)) ** 2)
    r2_l = 1 - (ss_res_l / ss_tot_l) if ss_tot_l > 0 else 1.0

    apex_pos = None
    if abs(slope_h - slope_l) > 1e-4:
        apex_pos = (intercept_l - intercept_h) / (slope_h - slope_l)

    return {
        "slope_h": slope_h,
        "slope_l": slope_l,
        "r2_h": r2_h,
        "r2_l": r2_l,
        "apex_pos": apex_pos,
        "lookback": lookback,
        "highs_count": len(high_idx),
        "lows_count": len(low_idx)
    }


# ==========================================
# 1. PHASE 1 PATTERNS (CONTRACTION SETUPS)
# ==========================================
def detect_inside_bar(df):
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
            if v.iloc[-1] <= vol_sma50 * 1.1: 
                return True
    return False

def detect_flat_base(df):
    if len(df) < 15: return False
    h = df['High']
    l = df['Low']
    v = df['Volume']
    
    max_lookback = min(65, len(df))
    
    for period in range(max_lookback, 9, -1):
        h_period = h.iloc[-period:]
        l_period = l.iloc[-period:]
        max_h = h_period.max()
        min_l = l_period.min()
        
        if min_l > 0 and (max_h - min_l) / min_l <= 0.15:
            avg_vol_5 = v.iloc[-5:].mean()
            vol_sma50 = v.rolling(50, min_periods=15).mean().iloc[-1]
            if avg_vol_5 <= vol_sma50 * 1.25:
                return True
    return False

def detect_bull_flag(df):
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


# ==========================================
# 2. PHASE 2 PATTERNS (GEOMETRIC BREAKOUTS)
# ==========================================
def detect_ascending_triangle(df):
    if len(df) < 30: return False
    geom = extract_pivots_and_slopes(df, lookback=40)
    if not geom: return False

    is_upper_flat = abs(geom["slope_h"]) <= 0.003
    is_lower_rising = geom["slope_l"] >= 0.002
    
    if is_upper_flat and is_lower_rising:
        if geom["apex_pos"] and geom["apex_pos"] > 0:
            apex_ratio = geom["lookback"] / geom["apex_pos"]
            if 0.40 <= apex_ratio <= 1.15:
                v = df['Volume']
                vol_sma50 = v.rolling(50, min_periods=15).mean().iloc[-1]
                if v.iloc[-5:].mean() <= vol_sma50 * 1.25:
                    return True
    return False

def detect_descending_triangle(df):
    if len(df) < 30: return False
    geom = extract_pivots_and_slopes(df, lookback=40)
    if not geom: return False

    is_lower_flat = abs(geom["slope_l"]) <= 0.003
    is_upper_falling = geom["slope_h"] <= -0.002
    
    if is_lower_flat and is_upper_falling:
        if geom["apex_pos"] and geom["apex_pos"] > 0:
            apex_ratio = geom["lookback"] / geom["apex_pos"]
            if 0.40 <= apex_ratio <= 1.15:
                return True
    return False

def detect_symmetrical_triangle(df):
    if len(df) < 30: return False
    geom = extract_pivots_and_slopes(df, lookback=40)
    if not geom: return False

    is_upper_falling = geom["slope_h"] <= -0.002
    is_lower_rising = geom["slope_l"] >= 0.002
    
    if is_upper_falling and is_lower_rising:
        ratio = abs(geom["slope_h"] / geom["slope_l"]) if geom["slope_l"] != 0 else 0
        if 0.40 <= ratio <= 2.50:
            if geom["apex_pos"] and geom["apex_pos"] > 0:
                apex_ratio = geom["lookback"] / geom["apex_pos"]
                if 0.40 <= apex_ratio <= 1.15:
                    v = df['Volume']
                    vol_sma50 = v.rolling(50, min_periods=15).mean().iloc[-1]
                    if v.iloc[-5:].mean() <= vol_sma50 * 1.25:
                        return True
    return False

def detect_falling_wedge(df):
    if len(df) < 30: return False
    geom = extract_pivots_and_slopes(df, lookback=40)
    if not geom: return False

    is_both_falling = geom["slope_h"] < -0.001 and geom["slope_l"] < -0.001
    is_converging = abs(geom["slope_h"]) > abs(geom["slope_l"])
    
    if is_both_falling and is_converging:
        v = df['Volume']
        vol_sma50 = v.rolling(50, min_periods=15).mean().iloc[-1]
        if v.iloc[-5:].mean() <= vol_sma50 * 1.25:
            return True
    return False

def detect_channel(df):
    if len(df) < 30: return False
    geom = extract_pivots_and_slopes(df, lookback=40)
    if not geom: return False

    slope_diff = abs(geom["slope_h"] - geom["slope_l"])
    if slope_diff <= 0.0035:
        if geom["slope_h"] > 0.0015:
            return "📈 Ascending Channel"
        elif geom["slope_h"] < -0.0015:
            return "📉 Descending Channel"
        else:
            return "⏸️ Horizontal Channel"
    return False


# ==========================================
# 3. MASTER PATTERN ENGINE CONTROLLER
# ==========================================
def run_pattern_engine(df_screener, pat_config, combo_mode):
    from modules.data import fetch_historical_data_yf
    
    symbols_tuple = tuple((df_screener["exchange"] + ":" + df_screener["name"]).tolist())
    data_dict, sym_map = fetch_historical_data_yf(symbols_tuple, period="3mo")
    
    pattern_results = {}
    
    if not data_dict:
        st.error("⚠️ Yahoo Finance returned no historical data (Possible rate limit or connection issue). Pattern scanning bypassed.")
        df_screener["Detected_Pattern"] = ""
        return df_screener
        
    for yf_t, tv_sym in sym_map.items():
        if yf_t not in data_dict:
            pattern_results[tv_sym] = ""
            continue
            
        df = data_dict[yf_t]
        
        # 1. Evaluate Contraction Setups
        check_inside = True if combo_mode == "Require Inside Bar INSIDE a Base" else pat_config.get("inside")
        has_inside = detect_inside_bar(df) if check_inside else False
        has_flat = detect_flat_base(df) if pat_config.get("flat") else False
        has_flag = detect_bull_flag(df) if pat_config.get("flag") else False
        
        # 2. Evaluate Geometric Setups
        has_asc_tri = detect_ascending_triangle(df) if pat_config.get("asc_tri") else False
        has_desc_tri = detect_descending_triangle(df) if pat_config.get("desc_tri") else False
        has_sym_tri = detect_symmetrical_triangle(df) if pat_config.get("sym_tri") else False
        has_wedge = detect_falling_wedge(df) if pat_config.get("wedge") else False
        channel_res = detect_channel(df) if pat_config.get("channel") else False
        
        detected = []
        if has_inside and (pat_config.get("inside") or combo_mode == "Require Inside Bar INSIDE a Base"):
            detected.append("🎯 NR14 Inside")
        if has_flat: detected.append("📐 Flat Base")
        if has_flag: detected.append("🚩 Bull Flag")
        if has_asc_tri: detected.append("📐 Asc Triangle")
        if has_desc_tri: detected.append("🔻 Desc Triangle")
        if has_sym_tri: detected.append("🔷 Sym Triangle")
        if has_wedge: detected.append("📉 Falling Wedge")
        if channel_res: detected.append(channel_res)
            
        # Apply Combo Filter Mode
        if combo_mode == "Require Inside Bar INSIDE a Base":
            base_present = False
            if pat_config.get("flat") and has_flat: base_present = True
            if pat_config.get("flag") and has_flag: base_present = True
            if pat_config.get("asc_tri") and has_asc_tri: base_present = True
            if pat_config.get("desc_tri") and has_desc_tri: base_present = True
            if pat_config.get("sym_tri") and has_sym_tri: base_present = True
            if pat_config.get("wedge") and has_wedge: base_present = True
            if pat_config.get("channel") and channel_res: base_present = True
            
            if has_inside and base_present:
                bases_only = [d for d in detected if d != "🎯 NR14 Inside"]
                pattern_results[tv_sym] = " | ".join(bases_only) + " + 🎯 Inside Bar"
            else:
                pattern_results[tv_sym] = ""
        else:
            pattern_results[tv_sym] = " | ".join(detected) if detected else ""

    df_screener["TV_Symbol"] = df_screener["exchange"] + ":" + df_screener["name"]
    df_screener["Detected_Pattern"] = df_screener["TV_Symbol"].map(pattern_results).fillna("")
    
    if any(pat_config.values()) or combo_mode == "Require Inside Bar INSIDE a Base":
        df_screener = df_screener[df_screener["Detected_Pattern"] != ""]
        
    return df_screener
