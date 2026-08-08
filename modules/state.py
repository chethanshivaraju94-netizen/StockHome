import json
import os
import requests
import streamlit as st

WATCHLIST_FILE = "local_watchlists.json"
PRESETS_FILE = "local_filter_presets.json"
REPORTS_FILE = "local_fundamental_reports.json"
BRIEFINGS_FILE = "local_market_briefings.json"
TRADEBOOK_FILE = "local_tradebook.json"

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", None)
GIST_ID = st.secrets.get("GIST_ID", None)

def load_watchlists():
    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            res = requests.get(
                f"https://api.github.com/gists/{GIST_ID}", headers=headers, timeout=5
            )
            if res.status_code == 200:
                gist_data = res.json()
                if WATCHLIST_FILE in gist_data["files"]:
                    content = gist_data["files"][WATCHLIST_FILE]["content"]
                    return json.loads(content)
        except Exception as e:
            st.warning(f"GitHub Gist load failed, switching to local disk: {e}")

    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "Post Breakout Monitor": ["NSE:ZOMATO", "NSE:CDSL", "NSE:TITAGARH"],
        "Focus List": ["NSE:JINDWORLD", "NSE:TRENT", "NSE:HAL", "NSE:RECLTD"],
        "Weekly Focus": ["NSE:BHEL", "NSE:ABB", "NSE:SIEMENS", "NSE:CGPOWER"],
        "Scan Bulk": [],
        "Sold Stocks": [],
    }

def save_watchlists(watchlists_dict):
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump(watchlists_dict, f, indent=2)
    except Exception:
        pass

    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            payload = {
                "files": {
                    WATCHLIST_FILE: {
                        "content": json.dumps(watchlists_dict, indent=2)
                    }
                }
            }
            requests.patch(
                f"https://api.github.com/gists/{GIST_ID}",
                headers=headers,
                json=payload,
                timeout=5,
            )
        except Exception:
            pass

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

    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            res = requests.get(
                f"https://api.github.com/gists/{GIST_ID}", headers=headers, timeout=5
            )
            if res.status_code == 200:
                gist_data = res.json()
                if PRESETS_FILE in gist_data["files"]:
                    content = gist_data["files"][PRESETS_FILE]["content"]
                    return json.loads(content)
        except Exception:
            pass

    if os.path.exists(PRESETS_FILE):
        try:
            with open(PRESETS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return default_presets

def save_filter_presets(presets_dict):
    try:
        with open(PRESETS_FILE, "w") as f:
            json.dump(presets_dict, f, indent=2)
    except Exception:
        pass

    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            payload = {
                "files": {PRESETS_FILE: {"content": json.dumps(presets_dict, indent=2)}}
            }
            requests.patch(
                f"https://api.github.com/gists/{GIST_ID}",
                headers=headers,
                json=payload,
                timeout=5,
            )
        except Exception:
            pass

def load_fundamental_reports():
    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            res = requests.get(
                f"https://api.github.com/gists/{GIST_ID}", headers=headers, timeout=5
            )
            if res.status_code == 200:
                gist_data = res.json()
                if REPORTS_FILE in gist_data["files"]:
                    content = gist_data["files"][REPORTS_FILE]["content"]
                    return json.loads(content)
        except Exception:
            pass

    if os.path.exists(REPORTS_FILE):
        try:
            with open(REPORTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return {}

def save_fundamental_reports(reports_dict):
    try:
        with open(REPORTS_FILE, "w") as f:
            json.dump(reports_dict, f, indent=2)
    except Exception:
        pass

    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            payload = {
                "files": {REPORTS_FILE: {"content": json.dumps(reports_dict, indent=2)}}
            }
            requests.patch(
                f"https://api.github.com/gists/{GIST_ID}",
                headers=headers,
                json=payload,
                timeout=5,
            )
        except Exception:
            pass

def load_market_briefings():
    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            res = requests.get(
                f"https://api.github.com/gists/{GIST_ID}", headers=headers, timeout=5
            )
            if res.status_code == 200:
                gist_data = res.json()
                if BRIEFINGS_FILE in gist_data["files"]:
                    content = gist_data["files"][BRIEFINGS_FILE]["content"]
                    return json.loads(content)
        except Exception:
            pass

    if os.path.exists(BRIEFINGS_FILE):
        try:
            with open(BRIEFINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return {}

def save_market_briefings(briefings_dict):
    try:
        with open(BRIEFINGS_FILE, "w") as f:
            json.dump(briefings_dict, f, indent=2)
    except Exception:
        pass

    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            payload = {
                "files": {BRIEFINGS_FILE: {"content": json.dumps(briefings_dict, indent=2)}}
            }
            requests.patch(
                f"https://api.github.com/gists/{GIST_ID}",
                headers=headers,
                json=payload,
                timeout=5,
            )
        except Exception:
            pass

def load_tradebook():
    default_tb = {"config": {"starting_capital": 500000.0}, "trades": []}
    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            res = requests.get(
                f"https://api.github.com/gists/{GIST_ID}", headers=headers, timeout=5
            )
            if res.status_code == 200:
                gist_data = res.json()
                if TRADEBOOK_FILE in gist_data["files"]:
                    content = gist_data["files"][TRADEBOOK_FILE]["content"]
                    return json.loads(content)
        except Exception:
            pass

    if os.path.exists(TRADEBOOK_FILE):
        try:
            with open(TRADEBOOK_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass

    return default_tb

def save_tradebook(tb_dict):
    try:
        with open(TRADEBOOK_FILE, "w") as f:
            json.dump(tb_dict, f, indent=2)
    except Exception:
        pass

    if GITHUB_TOKEN and GIST_ID:
        try:
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }
            payload = {
                "files": {TRADEBOOK_FILE: {"content": json.dumps(tb_dict, indent=2)}}
            }
            requests.patch(
                f"https://api.github.com/gists/{GIST_ID}",
                headers=headers,
                json=payload,
                timeout=5,
            )
        except Exception:
            pass

def init_session_state():
    if "watchlists" not in st.session_state:
        st.session_state.watchlists = load_watchlists()
    if "active_watchlist_name" not in st.session_state:
        st.session_state.active_watchlist_name = list(
            st.session_state.watchlists.keys()
        )[0]
    if "filter_presets" not in st.session_state:
        st.session_state.filter_presets = load_filter_presets()
    if "fundamental_reports" not in st.session_state:
        st.session_state.fundamental_reports = load_fundamental_reports()
    if "market_briefings" not in st.session_state:
        st.session_state.market_briefings = load_market_briefings()
    if "tradebook" not in st.session_state:
        st.session_state.tradebook = load_tradebook()
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
