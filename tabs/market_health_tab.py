import time
import streamlit as st
from modules.data import load_market_monitor_data, load_sector_monitor_data
from modules.styling import style_market_monitor, style_sector_heatmap, style_rotation_tracker
from modules.ai_analyst import run_gemini_market_awareness, create_pdf_bytes

def render_market_health_tab():
    st.subheader("🏥 Market Health & Sector Rotation Studio")
    st.markdown(
        "Automated **Nifty 500 Breadth Monitor**, **27-Sector CAN SLIM Rotation"
        " Engine**, and **AI Situational Awareness Intelligence**."
    )

    tab_ai_intel, tab_mm, tab_sector_heat, tab_sector_rot = st.tabs([
        "🎯 Daily AI Situational Awareness & Action Plan",
        "📈 NSE Market Breadth Monitor",
        "🔥 Sector RS Heatmap",
        "📊 Historical Rotation Tracker",
    ])

    df_mm = load_market_monitor_data()
    df_heat, df_rot = load_sector_monitor_data()

    # ------------------------------------------
    # SUB-TAB 4A: DAILY AI SITUATIONAL AWARENESS BRIEFING
    # ------------------------------------------
    with tab_ai_intel:
        st.subheader("🧠 Daily Market & Sector Situational Awareness")
        st.caption(
            "Synthesizes Nifty 500 Breadth Thrusts, 27-Sector RS Velocity, and"
            " Active Screener Scan Clusters to produce an actionable institutional"
            " trading plan."
        )

        today_str = time.strftime("%Y-%m-%d")
        latest_briefing = st.session_state.market_briefings.get(today_str)

        b_col1, b_col2 = st.columns([1.8, 1.2])

        with b_col1:
            if latest_briefing:
                st.success(f"✅ Active Briefing Loaded for Date: **{today_str}**")
            else:
                st.info(
                    f"No AI Briefing generated for **{today_str}** yet. Click the button"
                    " on the right to synthesize today's data!"
                )

        with b_col2:
            run_briefing_btn = st.button(
                "🔄 Generate / Refresh Today's AI Briefing Now",
                type="primary",
                use_container_width=True,
            )

        if run_briefing_btn:
            with st.status(
                "🤖 Synthesizing Market Breadth, Sector RS Velocities & Scan"
                " Clusters...",
                expanded=True,
            ) as status_box:
                scan_summary = st.session_state.get("active_scan_summary", {})
                latest_briefing = run_gemini_market_awareness(
                    df_mm, df_heat, df_rot, scan_summary, status_log=status_box
                )
                if latest_briefing:
                    status_box.update(
                        label="✅ Briefing Complete! Refreshing View...",
                        state="complete",
                    )
                    time.sleep(1)
                    st.rerun()

        if latest_briefing:
            st.markdown("---")
            st.markdown(latest_briefing.get("briefing_md", ""))
            st.markdown("---")

            pdf_bytes_briefing = create_pdf_bytes(
                f"Market_Awareness_{today_str}", latest_briefing.get("briefing_md", "")
            )
            st.download_button(
                label="📥 Download Daily Market Awareness Briefing (PDF)",
                data=pdf_bytes_briefing,
                file_name=f"NSE_Market_Situational_Awareness_{today_str}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    # ------------------------------------------
    # SUB-TAB 4B: NSE MARKET MONITOR
    # ------------------------------------------
    with tab_mm:
        if not df_mm.empty:
            st.markdown(
                f"#### 📊 Nifty Total Market Breadth & VCP Indicators ({len(df_mm)} Days)"
            )

            latest = df_mm.iloc[0] if len(df_mm) > 0 else {}
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric(
                    "Latest Nifty 500 Close",
                    f"{latest.get('Nifty 500 Close', 'N/A')}",
                    f"{latest.get('Nifty 500 Chg %', 0)}%",
                )
            with c2:
                st.metric("5-Day Thrust Ratio", f"{latest.get('5 Day Ratio', 'N/A')}")
            with c3:
                st.metric("10-Day Thrust Ratio", f"{latest.get('10 Day Ratio', 'N/A')}")
            with c4:
                st.metric("A/D Ratio", f"{latest.get('A/D Ratio', 'N/A')}")

            styled_mm = style_market_monitor(df_mm)
            st.table(styled_mm)
        else:
            st.info(
                "Market Monitor data not available yet. Ensure GitHub tokens are set in Secrets."
            )
            if st.button("🔄 Retry Fetching Market Monitor Now", key="retry_mm_btn", type="primary"):
                load_market_monitor_data.clear()
                st.rerun()

    # ------------------------------------------
    # SUB-TAB 4C: SECTOR RS HEATMAP
    # ------------------------------------------
    with tab_sector_heat:
        if not df_heat.empty:
            st.markdown("#### 🔥 27-Sector CAN SLIM Relative Strength Heatmap (Ranked by 65D RS)")
            st.caption(
                "💡 **Velocity Legend:** Positive (+) values indicate upward rank acceleration; Negative (-) indicate loss of relative momentum."
            )
            styled_heat = style_sector_heatmap(df_heat)
            st.table(styled_heat)
        else:
            st.info("Sector Heatmap data not available yet.")
            if st.button("🔄 Retry Fetching Sector Data Now", key="retry_sec_btn", type="primary"):
                load_sector_monitor_data.clear()
                st.rerun()

    # ------------------------------------------
    # SUB-TAB 4D: HISTORICAL ROTATION TRACKER
    # ------------------------------------------
    with tab_sector_rot:
        if not df_rot.empty:
            st.markdown("#### 📊 65-Day Historical Relative Strength Ranks (All Sectors)")
            st.caption("💡 Rank 1 = Strongest Relative Strength vs. Nifty 500 Benchmark (`^CRSLDX`).")
            styled_rot = style_rotation_tracker(df_rot)
            st.table(styled_rot)
        else:
            st.info("Rotation Tracker data not available yet.")
            if st.button("🔄 Retry Fetching Rotation Data Now", key="retry_rot_btn", type="primary"):
                load_sector_monitor_data.clear()
                st.rerun()

    st.markdown("---")
    with st.expander("⚡ Optional: Force Real-Time Scan Now (Bypass Daily Schedule)"):
        st.caption(
            "Your scheduled cronjob automatically pushes updated Excel files to GitHub every weekday. Click below only if you want to force an immediate intraday refresh of Streamlit's data cache."
        )
        if st.button("🔄 Clear Streamlit Data Cache & Reload", type="secondary"):
            st.cache_data.clear()
            st.success("✅ Data cache cleared! Reloading latest tables...")
            st.rerun()
