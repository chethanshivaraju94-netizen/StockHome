import pandas as pd
import streamlit as st

def get_left_aligned_column_config(col_list):
    cfg = {}
    for col in col_list:
        if col == "TV_Link":
            cfg[col] = st.column_config.LinkColumn(
                "TradingView", display_text="↗️ Chart", alignment="left", width=85
            )
        elif col == "Screener_Link":
            cfg[col] = st.column_config.LinkColumn(
                "Screener.in", display_text="↗️ Screener", alignment="left", width=95
            )
        elif col in ["S.No.", "S.No._num"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=75)
        elif col in ["TV_Symbol", "Ticker"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=135)
        elif col == "name":
            cfg[col] = st.column_config.Column(col, alignment="left", width=140)
        elif col == "RS Rating":
            cfg[col] = st.column_config.NumberColumn(
                "RS Rating", alignment="left", format="%d", width=95
            )
        elif col in ["Date", "Sector", "Date Bought", "Date Sold", "Status"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=130)
        elif col == "Fundamental":
            cfg[col] = st.column_config.Column(col, alignment="left", width=155)
        elif "Rank Velocity" in col:
            cfg[col] = st.column_config.NumberColumn(
                col, alignment="left", format="%+d", width=125
            )
        elif col in ["Sector", "Basic Industry"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=220)
        elif col == "Industry":
            cfg[col] = st.column_config.Column(col, alignment="left", width=250)
        elif col in ["Close", "Change %", "ADR %"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=85)
        elif col in ["EPS Q YoY %", "Sales Q YoY %", "IPO Date"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=110)
        elif "Perf %" in col or "EMA" in col or "SMA" in col:
            cfg[col] = st.column_config.Column(col, alignment="left", width=85)
        elif col in [
            "Market Cap (₹ Cr)", "Buy Price (₹)", "Initial SL (₹)",
            "Current / Sold Price (₹)", "Capital Invested (₹)", "Current Value (₹)",
            "Booked Value (₹)", "Unrealised Value (₹)", "Gain / Loss (₹)",
            "Realised Gains (₹)", "Total Return (₹)"
        ]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=140)
        elif col in ["Abs Return %", "Allocation %", "Realized R", "Win Rate %", "Day"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=110)
        elif col in ["Stocks Passed", "Trades", "Wins", "ISO Week"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=115)
        elif col == "% Share":
            cfg[col] = st.column_config.Column(col, alignment="left", width=90)
        elif col in ["% of Sector Total", "% of Industry Total"]:
            cfg[col] = st.column_config.Column(col, alignment="left", width=145)
        else:
            cfg[col] = st.column_config.Column(col, alignment="left", width=110)
    return cfg

def color_scale_3pt(val, v_min, v_mid, v_max, c_min=(248, 105, 107), c_mid=(255, 255, 255), c_max=(99, 190, 123)):
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return ""
    try:
        v = float(val)
    except Exception:
        return ""

    if v <= v_min:
        r, g, b = c_min
    elif v >= v_max:
        r, g, b = c_max
    elif v < v_mid:
        ratio = (v - v_min) / max((v_mid - v_min), 1e-6)
        r = int(c_min[0] + (c_mid[0] - c_min[0]) * ratio)
        g = int(c_min[1] + (c_mid[1] - c_min[1]) * ratio)
        b = int(c_min[2] + (c_mid[2] - c_min[2]) * ratio)
    else:
        ratio = (v - v_mid) / max((v_max - v_mid), 1e-6)
        r = int(c_mid[0] + (c_max[0] - c_mid[0]) * ratio)
        g = int(c_mid[1] + (c_max[1] - c_mid[1]) * ratio)
        b = int(c_mid[2] + (c_max[2] - c_mid[2]) * ratio)
    return f"background-color: #{r:02X}{g:02X}{b:02X}; color: #000000;"

def color_scale_2pt(val, v_min, v_max, c_min=(255, 255, 255), c_max=(99, 190, 123)):
    if pd.isna(val) or val == "" or str(val).strip() == "":
        return ""
    try:
        v = float(val)
    except Exception:
        return ""

    if v <= v_min:
        r, g, b = c_min
    elif v >= v_max:
        r, g, b = c_max
    else:
        ratio = (v - v_min) / max((v_max - v_min), 1e-6)
        r = int(c_min[0] + (c_max[0] - c_min[0]) * ratio)
        g = int(c_min[1] + (c_max[1] - c_min[1]) * ratio)
        b = int(c_min[2] + (c_max[2] - c_min[2]) * ratio) # <-- This was the line causing the error
    return f"background-color: #{r:02X}{g:02X}{b:02X}; color: #000000;"

def color_binary_badge(val):
    v_str = str(val).strip().lower()
    if v_str in ["yes", "up"]:
        return "background-color: #63BE7B; color: #000000; font-weight: bold;"
    elif v_str in ["no", "down"]:
        return "background-color: #F8696B; color: #000000; font-weight: bold;"
    return ""

def safe_map(styler, func, subset=None):
    if hasattr(styler, "map"):
        return styler.map(func, subset=subset)
    else:
        return styler.applymap(func, subset=subset)

def style_market_monitor(df):
    styler = df.style
    format_dict = {}
    int_cols = ["Up 4% Today", "Down 4% Today", "Advances", "Declines", "52W Highs", "52W Lows"]
    float_cols = ["5 Day Ratio", "10 Day Ratio", "A/D Ratio", "Volume Breadth", "> 200 SMA (%)", "> 50 SMA (%)", "> 20 EMA (%)", "> 10 EMA (%)", "Nifty 500 Close", "Nifty 500 Chg %"]
    for col in int_cols:
        if col in df.columns:
            format_dict[col] = "{:.0f}"
    for col in float_cols:
        if col in df.columns:
            format_dict[col] = "{:.2f}"
    styler = styler.format(format_dict, na_rep="N/A")

    for c in ["Up 4% Today", "Advances", "52W Highs"]:
        if c in df.columns:
            max_v = 750 if c == "Advances" else 200
            styler = safe_map(styler, lambda v, mv=max_v: color_scale_2pt(v, 0, mv, (255, 255, 255), (99, 190, 123)), subset=[c])
    for c in ["Down 4% Today", "Declines", "52W Lows"]:
        if c in df.columns:
            max_v = 750 if c == "Declines" else 200
            styler = safe_map(styler, lambda v, mv=max_v: color_scale_2pt(v, 0, mv, (255, 255, 255), (248, 105, 107)), subset=[c])
    for c in ["5 Day Ratio", "10 Day Ratio", "A/D Ratio", "Volume Breadth"]:
        if c in df.columns:
            styler = safe_map(styler, lambda v: color_scale_3pt(v, 0.5, 1.0, 2.0), subset=[c])
    for c in ["> 200 SMA (%)", "> 50 SMA (%)", "> 20 EMA (%)", "> 10 EMA (%)"]:
        if c in df.columns:
            styler = safe_map(styler, lambda v: color_scale_3pt(v, 0.0, 50.0, 100.0), subset=[c])
    if "Nifty 500 Chg %" in df.columns:
        styler = safe_map(styler, lambda v: color_scale_3pt(v, -2.0, 0.0, 2.0), subset=["Nifty 500 Chg %"])
    try:
        styler = styler.hide(axis="index")
    except Exception:
        pass
    return styler

def style_sector_heatmap(df):
    styler = df.style
    format_dict = {}
    int_cols = ["65D RS Rank"]
    vel_cols = ["5D Rank Velocity", "10D Rank Velocity", "21D Rank Velocity", "65D Rank Velocity"]
    float_cols = ["Close", "% Chg", "5D RS %", "21D RS %", "65D RS %", "% Off RS High"]
    for col in int_cols:
        if col in df.columns:
            format_dict[col] = "{:.0f}"
    for col in vel_cols:
        if col in df.columns:
            format_dict[col] = "{:+.0f}"
    for col in float_cols:
        if col in df.columns:
            format_dict[col] = "{:.2f}"
    styler = styler.format(format_dict, na_rep="N/A")

    for c in vel_cols:
        if c in df.columns:
            styler = safe_map(styler, lambda v: color_scale_3pt(v, -10, 0, 10), subset=[c])
    for c in ["5D RS %", "21D RS %", "65D RS %"]:
        if c in df.columns:
            styler = safe_map(styler, lambda v: color_scale_3pt(v, -10, 0, 10), subset=[c])
    if "% Off RS High" in df.columns:
        styler = safe_map(styler, lambda v: color_scale_3pt(v, -15.0, -5.0, 0.0), subset=["% Off RS High"])
    for c in ["RS Trend (>50 SMA)", "> 10 EMA", "> 20 EMA", "> 50 SMA", "> 200 SMA"]:
        if c in df.columns:
            styler = safe_map(styler, color_binary_badge, subset=[c])
    try:
        styler = styler.hide(axis="index")
    except Exception:
        pass
    return styler

def style_rotation_tracker(df):
    styler = df.style
    sec_cols = [c for c in df.columns if c != "Date"]
    format_dict = {c: "{:.0f}" for c in sec_cols}
    styler = styler.format(format_dict, na_rep="N/A")

    num_sec = max(len(sec_cols), 1)
    mid_rank = max((num_sec // 2) + 1, 1)
    for c in sec_cols:
        styler = safe_map(
            styler,
            lambda v, ms=num_sec, mr=mid_rank: color_scale_3pt(
                v, 1, mr, ms, c_min=(99, 190, 123), c_mid=(255, 255, 255), c_max=(248, 105, 107)
            ),
            subset=[c],
        )
    try:
        styler = styler.hide(axis="index")
    except Exception:
        pass
    return styler

def is_circuit_stock_badge(row, bands_map):
    sym = str(row.get("name", "")).replace("🚨", "").strip().upper()
    band_val = bands_map.get(sym, "")
    if band_val in ["2", "5", "10"]:
        return True

    high = pd.to_numeric(row.get("high"), errors="coerce")
    low = pd.to_numeric(row.get("low"), errors="coerce")
    open_p = pd.to_numeric(row.get("open"), errors="coerce")
    close_p = pd.to_numeric(row.get("close"), errors="coerce")
    change_p = abs(pd.to_numeric(row.get("change"), errors="coerce"))

    if pd.notna(high) and pd.notna(low) and high == low and high > 0 and pd.notna(change_p) and change_p > 1.5:
        return True

    is_locked = (
        pd.notna(close_p) and pd.notna(high) and pd.notna(low)
        and (close_p == high or close_p == low) and (high != open_p)
    )
    if is_locked and ((1.97 <= change_p <= 2.00) or (4.97 <= change_p <= 5.00) or (9.97 <= change_p <= 10.00)):
        return True

    return False
