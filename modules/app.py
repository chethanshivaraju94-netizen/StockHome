import streamlit as st
from modules.config import TABLE_CUSTOM_CSS
from modules.state import init_session_state

st.set_page_config(
    page_title="India Equities Screener & Watchlist Studio",
    page_icon="📈",
    layout="wide",
)

st.markdown(TABLE_CUSTOM_CSS, unsafe_allow_html=True)
init_session_state()

st.title("📈 India Equities Screener & Watchlist Studio")
st.markdown(
    "Professional **CAN SLIM Screener**, **Hierarchical Sector Rotation**, "
    "**Multi-Watchlist Studio**, and **Tradebook Risk Journal**."
)

# Render main tabs
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
