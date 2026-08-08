import re

# Custom Table CSS for Zero-Truncation Display
TABLE_CUSTOM_CSS = """
<style>
div[data-testid="stTable"] {
    overflow-x: auto !important;
}
div[data-testid="stTable"] table {
    width: 100% !important;
    border-collapse: collapse !important;
    font-size: 13px !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}
div[data-testid="stTable"] th {
    padding: 8px 12px !important;
    text-align: center !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    background-color: #1E222D !important;
    color: #E0E2EC !important;
    border-bottom: 2px solid #2B2F3E !important;
    min-width: 85px !important;
}
div[data-testid="stTable"] td {
    padding: 7px 12px !important;
    text-align: center !important;
    white-space: nowrap !important;
    border-bottom: 1px solid #2B2F3E !important;
    min-width: 85px !important;
}
div[data-testid="stTable"] th:nth-child(1),
div[data-testid="stTable"] td:nth-child(1) {
    text-align: left !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
    min-width: 115px !important;
    max-width: 150px !important;
}
</style>
"""

# Official 22 Sectors and 59 Industry Classifications
INDIAN_SECTOR_HIERARCHY = {
    "Automobile and Auto Components": [
        "Automobiles",
        "Auto Components & Ancillaries",
        "Tyres & Rubber",
    ],
    "Capital Goods": [
        "Aerospace & Defense",
        "Electrical Equipment",
        "Engineering Services",
        "Industrial Manufacturing",
        "Industrial Products",
    ],
    "Chemicals": ["Chemicals & Petrochemicals", "Fertilizers & Agrochemicals"],
    "Construction": ["Civil Construction", "Infrastructure Developers"],
    "Construction Materials": [
        "Cement & Cement Products",
        "Ceramics & Building Materials",
    ],
    "Consumer Durables": [
        "Consumer Electronics & Appliances",
        "Gems, Jewellery & Watches",
        "Household & Personal Products",
    ],
    "Consumer Services": [
        "Leisure Services",
        "Restaurants & QSR",
        "Retailing",
        "Travel & Tourism",
    ],
    "Diversified": [
        "Diversified Commercial Services",
        "Diversified Industrials",
    ],
    "Fast Moving Consumer Goods": [
        "Agricultural Food & Other Products",
        "Beverages",
        "Food Products",
        "Personal Care",
        "Tobacco Products",
    ],
    "Financial Services": [
        "Asset Management",
        "Banks",
        "Capital Markets",
        "Finance & NBFCs",
        "Financial Technology (Fintech)",
        "Insurance",
    ],
    "Forest Materials": ["Paper, Forest & Jute Products"],
    "Healthcare": [
        "Healthcare Research, Analytics & Technology",
        "Healthcare Services",
        "Medical Equipment & Supplies",
        "Pharmaceuticals & Biotechnology",
    ],
    "Information Technology": [
        "IT - Hardware",
        "IT - Software & Consulting",
        "IT - Services",
    ],
    "Media, Entertainment & Publication": [
        "Broadcasting & Cable TV",
        "Entertainment & Content",
        "Print Media & Publishing",
    ],
    "Metals & Mining": [
        "Ferrous Metals (Steel & Iron)",
        "Non-Ferrous Metals",
        "Minerals & Mining",
    ],
    "Oil, Gas & Consumable Fuels": [
        "Consumable Fuels & Coal",
        "Oil & Gas Exploration & Production",
        "Petroleum Products & Refining",
    ],
    "Power": ["Power Generation", "Power Transmission & Distribution"],
    "Realty": ["Real Estate Developers", "Real Estate Services"],
    "Services": [
        "Commercial & Professional Services",
        "Logistics & Transportation Services",
        "Port & Shipping Services",
    ],
    "Telecommunication": [
        "Telecom - Equipment & Accessories",
        "Telecom - Services",
    ],
    "Textiles": ["Garments & Apparels", "Textiles & Weaving"],
    "Utilities": ["Gas Transmission & Utilities", "Water & Other Utilities"],
}

TV_TO_INDIAN_MAP = {
    ("Commercial Services", "Financial Publishing/Services"): (
        "Financial Services",
        "Capital Markets",
    ),
    ("Commercial Services", "Miscellaneous Commercial Services"): (
        "Services",
        "Commercial & Professional Services",
    ),
    ("Commercial Services", "Personnel Services"): (
        "Services",
        "Commercial & Professional Services",
    ),
    ("Consumer Durables", "Automotive Aftermarket"): (
        "Automobile and Auto Components",
        "Auto Components & Ancillaries",
    ),
    ("Consumer Durables", "Electronics/Appliances"): (
        "Consumer Durables",
        "Consumer Electronics & Appliances",
    ),
    ("Consumer Durables", "Home Furnishings"): (
        "Consumer Durables",
        "Household & Personal Products",
    ),
    ("Consumer Durables", "Homebuilding"): ("Realty", "Real Estate Developers"),
    ("Consumer Durables", "Motor Vehicles"): (
        "Automobile and Auto Components",
        "Automobiles",
    ),
    ("Consumer Durables", "Other Consumer Specialties"): (
        "Consumer Durables",
        "Gems, Jewellery & Watches",
    ),
    ("Consumer Non-Durables", "Apparel/Footwear"): (
        "Textiles",
        "Garments & Apparels",
    ),
    ("Consumer Non-Durables", "Beverages: Alcoholic"): (
        "Fast Moving Consumer Goods",
        "Beverages",
    ),
    ("Consumer Non-Durables", "Food: Major Diversified"): (
        "Fast Moving Consumer Goods",
        "Food Products",
    ),
    ("Consumer Non-Durables", "Food: Specialty/Candy"): (
        "Fast Moving Consumer Goods",
        "Food Products",
    ),
    ("Consumer Non-Durables", "Household/Personal Care"): (
        "Fast Moving Consumer Goods",
        "Personal Care",
    ),
    ("Consumer Services", "Broadcasting"): (
        "Media, Entertainment & Publication",
        "Broadcasting & Cable TV",
    ),
    ("Consumer Services", "Hotels/Resorts/Cruise lines"): (
        "Consumer Services",
        "Travel & Tourism",
    ),
    ("Consumer Services", "Movies/Entertainment"): (
        "Media, Entertainment & Publication",
        "Entertainment & Content",
    ),
    ("Consumer Services", "Publishing: Books/Magazines"): (
        "Media, Entertainment & Publication",
        "Print Media & Publishing",
    ),
    ("Consumer Services", "Restaurants"): (
        "Consumer Services",
        "Restaurants & QSR",
    ),
    ("Distribution Services", "Electronics Distributors"): (
        "Capital Goods",
        "Industrial Products",
    ),
    ("Distribution Services", "Medical Distributors"): (
        "Healthcare",
        "Medical Equipment & Supplies",
    ),
    ("Distribution Services", "Wholesale Distributors"): (
        "Services",
        "Commercial & Professional Services",
    ),
    ("Electronic Technology", "Aerospace & Defense"): (
        "Capital Goods",
        "Aerospace & Defense",
    ),
    ("Electronic Technology", "Computer Communications"): (
        "Telecommunication",
        "Telecom - Equipment & Accessories",
    ),
    ("Electronic Technology", "Computer Peripherals"): (
        "Information Technology",
        "IT - Hardware",
    ),
    ("Electronic Technology", "Electronic Components"): (
        "Capital Goods",
        "Electrical Equipment",
    ),
    ("Electronic Technology", "Electronic Equipment/Instruments"): (
        "Capital Goods",
        "Electrical Equipment",
    ),
    ("Electronic Technology", "Electronic Production Equipment"): (
        "Capital Goods",
        "Industrial Manufacturing",
    ),
    ("Electronic Technology", "Telecommunications Equipment"): (
        "Telecommunication",
        "Telecom - Equipment & Accessories",
    ),
    ("Energy Minerals", "Oil & Gas Production"): (
        "Oil, Gas & Consumable Fuels",
        "Oil & Gas Exploration & Production",
    ),
    ("Energy Minerals", "Oil Refining/Marketing"): (
        "Oil, Gas & Consumable Fuels",
        "Petroleum Products & Refining",
    ),
    ("Finance", "Finance/Rental/Leasing"): ("Financial Services", "Finance & NBFCs"),
    ("Finance", "Financial Conglomerates"): (
        "Financial Services",
        "Finance & NBFCs",
    ),
    ("Finance", "Investment Banks/Brokers"): (
        "Financial Services",
        "Capital Markets",
    ),
    ("Finance", "Investment Managers"): (
        "Financial Services",
        "Asset Management",
    ),
    ("Finance", "Life/Health Insurance"): ("Financial Services", "Insurance"),
    ("Finance", "Major Banks"): ("Financial Services", "Banks"),
    ("Finance", "Multi-Line Insurance"): ("Financial Services", "Insurance"),
    ("Finance", "Real Estate Development"): ("Realty", "Real Estate Developers"),
    ("Finance", "Regional Banks"): ("Financial Services", "Banks"),
    ("Health Services", "Hospital/Nursing Management"): (
        "Healthcare",
        "Healthcare Services",
    ),
    ("Health Services", "Medical/Nursing Services"): (
        "Healthcare",
        "Healthcare Services",
    ),
    ("Health Technology", "Biotechnology"): (
        "Healthcare",
        "Pharmaceuticals & Biotechnology",
    ),
    ("Health Technology", "Medical Specialties"): (
        "Healthcare",
        "Medical Equipment & Supplies",
    ),
    ("Health Technology", "Pharmaceuticals: Generic"): (
        "Healthcare",
        "Pharmaceuticals & Biotechnology",
    ),
    ("Health Technology", "Pharmaceuticals: Major"): (
        "Healthcare",
        "Pharmaceuticals & Biotechnology",
    ),
    ("Health Technology", "Pharmaceuticals: Other"): (
        "Healthcare",
        "Pharmaceuticals & Biotechnology",
    ),
    ("Industrial Services", "Contract Drilling"): (
        "Oil, Gas & Consumable Fuels",
        "Oil & Gas Exploration & Production",
    ),
    ("Industrial Services", "Engineering & Construction"): (
        "Construction",
        "Civil Construction",
    ),
    ("Industrial Services", "Oilfield Services/Equipment"): (
        "Oil, Gas & Consumable Fuels",
        "Oil & Gas Exploration & Production",
    ),
    ("Non-Energy Minerals", "Construction Materials"): (
        "Construction Materials",
        "Ceramics & Building Materials",
    ),
    ("Non-Energy Minerals", "Forest Products"): (
        "Forest Materials",
        "Paper, Forest & Jute Products",
    ),
    ("Non-Energy Minerals", "Other Metals/Minerals"): (
        "Metals & Mining",
        "Minerals & Mining",
    ),
    ("Non-Energy Minerals", "Steel"): (
        "Metals & Mining",
        "Ferrous Metals (Steel & Iron)",
    ),
    ("Process Industries", "Agricultural Commodities/Milling"): (
        "Fast Moving Consumer Goods",
        "Agricultural Food & Other Products",
    ),
    ("Process Industries", "Chemicals: Agricultural"): (
        "Chemicals",
        "Fertilizers & Agrochemicals",
    ),
    ("Process Industries", "Chemicals: Major Diversified"): (
        "Chemicals",
        "Chemicals & Petrochemicals",
    ),
    ("Process Industries", "Chemicals: Specialty"): (
        "Chemicals",
        "Chemicals & Petrochemicals",
    ),
    ("Process Industries", "Containers/Packaging"): (
        "Capital Goods",
        "Industrial Products",
    ),
    ("Process Industries", "Industrial Specialties"): (
        "Capital Goods",
        "Industrial Manufacturing",
    ),
    ("Process Industries", "Pulp & Paper"): (
        "Forest Materials",
        "Paper, Forest & Jute Products",
    ),
    ("Process Industries", "Textiles"): ("Textiles", "Textiles & Weaving"),
    ("Producer Manufacturing", "Auto Parts: OEM"): (
        "Automobile and Auto Components",
        "Auto Components & Ancillaries",
    ),
    ("Producer Manufacturing", "Building Products"): (
        "Construction Materials",
        "Cement & Cement Products",
    ),
    ("Producer Manufacturing", "Electrical Products"): (
        "Capital Goods",
        "Electrical Equipment",
    ),
    ("Producer Manufacturing", "Industrial Machinery"): (
        "Capital Goods",
        "Industrial Manufacturing",
    ),
    ("Producer Manufacturing", "Metal Fabrication"): (
        "Capital Goods",
        "Industrial Manufacturing",
    ),
    ("Producer Manufacturing", "Miscellaneous Manufacturing"): (
        "Capital Goods",
        "Industrial Products",
    ),
    ("Producer Manufacturing", "Office Equipment/Supplies"): (
        "Consumer Durables",
        "Household & Personal Products",
    ),
    ("Producer Manufacturing", "Trucks/Construction/Farm Machinery"): (
        "Automobile and Auto Components",
        "Automobiles",
    ),
    ("Retail Trade", "Apparel/Footwear Retail"): (
        "Consumer Services",
        "Retailing",
    ),
    ("Retail Trade", "Electronics/Appliance Stores"): (
        "Consumer Services",
        "Retailing",
    ),
    ("Retail Trade", "Internet Retail"): ("Consumer Services", "Retailing"),
    ("Retail Trade", "Specialty Stores"): ("Consumer Services", "Retailing"),
    ("Technology Services", "Information Technology Services"): (
        "Information Technology",
        "IT - Services",
    ),
    ("Technology Services", "Internet Software/Services"): (
        "Information Technology",
        "IT - Software & Consulting",
    ),
    ("Technology Services", "Packaged Software"): (
        "Information Technology",
        "IT - Software & Consulting",
    ),
    ("Transportation", "Air Freight/Couriers"): (
        "Services",
        "Logistics & Transportation Services",
    ),
    ("Transportation", "Airlines"): ("Consumer Services", "Travel & Tourism"),
    ("Transportation", "Marine Shipping"): (
        "Services",
        "Port & Shipping Services",
    ),
    ("Transportation", "Other Transportation"): (
        "Services",
        "Logistics & Transportation Services",
    ),
    ("Transportation", "Railroads"): (
        "Services",
        "Logistics & Transportation Services",
    ),
    ("Utilities", "Electric Utilities"): ("Power", "Power Generation"),
    ("Utilities", "Gas Distributors"): ("Utilities", "Gas Transmission & Utilities"),
}

EXHAUSTIVE_INDICES = [
    "NIFTY 50",
    "NIFTY NEXT 50",
    "NIFTY 100",
    "NIFTY 200",
    "NIFTY 500",
    "NIFTY MIDCAP 50",
    "NIFTY MIDCAP 100",
    "NIFTY MIDCAP 150",
    "NIFTY SMALLCAP 50",
    "NIFTY SMALLCAP 100",
    "NIFTY SMALLCAP 250",
    "NIFTY MICROCAP 250",
    "NIFTY TOTAL MARKET",
    "NIFTY LARGEMIDCAP 250",
    "NIFTY BANK",
    "NIFTY AUTO",
    "NIFTY FINANCIAL SERVICES",
    "NIFTY FMCG",
    "NIFTY IT",
    "NIFTY MEDIA",
    "NIFTY METAL",
    "NIFTY PHARMA",
    "NIFTY PSU BANK",
    "NIFTY PRIVATE BANK",
    "NIFTY REALTY",
    "NIFTY HEALTHCARE",
    "NIFTY CONSUMER DURABLES",
    "NIFTY OIL & GAS",
    "NIFTY COMMODITIES",
    "NIFTY INDIA CONSUMPTION",
    "NIFTY CPSE",
    "NIFTY INFRASTRUCTURE",
    "NIFTY MNC",
    "NIFTY PSE",
    "NIFTY SERVICES SECTOR",
    "NIFTY ENERGY",
    "NIFTY HOUSING",
    "NIFTY INDIA DEFENCE",
    "NIFTY INDIA DIGITAL",
    "NIFTY INDIA MANUFACTURING",
    "NIFTY MOBILITY",
    "BSE SENSEX",
    "BSE 100",
    "BSE 200",
    "BSE 500",
]

def map_to_indian_classification(tv_industry, tv_sector):
    mapped = TV_TO_INDIAN_MAP.get((tv_sector, tv_industry))
    if mapped:
        return mapped
    return "Diversified", "Diversified Commercial Services"

def parse_chart_selection_multi(event):
    if event and isinstance(event, dict):
        sel = event.get("selection", {})
        points = sel.get("points", [])
        if points:
            return [p.get("label") for p in points if p.get("label")]
    return []

def parse_table_selection_multi(event, df_source, col_name):
    if event and isinstance(event, dict):
        sel = event.get("selection", {})
        rows = sel.get("rows", [])
        if rows:
            selected_vals = []
            for idx in rows:
                if idx < len(df_source):
                    selected_vals.append(df_source.iloc[idx][col_name])
            return selected_vals
    return []

def parse_pasted_tickers(raw_text):
    if not raw_text:
        return []
    tokens = re.split(r"[,\\n\\r\\t;]+", raw_text)
    cleaned = []
    for t in tokens:
        t = t.strip().upper()
        t = re.sub(r"[^A-Z0-9:]", "", t)
        if not t:
            continue
        if ":" not in t:
            t = f"NSE:{t}"
        if t not in cleaned:
            cleaned.append(t)
    return cleaned
