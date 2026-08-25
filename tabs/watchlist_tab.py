import json
import time
import pandas as pd
import streamlit as st
from modules.config import parse_pasted_tickers, parse_table_selection_multi
from modules.data import fetch_watchlist_enrichMENT, get_nse_circuit_bands
from modules.styling import get_left_aligned_column_config, is_circuit_stock_badge
from modules.state import save_watchlists
from modules.ai_analyst import (
    show_fundamental_modal,
    run_gemini_fundamental_analysis,
    run_gemini_news_catalyst_scan,
)

# --- Helper Callbacks for Reordering ---
def cb_move_top(wl_name, sym):
    lst = st.session_state.watchlists.get(wl_name, [])
    if sym in lst:
        lst.remove(sym)
        lst.insert(0, sym)
        save_watchlists(st.session_state.watchlists)

def cb_move_up(wl_name, sym):
    lst = st.session_state.watchlists.get(wl_name, [])
    if sym in lst:
        idx = lst.index(sym)
        if idx > 0:
            lst.pop(idx)
            lst.insert(idx - 1, sym)
            save_watchlists(st.session_state.watchlists)

def cb_move_down(wl_name, sym):
    lst = st.session_state.watchlists.get(wl_name, [])
    if sym in lst:
        idx = lst.index(sym)
        if idx < len(lst) - 1:
            lst.pop(idx)
            lst.insert(idx + 1, sym)
            save_watchlists(st.session_state.watchlists)

def cb_move_bottom(wl_name, sym):
    lst = st.session_state.watchlists.get(wl_name, [])
    if sym in lst:
        lst.remove(sym)
        lst.append(sym)
        save_watchlists(st.session_state.watchlists)

def cb_jump_rank(wl_name, sym, target_rank):
    lst = st.session_state.watchlists.get(wl_name, [])
    if sym in lst:
        lst.remove(sym)
        new_idx = max(0, min(len(lst), target_rank - 1))
        lst.insert(new_idx, sym)
        save_watchlists(st.session_state.watchlists)

def render_watchlist_tab():
    st.subheader("⭐ Multi-Watchlist Studio (Bypasses TV Free Tier 30-Symbol Cap)")

    col_sel, col_new, col_del = st.columns([2.4, 1.8, 0.8])
    with col_sel:
        wl_names = list(st.session_state.watchlists.keys())
        active_wl = st.selectbox(
            "Select Active Watchlist:",
            options=wl_names,
            index=(wl_names.index(st.session_state.active_watchlist_name) if st.session_state.active_watchlist_name in wl_names else 0),
            key="wl_active_selector",
        )
        st.session_state.active_watchlist_name = active_wl

        with st.form("inline_rename_form", clear_on_submit=True):
            r_col1, r_col2 = st.columns([2.6, 1.0])
            with r_col1:
                new_inline_name = st.text_input("✏️ Rename Selected Watchlist:", value=active_wl, label_visibility="collapsed", placeholder="Rename watchlist...")
            with r_col2:
                if st.form_submit_button("✏️ Rename", use_container_width=True):
                    if new_inline_name and new_inline_name != active_wl and new_inline_name not in st.session_state.watchlists:
                        old_name = active_wl
                        st.session_state.watchlists[new_inline_name] = st.session_state.watchlists.pop(old_name)
                        st.session_state.active_watchlist_name = new_inline_name
                        save_watchlists(st.session_state.watchlists)
                        st.success(f"Renamed to '{new_inline_name}'!")
                        st.rerun()

    with col_new:
        with st.form("create_wl_form", clear_on_submit=True):
            new_wl_name = st.text_input("Create New Watchlist:", placeholder="e.g., Sector: Capital Goods Build")
            if st.form_submit_button("➕ Create Watchlist", use_container_width=True):
                if new_wl_name and new_wl_name not in st.session_state.watchlists:
                    st.session_state.watchlists[new_wl_name] = []
                    st.session_state.active_watchlist_name = new_wl_name
                    save_watchlists(st.session_state.watchlists)
                    st.success(f"Created Watchlist: {new_wl_name}")
                    st.rerun()
    with col_del:
        st.markdown("<br>", unsafe_allow_html=True)
        if len(wl_names) > 1:
            if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                del st.session_state.watchlists[active_wl]
                save_watchlists(st.session_state.watchlists)
                st.session_state.active_watchlist_name = list(st.session_state.watchlists.keys())[0]
                st.rerun()

    current_symbols = st.session_state.watchlists[active_wl]

    with st.expander("📥 Import / Paste Tickers & Backup Local Text (.TXT) Library", expanded=False):
        ci1, ci2 = st.columns([2, 1])
        with ci1:
            pasted_text = st.text_area("Paste Tickers from TradingView (Comma, Space, or Newline separated):", placeholder="NSE:RELIANCE, BSE:TCS, ZOMATO, TRENT\nNSE:HAL")
            if st.button("➕ Import Tickers into Current Watchlist", type="primary"):
                parsed_symbols = parse_pasted_tickers(pasted_text)
                current_list = st.session_state.watchlists[active_wl]
                added = 0
                for s in parsed_symbols:
                    if s not in current_list:
                        current_list.append(s)
                        added += 1
                save_watchlists(st.session_state.watchlists)
                st.success(f"✅ Imported {added} symbols into **{active_wl}**!")
                st.rerun()
        with ci2:
            st.markdown("#### 💾 Backup & Restore Disk Library (.TXT)")
            txt_export_str = json.dumps(st.session_state.watchlists, indent=2)
            st.download_button(label="📥 Download Watchlists (.TXT)", data=txt_export_str, file_name="my_india_watchlists.txt", mime="text/plain", use_container_width=True)
            uploaded_file = st.file_uploader("Restore Watchlists (.TXT):", type=["txt", "json"], label_visibility="collapsed")
            if uploaded_file is not None:
                try:
                    loaded_wls = json.load(uploaded_file)
                    if isinstance(loaded_wls, dict):
                        st.session_state.watchlists = loaded_wls
                        st.session_state.active_watchlist_name = list(loaded_wls.keys())[0]
                        save_watchlists(loaded_wls)
                        st.success("✅ Watchlists restored successfully!")
                        st.rerun()
                except Exception:
                    st.error("Invalid file format. Ensure it is a valid backup file.")

    # --- PRE-MARKET CATALYST SCANNER UI ---
    with st.expander("🚀 AI Pre-Market Catalyst Scanner", expanded=False):
        st.markdown(
            "Scan overnight news feeds for tickers in **"
            f"{active_wl}** to identify high-probability breakout catalysts for today's session."
        )
        if st.button("🔍 Scan Overnight Catalysts", type="primary", use_container_width=True, key="scan_news_btn"):
            if not current_symbols:
                st.warning("Watchlist is currently empty.")
            else:
                with st.status("Initializing Catalyst Engine...", expanded=True) as status_box:
                    catalyst_report, raw_news_feed = run_gemini_news_catalyst_scan(current_symbols, status_log=status_box)
                    
                    if catalyst_report:
                        st.markdown("---")
                        st.markdown(catalyst_report)
                        
                        if raw_news_feed:
                            with st.expander("🔎 View Raw News Feed (Audit / Verification)"):
                                st.markdown(raw_news_feed)

    if not current_symbols:
        st.info(f"The watchlist **{active_wl}** is currently empty. Add setups from the Screener tab or paste symbols above!")
    else:
        if len(current_symbols) > 1:
            st.markdown("---")
            st.markdown("#### ⚡ Priority Mover & Rank Jumper")
            rm_col1, rm_col2, rm_col3, rm_col4, rm_col5, rm_col6, rm_col7 = st.columns([2.0, 0.8, 0.8, 0.8, 0.8, 1.1, 0.8])
            with rm_col1: move_target_sym = st.selectbox("Select Ticker to Move:", options=current_symbols, key=f"rapid_mover_sym_{active_wl}", label_visibility="collapsed")
            with rm_col2: st.button("🔝 Top", on_click=cb_move_top, args=(active_wl, move_target_sym), use_container_width=True)
            with rm_col3: st.button("⬆️ Up", on_click=cb_move_up, args=(active_wl, move_target_sym), use_container_width=True)
            with rm_col4: st.button("⬇️ Down", on_click=cb_move_down, args=(active_wl, move_target_sym), use_container_width=True)
            with rm_col5: st.button("🔻 Bottom", on_click=cb_move_bottom, args=(active_wl, move_target_sym), use_container_width=True)
            with rm_col6: target_rank = st.number_input("Rank #", min_value=1, max_value=len(current_symbols), value=1, step=1, key=f"rapid_mover_rank_{active_wl}", label_visibility="collapsed")
            with rm_col7: st.button("🎯 Jump", type="primary", on_click=cb_jump_rank, args=(active_wl, move_target_sym, target_rank), use_container_width=True)

        with st.spinner(f"📡 Enriching {len(current_symbols)} Tickers with Live Price & ADR%..."):
            enriched_df = fetch_watchlist_enrichMENT(current_symbols)

        ordered_df = pd.DataFrame({"TV_Symbol": current_symbols, "name": [s.split(":")[-1].strip().upper() for s in current_symbols]})

        if not enriched_df.empty:
            merged_df = ordered_df.merge(enriched_df, on="name", how="left", suffixes=("", "_tv"))
            if "TV_Symbol_tv" in merged_df.columns:
                merged_df["TV_Symbol"] = merged_df["TV_Symbol_tv"].fillna(merged_df["TV_Symbol"])
        else:
            merged_df = ordered_df.copy()
            for col_name in ["Close", "Change %", "ADR_pct", "EPS Q YoY %", "Sales Q YoY %", "Perf % 1W", "Perf % 1M", "Perf % 3M", "Perf % 6M", "Market Cap (₹ Cr)", "IPO Date", "Sector", "Industry"]:
                merged_df[col_name] = "N/A"

        merged_df["Close"] = merged_df.get("Close", pd.Series()).fillna("N/A")
        merged_df["Change %"] = merged_df.get("Change %", pd.Series()).fillna("N/A")
        merged_df["ADR %"] = merged_df.get("ADR_pct", pd.Series()).fillna("N/A")
        merged_df["EPS Q YoY %"] = merged_df.get("EPS Q YoY %", pd.Series()).fillna("N/A")
        merged_df["Sales Q YoY %"] = merged_df.get("Sales Q YoY %", pd.Series()).fillna("N/A")
        merged_df["Perf % 1W"] = merged_df.get("Perf % 1W", pd.Series()).fillna("N/A")
        merged_df["Perf % 1M"] = merged_df.get("Perf % 1M", pd.Series()).fillna("N/A")
        merged_df["Perf % 3M"] = merged_df.get("Perf % 3M", pd.Series()).fillna("N/A")
        merged_df["Perf % 6M"] = merged_df.get("Perf % 6M", pd.Series()).fillna("N/A")
        merged_df["Market Cap (₹ Cr)"] = merged_df.get("Market Cap (₹ Cr)", pd.Series()).fillna("N/A")
        merged_df["IPO Date"] = merged_df.get("IPO Date", pd.Series()).fillna("N/A")
        merged_df["Sector"] = merged_df.get("Sector", pd.Series()).fillna("Unclassified")
        merged_df["Industry"] = merged_df.get("Industry", pd.Series()).fillna("Unclassified")

        merged_df["S.No._num"] = range(1, len(merged_df) + 1)
        merged_df["TV_Link"] = "https://www.tradingview.com/chart/?symbol=" + merged_df["TV_Symbol"]
        merged_df["Screener_Link"] = "https://www.screener.in/company/" + merged_df["name"] + "/consolidated/"

        # --- DEDUPLICATED WL DOT LOGIC ---
        wl_dot_map_wl = {}
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
                if dot not in wl_dot_map_wl.get(bare_s, ""):
                    wl_dot_map_wl[bare_s] = wl_dot_map_wl.get(bare_s, "") + dot

        merged_df["WL_Dots"] = merged_df["name"].str.upper().map(wl_dot_map_wl).fillna("")
        merged_df["S.No."] = merged_df.apply(lambda r: f"{r['S.No._num']} {r['WL_Dots']}".strip() if r["WL_Dots"] else str(r['S.No._num']), axis=1)

        nse_bands_map = get_nse_circuit_bands()
        merged_df["_is_circuit_badge"] = merged_df.apply(lambda r: is_circuit_stock_badge(r, nse_bands_map), axis=1)
        merged_df["name"] = merged_df["name"].where(~merged_df["_is_circuit_badge"], merged_df["name"] + " 🚨")

        rs_map = st.session_state.get("rs_rating_map", {})
        merged_df["RS Rating"] = merged_df["name"].str.replace(" 🚨", "").str.upper().map(rs_map).fillna("N/A")
        merged_df["Fundamental"] = merged_df["name"].str.replace(" 🚨", "").str.upper().map(
            {k: f"{v.get('verdict')} ({v.get('date', '')})" for k, v in st.session_state.fundamental_reports.items()}
        ).fillna("⚪ Not Analyzed")

        wl_cols = ["S.No.", "TV_Symbol", "name", "RS Rating", "Fundamental", "Close", "Change %", "ADR %", "EPS Q YoY %", "Sales Q YoY %", "Perf % 1W", "Perf % 1M", "Perf % 3M", "Perf % 6M", "Market Cap (₹ Cr)", "IPO Date", "Sector", "Industry", "TV_Link", "Screener_Link"]

        wsc = st.session_state.wl_sel_counter

        # --- 1. RENDER FILTER DROPDOWN DIRECTLY ABOVE TABLE ---
        cross_filter_options = [w for w in wl_names if w != active_wl]
        cross_filter_wls = st.multiselect("🔍 Filter: Show only stocks also present in:", options=cross_filter_options, key=f"wl_filter_{wsc}")

        # --- 2. APPLY FILTER & SORTING ---
        sort_by_wl = st.session_state.get(f"wl_sort_{wsc}", "Original Watchlist Order")
        sort_asc_wl = st.session_state.get(f"wl_asc_{wsc}", False)

        if cross_filter_wls:
            valid_symbols = set()
            for f_wl in cross_filter_wls:
                valid_symbols.update([s.split(":")[-1].strip().upper() for s in st.session_state.watchlists.get(f_wl, [])])
            merged_df = merged_df[merged_df["name"].isin(valid_symbols)]

        if sort_by_wl != "Original Watchlist Order":
            temp_col = "_temp_sort_col"
            merged_df[temp_col] = pd.to_numeric(merged_df[sort_by_wl], errors="coerce")
            merged_df = merged_df.sort_values(by=temp_col, ascending=sort_asc_wl).drop(columns=[temp_col])

        st.markdown(f"### ⭐ Watchlist: **{active_wl}** ({len(merged_df)} Stocks)")
        st.caption("💡 **Watchlist Color Legend:** 🔵 Post Breakout Monitor | 🟢 Focus List | 🟡 Weekly Focus | 🟠 Scan Bulk | 🔴 Sold Stocks | 🟣 Custom | 🚨 **Circuit Band / Freeze**")

        wl_table_event = st.dataframe(
            merged_df[wl_cols], use_container_width=True, hide_index=True, height=460,
            on_select="rerun", selection_mode="multi-row", column_config=get_left_aligned_column_config(wl_cols), key=f"wl_manage_table_{wsc}"
        )

        sel_symbols = parse_table_selection_multi(wl_table_event, merged_df, "TV_Symbol")

        st.markdown("---")
        wf_col1, wf_col2, wf_col3 = st.columns([2.0, 1.3, 1.7])
        with wf_col1:
            if len(sel_symbols) == 1:
                active_sym_wl = sel_symbols[0]
                clean_wl_sym_name = active_sym_wl.split(":")[-1].strip().upper()
                if st.button(f"📖 Open Saved Report Modal ({clean_wl_sym_name})", type="primary", use_container_width=True, key=f"fund_btn_view_wl_{wsc}"):
                    show_fundamental_modal(active_sym_wl)
            else:
                st.button("📖 Select a Single Stock Row to Open Report", type="secondary", disabled=True, use_container_width=True, key=f"fund_btn_view_wl_dis_{wsc}")
        with wf_col2: force_reanalyze_wl = st.checkbox("Force Re-Analyze Existing", value=False, key=f"force_wl_{wsc}", help="If checked, AI will re-fetch Screener PDFs even if a report already exists.")
        with wf_col3: run_batch_wl = st.button(f"⚡ Analyze Selected ({len(sel_symbols)})", type="primary", use_container_width=True, disabled=len(sel_symbols) == 0, key=f"fund_btn_run_wl_{wsc}")

        if run_batch_wl and len(sel_symbols) > 0:
            with st.status("🧠 Minervini Fundamental AI Analyst — Active Queue", expanded=True) as status_box_wl:
                p_bar = st.progress(0.0)
                for idx, sym in enumerate(sel_symbols):
                    clean_sym = sym.split(":")[-1].strip().upper()
                    if clean_sym in st.session_state.fundamental_reports and not force_reanalyze_wl:
                        status_box_wl.write(f"⏩ **[{idx + 1}/{len(sel_symbols)}] {clean_sym}:** Report already exists in Database.")
                    else:
                        status_box_wl.write(f"⚙️ **[{idx + 1}/{len(sel_symbols)}] {clean_sym}:** Downloading Screener.in PDFs & Running AI...")
                        run_gemini_fundamental_analysis(clean_sym, st.session_state.fundamental_reports, status_log=status_box_wl)
                    p_bar.progress((idx + 1) / len(sel_symbols))
                status_box_wl.update(label="✅ Batch AI Analysis Complete! Updating Table...", state="complete", expanded=True)
                time.sleep(1.5)
                st.rerun()

        c_rem, c_clr, c_promo_sel, c_promo_btn = st.columns([1.5, 1.2, 2.0, 1.5])
        with c_rem:
            if st.button(f"🗑️ Remove Selected ({len(sel_symbols)})", type="secondary", use_container_width=True, disabled=len(sel_symbols) == 0):
                for sym in sel_symbols:
                    if sym in st.session_state.watchlists[active_wl]:
                        st.session_state.watchlists[active_wl].remove(sym)
                save_watchlists(st.session_state.watchlists)
                st.rerun()
        with c_clr:
            if st.button("🧹 Clear Selection", type="secondary", use_container_width=True, disabled=len(sel_symbols) == 0, key="clear_wl_sel_btn"):
                st.session_state.wl_sel_counter += 1
                st.rerun()
        with c_promo_sel:
            promo_target = st.selectbox("Promote Selected To Target Watchlist:", options=([name for name in wl_names if name != active_wl] if len(wl_names) > 1 else wl_names), key="promo_target_select", label_visibility="collapsed")
        with c_promo_btn:
            if st.button(f"➡️ Promote Selected ({len(sel_symbols)})", type="primary", use_container_width=True, disabled=len(sel_symbols) == 0):
                target_list = st.session_state.watchlists[promo_target]
                cnt = 0
                for sym in sel_symbols:
                    if sym not in target_list:
                        target_list.append(sym)
                        cnt += 1
                save_watchlists(st.session_state.watchlists)
                st.success(f"✅ Promoted {cnt} stocks to **{promo_target}**!")
                st.rerun()

        sorted_tv_symbols = merged_df["TV_Symbol"].tolist()

        # --- 3. RENDER SORTING ENGINE DIRECTLY UNDER HOT-SWAP HEADER ---
        st.markdown("#### ⚡ 30-Symbol TradingView Hot-Swap Batches")
        st.caption("💡 **Free Tier Bypass Workflow:** In TradingView, press **`Ctrl+A`** → **`Backspace`** → **`Ctrl+V`** in your TV watchlist box to hot-swap 30 stocks at a time!")

        sort_cols_wl = ["Original Watchlist Order", "RS Rating", "Change %", "ADR %", "Close", "Market Cap (₹ Cr)", "EPS Q YoY %", "Sales Q YoY %", "Perf % 1W", "Perf % 1M", "Perf % 3M", "Perf % 6M"]
        
        wl_s1, wl_s2 = st.columns([1.5, 3.5])
        with wl_s1:
            st.selectbox("🔀 Sort Watchlist By (Updates Hot-Swap):", options=sort_cols_wl, key=f"wl_sort_{wsc}")
        with wl_s2:
            st.write("")
            st.write("")
            st.checkbox("Ascending", key=f"wl_asc_{wsc}")

        if sorted_tv_symbols:
            batch_size = 30
            batches = [sorted_tv_symbols[i : i + batch_size] for i in range(0, len(sorted_tv_symbols), batch_size)]

            if len(batches) > 1:
                batch_labels = []
                for idx, b_list in enumerate(batches):
                    start_num = idx * batch_size + 1
                    end_num = idx * batch_size + len(b_list)
                    batch_labels.append(f"Batch {idx + 1} ({start_num}–{end_num})")
                selected_wl_batch_label = st.selectbox("Select 30-Symbol Batch to Copy:", options=batch_labels, key=f"wl_batch_select_{active_wl}_{wsc}")
                selected_wl_idx = batch_labels.index(selected_wl_batch_label)
                st.code(", ".join(batches[selected_wl_idx]), language="text")
            else:
                st.code(", ".join(sorted_tv_symbols), language="text")

            with st.expander("📋 View / Copy All Tickers (Full Unbatched String)", expanded=False):
                st.code(", ".join(sorted_tv_symbols), language="text")
        else:
            st.info("No stocks match the current filter criteria.")
