import streamlit as st
import pandas as pd
import yfinance as yf
from tradingview_screener import Query, col
from modules.styling import get_left_aligned_column_config

def run_tier2_sequential_analysis(yf_tickers, tv_to_yf_map, min_gap, min_vol, min_days, max_days, ema_prox):
    """
    Downloads historical data and runs the sequential pattern recognition based on user parameters.
    """
    if not yf_tickers:
        return pd.DataFrame()

    # Bulk download 60 days to get accurate 50-day volume average and 10 EMA
    data = yf.download(yf_tickers, period="60d", progress=False, threads=True)
    
    results = []
    
    for yf_sym in yf_tickers:
        try:
            if len(yf_tickers) > 1:
                df = pd.DataFrame({
                    'Open': data['Open'][yf_sym],
                    'High': data['High'][yf_sym],
                    'Low': data['Low'][yf_sym],
                    'Close': data['Close'][yf_sym],
                    'Volume': data['Volume'][yf_sym]
                })
            else:
                df = data.copy()
                
            df = df.dropna()
            if len(df) < 50:
                continue
            
            # Calculate Averages
            df['Vol_50SMA'] = df['Volume'].rolling(50).mean()
            df['EMA_10'] = df['Close'].ewm(span=10, adjust=False).mean()
            
            # Calculate Dailies
            df['Gap_Pct'] = (df['Open'] / df['Close'].shift(1)) - 1
            df['Vol_Spike'] = df['Volume'] / df['Vol_50SMA'].shift(1)
            
            # Slice the last 15 days to look for the anchor event
            recent_df = df.iloc[-15:]
            
            # Loop through recent days to find a valid anchor gap
            # We subtract min_days to ensure there is enough digestion after the gap
            for i in range(len(recent_df) - min_days):
                row = recent_df.iloc[i]
                
                # Check user-defined Gap and Volume parameters
                if row['Gap_Pct'] >= min_gap and row['Vol_Spike'] >= min_vol:
                    anchor_idx = recent_df.index[i]
                    digestion_df = df.loc[anchor_idx:]
                    
                    days_since = len(digestion_df) - 1
                    
                    # Ensure digestion period fits user criteria
                    if min_days <= days_since <= max_days:
                        anchor_low = digestion_df.iloc[0]['Low']
                        anchor_vol = digestion_df.iloc[0]['Volume']
                        
                        subsequent_df = digestion_df.iloc[1:]
                        
                        # Rule 1: Price must hold the gap day's low
                        if subsequent_df['Low'].min() >= anchor_low:
                            
                            # Rule 2: Volume Contraction (Avg volume during digestion < Gap day volume)
                            avg_sub_vol = subsequent_df['Volume'].mean()
                            if avg_sub_vol < anchor_vol:
                                
                                # Rule 3: Moving Average Catch-up
                                last_close = df['Close'].iloc[-1]
                                last_ema = df['EMA_10'].iloc[-1]
                                dist_to_ema = abs(last_close - last_ema) / last_ema
                                
                                if dist_to_ema <= ema_prox:
                                    results.append({
                                        "Ticker": tv_to_yf_map[yf_sym],
                                        "Anchor Date": anchor_idx.strftime('%Y-%m-%d'),
                                        "Gap Size": f"{row['Gap_Pct']*100:.1f}%",
                                        "Vol Spike": f"{row['Vol_Spike']:.1f}x",
                                        "Digestion Days": days_since,
                                        "Last Close": round(last_close, 2),
                                        "10 EMA": round(last_ema, 2),
                                        "EMA Proximity": f"{(last_close/last_ema - 1)*100:+.2f}%"
                                    })
                    # Stop searching older dates once the most recent valid anchor is found
                    break 
                    
        except Exception:
            continue
            
    return pd.DataFrame(results)

def render_power_play_tab():
    st.subheader("🔥 Episodic Pivot & Power Play Scanner")
    st.caption(
        "Tiered sequential scanner isolating Round 2 momentum setups. Identifies structural gaps "
        "on massive volume, followed by a tight volume-contraction digestion phase near the 10 EMA."
    )
    st.markdown("---")
    
    # Custom Parameter Inputs
    with st.expander("⚙️ Customize Scanner Parameters (Defaults set to Expert Standards)", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            p_gap = st.number_input("Min Gap Size (%)", min_value=1.0, max_value=20.0, value=5.0, step=0.5)
        with c2:
            p_vol = st.number_input("Min Volume Spike (x)", min_value=1.0, max_value=10.0, value=3.0, step=0.5)
        with c3:
            p_days = st.slider("Digestion Days (Min - Max)", min_value=1, max_value=20, value=(3, 7))
        with c4:
            p_ema = st.number_input("Max 10 EMA Distance (%)", min_value=0.5, max_value=15.0, value=3.5, step=0.5)

    col_info, col_btn = st.columns([3, 1])
    with col_info:
        st.info("💡 **Execution Logic:** Tier 1 queries Live TradingView breadth. Tier 2 downloads sequence footprints via yfinance.")
    with col_btn:
        run_scan = st.button("🚀 Run Sequential Scan", type="primary", use_container_width=True)

    if run_scan:
        with st.status("Initializing Two-Tier Scanner...", expanded=True) as status:
            try:
                # ==========================================
                # TIER 1: TradingView Liquidity & Broad Net
                # ==========================================
                st.write("📡 **Tier 1:** Querying Live Exchange Breadth (TradingView)...")
                
                # Dynamically set TV 1-Week change filter so it doesn't block custom gap sizes
                tv_min_perf = max(1.0, p_gap - 2.0) 

                q = (
                    Query()
                    .set_markets('india')
                    .select('name', 'exchange', 'close', 'volume')
                    .where(
                        col('change|1W') > tv_min_perf,  
                        col('close') > col('SMA50'),
                        col('close') > col('SMA200')
                    )
                )
                _, df_tv = q.get_scanner_data()
                
                if not df_tv.empty:
                    # Apply Turnover requirement in Pandas (Volume * Close > 10 Cr INR approx)
                    df_tv['turnover'] = df_tv['volume'] * df_tv['close']
                    df_tv = df_tv[df_tv['turnover'] > 100000000]

                if df_tv.empty:
                    status.update(label="No candidates passed Tier 1 liquidity filters.", state="error")
                    st.stop()
                    
                st.write(f"🎯 **Tier 1 Complete:** Found {len(df_tv)} highly liquid momentum candidates.")
                
                # ==========================================
                # TIER 2: YFinance Sequence Recognition
                # ==========================================
                st.write("🔬 **Tier 2:** Downloading footprints & running Volatility Contraction logic...")
                
                yf_tickers = []
                tv_to_yf_map = {}
                for _, row in df_tv.iterrows():
                    exc = row['exchange']
                    sym = row['name']
                    # Map NSE/BSE correctly for yfinance
                    yf_sym = f"{sym}.NS" if exc == "NSE" else f"{sym}.BO"
                    yf_tickers.append(yf_sym)
                    tv_to_yf_map[yf_sym] = f"{exc}:{sym}"
                
                # Pass custom UI parameters to the function
                df_results = run_tier2_sequential_analysis(
                    yf_tickers=yf_tickers, 
                    tv_to_yf_map=tv_to_yf_map, 
                    min_gap=p_gap / 100.0, 
                    min_vol=p_vol, 
                    min_days=p_days[0], 
                    max_days=p_days[1], 
                    ema_prox=p_ema / 100.0
                )
                
                if not df_results.empty:
                    status.update(label=f"Scan Complete! Found {len(df_results)} Round-2 Setup(s).", state="complete")
                else:
                    status.update(label=f"Scan Complete. No stocks met the {p_days[0]}-{p_days[1]} day digestion criteria.", state="complete")
            
            except Exception as e:
                status.update(label=f"Scanner Error: {e}", state="error")
                st.stop()
                
        # ==========================================
        # DISPLAY RESULTS
        # ==========================================
        if 'df_results' in locals() and not df_results.empty:
            st.subheader(f"🎯 Actionable Round 2 Setups ({len(df_results)})")
            st.dataframe(
                df_results, 
                use_container_width=True, 
                hide_index=True,
                column_config=get_left_aligned_column_config(df_results.columns.tolist())
            )
        elif 'df_results' in locals() and df_results.empty:
            st.warning("No stocks passed the custom Power Play criteria today. Cash is a position.")
