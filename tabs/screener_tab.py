import time
import math
import pandas as pd
import plotly.express as px
import streamlit as st
from modules.config import map_to_indian_classification, parse_chart_selection_multi, parse_table_selection_multi
from modules.data import (
    fetch_screener_data, get_nse_circuit_bands, coalesce_columns, 
    add_clean_ipo_date_col, EPS_Q_ALIASES, SALES_Q_ALIASES
)
from modules.styling import get_left_aligned_column_config
from modules.ai_analyst import show_fundamental_modal, run_gemini_fundamental_analysis
from modules.state import save_watchlists

def render_screener_tab():
    # 1. Retrieve Sidebar Filters from Session State
    exchange_choice = st.session_state.get("f_exchanges", ["NSE", "BSE"])
    sector_choice = st.session_state.get("f_sectors", [])
    industry_choice = st.session_state.get("f_industries", [])
    index_choice = st.session_state.get("f_indices", [])
    min_mcap_cr = st.session_state.get("f_min_mcap", 1000)
    vol_period_days = st.session_state.get("f_vol_period", 60)
    min_vol_cr = st.session_state.get("f_min_vol", 5.0)
    en_ipo = st.session_state.get("f_en_ipo", False)
    ipo_filter_choice = st.session_state.get("f_ipo", "All Stocks (No IPO Filter)")
    en_eps_q = st.session_state.get("f_en_eps_q", False)
    min_eps_q = float(st.session_state.get("f_min_eps_q", 10.0))
    en_sales_q = st.session_state.get("f_en_sales_q", False)
    min_sales_q = float(st.session_state.get("f_min_sales_q", 10.0))
    allow_na_growth = st.session_state.get("f_allow_na_growth", True)
    en_rs_rating = st.session_state.get("f_en_rs_rating", True)
    min_rs_rating = st.session_state.get("f_min_rs_rating", 80)
    en_adr = st.session_state.get("f_en_adr", True)
    min_adr = st.session_state.get("f_min_adr", 2.25)
    en_52l = st.session_state.get("f_en_52l", True)
    min_above_52l = st.session_state.get("f_min_52l", 20)
    en_52h = st.session_state.get("f_en_52h", True)
    max_below_52h = st.session_state.get("f_max_52h", 30)
    en_circuit = st.session_state.get("f_en_circuit", True)
    circuit_choice = st.session_state.get("f_circuit_val", ["2%", "5%", "10%"])
    selected_perf_labels = st.session_state.get("f_perf_labels", ["1 Week", "1 Month", "3 Months", "6 Months"])
    max_results = st.session_state.get("f_max_res", 4000)

    # Construct Dynamic Filters
    ma_filters = []
    for i in range(1, 6):
        en = st.session_state.get(f"ma_{i}_en", False)
        m_type = st.session_state.get(f"ma_{i}_type", "SMA")
        m_len = st.session_state.get(f"ma_{i}_len", 50)
        ma_filters.append({
            "enabled": en, "type": m_type, "length": m_len,
            "col_name": f"{m_type}{m_len}", "label": f"{m_type} {m_len}"
        })
    
    perf_options = {
        "1 Week": ("Perf.W", "Perf % 1W"), "1 Month": ("Perf.1M", "Perf % 1M"),
        "3 Months": ("Perf.3M", "Perf % 3M"), "6 Months": ("Perf.6M", "Perf % 6M"),
        "YTD": ("Perf.YTD", "Perf % YTD"), "1 Year": ("Perf.Y", "Perf % 1Y"),
    }
    perf_filters = []
    for label, (tv_col, disp_label) in perf_options.items():
        en_p = st.session_state.get(f"en_perf_{tv_col}", False)
        min_val = st.session_state.get(f"val_perf_{tv_col}", 0.0)
        perf_filters.append({
            "enabled": en_p, "label": label, "col_name": tv_col,
            "display_label": disp_label, "min_val": min_val
        })

    ma_cols_to_fetch = list(set([m["col_name"] for m in ma_filters]))
    tv_vol_col = f"average_volume_{vol_period_days}d_calc"

    with st.spinner("⚡ Scanning Indian Equities & Applying Active Filters..."):
        results_df = fetch_screener_data(
            exchange_choice, min_mcap_cr, vol_period_days, ma_cols_to_fetch, max_results
        )
        nse_bands_map = get_nse_circuit_bands()

        if not results_df.empty:
            p_3m = pd.to_numeric(results_df.get("Perf.3M"), errors="coerce").fillna(0)
            p_6m = pd.to_numeric(results_df.get("Perf.6M"), errors="coerce").fillna(0)
            p_1y = pd.to_numeric(results_df.get("Perf.Y"), errors="coerce").fillna(0)

            results_df["_ibd_raw_score"] = (2 * p_3m) + p_6m + p_1y
            rs_pct = results_df["_ibd_raw_score"].rank(pct=True, na_option="keep")
            results_df["RS Rating"] = ((rs_pct * 98 + 1).round().fillna(1).astype(int))

            st.session_state.rs_rating_map = dict(
                zip(results_df["name"].str.upper(), results_df["RS Rating"])
            )

    if results_df.empty:
        st.warning("No stocks matched your criteria. Adjust your sidebar filters or switch to another Preset.")
    else:
        df = results_df.copy()
        df = df[df["exchange"].isin(exchange_choice)]
        if "type" in df.columns:
            df = df[df["type"] == "stock"]
        df = df.drop_duplicates(subset=["name"], keep="first")

        mapped_sectors, mapped_industries = [], []
        for _, row in df.iterrows():
            sec, ind = map_to_indian_classification(row.get("industry", ""), row.get("sector", ""))
            mapped_sectors.append(sec)
            mapped_industries.append(ind)
        df["Sector"] = mapped_sectors
        df["Industry"] = mapped_industries

        total_sector_counts = df["Sector"].value_counts()
        total_industry_counts = df["Industry"].value_counts()

        if sector_choice: df = df[df["Sector"].isin(sector_choice)]
        if industry_choice: df = df[df["Industry"].isin(industry_choice)]

        if "index" in df.columns:
            df["Index"] = df["index"].fillna("N/A")
        else:
            df["Index"] = "N/A"

        if index_choice:
            def matches_index(val):
                if pd.isna(val) or val == "N/A" or not val: return False
                val_str = str(val).upper()
                for idx_name in index_choice:
                    if idx_name.upper() in val_str: return True
                return False
            df = df[df["Index"].apply(matches_index)]

        df["EPS Q YoY %"] = coalesce_columns(df, EPS_Q_ALIASES).round(2)
        df["Sales Q YoY %"] = coalesce_columns(df, SALES_Q_ALIASES).round(2)

        if en_eps_q:
            if allow_na_growth:
                df = df[(df["EPS Q YoY %"] >= min_eps_q) | (df["EPS Q YoY %"].isna())]
            else:
                df = df[df["EPS Q YoY %"] >= min_eps_q]

        if en_sales_q:
            if allow_na_growth:
                df = df[(df["Sales Q YoY %"] >= min_sales_q) | (df["Sales Q YoY %"].isna())]
            else:
                df = df[df["Sales Q YoY %"] >= min_sales_q]

        if en_rs_rating and "RS Rating" in df.columns:
            df = df[df["RS Rating"] >= min_rs_rating]

        df = add_clean_ipo_date_col(df)

        if en_ipo and ipo_filter_choice != "All Stocks (No IPO Filter)":
            now_dt = pd.Timestamp.now()
            if ipo_filter_choice == "Recent IPO: Past 1 Month":
                df = df[df["IPO_Date_DT"] >= now_dt - pd.DateOffset(months=1)]
            elif ipo_filter_choice == "Recent IPO: Past 3 Months":
                df = df[df["IPO_Date_DT"] >= now_dt - pd.DateOffset(months=3)]
            elif ipo_filter_choice == "Recent IPO: Past 6 Months":
                df = df[df["IPO_Date_DT"] >= now_dt - pd.DateOffset(months=6)]
            elif ipo_filter_choice == "Recent IPO: Past 1 Year":
                df = df[df["IPO_Date_DT"] >= now_dt - pd.DateOffset(years=1)]
            elif ipo_filter_choice == "Recent IPO: Past 2 Years":
                df = df[df["IPO_Date_DT"] >= now_dt - pd.DateOffset(years=2)]
            elif ipo_filter_choice == "Seasoned: Listed > 1 Year Ago":
                df = df[(df["IPO_Date_DT"] < now_dt - pd.DateOffset(years=1)) | (df["IPO Date"] == "N/A")]
            elif ipo_filter_choice == "Seasoned: Listed > 3 Years Ago":
                df = df[(df["IPO_Date_DT"] < now_dt - pd.DateOffset(years=3)) | (df["IPO Date"] == "N/A")]
            elif ipo_filter_choice == "Seasoned: Listed > 5 Years Ago":
                df = df[(df["IPO_Date_DT"] < now_dt - pd.DateOffset(years=5)) | (df["IPO Date"] == "N/A")]

        numeric_cols = [
            "market_cap_basic", "close", "change", "high", "low", "open",
            "volume", tv_vol_col, "ADR", "price_52_week_high", "price_52_week_low",
        ] + ma_cols_to_fetch
        for c in numeric_cols:
            if c in df.columns: df[c] = pd.to_numeric(df[c], errors="coerce")

        df["ADR_pct"] = (df["ADR"] / df["close"]) * 100
        if en_adr: df = df[df["ADR_pct"] >= min_adr]

        for ma in ma_filters:
            c_name = ma["col_name"]
            if ma["enabled"] and c_name in df.columns:
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df[c_name] = pd.to_numeric(df[c_name], errors="coerce")
                df = df[df["close"] > df[c_name]]

        if tv_vol_col in df.columns:
            df["val_traded_inr"] = df["close"] * df[tv_vol_col]
            df = df[df["val_traded_inr"] >= (min_vol_cr * 10_000_000)]

        if "price_52_week_low" in df.columns:
            pct_above_low = ((df["close"] - df["price_52_week_low"]) / df["price_52_week_low"]) * 100
            if en_52l: df = df[pct_above_low >= min_above_52l]

        if "price_52_week_high" in df.columns:
            pct_below_high = ((df["price_52_week_high"] - df["close"]) / df["price_52_week_high"]) * 100
            if en_52h: df = df[pct_below_high <= max_below_52h]

        for pf in perf_filters:
            if pf["enabled"] and pf["col_name"] in df.columns:
                df[pf["col_name"]] = pd.to_numeric(df[pf["col_name"]], errors="coerce")
                df = df[df[pf["col_name"]] >= pf["min_val"]]

        if en_circuit and circuit_choice:
            df["high"] = pd.to_numeric(df["high"], errors="coerce")
            df["low"] = pd.to_numeric(df["low"], errors="coerce")
            df["open"] = pd.to_numeric(df["open"], errors="coerce")
            df["change_abs"] = df["change"].abs()

            is_full_day_freeze = df["high"] == df["low"]
            is_at_high_lock = (df["close"] == df["high"]) & (df["high"] > df["open"])
            is_at_low_lock = (df["close"] == df["low"]) & (df["low"] < df["open"])
            is_locked_extreme = is_at_high_lock | is_at_low_lock

            selected_band_nums = [b.replace("%", "") for b in circuit_choice]

            def is_circuit_hit(row):
                sym = str(row["name"]).strip().upper()
                band_val = nse_bands_map.get(sym, "")
                c_abs = row["change_abs"]
                is_locked = row["high"] == row["low"] or (
                    (row["close"] == row["high"] or row["close"] == row["low"]) and row["high"] != row["open"]
                )
                if band_val in selected_band_nums: return True
                if is_locked:
                    if "2" in selected_band_nums and 1.97 <= c_abs <= 2.00: return True
                    if "5" in selected_band_nums and 4.97 <= c_abs <= 5.00: return True
                    if "10" in selected_band_nums and 9.97 <= c_abs <= 10.00: return True
                return False

            df["_is_circuit_excluded"] = df.apply(is_circuit_hit, axis=1)
            df = df[~df["_is_circuit_excluded"] & ~is_full_day_freeze]
            df = df.drop(columns=["_is_circuit_excluded"])

        if df.empty:
            st.warning("No stocks passed all criteria. Try broadening your NSE Sector/Industry selections or RS Rating slider.")
        else:
            total_passed = len(df)
            rc = st.session_state.reset_counter

            st.subheader("📊 Scan Summary & Market Rotation")
            tab_sector_sum, tab_industry_sum = st.tabs(["🛠️ Sector Summary", "🏢 Basic Industry Summary"])

            with tab_sector_sum:
                sec_counts = df["Sector"].value_counts().reset_index()
                sec_counts.columns = ["Sector", "Stocks Passed"]
                sec_counts["% Share"] = ((sec_counts["Stocks Passed"] / total_passed) * 100).round(1)
                sec_counts["% of Sector Total"] = sec_counts.apply(
                    lambda r: round((r["Stocks Passed"] / total_sector_counts.get(r["Sector"], 1)) * 100, 1), axis=1
                )
                c_chart1, c_table1 = st.columns([1.1, 1.3])
                with c_chart1:
                    fig_sec = px.pie(sec_counts, names="Sector", values="Stocks Passed", hole=0.55)
                    fig_sec.update_traces(textinfo="percent", textposition="inside")
                    fig_sec.update_layout(
                        annotations=[dict(text=f"<b>Total Stocks:<br>{total_passed}</b>", x=0.5, y=0.5, font_size=16, showarrow=False)],
                        showlegend=False, margin=dict(t=20, b=10, l=20, r=20), height=360,
                    )
                    chart_ev_sec = st.plotly_chart(fig_sec, use_container_width=True, on_select="rerun", selection_mode="points", key=f"sec_chart_{rc}")
                with c_table1:
                    table_ev_sec = st.dataframe(
                        sec_counts, use_container_width=True, hide_index=True, height=360, on_select="rerun",
                        selection_mode="multi-row", column_config=get_left_aligned_column_config(sec_counts.columns), key=f"sec_table_{rc}"
                    )
                sel_sec_chart = parse_chart_selection_multi(chart_ev_sec)
                sel_sec_table = parse_table_selection_multi(table_ev_sec, sec_counts, "Sector")
                active_sectors = sel_sec_table if sel_sec_table else sel_sec_chart

            with tab_industry_sum:
                if active_sectors:
                    df_ind_source = df[df["Sector"].isin(active_sectors)]
                    ind_total_passed = len(df_ind_source)
                    st.info(f"🏢 **Hierarchical View:** Showing Basic Industries inside **{', '.join(active_sectors)}** ({ind_total_passed} Stocks)")
                else:
                    df_ind_source = df
                    ind_total_passed = total_passed
                ind_counts = df_ind_source["Industry"].value_counts().reset_index()
                ind_counts.columns = ["Basic Industry", "Stocks Passed"]
                ind_counts["% Share"] = ((ind_counts["Stocks Passed"] / max(ind_total_passed, 1)) * 100).round(1)
                ind_counts["% of Industry Total"] = ind_counts.apply(
                    lambda r: round((r["Stocks Passed"] / total_industry_counts.get(r["Basic Industry"], 1)) * 100, 1), axis=1
                )
                sec_hash = "_".join(sorted(active_sectors)) if active_sectors else "all"
                c_chart2, c_table2 = st.columns([1.1, 1.3])
                with c_chart2:
                    fig_ind = px.pie(ind_counts, names="Basic Industry", values="Stocks Passed", hole=0.55)
                    fig_ind.update_traces(textinfo="percent", textposition="inside")
                    fig_ind.update_layout(
                        annotations=[dict(text=f"<b>Total Stocks:<br>{ind_total_passed}</b>", x=0.5, y=0.5, font_size=16, showarrow=False)],
                        showlegend=False, margin=dict(t=20, b=10, l=20, r=20), height=360,
                    )
                    chart_ev_ind = st.plotly_chart(fig_ind, use_container_width=True, on_select="rerun", selection_mode="points", key=f"ind_chart_{rc}_{sec_hash}")
                with c_table2:
                    table_ev_ind = st.dataframe(
                        ind_counts, use_container_width=True, hide_index=True, height=360, on_select="rerun",
                        selection_mode="multi-row", column_config=get_left_aligned_column_config(ind_counts.columns), key=f"ind_table_{rc}_{sec_hash}"
                    )
                sel_ind_chart = parse_chart_selection_multi(chart_ev_ind)
                sel_ind_table = parse_table_selection_multi(table_ev_ind, ind_counts, "Basic Industry")
                active_industries = sel_ind_table if sel_ind_table else sel_ind_chart

            st.session_state.active_scan_summary = {
                "total_passed": total_passed,
                "sectors": sec_counts.head(10).to_dict(orient="records"),
                "industries": ind_counts.head(10).to_dict(orient="records"),
            }

            st.markdown("---")
            df_display = df.copy()
            if active_sectors: df_display = df_display[df_display["Sector"].isin(active_sectors)]
            if active_industries: df_display = df_display[df_display["Industry"].isin(active_industries)]

            if active_sectors or active_industries:
                filter_labels = []
                if active_sectors: filter_labels.append(f"**Sector:** {', '.join(active_sectors)}")
                if active_industries: filter_labels.append(f"**Industry:** {', '.join(active_industries)}")
                col_info, col_reset = st.columns([3, 1])
                with col_info: st.info(f"🔍 **Active Drilldown:** {' | '.join(filter_labels)} ({len(df_display)} Stocks)")
                with col_reset:
                    if st.button("🔄 Reset Scan Results (Show All)", type="primary", use_container_width=True):
                        st.session_state.reset_counter += 1
                        st.rerun()

            df_display["Market Cap (₹ Cr)"] = (df_display["market_cap_basic"] / 10_000_000).round(2)
            vol_display_label = f"{vol_period_days}D Close×AvgVol (₹ Cr)"
            df_display[vol_display_label] = (df_display["val_traded_inr"] / 10_000_000).round(2)
            df_display["Close"] = df_display["close"].round(2)
            df_display["Change %"] = df_display["change"].round(2)
            df_display["ADR %"] = df_display["ADR_pct"].round(2)
            df_display["TV_Symbol"] = df_display["exchange"] + ":" + df_display["name"]
            df_display["TV_Link"] = "https://www.tradingview.com/chart/?symbol=NSE:" + df_display["name"]
            df_display["Screener_Link"] = "https://www.screener.in/company/" + df_display["name"] + "/consolidated/"

            wl_dot_map = {}
            for wl_name, sym_list in st.session_state.watchlists.items():
                wl_lower = wl_name.lower()
                
                if "breakout" in wl_lower:
                    dot = "🔵"
                elif "weekly" in wl_lower:
                    dot = "🟡"
                elif "focus" in wl_lower:
                    dot = "🟢"
                elif "bulk" in wl_lower:
                    dot = "🟠"
                elif "sold" in wl_lower:
                    dot = "🔴"
                else:
                    dot = "🟣"
                    
                for s in sym_list:
                    bare_s = s.split(":")[-1].strip().upper()
                    if dot not in wl_dot_map.get(bare_s, ""):
                        wl_dot_map[bare_s] = wl_dot_map.get(bare_s, "") + dot

            df_display["WL_Dots"] = df_display["name"].str.upper().map(wl_dot_map).fillna("")

            df_display["_in_band"] = df_display["name"].str.upper().map(nse_bands_map)
            cond1 = df_display["_in_band"].isin(["2", "5", "10"])
            cond2 = ((df_display["high"] == df_display["low"]) & (df_display["high"] > 0) & (df_display["change"].abs() > 1.5))
            df_display["_is_circuit_badge"] = cond1 | cond2
            df_display["name"] = df_display["name"].where(~df_display["_is_circuit_badge"], df_display["name"] + " 🚨")

            def format_v(v_str):
                if v_str == "PASS 🟢": return "🟢 PASS"
                if v_str == "WATCHLIST 🟡": return "🟡 WATCHLIST"
                if v_str == "FAIL 🔴": return "🔴 FAIL"
                return v_str

            fund_badge_map = {k: f"{format_v(v.get('verdict', ''))} ({v.get('date', '')})" for k, v in st.session_state.fundamental_reports.items()}
            df_display["Fundamental"] = df_display["name"].str.replace(" 🚨", "").str.upper().map(fund_badge_map).fillna("⚪ Not Analyzed")

            canonical_perf_order = ["Perf % 1W", "Perf % 1M", "Perf % 3M", "Perf % 6M", "Perf % YTD", "Perf % 1Y"]
            for label, (tv_col, disp_label) in perf_options.items():
                if tv_col in df_display.columns:
                    df_display[disp_label] = pd.to_numeric(df_display[tv_col], errors="coerce").round(2)

            active_perf_labels = [p for p in canonical_perf_order if p in [perf_options[lbl][1] for lbl in selected_perf_labels] and p in df_display.columns]
            active_ma_labels = []
            for ma in ma_filters:
                if ma["enabled"] and ma["col_name"] in df_display.columns:
                    df_display[ma["label"]] = df_display[ma["col_name"]].round(2)
                    active_ma_labels.append(ma["label"])

            table_columns = (
                ["S.No.", "TV_Symbol", "name", "RS Rating", "Fundamental", "Close", "Change %", "ADR %", "EPS Q YoY %", "Sales Q YoY %"]
                + active_perf_labels + active_ma_labels
                + [vol_display_label, "Market Cap (₹ Cr)", "IPO Date", "Sector", "Industry", "TV_Link", "Screener_Link"]
            )

            sc = st.session_state.scan_sel_counter
            wl_names = list(st.session_state.watchlists.keys())

            # --- UNIFIED CONTROL BAR DIRECTLY ABOVE TABLE ---
            col_inc, col_exc = st.columns(2)
            with col_inc:
                cross_filter_wls = st.multiselect(
                    "🔍 Include ONLY stocks present in:", 
                    options=wl_names, 
                    key=f"scan_filter_inc_{rc}_{sc}"
                )
            with col_exc:
                exclude_wls = st.multiselect(
                    "🚫 Exclude stocks present in:", 
                    options=["[ALL WATCHLISTS]"] + wl_names, 
                    key=f"scan_filter_exc_{rc}_{sc}"
                )

            sort_options = ["Original Scan Order", "RS Rating", "Change %", "ADR %", "Close", "Market Cap (₹ Cr)", "EPS Q YoY %", "Sales Q YoY %"]
            for p_lbl in active_perf_labels:
                if p_lbl not in sort_options:
                    sort_options.insert(1, p_lbl) # Put performance labels near the top

            st.write("") 
            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns([1.6, 0.9, 1.0, 1.0, 1.8])
            with col_s1:
                sort_by = st.selectbox("🔀 Sort Results By:", options=sort_options, index=0, key=f"scan_sort_{rc}_{sc}")
            with col_s2:
                st.write("")
                st.write("")
                sort_asc = st.checkbox("Ascending Order", value=False, key=f"scan_asc_{rc}_{sc}")
            with col_s3:
                st.write("")
                st.write("")
                en_top_pct = st.checkbox(
                    "🎯 Top % Only", 
                    value=False, 
                    key=f"scan_top_pct_en_{rc}_{sc}",
                    help="Filter down to only the top X% of stocks based on your chosen sort."
                )
            with col_s4:
                top_pct_val = st.number_input(
                    "Top % Limit:", 
                    min_value=0.1, 
                    max_value=100.0, 
                    value=2.0, 
                    step=0.5, 
                    disabled=not en_top_pct, 
                    key=f"scan_top_pct_val_{rc}_{sc}"
                )
            with col_s5:
                cross_metric_exc = st.multiselect(
                    "🚫 Exclude Top % from:",
                    options=active_perf_labels,
                    disabled=not en_top_pct,
                    key=f"scan_cross_metric_exc_{rc}_{sc}",
                    help="Automatically calculates the Top X% of the selected metrics and removes those stocks from your current view to prevent overlap."
                )

            # Apply Watchlist Cross-Filter (INCLUDE)
            if cross_filter_wls:
                valid_symbols = set()
                for f_wl in cross_filter_wls:
                    valid_symbols.update([s.split(":")[-1].strip().upper() for s in st.session_state.watchlists.get(f_wl, [])])
                df_display = df_display[df_display["name"].isin(valid_symbols)]
                
            # Apply Watchlist Cross-Filter (EXCLUDE)
            if exclude_wls:
                exclude_symbols = set()
                wls_to_check = wl_names if "[ALL WATCHLISTS]" in exclude_wls else exclude_wls
                for f_wl in wls_to_check:
                    if f_wl in st.session_state.watchlists:
                        exclude_symbols.update([s.split(":")[-1].strip().upper() for s in st.session_state.watchlists[f_wl]])
                df_display = df_display[~df_display["name"].isin(exclude_symbols)]

            total_before_slice = len(df_display)

            # Apply Cross-Metric Momentum Exclusions (Background calculation)
            if en_top_pct and total_before_slice > 0 and cross_metric_exc:
                num_to_keep = max(1, int(math.ceil(total_before_slice * (top_pct_val / 100.0))))
                cross_exclude_symbols = set()
                
                for metric in cross_metric_exc:
                    if metric in df_display.columns:
                        temp_top = df_display.sort_values(by=metric, ascending=False, na_position="last").head(num_to_keep)
                        cross_exclude_symbols.update(temp_top['name'].tolist())
                
                df_display = df_display[~df_display['name'].isin(cross_exclude_symbols)]
                if len(cross_exclude_symbols) > 0:
                    st.info(f"🚀 **Momentum Overlap Excluder:** Automatically removed {len(cross_exclude_symbols)} stocks that already appeared in the Top {top_pct_val}% of your selected exclusion metrics.")

            # Apply Primary Sorting
            if sort_by != "Original Scan Order" and sort_by in df_display.columns:
                temp_col = "_temp_sort_col"
                df_display[temp_col] = pd.to_numeric(df_display[sort_by], errors="coerce")
                df_display = df_display.sort_values(by=temp_col, ascending=sort_asc, na_position="last").drop(columns=[temp_col])

            # Apply Top % Slicing to the remaining pool
            if en_top_pct and total_before_slice > 0:
                num_to_keep = max(1, int(math.ceil(total_before_slice * (top_pct_val / 100.0))))
                df_display = df_display.head(num_to_keep)
                results_heading = f"📋 Scan Results ({len(df_display)} Fresh Stocks Shown — Top {top_pct_val}% Quota)"
            else:
                results_heading = f"📋 Scan Results ({len(df_display)} Stocks Found)"

            # Assign sequential S.No. post-sorting & slicing
            df_display["S.No._num"] = range(1, len(df_display) + 1)
            df_display["S.No."] = df_display.apply(lambda r: f"{r['S.No._num']} {r['WL_Dots']}".strip() if r["WL_Dots"] else str(r["S.No._num"]), axis=1)

            st.subheader(results_heading)
            st.caption("💡 **RS Rating:** IBD-Style 1-99 Percentile Score calculated across 4,000+ listed Indian equities before filters.")

            table_ev_scan = st.dataframe(
                df_display[table_columns], use_container_width=True, hide_index=True, on_select="rerun",
                selection_mode="multi-row", column_config=get_left_aligned_column_config(table_columns), key=f"scan_table_{rc}_{sc}"
            )

            selected_rows = parse_table_selection_multi(table_ev_scan, df_display, "TV_Symbol")

            st.markdown("---")
            f_col1, f_col2, f_col3 = st.columns([2.0, 1.3, 1.7])
            with f_col1:
                if len(selected_rows) == 1:
                    active_sym = selected_rows[0]
                    clean_sym_name = active_sym.split(":")[-1].strip().upper()
                    if st.button(f"📖 Open Saved Report Modal ({clean_sym_name})", type="primary", use_container_width=True, key=f"fund_btn_view_scan_{rc}_{sc}"):
                        show_fundamental_modal(active_sym)
                else:
                    st.button("📖 Select a Single Stock Row to Open Report", type="secondary", disabled=True, use_container_width=True, key=f"fund_btn_view_scan_dis_{rc}_{sc}")
            with f_col2:
                force_reanalyze_scan = st.checkbox("Force Re-Analyze Existing", value=False, key=f"force_scan_{rc}_{sc}", help="If checked, AI will re-fetch data even if a report already exists.")
            with f_col3:
                run_batch_scan = st.button(f"⚡ Analyze Selected ({len(selected_rows)})", type="primary", use_container_width=True, disabled=len(selected_rows) == 0, key=f"fund_btn_run_scan_{rc}_{sc}")

            if run_batch_scan and len(selected_rows) > 0:
                with st.status("🧠 Minervini Fundamental AI Analyst — Active Queue", expanded=True) as status_box:
                    p_bar = st.progress(0.0)
                    for idx, sym in enumerate(selected_rows):
                        clean_sym = sym.split(":")[-1].strip().upper()
                        if clean_sym in st.session_state.fundamental_reports and not force_reanalyze_scan:
                            status_box.write(f"⏩ **[{idx + 1}/{len(selected_rows)}] {clean_sym}:** Report already exists in Gist.")
                        else:
                            status_box.write(f"⚙️ **[{idx + 1}/{len(selected_rows)}] {clean_sym}:** Extracting live data & Running AI...")
                            run_gemini_fundamental_analysis(clean_sym, st.session_state.fundamental_reports, status_log=status_box)
                        p_bar.progress((idx + 1) / len(selected_rows))
                    status_box.update(label="✅ Batch AI Analysis Complete! Updating Table...", state="complete", expanded=True)
                    time.sleep(1.5)
                    st.rerun()

            st.markdown("---")
            cw1, cw2, cw3, cw4 = st.columns([1.8, 1.5, 2.0, 0.9])
            with cw1:
                target_wl = st.selectbox("Select Target Watchlist to Add Setups:", options=wl_names, index=(wl_names.index(st.session_state.active_watchlist_name) if st.session_state.active_watchlist_name in wl_names else 0), key="wl_table_target_select")
            with cw2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button(f"➕ Add Selected ({len(selected_rows)}) to Watchlist", type="primary", use_container_width=True, disabled=len(selected_rows) == 0):
                    current_list = st.session_state.watchlists[target_wl]
                    added_cnt = 0
                    for sym in selected_rows:
                        if sym not in current_list:
                            current_list.append(sym)
                            added_cnt += 1
                    save_watchlists(st.session_state.watchlists)
                    st.success(f"✅ Successfully added {added_cnt} new stocks to **{target_wl}**!")
            with cw3:
                st.caption("➕ Create New Watchlist:")
                with st.form("create_wl_scan_form", clear_on_submit=True):
                    fc1, fc2 = st.columns([1.7, 1.0])
                    with fc1: new_scan_wl = st.text_input("Create New Watchlist", placeholder="e.g., Telecom Breakout", label_visibility="collapsed")
                    with fc2:
                        if st.form_submit_button("➕ Create", use_container_width=True):
                            if new_scan_wl and new_scan_wl not in st.session_state.watchlists:
                                st.session_state.watchlists[new_scan_wl] = []
                                st.session_state.active_watchlist_name = new_scan_wl
                                save_watchlists(st.session_state.watchlists)
                                st.success(f"Created '{new_scan_wl}'!")
                                st.rerun()
            with cw4:
                st.markdown("<br>", unsafe_allow_html=True)
                st.caption("💡 Check rows above to enable actions.")

            st.markdown("---")
            if len(selected_rows) > 0:
                st.subheader(f"📋 Copy Selected Setups to TradingView ({len(selected_rows)} Stocks)")
                st.code(", ".join(selected_rows), language="text")

            filtered_symbols = df_display["TV_Symbol"].tolist()
            st.subheader(f"📋 Copy Filtered Scan Results to TradingView ({len(filtered_symbols)} Stocks)")

            if filtered_symbols:
                batch_size = 30
                batches = [filtered_symbols[i : i + batch_size] for i in range(0, len(filtered_symbols), batch_size)]

                if len(batches) > 1:
                    st.markdown("#### ⚡ 30-Symbol TradingView Hot-Swap Batches")
                    st.caption("💡 **Free Tier Bypass Workflow:** In TradingView, press **`Ctrl+A`** → **`Backspace`** → **`Ctrl+V`** in your TV watchlist box to hot-swap 30 stocks at a time!")
                    batch_labels = []
                    for idx, b_list in enumerate(batches):
                        start_num = idx * batch_size + 1
                        end_num = idx * batch_size + len(b_list)
                        batch_labels.append(f"Batch {idx + 1} ({start_num}–{end_num})")
                    selected_batch_label = st.selectbox("Select 30-Symbol Batch to Copy:", options=batch_labels, key=f"scan_batch_dropdown_{rc}_{sc}")
                    selected_idx = batch_labels.index(selected_batch_label)
                    st.code(", ".join(batches[selected_idx]), language="text")

                with st.expander("📋 View / Copy All Tickers (Full Unbatched String)", expanded=False):
                    tv_watchlist_string = ", ".join(filtered_symbols)
                    st.code(tv_watchlist_string, language="text")
