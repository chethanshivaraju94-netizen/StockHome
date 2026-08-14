import time
import calendar
import re
from datetime import datetime, date
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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


def get_nifty500_price_fallback(date_str, df_mm_tb):
    val = fetch_nifty500_close_on_date(date_str, df_mm_tb)
    if val is not None and float(val) > 18000:
        return float(val)
    
    try:
        dt = pd.to_datetime(date_str)
        if dt.year == 2026:
            if dt.month <= 6:
                return 22438.0
            elif dt.month == 7:
                return 23150.0 if dt.day <= 15 else 23350.0
            elif dt.month >= 8:
                return 23681.15
    except Exception:
        pass
    
    return 22438.0


def render_tradebook_tab():
    st.subheader("📓 Tradebook & Institutional Risk Journal")
    st.caption(
        "Lot-based execution tracking, 1R risk-reward metrics, portfolio"
        " heat, Nifty 500 Shadow Benchmark Alpha, and Trading Performance Calendar."
    )

    tb_data = st.session_state.tradebook
    starting_cap = float(tb_data.get("config", {}).get("starting_capital", 500000.0))
    raw_trades = tb_data.get("trades", [])

    all_trades = sorted(
        raw_trades,
        key=lambda x: (
            pd.to_datetime(x.get("date_bought", "1900-01-01")),
            1 if x.get("status") == "OPEN" else 0,
        ),
        reverse=True
    )

    df_mm_tb = load_market_monitor_data()

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

    cash_balance = starting_cap
    realized_pnl_total = 0.0
    unrealized_pnl_total = 0.0
    open_invested_total = 0.0
    open_current_val_total = 0.0

    bench_open_live_val_total = 0.0
    bench_realized_pnl_total = 0.0
    trades_beating_bench = 0
    evaluated_bench_trades = 0

    latest_nifty_close = (
        float(df_mm_tb.iloc[0]["Nifty 500 Close"])
        if not df_mm_tb.empty and "Nifty 500 Close" in df_mm_tb.columns
        else 23681.15
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
        nifty_buy_close = get_nifty500_price_fallback(date_b, df_mm_tb)

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

            open_invested_total += capital_invested
            open_current_val_total += curr_val
            unrealized_pnl_total += unrealized_pnl

            cash_balance -= capital_invested

            bench_lot_val = capital_invested * (latest_nifty_close / nifty_buy_close) if nifty_buy_close > 0 else capital_invested
            bench_open_live_val_total += bench_lot_val

            lot_return_pct = (((curr_price - b_price) / b_price) * 100) if b_price > 0 else 0.0
            bench_return_pct = (((latest_nifty_close - nifty_buy_close) / nifty_buy_close) * 100) if nifty_buy_close > 0 else 0.0
            
            if lot_return_pct > bench_return_pct:
                trades_beating_bench += 1
            evaluated_bench_trades += 1

            realized_r = 0.0
            r_num = 0.0

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

            nifty_sell_close = get_nifty500_price_fallback(date_s, df_mm_tb)
            bench_lot_pnl = capital_invested * ((nifty_sell_close - nifty_buy_close) / nifty_buy_close) if nifty_buy_close > 0 else 0.0
            bench_realized_pnl_total += bench_lot_pnl

            lot_return_pct = (((sold_price - b_price) / b_price) * 100) if b_price > 0 else 0.0
            bench_return_pct = (((nifty_sell_close - nifty_buy_close) / nifty_buy_close) * 100) if nifty_buy_close > 0 else 0.0
            
            if lot_return_pct > bench_return_pct:
                trades_beating_bench += 1
            evaluated_bench_trades += 1

            r_num = realized_pnl / (sh_sold * unit_risk) if (sh_sold * unit_risk) > 0 else 0.0
            realized_r = r_num

        tot_return_inr = realized_pnl + unrealized_pnl
        abs_return_pct = (
            ((curr_price - b_price) / b_price) * 100 if b_price > 0 else 0.0
        )

        processed_trade_rows.append({
            "trade_id": tr.get("id"),
            "S.No._num": sl_num_shared,
            "Signature": sig,
            "Ticker": ticker,
            "Shares Bought": sh_bought,
            "Date Bought": date_b,
            "Buy Price (₹)": b_price,
            "Initial SL (₹)": sl_price,
            "Unit Risk (₹)": unit_risk,
            "Current / Sold Price (₹)": curr_price,
            "Gain / Loss (₹)": tot_return_inr,
            "Realized R": f"{realized_r:+.2f}R" if status == "CLOSED" else "0.00R",
            "Realized R Num": r_num,
            "Shares Sold": sh_sold,
            "Booked Value (₹)": booked_val,
            "Realised Gains (₹)": realized_pnl,
            "Shares Remaining": sh_rem,
            "Abs Return %": abs_return_pct,
            "Unrealised Value (₹)": unrealized_pnl,
            "Capital Invested (₹)": capital_invested,
            "Current Value (₹)": curr_val,
            "Date Sold": date_s,
            "raw_status": status,
        })

    total_portfolio_nav = cash_balance + open_current_val_total

    group_metrics = {}
    for r in processed_trade_rows:
        sig = r["Signature"]
        if sig not in group_metrics:
            group_metrics[sig] = {
                "total_capital": 0.0,
                "total_gain_loss": 0.0,
                "total_shares_rem": 0,
                "total_shares_sold": 0,
                "rows_processed": 0
            }
        group_metrics[sig]["total_capital"] += r["Capital Invested (₹)"]
        group_metrics[sig]["total_gain_loss"] += r["Gain / Loss (₹)"]
        group_metrics[sig]["total_shares_rem"] += r["Shares Remaining"]
        group_metrics[sig]["total_shares_sold"] += r["Shares Sold"]

    open_risk_total = 0.0

    for r in processed_trade_rows:
        sig = r["Signature"]
        tot_cap = group_metrics[sig]["total_capital"]
        tot_gl = group_metrics[sig]["total_gain_loss"]
        tot_rem = group_metrics[sig]["total_shares_rem"]
        tot_sold = group_metrics[sig]["total_shares_sold"]

        r["Avg Ret %"] = (tot_gl / tot_cap * 100) if tot_cap > 0 else 0.0
        r["Total Ret (₹)"] = tot_gl

        is_first_row = (group_metrics[sig]["rows_processed"] == 0)
        group_metrics[sig]["rows_processed"] += 1

        if is_first_row:
            if tot_rem == 0:
                if tot_gl > 0:
                    r["Status"] = "🔵 WIN"
                elif tot_gl < 0:
                    r["Status"] = "🔴 LOSS"
                else:
                    r["Status"] = "⚪ SCRATCH"
                r["Portfolio Risk %"] = None
            else:
                r["Status"] = "🟢 OPEN"
                if tot_sold > 0:
                    r["Portfolio Risk %"] = 0.0
                else:
                    lot_risk_inr = r["Shares Remaining"] * r["Unit Risk (₹)"]
                    r_pct = (lot_risk_inr / max(total_portfolio_nav, 1.0)) * 100
                    r["Portfolio Risk %"] = r_pct
                    open_risk_total += lot_risk_inr
        else:
            r["Status"] = "PARTIAL EXIT"
            r["Portfolio Risk %"] = None

    portfolio_heat_pct = (
        (open_risk_total / max(total_portfolio_nav, 1.0)) * 100
    )

    cash_pct = (cash_balance / max(total_portfolio_nav, 1.0)) * 100 if total_portfolio_nav > 0 else 0.0
    invested_pct = (open_current_val_total / max(total_portfolio_nav, 1.0)) * 100 if total_portfolio_nav > 0 else 0.0
    net_return_inr = total_portfolio_nav - starting_cap

    portfolio_net_return_pct = (
        (net_return_inr / starting_cap) * 100
        if starting_cap > 0
        else 0.0
    )

    bench_cash_allocated = starting_cap - open_invested_total
    bench_total_nav = bench_cash_allocated + bench_open_live_val_total + bench_realized_pnl_total
    
    bench_net_return_pct = (
        ((bench_total_nav - starting_cap) / starting_cap) * 100
        if starting_cap > 0
        else 0.0
    )
    alpha_pct = portfolio_net_return_pct - bench_net_return_pct
    alpha_inr = total_portfolio_nav - bench_total_nav

    # --- TOP METRICS BAR ---
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("Starting Capital", f"₹{starting_cap:,.2f}", f"Cash: ₹{cash_balance:,.2f} ({cash_pct:.1f}%)")
    with c2:
        net_inr_sign = "+" if net_return_inr >= 0 else "-"
        st.metric("Portfolio NAV", f"₹{total_portfolio_nav:,.2f}", f"{net_inr_sign}₹{abs(net_return_inr):,.2f} ({portfolio_net_return_pct:+.2f}%) Net")
    with c3:
        st.metric("Open Invested (Cost)", f"₹{open_invested_total:,.2f}", f"Live: ₹{open_current_val_total:,.2f} ({invested_pct:.1f}%)")
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
    st.caption("🏆 **Nifty 500 Shadow Benchmark Comparison (Dollar-Weighted Opportunity Cost):**")
    ac1, ac2, ac3, ac4 = st.columns(4)
    with ac1:
        st.metric("Portfolio Net Return", f"{portfolio_net_return_pct:+.2f}%")
    with ac2:
        st.metric("Nifty 500 Shadow Return", f"{bench_net_return_pct:+.2f}%")
    with ac3:
        alpha_inr_sign = "+" if alpha_inr >= 0 else "-"
        st.metric("Alpha (Excess Return)", f"{alpha_pct:+.2f}%", f"{alpha_inr_sign}₹{abs(alpha_inr):,.2f}")
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
    
    # Strict secondary sorting for display table to ensure newest dates are top
    if not df_tb_display.empty:
        df_tb_display["Sort_Date"] = pd.to_datetime(df_tb_display["Date Bought"], errors="coerce")
        df_tb_display = df_tb_display.sort_values(by=["Sort_Date", "Ticker"], ascending=[False, True]).drop(columns=["Sort_Date"]).reset_index(drop=True)

    tb_filter = st.session_state.get("tb_display_filter", "All Positions")

    if not df_tb_display.empty:
        if tb_filter == "Open Positions Only":
            df_tb_display = df_tb_display[df_tb_display["Status"].str.contains("OPEN")].reset_index(drop=True)
        elif tb_filter == "Closed Trades Only":
            df_tb_display = df_tb_display[df_tb_display["Status"].str.contains("WIN|LOSS|SCRATCH|PARTIAL")].reset_index(drop=True)

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
            
            b_shares = st.number_input("Shares Bought:", min_value=1, value=1, step=1)
            b_price = st.number_input("Buy Price (₹):", min_value=0.0, value=0.0, step=1.0)
            b_sl = st.number_input("Initial Stop Loss Price (₹):", min_value=0.0, value=0.0, step=1.0)

            entry_chart_url = st.text_input("Entry Chart Image URL(s) (Optional):", placeholder="Paste TradingView image link(s)...")
            trade_notes = st.text_area("Trade Notes & Thesis (Optional):", placeholder="Why are you taking this setup? What is the trigger?")

            outlay = b_shares * b_price
            risk_amount = b_shares * (b_price - b_sl)
            st.caption(f"💡 Total Outlay: **₹{outlay:,.2f}** | Initial Risk (1R): **₹{risk_amount:,.2f}**")

            if st.form_submit_button("💾 Save Position Entry", use_container_width=True):
                if final_ticker and b_price > 0:
                    date_s_str = b_date.strftime("%Y-%m-%d")
                    nifty_close_buy = get_nifty500_price_fallback(date_s_str, df_mm_tb)

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
                        "entry_chart_url": entry_chart_url,
                        "trade_notes": trade_notes,
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
            
            exit_chart_url = st.text_input("Exit Chart Image URL(s) (Optional):", placeholder="Paste TradingView image link(s)...")
            
            # Use appending logic so original notes are never erased
            st.caption("📝 Original notes are preserved automatically. Add new exit notes below:")
            new_exit_notes = st.text_area("Exit Notes / Lessons (will be appended):", placeholder="What did you do well? What could be improved?")

            if st.form_submit_button("💾 Execute Exit / Partial Sell", use_container_width=True):
                date_s_str = s_date.strftime("%Y-%m-%d")
                nifty_close_sell = get_nifty500_price_fallback(date_s_str, df_mm_tb)
                
                # Safely construct the new combined notes
                final_notes = sel_lot.get("trade_notes", "")
                if new_exit_notes.strip():
                    prefix = "\n\n--- Exit Notes ---\n" if final_notes.strip() else ""
                    final_notes += prefix + new_exit_notes.strip()

                if s_shares == max_sell:
                    sel_lot["status"] = "CLOSED"
                    sel_lot["shares_sold"] += s_shares
                    sel_lot["sell_price"] = float(s_price)
                    sel_lot["date_sold"] = date_s_str
                    sel_lot["nifty500_sell_close"] = nifty_close_sell
                    sel_lot["exit_chart_url"] = exit_chart_url
                    sel_lot["trade_notes"] = final_notes
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
                        "nifty500_buy_close": sel_lot.get("nifty500_buy_close", get_nifty500_price_fallback(sel_lot["date_bought"], df_mm_tb)),
                        "nifty500_sell_close": nifty_close_sell,
                        "entry_chart_url": sel_lot.get("entry_chart_url", ""),
                        "exit_chart_url": exit_chart_url,
                        "trade_notes": final_notes,
                    }
                    sel_lot["shares_bought"] -= s_shares
                    # Original open lot keeps its original notes without the exit context
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

            with st.expander("🖼️ Chart URLs & Trade Notes", expanded=False):
                e_entry_url = st.text_input("Entry Chart URL(s)", sel_tr.get("entry_chart_url", ""))
                e_exit_url = st.text_input("Exit Chart URL(s)", sel_tr.get("exit_chart_url", ""))
                e_notes = st.text_area("Trade Notes", sel_tr.get("trade_notes", ""))

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
                sel_tr["entry_chart_url"] = e_entry_url
                sel_tr["exit_chart_url"] = e_exit_url
                sel_tr["trade_notes"] = e_notes
                save_tradebook(st.session_state.tradebook)
                st.success("Trade updated successfully!")
                st.rerun()
            if submit_del:
                st.session_state.tradebook["trades"].pop(idx)
                save_tradebook(st.session_state.tradebook)
                st.success("Trade deleted successfully!")
                st.rerun()

    @st.dialog("👁️ Post-Trade Review Studio", width="large")
    def show_review_modal(initial_t_id):
        # Manage Session State for Interactive Navigation
        if "review_modal_init_id" not in st.session_state or st.session_state["review_modal_init_id"] != initial_t_id:
            st.session_state["review_modal_init_id"] = initial_t_id
            st.session_state["review_modal_current_id"] = initial_t_id
            
        curr_id = st.session_state["review_modal_current_id"]
        
        # Pull display order mathematically to sync with table
        trade_ids = [r["trade_id"] for r in df_tb_display.to_dict('records')]
        
        if curr_id not in trade_ids:
            st.error("Trade data not found.")
            return
            
        curr_idx = trade_ids.index(curr_id)
        
        # Interactive Navigation Bar
        nav_col1, nav_col2, nav_col3 = st.columns([1.5, 2, 1.5])
        with nav_col1:
            if st.button("⬅️ Previous Trade", disabled=(curr_idx == 0), use_container_width=True):
                st.session_state["review_modal_current_id"] = trade_ids[curr_idx - 1]
                st.rerun()
        with nav_col2:
            st.markdown(f"<div style='text-align: center; padding-top: 5px; color: #a0aec0;'><b>Reviewing Trade {curr_idx + 1} of {len(trade_ids)}</b></div>", unsafe_allow_html=True)
        with nav_col3:
            if st.button("Next Trade ➡️", disabled=(curr_idx == len(trade_ids) - 1), use_container_width=True):
                st.session_state["review_modal_current_id"] = trade_ids[curr_idx + 1]
                st.rerun()
                
        st.markdown("---")
        
        # Fetch Target Trade Data
        sel_tr = next((tr for tr in st.session_state.tradebook["trades"] if tr.get("id") == curr_id), None)
        p_row = next((r for r in df_tb_display.to_dict('records') if r["trade_id"] == curr_id), None)
        
        st.subheader(f"🔍 {p_row['Ticker']} | {p_row['Status']}")
        
        try:
            d1 = pd.to_datetime(p_row['Date Bought'])
            d2 = pd.to_datetime(p_row['Date Sold'] if p_row['Date Sold'] != 'N/A' else date.today())
            days_held = max(1, (d2 - d1).days)
        except Exception:
            days_held = 1
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Abs Return %", f"{p_row['Abs Return %']:+.2f}%")
        m2.metric("Realized R", p_row['Realized R'])
        m3.metric("Gain / Loss", f"₹{p_row['Gain / Loss (₹)']:,.2f}")
        m4.metric("Days Held", f"{days_held}d")

        st.markdown("---")
        
        # Tabs for Charts and Notes Layout
        tab1, tab2, tab3 = st.tabs(["🟢 Entry Charts", "🔴 Exit Charts", "📝 Trade Notes & Lessons"])
        
        # Robust Multi-Image Rendering Engine
        def render_multi_charts(url_string):
            if not url_string:
                st.info("No chart URLs provided for this stage.")
                return
                
            urls = [u.strip() for u in re.split(r'[,;\s\n]+', url_string) if u.strip().startswith('http')]
            if not urls:
                st.info("No valid URLs found. Make sure links start with http:// or https://")
                return
                
            for i, url in enumerate(urls):
                st.markdown(
                    f'<img src="{url}" style="width: 100%; border-radius: 8px; margin-bottom: 15px; border: 1px solid #334155;">', 
                    unsafe_allow_html=True
                )
                st.caption(f"🔗 [Open Chart {i+1} in Browser]({url})")
        
        with tab1:
            render_multi_charts(sel_tr.get("entry_chart_url", ""))
            
        with tab2:
            render_multi_charts(sel_tr.get("exit_chart_url", ""))
            
        with tab3:
            with st.form("trade_notes_form_" + curr_id):
                notes = st.text_area("📝 Trade Notes & Lessons Learned:", value=sel_tr.get("trade_notes", ""), height=250)
                if st.form_submit_button("💾 Save Notes", use_container_width=True):
                    sel_tr["trade_notes"] = notes
                    save_tradebook(st.session_state.tradebook)
                    st.success("Notes saved successfully!")
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
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5, ctrl_col6 = st.columns([1.1, 1.1, 1.1, 1.1, 1.1, 2.2])
    with ctrl_col1:
        if st.button("➕ Log New Buy", type="primary", use_container_width=True): show_buy_modal()
    with ctrl_col2:
        if st.button("➖ Log Exit", type="secondary", use_container_width=True): show_sell_modal(selected_trade_id)
    with ctrl_col3:
        if st.button("✏️ Edit", type="secondary", use_container_width=True, disabled=(selected_trade_id is None)): show_edit_modal(selected_trade_id)
    with ctrl_col4:
        if st.button("👁️ Review", type="secondary", use_container_width=True, disabled=(selected_trade_id is None)): show_review_modal(selected_trade_id)
    with ctrl_col5:
        if st.button("⚙️ Config", type="secondary", use_container_width=True): show_config_modal()
    with ctrl_col6:
        st.radio("Display Filter:", options=["All Positions", "Open Positions Only", "Closed Trades Only"], horizontal=True, key="tb_display_filter", label_visibility="collapsed")

    if df_tb_display.empty:
        st.info("Your Tradebook is empty! Click **'➕ Log New Buy'** above to record your first position.")
    else:
        if total_portfolio_nav > 0:
            df_tb_display["Allocation %"] = df_tb_display["Current Value (₹)"].apply(
                lambda v: (v / total_portfolio_nav) * 100 if v > 0 else 0.0
            )
        else:
            df_tb_display["Allocation %"] = 0.0

        float_cols_2dec = [
            "Buy Price (₹)", "Initial SL (₹)", "Current / Sold Price (₹)",
            "Gain / Loss (₹)", "Booked Value (₹)", "Realised Gains (₹)",
            "Abs Return %", "Avg Ret %", "Total Ret (₹)", "Unrealised Value (₹)", 
            "Capital Invested (₹)", "Current Value (₹)", "Allocation %", "Portfolio Risk %"
        ]
        for fc in float_cols_2dec:
            if fc in df_tb_display.columns:
                df_tb_display[fc] = pd.to_numeric(df_tb_display[fc], errors="coerce").round(2)

        seen_sigs = set()
        sno_display_list = []
        avg_ret_list = []
        tot_ret_list = []
        port_risk_list = []
        for idx, row in df_tb_display.iterrows():
            sig = row["Signature"]
            if sig not in seen_sigs:
                seen_sigs.add(sig)
                sno_display_list.append(str(row["S.No._num"]))
                avg_ret_list.append(row["Avg Ret %"])
                tot_ret_list.append(row["Total Ret (₹)"])
                port_risk_list.append(row["Portfolio Risk %"])
            else:
                sno_display_list.append("")
                avg_ret_list.append(None)
                tot_ret_list.append(None)
                port_risk_list.append(None)
                
        df_tb_display["S.No."] = sno_display_list
        df_tb_display["Avg Ret %"] = avg_ret_list
        df_tb_display["Total Ret (₹)"] = tot_ret_list
        df_tb_display["Portfolio Risk %"] = port_risk_list

        tb_table_columns = [
            "S.No.", "Ticker", "Status", "Shares Bought", "Date Bought", "Buy Price (₹)",
            "Initial SL (₹)", "Current / Sold Price (₹)", "Gain / Loss (₹)", "Realized R",
            "Shares Sold", "Booked Value (₹)", "Realised Gains (₹)", "Shares Remaining",
            "Abs Return %", "Unrealised Value (₹)", "Capital Invested (₹)", 
            "Current Value (₹)", "Allocation %", "Portfolio Risk %", "Avg Ret %", "Total Ret (₹)",
        ]

        st.subheader(f"📋 Tradebook ({len(df_tb_display)} Rows)")
        st.caption("💡 Select a row to Edit, Delete, Log an Exit, or Review your charts.")
        
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

        # =========================================================================
        # 📈 INSTITUTIONAL PERFORMANCE STUDIO & MULTI-YEAR MONTHLY ANALYTICS
        # =========================================================================
        st.markdown("---")
        st.subheader("📈 Institutional Performance Studio & Monthly Seasonality")
        st.caption("Monthly cumulative equity curve, multi-year performance matrix, and monthly execution breakdown.")

        all_closed_lots = [t for t in processed_trade_rows if t["Shares Sold"] > 0]
        
        if all_closed_lots:
            df_perf = pd.DataFrame(all_closed_lots)
            df_perf["Date_DT"] = pd.to_datetime(df_perf["Date Sold"], errors="coerce")
            df_perf = df_perf.dropna(subset=["Date_DT"]).sort_values(by="Date_DT", ascending=True)

            def get_holding_days(row):
                try:
                    d1 = datetime.strptime(row["Date Bought"], "%Y-%m-%d")
                    d2 = datetime.strptime(row["Date Sold"], "%Y-%m-%d")
                    return max(1, (d2 - d1).days)
                except Exception:
                    return 1

            df_perf["Holding_Days"] = df_perf.apply(get_holding_days, axis=1)
            df_perf["Year"] = df_perf["Date_DT"].dt.year
            df_perf["Month"] = df_perf["Date_DT"].dt.month

            # 1. Multi-Year Monthly P&L Matrix
            all_years = sorted(df_perf["Year"].unique().tolist(), reverse=True)
            month_abbrs = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            
            matrix_data = []
            for y in all_years:
                row_dict = {"Year": str(y)}
                y_pnl_cum = 0.0
                for m_idx, m_name in enumerate(month_abbrs, 1):
                    subset = df_perf[(df_perf["Year"] == y) & (df_perf["Month"] == m_idx)]
                    if not subset.empty:
                        m_pnl = subset["Realised Gains (₹)"].sum()
                        m_ret_pct = (m_pnl / starting_cap) * 100
                        row_dict[m_name] = f"{m_ret_pct:+.2f}%"
                        y_pnl_cum += m_pnl
                    else:
                        row_dict[m_name] = "-"
                y_tot_pct = (y_pnl_cum / starting_cap) * 100
                row_dict["YTD Total"] = f"{y_tot_pct:+.2f}%"
                matrix_data.append(row_dict)

            seasonality_row = {"Year": "Historical Avg"}
            for m_idx, m_name in enumerate(month_abbrs, 1):
                m_pnls = []
                for y in all_years:
                    sub = df_perf[(df_perf["Year"] == y) & (df_perf["Month"] == m_idx)]
                    if not sub.empty:
                        m_pnls.append((sub["Realised Gains (₹)"].sum() / starting_cap) * 100)
                if m_pnls:
                    avg_m = sum(m_pnls) / len(m_pnls)
                    seasonality_row[m_name] = f"{avg_m:+.2f}%"
                else:
                    seasonality_row[m_name] = "-"
            seasonality_row["YTD Total"] = "-"
            matrix_data.append(seasonality_row)

            df_matrix = pd.DataFrame(matrix_data)
            st.markdown("#### 🗓️ Multi-Year Monthly Return Matrix (% of Capital)")
            st.dataframe(df_matrix, use_container_width=True, hide_index=True, column_config=get_left_aligned_column_config(df_matrix.columns))

            # 2. Clean Monthly Cumulative Equity Curve
            df_monthly_agg = df_perf.groupby(["Year", "Month"]).agg(
                Monthly_PnL=("Realised Gains (₹)", "sum"),
                Date_Key=("Date_DT", "max")
            ).reset_index().sort_values("Date_Key")

            df_monthly_agg["Return_%"] = (df_monthly_agg["Monthly_PnL"] / starting_cap) * 100
            df_monthly_agg["Label"] = df_monthly_agg["Date_Key"].dt.strftime("%b %Y")

            x_labels = df_monthly_agg["Label"].tolist()
            cum_vals = list(df_monthly_agg["Return_%"].cumsum())

            fig_equity = go.Figure()
            
            fig_equity.add_trace(
                go.Scatter(
                    x=x_labels,
                    y=cum_vals,
                    mode="lines+markers",
                    name="Cumulative P&L %",
                    line=dict(color="#38bdf8", width=3),
                    marker=dict(size=8, color="#38bdf8"),
                    hovertemplate="<b>%{x}</b><br>Cumulative P&L: %{y:+.2f}%<extra></extra>",
                )
            )

            fig_equity.update_layout(
                title="<b>Monthly Cumulative P&L % Growth Curve</b>",
                template="plotly_dark",
                height=320,
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20),
                xaxis=dict(showgrid=True, gridcolor="#1e293b"),
                yaxis=dict(showgrid=True, gridcolor="#1e293b", ticksuffix="%"),
            )
            fig_equity.add_hline(y=0, line_dash="solid", line_color="#64748b", opacity=0.8)

            st.plotly_chart(fig_equity, use_container_width=True)

            # 3. Monthly Risk & Execution Tracker Matrix
            st.markdown("#### 🎯 Monthly Execution & Risk-Reward Breakdown")
            
            monthly_groups = list(df_perf.groupby(["Year", "Month"]))
            monthly_groups.sort(key=lambda x: (x[0][0], x[0][1]), reverse=True)

            tracker_rows = []
            m_trades_list = []
            m_total_r_list = []
            m_rrr_list = []
            m_win_pct_list = []
            m_avg_gain_list = []
            m_avg_loss_list = []
            m_max_gain_list = []
            m_max_loss_list = []
            m_days_gain_list = []
            m_days_loss_list = []

            for (y, m), group in monthly_groups:
                m_label = group["Date_DT"].iloc[0].strftime("%b %Y")
                trades_cnt = len(group)
                tot_r = group["Realized R Num"].sum()
                
                wins = group[group["Realised Gains (₹)"] > 0]
                losses = group[group["Realised Gains (₹)"] <= 0]
                win_pct = (len(wins) / trades_cnt) * 100 if trades_cnt > 0 else 0.0
                
                avg_gain = wins["Abs Return %"].mean() if not wins.empty else 0.0
                avg_loss = abs(losses["Abs Return %"].mean()) if not losses.empty else 0.0
                rrr = (avg_gain / avg_loss) if avg_loss > 0 else avg_gain
                
                biggest_gain = group["Abs Return %"].max()
                biggest_loss = group["Abs Return %"].min()
                
                avg_days_win = wins["Holding_Days"].mean() if not wins.empty else 0.0
                avg_days_loss = losses["Holding_Days"].mean() if not losses.empty else 0.0
                
                m_trades_list.append(trades_cnt)
                m_total_r_list.append(tot_r)
                m_rrr_list.append(rrr)
                m_win_pct_list.append(win_pct)
                m_avg_gain_list.append(avg_gain)
                m_avg_loss_list.append(avg_loss)
                m_max_gain_list.append(biggest_gain)
                m_max_loss_list.append(biggest_loss)
                m_days_gain_list.append(avg_days_win)
                m_days_loss_list.append(avg_days_loss)

                tracker_rows.append({
                    "Month": m_label,
                    "Trades": str(trades_cnt),
                    "Total R": f"{tot_r:+.2f}R",
                    "RRR (Payoff)": f"{rrr:.2f}x",
                    "Win %": f"{win_pct:.1f}%",
                    "Avg Gain %": f"+{avg_gain:.2f}%",
                    "Avg Loss %": f"-{avg_loss:.2f}%",
                    "Biggest Gain": f"{biggest_gain:+.2f}%",
                    "Biggest Loss": f"{biggest_loss:+.2f}%",
                    "Avg Days Gain": f"{avg_days_win:.1f}d",
                    "Avg Days Loss": f"{avg_days_loss:.1f}d",
                })

            avg_trades = np.mean(m_trades_list) if m_trades_list else 0.0
            avg_tot_r = np.mean(m_total_r_list) if m_total_r_list else 0.0
            avg_rrr = np.mean(m_rrr_list) if m_rrr_list else 0.0
            avg_win_pct_m = np.mean(m_win_pct_list) if m_win_pct_list else 0.0
            avg_gain_m = np.mean(m_avg_gain_list) if m_avg_gain_list else 0.0
            avg_loss_m = np.mean(m_avg_loss_list) if m_avg_loss_list else 0.0
            avg_max_gain = np.mean(m_max_gain_list) if m_max_gain_list else 0.0
            avg_max_loss = np.mean(m_max_loss_list) if m_max_loss_list else 0.0
            avg_days_gain_m = np.mean(m_days_gain_list) if m_days_gain_list else 0.0
            avg_days_loss_m = np.mean(m_days_loss_list) if m_days_loss_list else 0.0

            tracker_rows.append({
                "Month": "Average",
                "Trades": f"{avg_trades:.1f}",
                "Total R": f"{avg_tot_r:+.2f}R",
                "RRR (Payoff)": f"{avg_rrr:.2f}x",
                "Win %": f"{avg_win_pct_m:.1f}%",
                "Avg Gain %": f"+{avg_gain_m:.2f}%",
                "Avg Loss %": f"-{avg_loss_m:.2f}%",
                "Biggest Gain": f"{avg_max_gain:+.2f}%",
                "Biggest Loss": f"{avg_max_loss:+.2f}%",
                "Avg Days Gain": f"{avg_days_gain_m:.1f}d",
                "Avg Days Loss": f"{avg_days_loss_m:.1f}d",
            })

            df_monthly_tracker = pd.DataFrame(tracker_rows)
            st.dataframe(df_monthly_tracker, use_container_width=True, hide_index=True, column_config=get_left_aligned_column_config(df_monthly_tracker.columns))

        # --- INSTITUTIONAL PERFORMANCE ANALYTICS SUMMARY ---
        st.markdown("---")
        st.subheader("📊 Performance Analytics & Risk Metrics")

        fully_closed_setups = [
            t for t in processed_trade_rows
            if "WIN" in str(t.get("Status", "")) or "LOSS" in str(t.get("Status", "")) or "SCRATCH" in str(t.get("Status", ""))
        ]
        
        fully_closed_setups = sorted(
            fully_closed_setups, 
            key=lambda x: x.get("Date Sold", "1900-01-01"), 
            reverse=True
        )
        
        total_closed = len(fully_closed_setups)
        unique_setups = len(trade_signatures)
        active_setups = len(set(t["Signature"] for t in processed_trade_rows if "OPEN" in t["Status"]))

        if total_closed > 0:
            wins = [t for t in fully_closed_setups if t["Total Ret (₹)"] > 0]
            losses = [t for t in fully_closed_setups if t["Total Ret (₹)"] <= 0]
            win_count = len(wins)
            loss_count = len(losses)
            win_rate = (win_count / total_closed) * 100

            avg_win_inr = sum(t["Total Ret (₹)"] for t in wins) / win_count if win_count > 0 else 0.0
            avg_loss_inr = abs(sum(t["Total Ret (₹)"] for t in losses)) / loss_count if loss_count > 0 else 0.0
            avg_win_pct = sum(t["Avg Ret %"] for t in wins) / win_count if win_count > 0 else 0.0
            avg_loss_pct = abs(sum(t["Avg Ret %"] for t in losses)) / loss_count if loss_count > 0 else 0.0

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
            for t in fully_closed_setups:
                is_win = t["Total Ret (₹)"] > 0
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
        
        if len(all_closed_lots) == 0:
            st.info("No closed trades available to generate the Trading Calendar yet.")
        else:
            df_closed_cal = pd.DataFrame(all_closed_lots)
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
