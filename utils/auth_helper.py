import os
import json
import requests
from datetime import datetime, timedelta
import yaml

# Load config from YAML
with open("configs/global.yaml", "r") as f:
    config = yaml.safe_load(f)

API_KEY = config["ig"]["api_key"]
USERNAME = config["ig"]["username"]
PASSWORD = config["ig"]["password"]
BASE_URL = config["ig"]["base_url"]
CACHE_FILE = config["ig"]["cache_file"]
SESSION_DURATION = config["ig"]["session_duration"]

def load_tokens():
    """Load cached session tokens if still valid."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            data = json.load(file)
            expiry_time = datetime.fromisoformat(data["expiry"])
            if expiry_time > datetime.utcnow():
                return data["CST"], data["XST"], data["lightstreamer_endpoint"], data["account_id"]
    return None, None, None, None

def save_tokens(cst, xst, lightstreamer_endpoint, account_id):
    """Save session tokens to cache."""
    expiry_time = datetime.utcnow() + timedelta(seconds=SESSION_DURATION - 60)
    with open(CACHE_FILE, "w") as file:
        json.dump({
            "CST": cst,
            "XST": xst,
            "lightstreamer_endpoint": lightstreamer_endpoint,
            "account_id": account_id,
            "expiry": expiry_time.isoformat(),
        }, file)

def authenticate():
    """Authenticate and retrieve session tokens."""
    cst, xst, ls_endpoint, account_id = load_tokens()
    if cst and xst:
        return cst, xst, ls_endpoint, account_id

    headers = {
        "Content-Type": "application/json",
        "X-IG-API-KEY": API_KEY,
        "Version": "2",
    }
    data = {"identifier": USERNAME, "password": PASSWORD}

    response = requests.post(f"{BASE_URL}/session", json=data, headers=headers)
    response.raise_for_status()
    auth_data = response.json()

    spread_bet_account = next(acc for acc in auth_data["accounts"] if acc["accountType"] == "SPREADBET")
    account_id = spread_bet_account["accountId"]

    cst = response.headers["CST"]
    xst = response.headers["X-SECURITY-TOKEN"]
    ls_endpoint = auth_data["lightstreamerEndpoint"]

    save_tokens(cst, xst, ls_endpoint, account_id)
    return cst, xst, ls_endpoint, account_id
