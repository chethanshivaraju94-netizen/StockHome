"""
Data fetching, enrichment, and classification module for India Equities Screener.
"""

import json
import os
import requests
import pandas as pd
import streamlit as st

from modules.config import (
    GITHUB_USER,
    GITHUB_REPO,
    GITHUB_BRANCH,
    TV_SCANNER_URL,
    get_fallback_classification
)


@st.cache_data(ttl=86400)
def load_sector_master():
    """
    Loads the official NSE sector and industry master dictionary.
    First tries loading locally; if not found (e.g. Streamlit Cloud),
    it fetches directly from the GitHub repository raw endpoint.
    """
    local_path = "nse_sector_master.json"
    if os.path.exists(local_path):
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Failed to load local sector master: {e}")

    # Fallback to GitHub raw
    github_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/nse_sector_master.json"
    try:
        resp = requests.get(github_url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.warning(f"Could not load sector master from GitHub: {e}")

    return {}


def apply_nse_classification(df: pd.DataFrame, master_dict: dict) -> pd.DataFrame:
    """
    Enriches the dataframe with official NSE Sector and Industry from master_dict.
    If a ticker is missing from the master dictionary, falls back cleanly to the
    TradingView category-level mapping.
    """
    if df.empty:
        return df

    final_sectors = []
    final_industries = []

    for _, row in df.iterrows():
        # Strip exchange prefix (e.g., 'NSE:TCS' -> 'TCS')
        ticker = str(row.get("Ticker", "")).split(":")[-1].strip().upper()
        tv_sec = row.get("raw_sector", row.get("Sector", "Unclassified"))
        tv_ind = row.get("raw_industry", row.get("Industry", "Unclassified"))

        if ticker in master_dict:
            rec = master_dict[ticker]
            final_sectors.append(rec.get("Sector") or "Unclassified")
            final_industries.append(rec.get("Industry") or "Unclassified")
        else:
            fb_sec, fb_ind = get_fallback_classification(tv_sec, tv_ind)
            final_sectors.append(fb_sec)
            final_industries.append(fb_ind)

    df["Sector"] = final_sectors
    df["Industry"] = final_industries
    return df


def fetch_screener_data(columns_payload, filter_payload=None):
    """
    Queries the TradingView scanner endpoint and returns a cleaned DataFrame
    enriched with official NSE 4-tier Sector and Industry classifications.
    """
    payload = {
        "filter": filter_payload or [],
        "options": {"lang": "en"},
        "symbols": {"query": {"types": []}, "tickers": []},
        "columns": columns_payload,
        "sort": {"sortBy": "market_cap_basic", "sortOrder": "desc"},
        "range": [0, 5000]
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(TV_SCANNER_URL, json=payload, headers=headers, timeout=15)
        if response.status_code != 200:
            st.error(f"TradingView API returned status code {response.status_code}")
            return pd.DataFrame()

        raw_data = response.json().get("data", [])
        if not raw_data:
            return pd.DataFrame()

        rows = []
        for item in raw_data:
            sym = item.get("s", "")
            d = item.get("d", [])
            row_dict = {"Ticker": sym}
            for col_name, val in zip(columns_payload, d):
                row_dict[col_name] = val
            rows.append(row_dict)

        df = pd.DataFrame(rows)

        # Retain raw TV categories for the fallback path
        if "sector" in df.columns:
            df["raw_sector"] = df["sector"]
        if "industry" in df.columns:
            df["raw_industry"] = df["industry"]

        # Load master dictionary and apply classification
        master_dict = load_sector_master()
        df = apply_nse_classification(df, master_dict)

        return df

    except Exception as e:
        st.error(f"Error fetching data from TradingView: {e}")
        return pd.DataFrame()


def fetch_watchlist_enrichment(tickers: list, columns_payload: list):
    """
    Fetches fundamental and technical metrics for an explicit list of tickers
    and enriches them with official NSE Sector and Industry data.
    """
    if not tickers:
        return pd.DataFrame()

    # Ensure exchange prefix
    formatted_tickers = [t if ":" in t else f"NSE:{t}" for t in tickers]

    payload = {
        "symbols": {"tickers": formatted_tickers},
        "columns": columns_payload
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(TV_SCANNER_URL, json=payload, headers=headers, timeout=15)
        if response.status_code != 200:
            return pd.DataFrame()

        raw_data = response.json().get("data", [])
        rows = []
        for item in raw_data:
            sym = item.get("s", "")
            d = item.get("d", [])
            row_dict = {"Ticker": sym}
            for col_name, val in zip(columns_payload, d):
                row_dict[col_name] = val
            rows.append(row_dict)

        df = pd.DataFrame(rows)

        if "sector" in df.columns:
            df["raw_sector"] = df["sector"]
        if "industry" in df.columns:
            df["raw_industry"] = df["industry"]

        master_dict = load_sector_master()
        df = apply_nse_classification(df, master_dict)

        return df

    except Exception:
        return pd.DataFrame()
