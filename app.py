import streamlit as st
from modules.config import TABLE_CUSTOM_CSS, INDIAN_SECTOR_HIERARCHY, EXHAUSTIVE_INDICES
from modules.state import init_session_state, save_filter_presets

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="StockHome",
    page_icon="📈",
    layout="wide",
)

st.markdown(TABLE_CUSTOM_CSS, unsafe_allow_html=True)

# Initialize all Session State variables from GitHub Gists
init_session_state()

st.title("📈 StockHome")
st.markdown(
    "Professional **CAN SLIM Screener**, **Hierarchical Sector Rotation**, "
    "**Multi-Watchlist Studio**, and **Tradebook Risk Journal**."
)

# ==========================================
# SIDEBAR CONTROLS & STRATEGY PRESETS
# ==========================================
st.sidebar.markdown("### 💾 Saved Filter Presets")
preset_names = list(st.session_state.filter_presets.keys())
selected_preset_name = st.sidebar.selectbox(
    "Load or Update Strategy Preset:",
    options=preset_names,
    index=0 if preset_names else None,
    key="sb_preset_selector",
)

col_load, col_update, col_del = st.sidebar.columns([1.2, 1.2, 0.9])
with col_load:
    if st.sidebar.button("⚡ Load", use_container_width=True, type="primary"):
        if selected_preset_name in st.session_state.filter_presets:
            p = st.session_state.filter_presets[selected_preset_name]
            st.session_state["f_exchanges"] = p.get("exchanges", ["NSE", "BSE"])
            st.session_state["f_sectors"] = p.get("sectors", [])
            st.session_state["f_industries"] = p.get("industries", [])
            st.session_state["f_indices"] = p.get("indices", [])
            st.session_state["f_min_mcap"] = p.get("min_mcap_cr", 1000)
            st.session_state["f_vol_period"] = p.get("vol_period_days", 60)
            st.session_state["f_min_vol"] = p.get("min_vol_cr", 5.0)
            st.session_state["f_en_ipo"] = p.get("en_ipo", False)
            st.session_state["f_ipo"] = p.get("ipo_filter", "All Stocks (No IPO Filter)")
            st.session_state["f_en_eps_q"] = p.get("en_eps_q", False)
            st.session_state["f_min_eps_q"] = p.get("min_eps_q", 10.0)
            st.session_state["f_en_sales_q"] = p.get("en_sales_q", False)
            st.session_state["f_min_sales_q"] = p.get("min_sales_q", 10.0)
            st.session_state["f_allow_na_growth"] = p.get("allow_na_growth", True)
            st.session_state["f_en_rs_rating"] = p.get("en_rs_rating", True)
            st.session_state["f_min_rs_rating"] = p.get("min_rs_rating", 80)
            st.session_state["f_en_adr"] = p.get("en_adr", True)
            st.session_state["f_min_adr"] = p.get("min_adr", 2.25)
            st.session_state["f_en_52l"] = p.get("en_above_52l", True)
            st.session_state["f_min_52l"] = p.get("min_above_52l", 20)
            st.session_state["f_en_52h"] = p.get("en_below_52h", True)
            st.session_state["f_max_52h"] = p.get("max_below_52h", 30)
            st.session_state["f_en_circuit"] = p.get("en_circuit", True)

            c_val = p.get("circuit_val", ["2%", "5%", "10%"])
            st.session_state["f_circuit_val"] = c_val if isinstance(c_val, list) else ["2%", "5%", "10%"]

            st.session_state["f_perf_labels"] = p.get("selected_perf_labels", ["1 Week", "1 Month", "3 Months", "6 Months"])
            st.session_state["f_max_res"] = p.get("max_results", 4000)

            ma_cfgs = p.get("ma_configs", [])
            for i, cfg in enumerate(ma_cfgs, 1):
                st.session_state[f"ma_{i}_en"] = cfg.get("en", False)
                st.session_state[f"ma_{i}_type"] = cfg.get("type", "SMA")
                st.session_state[f"ma_{i}_len"] = cfg.get("len", 50)

            perf_cfgs = p.get("perf_configs", {})
            for c_key, p_val in perf_cfgs.items():
                st.session_state[f"en_perf_{c_key}"] = p_val.get("en", False)
                st.session_state[f"val_perf_{c_key}"] = p_val.get("val", 0.0)

            st.success(f"Loaded '{selected_preset_name}'!")
            st.rerun()

with col_update:
    if st.sidebar.button("🔄 Update", use_container_width=True):
        if selected_preset_name in st.session_state.filter_presets:
            st.session_state.filter_presets[selected_preset_name] = {
                "exchanges": st.session_state.get("f_exchanges", ["NSE", "BSE"]),
                "sectors": st.session_state.get("f_sectors", []),
                "industries": st.session_state.get("f_industries", []),
                "indices": st.session_state.get("f_indices", []),
                "min_mcap_cr": st.session_state.get("f_min_mcap", 1000),
                "vol_period_days": st.session_state.get("f_vol_period", 60),
                "min_vol_cr": st.session_state.get("f_min_vol", 5.0),
                "en_ipo": st.session_state.get("f_en_ipo", False),
                "ipo_filter": st.session_state.get("f_ipo", "All Stocks (No IPO Filter)"),
                "en_eps_q": st.session_state.get("f_en_eps_q", False),
                "min_eps_q": st.session_state.get("f_min_eps_q", 10.0),
                "en_sales_q": st.session_state.get("f_en_sales_q", False),
                "min_sales_q": st.session_state.get("f_min_sales_q", 10.0),
                "allow_na_growth": st.session_state.get("f_allow_na_growth", True),
                "en_rs_rating": st.session_state.get("f_en_rs_rating", True),
                "min_rs_rating": st.session_state.get("f_min_rs_rating", 80),
                "en_adr": st.session_state.get("f_en_adr", True),
                "min_adr": st.session_state.get("f_min_adr", 2.25),
                "en_above_52l": st.session_state.get("f_en_52l", True),
                "min_above_52l": st.session_state.get("f_min_52l", 20),
                "en_below_52h": st.session_state.get("f_en_52h", True),
                "max_below_52h": st.session_state.get("f_max_52h", 30),
                "en_circuit": st.session_state.get("f_en_circuit", True),
                "circuit_val": st.session_state.get("f_circuit_val", ["2%", "5%", "10%"]),
                "selected_perf_labels": st.session_state.get("f_perf_labels", ["1 Week", "1 Month", "3 Months", "6 Months"]),
                "max_results": st.session_state.get("f_max_res", 4000),
                "ma_configs": [
                    {
                        "en": st.session_state.get(f"ma_{i}_en", False),
                        "type": st.session_state.get(f"ma_{i}_type", "SMA"),
                        "len": st.session_state.get(f"ma_{i}_len", 50),
                    }
                    for i in range(1, 6)
                ],
                "perf_configs": {
                    col: {
                        "en": st.session_state.get(f"en_perf_{col}", False),
                        "val": st.session_state.get(f"val_perf_{col}", 0.0),
                    }
                    for col in ["Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.YTD", "Perf.Y"]
                },
            }
            save_filter_presets(st.session_state.filter_presets)
            st.success(f"Updated '{selected_preset_name}'!")
            st.rerun()

with col_del:
    if st.sidebar.button("🗑️ Del", use_container_width=True):
        if len(preset_names) > 1 and selected_preset_name in st.session_state.filter_presets:
            del st.session_state.filter_presets[selected_preset_name]
            save_filter_presets(st.session_state.filter_presets)
            st.rerun()

with st.sidebar.expander("➕ Save Current Filters as New Preset"):
    with st.form("save_preset_form", clear_on_submit=True):
        new_preset_name = st.text_input("Preset Name:", placeholder="e.g., Breakout Momentum")
        if st.form_submit_button("💾 Save Preset", use_container_width=True):
            if new_preset_name:
                st.session_state.filter_presets[new_preset_name] = {
                    "exchanges": st.session_state.get("f_exchanges", ["NSE", "BSE"]),
                    "sectors": st.session_state.get("f_sectors", []),
                    "industries": st.session_state.get("f_industries", []),
                    "indices": st.session_state.get("f_indices", []),
                    "min_mcap_cr": st.session_state.get("f_min_mcap", 1000),
                    "vol_period_days": st.session_state.get("f_vol_period", 60),
                    "min_vol_cr": st.session_state.get("f_min_vol", 5.0),
                    "en_ipo": st.session_state.get("f_en_ipo", False),
                    "ipo_filter": st.session_state.get("f_ipo", "All Stocks (No IPO Filter)"),
                    "en_eps_q": st.session_state.get("f_en_eps_q", False),
                    "min_eps_q": st.session_state.get("f_min_eps_q", 10.0),
                    "en_sales_q": st.session_state.get("f_en_sales_q", False),
                    "min_sales_q": st.session_state.get("f_min_sales_q", 10.0),
                    "allow_na_growth": st.session_state.get("f_allow_na_growth", True),
                    "en_rs_rating": st.session_state.get("f_en_rs_rating", True),
                    "min_rs_rating": st.session_state.get("f_min_rs_rating", 80),
                    "en_adr": st.session_state.get("f_en_adr", True),
                    "min_adr": st.session_state.get("f_min_adr", 2.25),
                    "en_above_52l": st.session_state.get("f_en_52l", True),
                    "min_above_52l": st.session_state.get("f_min_52l", 20),
                    "en_below_52h": st.session_state.get("f_en_52h", True),
                    "max_below_52h": st.session_state.get("f_max_52h", 30),
                    "en_circuit": st.session_state.get("f_en_circuit", True),
                    "circuit_val": st.session_state.get("f_circuit_val", ["2%", "5%", "10%"]),
                    "selected_perf_labels": st.session_state.get("f_perf_labels", ["1 Week", "1 Month", "3 Months", "6 Months"]),
                    "max_results": st.session_state.get("f_max_res", 4000),
                    "ma_configs": [
                        {
                            "en": st.session_state.get(f"ma_{i}_en", False),
                            "type": st.session_state.get(f"ma_{i}_type", "SMA"),
                            "len": st.session_state.get(f"ma_{i}_len", 50),
                        }
                        for i in range(1, 6)
                    ],
                    "perf_configs": {
                        col: {
                            "en": st.session_state.get(f"en_perf_{col}", False),
                            "val": st.session_state.get(f"val_perf_{col}", 0.0),
                        }
                        for col in ["Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.YTD", "Perf.Y"]
                    },
                }
                save_filter_presets(st.session_state.filter_presets)
                st.success(f"Saved preset '{new_preset_name}'!")
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("⚡ **Auto-Update Enabled:** Adjusting any filter below updates results instantly.")

# ----------------------------------------------------
# 1. EXCHANGE & UNIVERSE
# ----------------------------------------------------
st.sidebar.header("1. Exchange & Universe")
st.sidebar.multiselect("Select Exchanges:", options=["NSE", "BSE"], default=st.session_state.get("f_exchanges", ["NSE", "BSE"]), key="f_exchanges")

st.sidebar.markdown("---")
st.sidebar.header("🏛️ Official NSE Filters & Indices")
sector_options = list(INDIAN_SECTOR_HIERARCHY.keys())
sector_choice = st.sidebar.multiselect("NSE Sector (22 Economic Sectors):", options=sector_options, default=st.session_state.get("f_sectors", []), key="f_sectors")

if sector_choice:
    industry_options = []
    for sec in sector_choice:
        industry_options.extend(INDIAN_SECTOR_HIERARCHY.get(sec, []))
    industry_options = sorted(list(set(industry_options)))
else:
    all_industries = [ind for inds in INDIAN_SECTOR_HIERARCHY.values() for ind in inds]
    industry_options = sorted(list(set(all_industries)))

st.sidebar.multiselect("NSE Industry (59 Distinct Classifications):", options=industry_options, default=st.session_state.get("f_industries", []), key="f_industries")
st.sidebar.multiselect("Index Membership (45+ Available):", options=EXHAUSTIVE_INDICES, default=st.session_state.get("f_indices", []), key="f_indices")

# ----------------------------------------------------
# 2. FUNDAMENTAL, LIQUIDITY & IPO DATE
# ----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("2. Fundamental, Liquidity & IPO Date")
st.sidebar.number_input("Min Market Cap (₹ Crores):", min_value=0, value=st.session_state.get("f_min_mcap", 1000), step=100, key="f_min_mcap")
st.sidebar.selectbox("Average Volume Period:", options=[10, 30, 60, 90], index=[10, 30, 60, 90].index(st.session_state.get("f_vol_period", 60)), format_func=lambda x: f"{x} Days", key="f_vol_period")
st.sidebar.number_input(f"Min Avg Rupee Volume (₹ Cr):", min_value=0.0, value=st.session_state.get("f_min_vol", 5.0), step=0.5, key="f_min_vol")

en_ipo = st.sidebar.checkbox("Filter by IPO Listing Age", value=st.session_state.get("f_en_ipo", False), key="f_en_ipo")
ipo_filter_options = [
    "All Stocks (No IPO Filter)", "Recent IPO: Past 1 Month", "Recent IPO: Past 3 Months", 
    "Recent IPO: Past 6 Months", "Recent IPO: Past 1 Year", "Recent IPO: Past 2 Years", 
    "Seasoned: Listed > 1 Year Ago", "Seasoned: Listed > 3 Years Ago", "Seasoned: Listed > 5 Years Ago"
]
st.sidebar.selectbox("IPO Date / Listing Age Filter:", options=ipo_filter_options, index=ipo_filter_options.index(st.session_state.get("f_ipo", "All Stocks (No IPO Filter)")), key="f_ipo", disabled=not en_ipo)

# ----------------------------------------------------
# 2B. QUARTERLY YOY FUNDAMENTAL GROWTH
# ----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("2B. Quarterly YoY Fundamental Growth")
en_eps_q = st.sidebar.checkbox("Filter by Min Quarterly YoY EPS Growth %", value=st.session_state.get("f_en_eps_q", False), key="f_en_eps_q")
st.sidebar.slider("Min Quarterly YoY EPS Growth %:", min_value=-50.0, max_value=200.0, value=float(st.session_state.get("f_min_eps_q", 10.0)), step=5.0, key="f_min_eps_q", disabled=not en_eps_q)
en_sales_q = st.sidebar.checkbox("Filter by Min Quarterly YoY Sales Growth %", value=st.session_state.get("f_en_sales_q", False), key="f_en_sales_q")
st.sidebar.slider("Min Quarterly YoY Sales Growth %:", min_value=-50.0, max_value=200.0, value=float(st.session_state.get("f_min_sales_q", 10.0)), step=5.0, key="f_min_sales_q", disabled=not en_sales_q)
st.sidebar.checkbox("Pass stocks with missing (N/A) TradingView growth data", value=st.session_state.get("f_allow_na_growth", True), key="f_allow_na_growth", help="TradingView sometimes lags on quarterly data for Indian small-caps. Checking this ensures great technical setups aren't dropped.")

# ----------------------------------------------------
# 3. TREND & MOVING AVERAGES (5 MAs)
# ----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("3. Trend & Moving Averages (5 MAs)")
default_ma_configs = [
    {"en": True, "type": "EMA", "len": 21},
    {"en": True, "type": "SMA", "len": 50},
    {"en": False, "type": "SMA", "len": 200},
    {"en": False, "type": "EMA", "len": 10},
    {"en": False, "type": "SMA", "len": 150},
]
for i, cfg in enumerate(default_ma_configs, 1):
    c1, c2, c3 = st.sidebar.columns([1.8, 1.6, 1.6])
    with c1: st.checkbox(f"MA {i} >", value=st.session_state.get(f"ma_{i}_en", cfg["en"]), key=f"ma_{i}_en")
    with c2: st.selectbox("Type", ["EMA", "SMA"], index=0 if st.session_state.get(f"ma_{i}_type", cfg["type"]) == "EMA" else 1, key=f"ma_{i}_type", label_visibility="collapsed")
    with c3: st.number_input("Len", min_value=1, max_value=500, value=st.session_state.get(f"ma_{i}_len", cfg["len"]), step=1, key=f"ma_{i}_len", label_visibility="collapsed")

# ----------------------------------------------------
# 4. VOLATILITY & 52-WEEK RANGE
# ----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("4. Volatility & 52-Week Range")
en_adr = st.sidebar.checkbox("Filter by Min ADR %", value=st.session_state.get("f_en_adr", True), key="f_en_adr")
st.sidebar.slider("Min ADR % (TradingView Standard):", min_value=0.0, max_value=10.0, value=st.session_state.get("f_min_adr", 2.25), step=0.25, key="f_min_adr", disabled=not en_adr)
en_52l = st.sidebar.checkbox("Filter by Min % Above 52-Week Low", value=st.session_state.get("f_en_52l", True), key="f_en_52l")
st.sidebar.slider("Min % Above 52-Week Low:", min_value=0, max_value=100, value=st.session_state.get("f_min_52l", 20), step=5, key="f_min_52l", disabled=not en_52l)
en_52h = st.sidebar.checkbox("Filter by Max % Below 52-Week High", value=st.session_state.get("f_en_52h", True), key="f_en_52h")
st.sidebar.slider("Max % Below 52-Week High:", min_value=0, max_value=50, value=st.session_state.get("f_max_52h", 30), step=5, key="f_max_52h", disabled=not en_52h)

# ----------------------------------------------------
# 4B. CIRCUIT LIMIT PROTECTION
# ----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("4B. Circuit Limit Protection")
c_cb, c_sb = st.sidebar.columns([1.1, 1.4])
with c_cb:
    en_circuit = st.checkbox("Exclude Circuit:", value=st.session_state.get("f_en_circuit", True), key="f_en_circuit")
with c_sb:
    default_circuits = st.session_state.get("f_circuit_val", ["2%", "5%", "10%"])
    if isinstance(default_circuits, str): default_circuits = ["2%", "5%", "10%"]
    st.multiselect("Circuit Bands to Exclude:", options=["2%", "5%", "10%"], default=default_circuits, key="f_circuit_val", disabled=not en_circuit, label_visibility="collapsed")

# ----------------------------------------------------
# 5. PERFORMANCE % & IBD RS RATING
# ----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("5. Performance % & IBD RS Rating")
en_rs_rating = st.sidebar.checkbox("Filter by Min IBD RS Rating (1-99)", value=st.session_state.get("f_en_rs_rating", True), key="f_en_rs_rating")
st.sidebar.slider("Min IBD RS Rating (1-99 Market Percentile):", min_value=1, max_value=99, value=st.session_state.get("f_min_rs_rating", 80), step=1, key="f_min_rs_rating", disabled=not en_rs_rating)

perf_options = {
    "1 Week": ("Perf.W", "Perf % 1W"), "1 Month": ("Perf.1M", "Perf % 1M"),
    "3 Months": ("Perf.3M", "Perf % 3M"), "6 Months": ("Perf.6M", "Perf % 6M"),
    "YTD": ("Perf.YTD", "Perf % YTD"), "1 Year": ("Perf.Y", "Perf % 1Y"),
}
st.sidebar.multiselect("Display Perf % Columns in Table:", options=list(perf_options.keys()), default=st.session_state.get("f_perf_labels", ["1 Week", "1 Month", "3 Months", "6 Months"]), key="f_perf_labels")

st.sidebar.caption("Optional Minimum Performance % Thresholds:")
p_cols = st.sidebar.columns(2)
for idx, (label, (tv_col, disp_label)) in enumerate(perf_options.items()):
    with p_cols[idx % 2]:
        st.checkbox(f"Min {label} >", value=st.session_state.get(f"en_perf_{tv_col}", False), key=f"en_perf_{tv_col}")
        st.number_input(f"Min % ({label})", min_value=-100.0, max_value=10000.0, value=st.session_state.get(f"val_perf_{tv_col}", 0.0), step=5.0, key=f"val_perf_{tv_col}", label_visibility="collapsed")

# ----------------------------------------------------
# 6. DISPLAY SETTINGS
# ----------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.header("6. Display Settings")
st.sidebar.slider("Max Results to Fetch:", min_value=1000, max_value=5000, value=st.session_state.get("f_max_res", 4000), step=250, key="f_max_res")

# ==========================================
# RENDER MAIN TABS
# ==========================================
tab_screener, tab_watchlists, tab_tradebook, tab_market_health = st.tabs([
    "🔎 CAN SLIM Screener & Rotation",
    "⭐ Multi-Watchlist Studio & TV Free-Tier Bridge",
    "📓 Tradebook & Portfolio Journal",
    "🏥 Market Health & Sector Rotation",
])

# Import and execute tab components
from tabs.screener_tab import render_screener_tab
from tabs.watchlist_tab import render_watchlist_tab
from tabs.tradebook_tab import render_tradebook_tab
from tabs.market_health_tab import render_market_health_tab

with tab_screener:
    render_screener_tab()

with tab_watchlists:
    render_watchlist_tab()

with tab_tradebook:
    render_tradebook_tab()

with tab_market_health:
    render_market_health_tab()
