# Allocations and Returns
    cash_pct = (cash_balance / max(total_portfolio_nav, 1.0)) * 100 if total_portfolio_nav > 0 else 0.0
    invested_pct = (open_current_val_total / max(total_portfolio_nav, 1.0)) * 100 if total_portfolio_nav > 0 else 0.0
    net_return_inr = total_portfolio_nav - starting_cap

    # --- TOP METRICS BAR ---
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric(
            "Starting Capital", 
            f"₹{starting_cap:,.2f}", 
            f"Cash: ₹{cash_balance:,.2f} ({cash_pct:.1f}%)"
        )
    with c2:
        net_inr_sign = "+" if net_return_inr >= 0 else "-"
        st.metric(
            "Portfolio NAV", 
            f"₹{total_portfolio_nav:,.2f}", 
            f"{net_inr_sign}₹{abs(net_return_inr):,.2f} ({portfolio_net_return_pct:+.2f}%) Net"
        )
    with c3:
        st.metric(
            "Open Invested (Cost)", 
            f"₹{open_invested_total:,.2f}", 
            f"Live: ₹{open_current_val_total:,.2f} ({invested_pct:.1f}%)"
        )
    with c4:
        st.metric(
            "Realized P&L", 
            f"₹{realized_pnl_total:,.2f}", 
            f"Unrealized: ₹{unrealized_pnl_total:,.2f}"
        )
    with c5:
        heat_color = (
            "🟢 SAFE"
            if portfolio_heat_pct <= 5.0
            else "🟡 MODERATE" if portfolio_heat_pct <= 7.0 else "🔴 HIGH"
        )
        st.metric("Portfolio Heat %", f"{portfolio_heat_pct:.2f}%", heat_color)
