"""
Configuration settings, constants, and fallback mappings for India Equities Screener.
"""

# GitHub configuration for remote data fetching (Excel monitors, JSON masters)
GITHUB_USER = "chethanshivaraju94-netizen"
GITHUB_REPO = "StockHome"
GITHUB_BRANCH = "main"

# TradingView Scanner API configuration
TV_SCANNER_URL = "https://scanner.tradingview.com/india/scan"

# Fallback mapping: Used ONLY if a ticker is not found in nse_sector_master.json
# Translates raw TradingView (FactSet) sector/industry strings into standard Indian terminology
TV_TO_INDIAN_MAP = {
    # Broad Sector Normalization
    "Electronic Technology": {"Sector": "Information Technology", "Industry": "IT - Hardware"},
    "Technology Services": {"Sector": "Information Technology", "Industry": "IT - Software"},
    "Finance": {"Sector": "Financial Services", "Industry": "Finance"},
    "Health Technology": {"Sector": "Healthcare", "Industry": "Pharmaceuticals & Biotechnology"},
    "Health Services": {"Sector": "Healthcare", "Industry": "Healthcare Services"},
    "Process Industries": {"Sector": "Chemicals", "Industry": "Chemicals & Petrochemicals"},
    "Producer Manufacturing": {"Sector": "Capital Goods", "Industry": "Industrial Manufacturing"},
    "Non-Energy Minerals": {"Sector": "Metals & Mining", "Industry": "Minerals & Mining"},
    "Energy Minerals": {"Sector": "Energy", "Industry": "Consumable Fuels"},
    "Consumer Non-Durables": {"Sector": "Fast Moving Consumer Goods", "Industry": "Food Products"},
    "Consumer Durables": {"Sector": "Consumer Durables", "Industry": "Consumer Durables"},
    "Consumer Services": {"Sector": "Consumer Services", "Industry": "Other Consumer Services"},
    "Retail Trade": {"Sector": "Consumer Services", "Industry": "Retailing"},
    "Commercial Services": {"Sector": "Services", "Industry": "Commercial Services & Supplies"},
    "Transportation": {"Sector": "Services", "Industry": "Transport Services"},
    "Utilities": {"Sector": "Utilities", "Industry": "Power"},
    "Communications": {"Sector": "Telecommunication", "Industry": "Telecom Services"},
    "Distribution Services": {"Sector": "Services", "Industry": "Trading & Distributors"},
    "Industrial Services": {"Sector": "Industrials", "Industry": "Civil Construction"},
    "Miscellaneous": {"Sector": "Diversified", "Industry": "Diversified"},
}

def get_fallback_classification(tv_sector, tv_industry):
    """
    Fallback mechanism if a stock is not present in nse_sector_master.json.
    Attempts a lookup in TV_TO_INDIAN_MAP, then cleans the raw TradingView text.
    """
    tv_sector_clean = str(tv_sector).strip() if tv_sector else "Unclassified"
    tv_industry_clean = str(tv_industry).strip() if tv_industry else "Unclassified"
    
    if tv_sector_clean in TV_TO_INDIAN_MAP:
        mapped = TV_TO_INDIAN_MAP[tv_sector_clean]
        return mapped["Sector"], (mapped["Industry"] if tv_industry_clean == "Unclassified" else tv_industry_clean)
        
    return tv_sector_clean, tv_industry_clean
