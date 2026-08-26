import json
import os
import requests
import streamlit as st
from google.cloud import firestore
from google.oauth2 import service_account

# Local & Gist Reference Filenames
WATCHLIST_FILE = "watchlists.json"
PRESETS_FILE = "filter_presets.json"
REPORTS_FILE = "fundamental_reports.json"
BRIEFINGS_FILE = "market_briefings.json"
TRADEBOOK_FILE = "tradebook.json"
CATALYSTS_FILE = "catalyst_reports.json"

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", None)
GIST_ID = st.secrets.get("GIST_ID", None)


@st.cache_resource
def get_db():
    """Securely connects to Google Firestore using Streamlit Secrets."""
    if "firebase" in st.secrets:
        try:
            firebase_secrets = dict(st.secrets["firebase"])
            if "private_key" in firebase_secrets and isinstance(firebase_secrets["private_key"], str):
                firebase_secrets["private_key"] = firebase_secrets["private_key"].replace("\\n", "\n")
                
            creds = service_account.Credentials.from_service_account_info(firebase_secrets)
            
            return firestore.Client(
                credentials=creds, 
                project=firebase_secrets.get("project_id"),
                database="(default)"
            )
        except Exception as e:
            st.warning(f"Firestore connection failed: {e}")
            return None
    return None


def fetch_from_gist(filename):
    """Fetches data from GitHub Gist for seamless one-time migration."""
    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            res = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers, timeout=5)
            if res.status_code == 200:
                gist_data = res.json()
                if filename in gist_data.get("files", {}):
                    content = gist_data["files"][filename].get("content", "")
                    if content.strip():
                        return json.loads(content)
        except Exception:
            pass
    return None


def load_data_from_db(doc_name, filename, default_data):
    """Loads from Firestore. If empty, migrates automatically from Gist or local disk."""
    db = get_db()
    
    # 1. Read from Firestore
    if db:
        try:
            doc_ref = db.collection("stockhome_data").document(doc_name)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return data.get("data", data)
        except Exception as e:
            st.warning(f"Error reading {doc_name} from Firestore: {e}")

    # 2. Auto-Migrate from GitHub Gist if Firestore is not yet populated
    gist_data = fetch_from_gist(filename)
    if gist_data is not None:
        if db:
            try:
                db.collection("stockhome_data").document(doc_name).set({"data": gist_data})
            except Exception:
                pass
        return gist_data

    # 3. Fallback to local disk
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                local_data = json.load(f)
                if db:
                    try:
                        db.collection("stockhome_data").document(doc_name).set({"data": local_data})
                    except Exception:
                        pass
                return local_data
        except Exception:
            pass

    return default_data


def save_data_to_db(doc_name, data_dict, filename):
    """Persists data to Firestore and saves a local disk backup."""
    try:
        with open(filename, "w") as f:
            json.dump(data_dict, f, indent=2)
    except Exception:
        pass

    db = get_db()
    if db:
        try:
            db.collection("stockhome_data").document(doc_name).set({"data": data_dict})
        except Exception as e:
            st.error(f"Failed to persist {doc_name} to Firestore: {e}")


# ==========================================
# DATA GETTERS & SETTERS
# ==========================================

def load_watchlists():
    default_wl = {
        "Post Breakout Monitor": ["NSE:ZOMATO", "NSE:CDSL", "NSE:TITAGARH"],
        "Focus List": ["NSE:JINDWORLD", "NSE:TRENT", "NSE:HAL", "NSE:RECLTD"],
        "Weekly Focus": ["NSE:BHEL", "NSE:ABB", "NSE:SIEMENS", "NSE:CGPOWER"],
        "Scan Bulk": [],
        "Sold Stocks": [],
    }
    return load_data_from_db("watchlists", WATCHLIST_FILE, default_wl)


def save_watchlists(watchlists_dict):
    save_data_to_db("watchlists", watchlists_dict, WATCHLIST_FILE)


def load_filter_presets():
    default_ma_configs = [
        {"en": True, "type": "EMA", "len": 21},
        {"en": True, "type": "SMA", "len": 50},
        {"en": False, "type": "SMA", "len": 200},
        {"en": False, "type": "EMA", "len": 10},
        {"en": False, "type": "SMA", "len": 150},
    ]
    default_presets = {
        "🏆 CAN SLIM & Growth Breakout": {
            "exchanges": ["NSE", "BSE"],
            "sectors": [],
            "industries": [],
            "indices": [],
            "min_mcap_cr": 1000,
            "vol_period_days": 60,
            "min_vol_cr": 5.0,
            "en_ipo": False,
            "ipo_filter": "All Stocks (No IPO Filter)",
            "en_eps_q": True,
            "min_eps_q": 15.0,
            "en_sales_q": True,
            "min_sales_q": 10.0,
            "allow_na_growth": True,
            "en_rs_rating": True,
            "min_rs_rating": 80,
            "en_adr": True,
            "min_adr": 2.5,
            "en_above_52l": True,
            "min_above_52l": 20,
            "en_below_52h": True,
            "max_below_52h": 25,
            "en_circuit": True,
            "circuit_val": ["2%", "5%", "10%"],
            "selected_perf_labels": ["1 Week", "1 Month", "3 Months", "6 Months"],
            "max_results": 4000,
            "ma_configs": default_ma_configs,
            "perf_configs": {
                c: {"en": False, "val": 0.0}
                for c in ["Perf.W", "Perf.1M", "Perf.3M", "Perf.6M", "Perf.YTD", "Perf.Y"]
            },
        },
    }
    return load_data_from_db("filter_presets", PRESETS_FILE, default_presets)


def save_filter_presets(presets_dict):
    save_data_to_db("filter_presets", presets_dict, PRESETS_FILE)


def load_fundamental_reports():
    return load_data_from_db("fundamental_reports", REPORTS_FILE, {})


def save_fundamental_reports(reports_dict):
    save_data_to_db("fundamental_reports", reports_dict, REPORTS_FILE)


def load_market_briefings():
    return load_data_from_db("market_briefings", BRIEFINGS_FILE, {})


def save_market_briefings(briefings_dict):
    save_data_to_db("market_briefings", briefings_dict, BRIEFINGS_FILE)


def load_tradebook():
    default_tb = {"config": {"starting_capital": 500000.0}, "trades": []}
    return load_data_from_db("tradebook", TRADEBOOK_FILE, default_tb)


def save_tradebook(tb_dict):
    save_data_to_db("tradebook", tb_dict, TRADEBOOK_FILE)


def load_catalyst_reports():
    return load_data_from_db("catalyst_reports", CATALYSTS_FILE, {})


def save_catalyst_reports(catalysts_dict):
    save_data_to_db("catalyst_reports", catalysts_dict, CATALYSTS_FILE)


# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================

def init_session_state():
    if "watchlists" not in st.session_state:
        st.session_state.watchlists = load_watchlists()
    if "active_watchlist_name" not in st.session_state:
        st.session_state.active_watchlist_name = list(st.session_state.watchlists.keys())[0]
    if "filter_presets" not in st.session_state:
        st.session_state.filter_presets = load_filter_presets()
    if "fundamental_reports" not in st.session_state:
        st.session_state.fundamental_reports = load_fundamental_reports()
    if "market_briefings" not in st.session_state:
        st.session_state.market_briefings = load_market_briefings()
    if "tradebook" not in st.session_state:
        st.session_state.tradebook = load_tradebook()
    if "catalyst_reports" not in st.session_state:
        st.session_state.catalyst_reports = load_catalyst_reports()
    
    if "active_scan_summary" not in st.session_state:
        st.session_state.active_scan_summary = {}
    if "rs_rating_map" not in st.session_state:
        st.session_state.rs_rating_map = {}
    if "reset_counter" not in st.session_state:
        st.session_state.reset_counter = 0
    if "scan_sel_counter" not in st.session_state:
        st.session_state.scan_sel_counter = 0
    if "wl_sel_counter" not in st.session_state:
        st.session_state.wl_sel_counter = 0
