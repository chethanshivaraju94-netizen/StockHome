import time
import calendar
from datetime import datetime, date
import pandas as pd
import streamlit as st
from tradingview_screener import Query, col
from modules.data import load_market_monitor_data, fetch_nifty500_close_on_date
from modules.state import save_tradebook
from modules.styling import get_left_aligned_column_config


def format_currency_cal(val):
    if val == 0:
        return "₹0"
    sign = "+" if val > 0 else "-"
    abs_val = abs(val)
    if abs_val >= 10000000:
        return f"{sign}₹{abs_val/10000000:.2f}Cr"
    elif abs_val >= 100000:
        return f"{sign}₹{abs_val/100000:.2f}L"
    elif abs_val >= 1000:
        if abs_val % 1000 >= 100:
            return f"{sign}₹{abs_val/1000:.1f}K"
        else:
            return f"{sign}₹{abs_val/1000:.0f}K"
    else:
        return f"{sign}₹{abs_val:.0f}"


def render_tradebook_tab():
    st.subheader("📓 Tradebook & Institutional Risk Journal")
    st.caption(
        "Lot-based execution tracking, 1R risk-reward metrics, portfolio"
        " heat, Nifty 500 Shadow Benchmark Alpha, and Trading Performance Calendar."
    )

    tb_data = st.session_state.tradebook
    starting_cap = float(tb_data.get("config", {}).get("starting_capital", 500000.0))
    all_trades = tb_data.get("trades", [])

    # Load market monitor for Nifty 500 benchmark lookup
    df_mm_tb = load_market_monitor_data()

    # Enrich open trades with live prices explicitly matching exchange
    open_trade_tickers = [
        t["ticker"] for t in all_trades if t.get("status") == "OPEN"
    ]
    live_price_map = {}
    if open_trade_tickers:
        bare_names = [
            t.split(":")[-1].strip().upper() if ":" in t else t.strip().upper()
            for t in open_trade_tickers
        ]
        try:
            q = (
                Query()
                .set_markets("india")
                .select("name", "close", "exchange")
                .where(col("name").isin(bare_names))
            )
            _, df_live = q.get_scanner_data()
            if not df_live.empty:
                for _, r in df_live.iterrows():
                    sym = str(r.get("name", "")).strip().upper()
                    exc = str(r.get("exchange", "")).strip().upper()
                    p = r.get("close")
                    if pd.notna(p) and p > 0:
                        live_price_map[f"{exc}:{sym}"] = float(p)
                        if sym not in live_price_map:
                            live_price_map[sym] = float(p)
        except Exception:
            pass

    # Calculate Cash, Portfolio Values, and Risk Metrics
    cash_balance = starting_cap
    realized_pnl_total = 0.0
    unrealized_pnl_total = 0.0
    open_invested_total = 0.0
    open_current_val_total = 0.0
    open_risk_total = 0.0

    # Benchmark Shadow Portfolio Variables
    bench_bought_total = 0.0
    bench_current_val_total = 0.0
    trades_beating_bench = 0
    evaluated_bench_trades = 0

    latest_nifty_close = (
        float(df_mm_tb.iloc[0]["Nifty 500 Close"])
        if not df_mm_tb.empty and "Nifty 500 Close" in df_mm_tb.columns
        else 23700.0
    )

    processed_trade_rows = []
    trade_signatures = {}
    sig_counter = 1

    for tr in all_trades:
        sig = f"{tr.get('ticker')}_{tr.get('date_bought')}_{tr.get('buy_price')}"
        if sig not in trade_signatures:
            trade_signatures[sig] = sig_counter
            sig_counter += 1

    for idx, tr in enumerate(all_trades, 1):
        status = tr.get("status", "OPEN")
        ticker = tr.get("ticker", "N/A").strip().upper()
        clean_sym = ticker.split(":")[-1] if ":" in ticker else ticker

        sh_bought = int(tr.get("shares_bought", 0))
        sh_sold = int(tr.get("shares_sold", 0))
        sh_rem = max(0, sh_bought - sh_sold)

        b_price = float(tr.get("buy_price", 0.0))
        sl_price = float(tr.get("initial_sl", b_price * 0.92))
        date_b = tr.get("date_bought", "N/A")

        sig = f"{ticker}_{date_b}_{b_price}"
        sl_num_shared = trade_signatures[sig]

        unit_risk = max(0.01, b_price - sl_price)

        nifty_buy_close = float(
            tr.get(
                "nifty500_buy_close",
                fetch_nifty500_close_on_date(date_b, df_mm_tb),
            )
        )

        if status == "OPEN":
            curr_price = float(
                live_price_map.get(
                    ticker,
                    live_price_map.get(clean_sym, tr.get("current_price", b_price)),
                )
            )
            date_s = "N/A"

            capital_invested = sh_rem * b_price
            curr_val = sh_rem * curr_price
            booked_val = 0.0

            realized_pnl = 0.0
            unrealized_pnl = sh_rem * (curr_price - b_price)

            sh_risk = sh_rem * unit_risk
            open_risk_total += sh_risk

            open_invested_total += capital_invested
            open_current_val_total += curr_val
            unrealized_pnl_total += unrealized_pnl

            cash_balance -= capital_invested

            bench_val = (
                capital_invested * (latest_nifty_close / nifty_buy_close)
                if nifty_buy_close > 0
                else capital_invested
            )
            bench_bought_total += capital_invested
            bench_current_val_total += bench_val

            lot_return_pct = (
                ((curr_price - b_price) / b_price) * 100 if b_price > 0 else 0.0
            )
            bench_return_pct = (
                ((latest_nifty_close - nifty_buy_close) / nifty_buy_close) * 100
                if nifty_buy_close > 0
                else 0.0
            )
            if lot_return_pct > bench_return_pct:
                trades_beating_bench += 1
            evaluated_bench_trades += 1

            realized_r = 0.0
            status_label = "🟢 OPEN"

        else:
            sold_price = float(tr.get("sell_price", b_price))
            curr_price = sold_price
            date_s = tr.get("date_sold", "N/A")

            capital_invested = sh_sold * b_price
            booked_val = sh_sold * sold_price
            curr_val = 0.0

            realized_pnl = sh_sold * (sold_price - b_price)
            unrealized_pnl = 0.0

            realized_pnl_total += realized_pnl
            cash_balance += (booked_val - capital_invested)

            nifty_sell_close = float(
                tr.get(
                    "nifty500_sell_close",
                    fetch_nifty500_close_on_date(date_s, df_mm_tb),
                )
            )
            bench_val = (
                capital_invested * (nifty_sell_close / nifty_buy_close)
                if nifty_buy_close > 0
                else capital_invested
            )
            bench_bought_total += capital_invested
            bench_current_val_total += bench_val

            lot_return_pct = (
                ((sold_price - b_price) / b_price) * 100 if b_price > 0 else 0.0
            )
            bench_return_pct = (
                ((nifty_sell_close - nifty_buy_close) / nifty_buy_close) * 100
                if nifty_buy_close > 0
                else 0.0
            )
            if lot_return_pct > bench_return_pct:
                trades_beating_bench += 1
            evaluated_bench_trades += 1

            realized_r = (
                realized_pnl / (sh_sold * unit_risk) if (sh_sold * unit_risk) > 0 else 0.0
            )

            if realized_pnl > 0:
                status_label = "🔵 WIN"
            elif realized_pnl < 0:
                status_label = "🔴 LOSS"
            else:
                status_label = "⚪ SCRATCH"

        tot_return_inr = realized_pnl + unrealized_pnl
        abs_return_pct = (
            ((curr_price - b_price) / b_price) * 100 if b_price > 0 else 0.0
        )

        processed_trade_rows.append({
            "trade_id": tr.get("id"),
            "S.No._num": sl_num_shared,
            "Signature": sig,
            "Ticker": ticker,
            "Status": status_label,
            "Shares Bought": sh_bought,
            "Date Bought": date_b,
            "Buy Price (₹)": b_price,
            "Initial SL (₹)": sl_price,
            "Current / Sold Price (₹)": curr_price,
            "Gain / Loss (₹)": tot_return_inr,
            "Realized R": f"{realized_r:+.2f}R" if status == "CLOSED" else "0.00R",
            "Shares Sold": sh_sold,
            "Booked Value (₹)": booked_val,
            "Realised Gains (₹)": realized_pnl,
            "Shares Remaining": sh_rem,
            "Abs Return %": abs_return_pct,
            "Unrealised Value (₹)": unrealized_pnl,
            "Capital Invested (₹)": capital_invested,
            "Current Value (₹)": curr_val,
            "Date Sold": date_s,
        })

    total_portfolio_nav = cash_balance + open_current_val_total
    portfolio_heat_pct = (
        (open_risk_total / max(total_portfolio_nav, 1.0)) * 100
    )

    bench_total_nav = cash_balance + bench_current_val_total
    alpha_inr = total_portfolio_nav - bench_total_nav
    portfolio_net_return_pct = (
        ((total_portfolio_nav - starting_cap) / starting_cap) * 100
        if starting_cap > 0
        else 0.0
    )
    bench_net_return_pct = (
        ((bench_total_nav - starting_cap) / starting_cap) * 100
        if starting_cap > 0
        else 0.0
    )
    alpha_pct = portfolio_net_return_pct - bench_net_return_pct

    # --- TOP METRICS BAR ---
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Starting Capital", f"₹{starting_cap:,.2f}", f"Cash: ₹{cash_balance:,.2f}")
    with c2:
        st.metric("Portfolio NAV", f"₹{total_portfolio_nav:,.2f}", f"{portfolio_net_return_pct:+.2f}% Net")
    with c3:
        st.metric("Open Invested Value", f"₹{open_invested_total:,.2f}", f"Live: ₹{open_current_val_total:,.2f}")
    with c4:
        st.metric("Realized P&L", f"₹{realized_pnl_total:,.2f}", f"Unrealized: ₹{unrealized_pnl_total:,.2f}")
    with c5:
        heat_color = (
            "🟢 SAFE"
            if portfolio_heat_pct <= 5.0
            else "🟡 MODERATE" if portfolio_heat_pct <= 7.0 else "🔴 HIGH"
        )
        st.metric("Portfolio Heat %", f"{portfolio_heat_pct:.2f}%", heat_color)

    st.markdown("---")
    st.caption("🏆 **Nifty 500 Shadow Benchmark Comparison (Dollar-Weighted):**")
    ac1, ac2, ac3, ac4 = st.columns(4)
    with ac1:
        st.metric("Portfolio Net Return", f"{portfolio_net_return_pct:+.2f}%")
    with ac2:
        st.metric("Nifty 500 Shadow Return", f"{bench_net_return_pct:+.2f}%")
    with ac3:
        st.metric("Alpha (Excess Return)", f"{alpha_pct:+.2f}%", f"₹{alpha_inr:,.2f}")
    with ac4:
        beat_pct = (
            (trades_beating_bench / max(evaluated_bench_trades, 1)) * 100
            if evaluated_bench_trades > 0
            else 0.0
        )
        st.metric("Beat Index Win Rate", f"{beat_pct:.1f}%")

    st.markdown("---")

    # ==========================================
    # DATA PROCESSING & TABLE SELECTION LOGIC
    # ==========================================
    df_tb_display = pd.DataFrame(processed_trade_rows)
    tb_filter = st.session_state.get("tb_display_filter", "All Positions")

    if not df_tb_display.empty:
        if tb_filter == "Open Positions Only":
            df_tb_display = df_tb_display[df_tb_display["Status"].str.contains("OPEN")].reset_index(drop=True)
        elif tb_filter == "Closed Trades Only":
            df_tb_display = df_tb_display[df_tb_display["Status"].str.contains("WIN|LOSS|SCRATCH")].reset_index(drop=True)

    # Read selected row directly from table interaction
    selection_state = st.session_state.get("tb_manage_table", {"selection": {"rows": []}})
    selected_rows = selection_state.get("selection", {}).get("rows", [])
    
    selected_trade_id = None
    if selected_rows and not df_tb_display.empty:
        idx = selected_rows[0]
        if idx < len(df_tb_display):
            selected_trade_id = df_tb_display.iloc[idx]["trade_id"]

    # --- DIALOG MODALS ---
    @st.dialog("➕ Log New Position Entry", width="medium")
    def show_buy_modal():
        active_wl = st.session_state.get(
            "active_watchlist_name",
            list(st.session_state.watchlists.keys())[0],
        )
        wl_tickers = st.session_state.watchlists.get(active_wl, [])
        st.caption(f"📍 Populating tickers strictly from active watchlist: **{active_wl}**")

        with st.form("buy_trade_form", clear_on_submit=True):
            sel_ticker = st.selectbox("Select Ticker from Active Watchlist:", options=wl_tickers)
            custom_ticker = st.text_input("OR Type Custom Ticker (e.g. NSE:BEL):", placeholder="NSE:BEL")
            final_ticker = custom_ticker.strip().upper() if custom_ticker.strip() else sel_ticker

            b_date = st.date_input("Date Bought:", value=date.today())
            b_shares = st.number_input("Shares Bought:", min_value=1, value=100, step=1)
            b_price = st.number_input("Buy Price (₹):", min_value=0.1, value=100.0, step=1.0)
            b_sl = st.number_input("Initial Stop Loss Price (₹):", min_value=0.01, value=round(b_price * 0.92, 2), step=1.0)

            outlay = b_shares * b_price
            risk_amount = b_shares * (b_price - b_sl)
            st.caption(f"💡 Total Outlay: **₹{outlay:,.2f}** | Initial Risk (1R): **₹{risk_amount:,.2f}**")

            if st.form_submit_button("💾 Save Position Entry", use_container_width=True):
                if final_ticker:
                    date_s_str = b_date.strftime("%Y-%m-%d")
                    nifty_close_buy = fetch_nifty500_close_on_date(date_s_str, df_mm_tb)

                    new_trade = {
                        "id": f"TRD_{int(time.time()*1000)}",
                        "ticker": final_ticker,
                        "status": "OPEN",
                        "date_bought": date_s_str,
                        "shares_bought": int(b_shares),
                        "shares_sold": 0,
                        "buy_price": float(b_price),
                        "initial_sl": float(b_sl),
                        "nifty500_buy_close": nifty_close_buy,
                    }
                    st.session_state.tradebook["trades"].append(new_trade)
                    save_tradebook(st.session_state.tradebook)
                    st.success(f"✅ Logged position for **{final_ticker}**!")
                    st.rerun()

    @st.dialog("➖ Log Exit or Partial Sell", width="medium")
    def show_sell_modal(preselected_t_id=None):
        open_lots = [t for t in st.session_state.tradebook["trades"] if t.get("status") == "OPEN"]
        if not open_lots:
            st.info("No open trades currently in your Tradebook!")
            return

        lot_options = []
        default_idx = 0
        for i, t in enumerate(open_lots):
            lbl = f"{t['ticker']} (Bought {t['date_bought']} | {t['shares_bought'] - t['shares_sold']} shs @ ₹{t['buy_price']})"
            lot_options.append((lbl, t))
            if t.get("id") == preselected_t_id:
                default_idx = i

        lot_labels = [opt[0] for opt in lot_options]
        sel_label = st.selectbox("Select Active Position Lot to Sell:", options=lot_labels, index=default_idx)
        sel_lot = next(opt[1] for opt in lot_options if opt[0] == sel_label)
        max_sell = sel_lot["shares_bought"] - sel_lot["shares_sold"]

        with st.form("sell_trade_form", clear_on_submit=True):
            s_date = st.date_input("Date Sold:", value=date.today())
            s_shares = st.number_input("Shares Sold:", min_value=1, max_value=max_sell, value=max_sell, step=1)
            s_price = st.number_input("Sell Price (₹):", min_value=0.1, value=sel_lot["buy_price"], step=1.0)

            if st.form_submit_button("💾 Execute Exit / Partial Sell", use_container_width=True):
                date_s_str = s_date.strftime("%Y-%m-%d")
                nifty_close_sell = fetch_nifty500_close_on_date(date_s_str, df_mm_tb)

                if s_shares == max_sell:
                    sel_lot["status"] = "CLOSED"
                    sel_lot["shares_sold"] += s_shares
                    sel_lot["sell_price"] = float(s_price)
                    sel_lot["date_sold"] = date_s_str
                    sel_lot["nifty500_sell_close"] = nifty_close_sell
                else:
                    closed_split_lot = {
                        "id": f"TRD_{int(time.time()*1000)}",
                        "ticker": sel_lot["ticker"],
                        "status": "CLOSED",
                        "date_bought": sel_lot["date_bought"],
                        "date_sold": date_s_str,
                        "shares_bought": int(s_shares),
                        "shares_sold": int(s_shares),
                        "buy_price": sel_lot["buy_price"],
                        "sell_price": float(s_price),
                        "initial_sl": sel_lot["initial_sl"],
                        "nifty500_buy_close": sel_lot["nifty500_buy_close"],
                        "nifty500_sell_close": nifty_close_sell,
                    }
                    sel_lot["shares_bought"] -= s_shares
                    st.session_state.tradebook["trades"].append(closed_split_lot)

                save_tradebook(st.session_state.tradebook)
                st.success(f"✅ Executed exit for **{sel_lot['ticker']}**!")
                st.rerun()

    @st.dialog("✏️ Edit or Delete Trade", width="medium")
    def show_edit_modal(t_id):
        idx = None
        for i, tr in enumerate(st.session_state.tradebook["trades"]):
            if tr.get("id") == t_id:
                idx = i
                break

        if idx is None:
            st.error("Trade not found.")
            return

        sel_tr = st.session_state.tradebook["trades"][idx]

        st.markdown(f"**Editing Trade:** {sel_tr.get('ticker')} | **Bought:** {sel_tr.get('date_bought')}")
        st.markdown("---")
        
        with st.form("edit_trade_form"):
            e_status = st.selectbox("Status", ["OPEN", "CLOSED"], index=0 if sel_tr.get("status") == "OPEN" else 1)
            e_tick = st.text_input("Ticker", sel_tr.get("ticker", ""))
            c1, c2 = st.columns(2)
            with c1:
                e_sh_b = st.number_input("Shares Bought", value=int(sel_tr.get("shares_bought", 0)))
                e_bp = st.number_input("Buy Price", value=float(sel_tr.get("buy_price", 0.0)))
                e_db = st.date_input("Date Bought", pd.to_datetime(sel_tr.get("date_bought", date.today())))
                e_sl = st.number_input("Initial SL", value=float(sel_tr.get("initial_sl", 0.0)))
            with c2:
                e_sh_s = st.number_input("Shares Sold", value=int(sel_tr.get("shares_sold", 0)))
                e_sp = st.number_input("Sell Price", value=float(sel_tr.get("sell_price", 0.0)))
                e_ds_val = (pd.to_datetime(sel_tr.get("date_sold")) if sel_tr.get("date_sold") and sel_tr.get("date_sold") != "N/A" else date.today())
                e_ds = st.date_input("Date Sold", e_ds_val)

            col_upd, col_del = st.columns(2)
            with col_upd:
                submit_upd = st.form_submit_button("💾 Update Trade", use_container_width=True)
            with col_del:
                submit_del = st.form_submit_button("🗑️ Delete Trade", use_container_width=True)

            if submit_upd:
                sel_tr["status"] = e_status
                sel_tr["ticker"] = e_tick
                sel_tr["shares_bought"] = e_sh_b
                sel_tr["buy_price"] = e_bp
                sel_tr["date_bought"] = e_db.strftime("%Y-%m-%d")
                sel_tr["initial_sl"] = e_sl
                sel_tr["shares_sold"] = e_sh_s
                sel_tr["sell_price"] = e_sp
                sel_tr["date_sold"] = e_ds.strftime("%Y-%m-%d") if e_status == "CLOSED" else "N/A"
                save_tradebook(st.session_state.tradebook)
                st.success("Trade updated successfully!")
                st.rerun()
            if submit_del:
                st.session_state.tradebook["trades"].pop(idx)
                save_tradebook(st.session_state.tradebook)
                st.success("Trade deleted successfully!")
                st.rerun()

    @st.dialog("⚙️ Configure Account Capital", width="small")
    def show_config_modal():
        with st.form("config_capital_form"):
            cap = st.number_input("Starting Portfolio Capital (₹):", min_value=10000.0, value=starting_cap, step=25000.0)
            if st.form_submit_button("💾 Save Config", use_container_width=True):
                st.session_state.tradebook["config"]["starting_capital"] = float(cap)
                save_tradebook(st.session_state.tradebook)
                st.success("Config updated!")
                st.rerun()

    # --- TOP ACTION BUTTONS ---
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5 = st.columns([1.2, 1.2, 1.2, 1.2, 2.0])
    with ctrl_col1:
        if st.button("➕ Log New Buy", type="primary", use_container_width=True): show_buy_modal()
    with ctrl_col2:
        if st.button("➖ Log Exit / Sell", type="secondary", use_container_width=True): show_sell_modal(selected_trade_id)
    with ctrl_col3:
        if st.button("✏️ Edit / Delete", type="secondary", use_container_width=True, disabled=(selected_trade_id is None)): 
            show_edit_modal(selected_trade_id)
    with ctrl_col4:
        if st.button("⚙️ Config Capital", type="secondary", use_container_width=True): show_config_modal()
    with ctrl_col5:
        st.radio("Display Filter:", options=["All Positions", "Open Positions Only", "Closed Trades Only"], horizontal=True, key="tb_display_filter")

    if df_tb_display.empty:
        st.info("Your Tradebook is empty! Click **'➕ Log New Buy'** above to record your first position.")
    else:
        # Calculate Allocation % dynamically based on total NAV
        if total_portfolio_nav > 0:
            df_tb_display["Allocation %"] = df_tb_display["Current Value (₹)"].apply(
                lambda v: (v / total_portfolio_nav) * 100 if v > 0 else 0.0
            )
        else:
            df_tb_display["Allocation %"] = 0.0

        # Group S.No. to prevent repeating numbers for partial exits
        seen_snos = set()
        sno_display_list = []
        for sno in df_tb_display["S.No._num"]:
            if sno not in seen_snos:
                seen_snos.add(sno)
                sno_display_list.append(str(sno))
            else:
                sno_display_list.append("")
        df_tb_display["S.No."] = sno_display_list

        # Strictly enforce 2-decimal rounding
        float_cols_2dec = [
            "Buy Price (₹)", "Initial SL (₹)", "Current / Sold Price (₹)",
            "Gain / Loss (₹)", "Booked Value (₹)", "Realised Gains (₹)",
            "Abs Return %", "Unrealised Value (₹)", "Capital Invested (₹)",
            "Current Value (₹)", "Allocation %"
        ]
        for fc in float_cols_2dec:
            if fc in df_tb_display.columns:
                df_tb_display[fc] = pd.to_numeric(df_tb_display[fc], errors="coerce").round(2)

        tb_table_columns = [
            "S.No.", "Ticker", "Status", "Shares Bought", "Date Bought", "Buy Price (₹)",
            "Initial SL (₹)", "Current / Sold Price (₹)", "Gain / Loss (₹)", "Realized R",
            "Shares Sold", "Booked Value (₹)", "Realised Gains (₹)", "Shares Remaining",
            "Abs Return %", "Unrealised Value (₹)", "Capital Invested (₹)", "Current Value (₹)", "Allocation %",
        ]

        st.subheader(f"📋 Tradebook ({len(df_tb_display)} Rows)")
        st.caption("💡 Select a row to Edit, Delete, or Log an Exit.")
        
        # Enable row selection
        st.dataframe(
            df_tb_display[tb_table_columns],
            use_container_width=True,
            hide_index=True,
            height=400,
            on_select="rerun",
            selection_mode="single-row",
            key="tb_manage_table",
            column_config=get_left_aligned_column_config(tb_table_columns),
        )

        # --- INSTITUTIONAL PERFORMANCE ANALYTICS ---
        st.markdown("---")
        st.subheader("📊 Elite Risk Management & Performance Analytics")

        closed_lots = [
            t for t in processed_trade_rows
            if "WIN" in str(t.get("Status", "")) or "LOSS" in str(t.get("Status", "")) or "SCRATCH" in str(t.get("Status", ""))
        ]
        total_closed = len(closed_lots)
        unique_setups = len(trade_signatures)
        active_setups = len(set(t["Signature"] for t in processed_trade_rows if "OPEN" in t["Status"]))

        if total_closed > 0:
            wins = [t for t in closed_lots if t["Realised Gains (₹)"] > 0]
            losses = [t for t in closed_lots if t["Realised Gains (₹)"] <= 0]
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = (win_count / total_closed) * 100

            avg_win_inr = sum(t["Realised Gains (₹)"] for t in wins) / win_count if win_count > 0 else 0.0
            avg_loss_inr = abs(sum(t["Realised Gains (₹)"] for t in losses)) / loss_count if loss_count > 0 else 0.0
            avg_win_pct = sum(t["Abs Return %"] for t in wins) / win_count if win_count > 0 else 0.0
            avg_loss_pct = abs(sum(t["Abs Return %"] for t in losses)) / loss_count if loss_count > 0 else 0.0

            rr_monetary = avg_win_inr / avg_loss_inr if avg_loss_inr > 0 else avg_win_inr
            rr_ratio = avg_win_pct / avg_loss_pct if avg_loss_pct > 0 else avg_win_pct

            def calc_days(t):
                try:
                    d1 = datetime.strptime(t["Date Bought"], "%Y-%m-%d")
                    d2 = datetime.strptime(t["Date Sold"], "%Y-%m-%d")
                    return max(1, (d2 - d1).days)
                except Exception:
                    return 1

            avg_days_win = sum(calc_days(t) for t in wins) / win_count if win_count > 0 else 0
            avg_days_loss = sum(calc_days(t) for t in losses) / loss_count if loss_count > 0 else 0

            streak_count = 0
            last_outcome = None
            for t in reversed(closed_lots):
                is_win = t["Realised Gains (₹)"] > 0
                if last_outcome is None:
                    last_outcome = is_win
                    streak_count = 1
                elif last_outcome == is_win:
                    streak_count += 1
                else:
                    break
            streak_label = f"🟢 {streak_count} Wins" if last_outcome else f"🔴 {streak_count} Losses"
            if not last_outcome and streak_count >= 3:
                streak_label += " (⚠️ Cut Size 50%)"
        else:
            win_count, loss_count, win_rate = 0, 0, 0.0
            avg_win_inr, avg_loss_inr, avg_win_pct, avg_loss_pct = 0.0, 0.0, 0.0, 0.0
            rr_monetary, rr_ratio, avg_days_win, avg_days_loss = 0.0, 0.0, 0, 0
            streak_label = "⚪ No Closed Trades"

        k1, k2, k3, k4, k5 = st.columns(5)
        with k1: st.metric("Total Setups Logged", f"{unique_setups}", f"Live / Active: {active_setups}")
        with k2: st.metric("Win Rate %", f"{win_rate:.1f}%", f"{win_count}W / {loss_count}L")
        with k3: st.metric("Avg Win (₹ / %)", f"₹{avg_win_inr:,.0f}", f"+{avg_win_pct:.2f}%")
        with k4: st.metric("Avg Loss (₹ / %)", f"-₹{avg_loss_inr:,.0f}", f"-{avg_loss_pct:.2f}%")
        with k5: st.metric("Payoff Ratio (R:R)", f"{rr_ratio:.2f}x", f"Monetary: {rr_monetary:.2f}x")

        k6, k7, k8 = st.columns(3)
        with k6: st.metric("Avg Days Held (Winners)", f"{avg_days_win:.1f} Days")
        with k7: st.metric("Avg Days Held (Losers)", f"{avg_days_loss:.1f} Days")
        with k8: st.metric("Progressive Exposure Streak", streak_label)

        # --- TRADING PERFORMANCE VISUAL CALENDAR ---
        st.markdown("---")
        st.subheader("📅 Trading Performance Calendar")
        
        if total_closed == 0:
            st.info("No closed trades available to generate the Trading Calendar yet.")
        else:
            df_closed_cal = pd.DataFrame(closed_lots)
            df_closed_cal["Date_DT"] = pd.to_datetime(df_closed_cal["Date Sold"], errors="coerce")
            df_closed_cal = df_closed_cal.dropna(subset=["Date_DT"]).sort_values(by="Date_DT", ascending=True)

            df_closed_cal['Month_Year'] = df_closed_cal['Date_DT'].dt.strftime('%b %Y')
            months = df_closed_cal['Month_Year'].unique().tolist()
            months.reverse()

            cal_col1, cal_col2 = st.columns([1, 3])
            with cal_col1:
                selected_month_str = st.selectbox("Select Month to Display", months, label_visibility="collapsed")
            
            selected_dt = datetime.strptime(selected_month_str, '%b %Y')
            target_year, target_month = selected_dt.year, selected_dt.month

            month_data = df_closed_cal[(df_closed_cal['Date_DT'].dt.year == target_year) & (df_closed_cal['Date_DT'].dt.month == target_month)]
            monthly_pnl = month_data['Realised Gains (₹)'].sum()
            monthly_trades = month_data['Ticker'].count()
            
            monthly_color_hex = "#63BE7B" if monthly_pnl > 0 else "#F8696B" if monthly_pnl < 0 else "#A0A5B5"

            with cal_col2:
                st.markdown(f"<div style='text-align: right; padding-top: 5px; color: #A0A5B5; font-size: 14px;'>Monthly P&L: <span style='color: {monthly_color_hex}; font-weight: bold;'>{format_currency_cal(monthly_pnl)}</span> ({monthly_trades} {'trade' if monthly_trades == 1 else 'trades'})</div>", unsafe_allow_html=True)

            cal = calendar.Calendar(firstweekday=6)
            month_days = cal.monthdatescalendar(target_year, target_month)

            daily_pnl = df_closed_cal.groupby(df_closed_cal["Date_DT"].dt.date).agg(
                pnl=("Realised Gains (₹)", "sum"),
                trades=("Ticker", "count")
            ).to_dict('index')

            html = "<style>"
            html += ".cal-wrapper { overflow-x: auto; margin-top: 10px; padding-bottom: 10px; }"
            html += ".cal-container { width: 100%; border-collapse: separate; border-spacing: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; min-width: 800px; }"
            html += ".cal-header th { text-align: center; padding: 5px; font-weight: 600; color: #A0A5B5; font-size: 13px; text-transform: uppercase; }"
            html += ".cal-cell { background-color: #1E222D; border: 1px solid #2B2F3E; border-radius: 6px; padding: 10px; width: 12.5%; height: 95px; vertical-align: top; box-shadow: 0 2px 4px rgba(0,0,0,0.1);}"
            html += ".cal-cell-empty { background-color: transparent; border: none; box-shadow: none; }"
            html += ".cal-date { text-align: right; font-size: 13px; color: #A0A5B5; margin-bottom: 2px; font-weight: 600;}"
            html += ".cal-pnl { font-size: 16px; font-weight: 700; text-align: left; margin-top: 10px;}"
            html += ".cal-pnl.green { color: #63BE7B; }"
            html += ".cal-pnl.red { color: #F8696B; }"
            html += ".cal-pnl.zero { color: #7B8191; }"
            html += ".cal-trades { font-size: 12px; color: #A0A5B5; text-align: left; margin-top: 4px; }"
            html += ".cal-week-total { background-color: #262A38; border: 1px solid #363B4E; }"
            html += ".cal-week-label { text-align: center; font-size: 12px; color: #A0A5B5; margin-bottom: 2px; font-weight: 600; text-transform: uppercase;}"
            html += ".cal-week-pnl { text-align: center; font-size: 16px; font-weight: 700; margin-top: 10px; }"
            html += ".cal-week-trades { text-align: center; font-size: 12px; color: #A0A5B5; margin-top: 4px; }"
            html += "</style>"
            html += "<div class='cal-wrapper'><table class='cal-container'>"
            html += "<tr class='cal-header'><th>Sun</th><th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Week Total</th></tr>"

            week_num = 1
            for week in month_days:
                html += "<tr>"
                week_pnl = 0
                week_trades = 0
                for day in week:
                    if day.month != target_month:
                        html += "<td class='cal-cell cal-cell-empty'></td>"
                    else:
                        day_data = daily_pnl.get(day, {'pnl': 0, 'trades': 0})
                        pnl = day_data['pnl']
                        trades = day_data['trades']
                        week_pnl += pnl
                        week_trades += trades

                        pnl_class = "green" if pnl > 0 else "red" if pnl < 0 else "zero"
                        pnl_str = format_currency_cal(pnl)
                        trade_str = f"{trades} trades" if trades != 1 else "1 trade"

                        html += f"<td class='cal-cell'><div class='cal-date'>{day.day}</div><div class='cal-pnl {pnl_class}'>{pnl_str}</div><div class='cal-trades'>{trade_str}</div></td>"

                wpnl_class = "green" if week_pnl > 0 else "red" if week_pnl < 0 else "zero"
                wpnl_str = format_currency_cal(week_pnl)
                wtrade_str = f"{week_trades} trades" if week_trades != 1 else "1 trade"

                html += f"<td class='cal-cell cal-week-total'><div class='cal-week-label'>Week {week_num}</div><div class='cal-week-pnl {wpnl_class}'>{wpnl_str}</div><div class='cal-week-trades'>{wtrade_str}</div></td>"
                html += "</tr>"
                week_num += 1

            html += "</table></div>"
            st.markdown(html, unsafe_allow_html=True)
