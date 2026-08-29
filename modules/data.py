import io
import os
import requests
import pandas as pd
import streamlit as st
import yfinance as yf
from tradingview_screener import Query, col
from modules.config import map_to_indian_classification

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", None)

EPS_Q_ALIASES = [
    "earnings_per_share_diluted_yoy_growth_fq",
    "earnings_per_share_fq_yoy_growth",
    "earnings_per_share_diluted_yoy_growth_quarterly",
    "basic_eps_yoy_growth_fq",
]

SALES_Q_ALIASES = [
    "revenue_yoy_growth_fq",
    "total_revenue_yoy_growth_fq",
    "revenue_yoy_growth_quarterly",
    "sales_yoy_growth_fq",
]

def coalesce_columns(df, col_list):
    res = pd.Series(index=df.index, dtype="float64")
    for c in col_list:
        if c in df.columns:
            s = pd.to_numeric(df[c], errors="coerce")
            res = res.fillna(s)
    return res

def clean_tv_date_col(val_series):
    num_s = pd.to_numeric(val_series, errors="coerce")
    num_valid = num_s.where(num_s > 0)
    dt_unix_s = pd.to_datetime(num_valid.where(num_valid <= 1e11), unit="s", errors="coerce")
    dt_unix_ms = pd.to_datetime(num_valid.where(num_valid > 1e11), unit="ms", errors="coerce")
    dt_unix = dt_unix_s.fillna(dt_unix_ms)
    dt_iso = pd.to_datetime(val_series, errors="coerce")
    dt_combined = dt_unix.fillna(dt_iso)
    return dt_combined.where(dt_combined >= pd.Timestamp("1980-01-01"), pd.NaT)

def add_clean_ipo_date_col(df):
    ipo_cols = [
        c for c in ["ipo_offer_date", "offer_date", "recent_ipo_date", "ipo_date", "listing_date"]
        if c in df.columns
    ]
    if ipo_cols:
        clean_dt_df = pd.DataFrame(index=df.index)
        for c in ipo_cols:
            clean_dt_df[c] = clean_tv_date_col(df[c])
        df["IPO_Date_DT"] = clean_dt_df.max(axis=1)
    else:
        df["IPO_Date_DT"] = pd.NaT
    df["IPO Date"] = df["IPO_Date_DT"].dt.strftime("%Y-%m-%d").fillna("N/A")
    return df

@st.cache_data(ttl=43200, show_spinner="⚡ Synchronizing Daily Circuit Price Bands...")
def get_nse_circuit_bands():
    symbol_to_band = {}
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
        }
        session = requests.Session()
        session.headers.update(headers)
        session.get("https://www.nseindia.com", timeout=5)
        url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
        res = session.get(url, timeout=6)
        if res.status_code == 200:
            data = res.json()
            for row in data.get("data", []):
                sym = str(row.get("symbol", "")).strip().upper()
                band_val = str(row.get("priceBand", "")).strip()
                if sym and band_val:
                    symbol_to_band[sym] = band_val
    except Exception:
        pass
    return symbol_to_band

def fetch_excel_file(filename):
    if os.path.exists(filename):
        return filename
    headers_list = []
    if GITHUB_TOKEN:
        headers_list.append({"User-Agent": "Mozilla/5.0", "Authorization": f"Bearer {GITHUB_TOKEN}"})
        headers_list.append({"User-Agent": "Mozilla/5.0", "Authorization": f"token {GITHUB_TOKEN}"})
    headers_list.append({"User-Agent": "Mozilla/5.0"})

    repos = ["chethanshivaraju94-netizen/nse-market-monitor", "chethanshivaraju94-netizen/India-equities-screener"]
    branches = ["main", "master"]

    for repo in repos:
        for branch in branches:
            url = f"https://raw.githubusercontent.com/{repo}/{branch}/{filename}"
            for headers in headers_list:
                try:
                    res = requests.get(url, headers=headers, timeout=10)
                    if res.status_code == 200:
                        return io.BytesIO(res.content)
                except Exception:
                    pass
    return None

@st.cache_data(ttl=3600, show_spinner="⚡ Fetching latest Market Health & Sector tables...")
def load_market_monitor_data():
    file_source = fetch_excel_file("NSE_Market_Monitor.xlsx")
    if file_source is None:
        return pd.DataFrame()
    try:
        df = pd.read_excel(file_source, sheet_name=0)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        return df
    except Exception as e:
        st.error(f"Could not parse Market Monitor file: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner="⚡ Fetching Sector Rotation & Heatmap tables...")
def load_sector_monitor_data():
    file_source = fetch_excel_file("NSE_Sector_Monitor.xlsx")
    if file_source is None:
        return pd.DataFrame(), pd.DataFrame()
    try:
        xls = pd.ExcelFile(file_source)
        df_heat = pd.read_excel(xls, sheet_name="Heatmap") if "Heatmap" in xls.sheet_names else pd.DataFrame()
        df_rot = pd.read_excel(xls, sheet_name="Rotation Tracker") if "Rotation Tracker" in xls.sheet_names else pd.DataFrame()
        if "Date" in df_rot.columns:
            df_rot["Date"] = pd.to_datetime(df_rot["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        return df_heat, df_rot
    except Exception as e:
        st.error(f"Could not parse Sector Monitor file: {e}")
        return pd.DataFrame(), pd.DataFrame()

def fetch_screener_data(exchanges, min_mcap, vol_period_days, ma_columns_to_fetch, limit_rows):
    if not exchanges:
        return pd.DataFrame()
    min_mcap_inr = min_mcap * 10_000_000
    tv_vol_col = f"average_volume_{vol_period_days}d_calc"
    select_cols = (
        ["name", "close", "change", "high", "low", "open", "volume", "market_cap_basic",
         tv_vol_col, "ADR", "price_52_week_high", "price_52_week_low", "exchange", "type",
         "industry", "sector", "index", "ipo_offer_date", "offer_date", "recent_ipo_date",
         "ipo_date", "listing_date", "Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.YTD", "Perf.Y"]
        + EPS_Q_ALIASES + SALES_Q_ALIASES
    )
    for c in ma_columns_to_fetch:
        if c not in select_cols:
            select_cols.append(c)
    q = (
        Query().set_markets("india")
        .select(*select_cols)
        .where(col("market_cap_basic") >= min_mcap_inr)
        .order_by("volume", ascending=False)
        .limit(limit_rows)
    )
    try:
        _, df = q.get_scanner_data()
        return df
    except Exception as e:
        st.error(f"Error fetching data from TradingView API: {e}")
        return pd.DataFrame()

def fetch_watchlist_enrichMENT(symbol_list):
    if not symbol_list:
        return pd.DataFrame()
    bare_names = [s.split(":")[-1].strip().upper() for s in symbol_list]
    select_cols = (
        ["name", "close", "change", "ADR", "market_cap_basic", "exchange", "industry", "sector",
         "index", "ipo_offer_date", "offer_date", "recent_ipo_date", "ipo_date", "listing_date",
         "Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.YTD", "Perf.Y"]
        + EPS_Q_ALIASES + SALES_Q_ALIASES
    )
    q = Query().set_markets("india").select(*select_cols).where(col("name").isin(bare_names)).limit(max(len(bare_names) * 5, 1500))
    try:
        _, df = q.get_scanner_data()
        if not df.empty:
            df["ADR_pct"] = ((df["ADR"] / df["close"]) * 100).round(2)
            df["Close"] = df["close"].round(2)
            df["Change %"] = df["change"].round(2)
            df["Market Cap (₹ Cr)"] = (df["market_cap_basic"] / 10_000_000).round(2)
            df["EPS Q YoY %"] = coalesce_columns(df, EPS_Q_ALIASES).round(2)
            df["Sales Q YoY %"] = coalesce_columns(df, SALES_Q_ALIASES).round(2)
            df = add_clean_ipo_date_col(df)
            if "Perf.W" in df.columns: df["Perf % 1W"] = pd.to_numeric(df["Perf.W"], errors="coerce").round(2)
            if "Perf.1M" in df.columns: df["Perf % 1M"] = pd.to_numeric(df["Perf.1M"], errors="coerce").round(2)
            if "Perf.3M" in df.columns: df["Perf % 3M"] = pd.to_numeric(df["Perf.3M"], errors="coerce").round(2)
            if "Perf.6M" in df.columns: df["Perf % 6M"] = pd.to_numeric(df["Perf.6M"], errors="coerce").round(2)
            if "Perf.YTD" in df.columns: df["Perf % YTD"] = pd.to_numeric(df["Perf.YTD"], errors="coerce").round(2)
            if "Perf.Y" in df.columns: df["Perf % 1Y"] = pd.to_numeric(df["Perf.Y"], errors="coerce").round(2)

            df = df.drop_duplicates(subset=["name"], keep="first")
            mapped_sectors, mapped_industries = [], []
            for _, row in df.iterrows():
                sec, ind = map_to_indian_classification(row.get("industry", ""), row.get("sector", ""))
                mapped_sectors.append(sec)
                mapped_industries.append(ind)
            df["Sector"] = mapped_sectors
            df["Industry"] = mapped_industries
        return df
    except Exception:
        return pd.DataFrame()

def fetch_nifty500_close_on_date(date_str, df_mm=None):
    try:
        if df_mm is not None and not df_mm.empty and "Date" in df_mm.columns and "Nifty 500 Close" in df_mm.columns:
            match = df_mm[df_mm["Date"] == date_str]
            if not match.empty:
                val = pd.to_numeric(match.iloc[0]["Nifty 500 Close"], errors="coerce")
                if pd.notna(val) and val > 0:
                    return float(val)
    except Exception:
        pass
    try:
        dt_obj = pd.to_datetime(date_str)
        p_start = int(dt_obj.timestamp())
        p_end = p_start + 86400 * 4
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/^CRSLDX?period1={p_start}&period2={p_end}&interval=1d"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if res.status_code == 200:
            data = res.json()
            quotes = data["chart"]["result"][0]["indicators"]["quote"][0]["close"]
            for q in quotes:
                if q is not None and q > 0:
                    return float(q)
    except Exception:
        pass
    return 23700.0

@st.cache_data(ttl=900, show_spinner=False)
def fetch_historical_data_yf_v7(symbols_tuple, period="3mo"):
    """
    V7: Reverted to the pristine, robust, native download.
    No artificial chunking, no over-engineered threading.
    Let yfinance handle the batching internally, ensuring stable column extraction.
    """
    tickers = []
    sym_map = {}
    for s in symbols_tuple:
        clean = str(s).split(":")[-1].strip().upper()
        yf_t = f"{clean}.BO" if "BSE" in str(s).upper() else f"{clean}.NS"
        tickers.append(yf_t)
        sym_map[yf_t] = s
        
    data_dict = {}
    if not tickers: 
        return data_dict, sym_map

    # Native yfinance download (fastest & most reliable)
    data = yf.download(tickers, period=period, progress=False)

    if data.empty: 
        return data_dict, sym_map

    if len(tickers) == 1:
        df_t = data.dropna(how='all')
        if not df_t.empty:
            data_dict[tickers[0]] = df_t
    else:
        for t in tickers:
            try:
                # The indestructible, version-agnostic column parser
                df_t = pd.DataFrame()
                if 'Open' in data: df_t['Open'] = data['Open'][t]
                if 'High' in data: df_t['High'] = data['High'][t]
                if 'Low' in data: df_t['Low'] = data['Low'][t]
                if 'Close' in data: df_t['Close'] = data['Close'][t]
                if 'Volume' in data: df_t['Volume'] = data['Volume'][t]

                df_t = df_t.dropna(how='all')
                if not df_t.empty:
                    data_dict[t] = df_t
            except Exception:
                pass

    return data_dict, sym_map
