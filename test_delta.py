import os
import time
import json
import hmac
import hashlib
import requests
import email.utils
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

# Delta Exchange API Settings
DELTA_BASE_URL = os.getenv("DELTA_BASE_URL", "https://cdn-ind.testnet.deltaex.org").strip().rstrip("/")
API_KEY = os.getenv("DELTA_API_KEY", "").strip()
API_SECRET = os.getenv("DELTA_API_SECRET", "").strip()

# Build proxy configuration with fallbacks
proxy_host = os.getenv("PROXY_HOST", "45.38.107.97").strip()
proxy_port = os.getenv("PROXY_PORT", "6014").strip()
proxy_user = os.getenv("PROXY_USERNAME", "wcakifdd").strip()
proxy_pass = os.getenv("PROXY_PASSWORD", "bef9r26uv6jm").strip()
default_proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"

HTTP_PROXY = os.getenv("HTTP_PROXY", default_proxy_url).strip()
HTTPS_PROXY = os.getenv("HTTPS_PROXY", default_proxy_url).strip()

PROXIES = {
    "http": HTTP_PROXY,
    "https": HTTPS_PROXY,
}

def check_egress_ip():
    """Verify karein ki traffic Webshare static IP (45.38.107.97) se hi ja raha hai"""
    print("\n--- [Step 1] Checking Outbound Egress IP ---")
    try:
        res = requests.get("https://ipv4.webshare.io/", proxies=PROXIES, timeout=15)
        current_ip = res.text.strip()
        print(f"Detected Outbound IP: {current_ip}")
        if current_ip == proxy_host:
            print(f"✅ Success! Static Outbound IP matches {proxy_host}.")
            return True
        else:
            print(f"⚠️ Warning: Outbound IP ({current_ip}) does not match expected ({proxy_host}).")
            return False
    except Exception as e:
        print(f"❌ Proxy connection error: {e}")
        return False

def get_server_timestamp():
    """Delta server ka exact timestamp fetch karein via Date header taaki time drift na ho"""
    try:
        res = requests.get(f"{DELTA_BASE_URL}/v2/products", proxies=PROXIES, timeout=10)
        date_header = res.headers.get("Date")
        if date_header:
            dt = email.utils.parsedate_to_datetime(date_header)
            return int(dt.timestamp())
    except Exception:
        pass
    return int(time.time())

def make_authenticated_request(method, path, query_string="", payload=""):
    """Generic helper to make signed Delta Exchange API requests"""
    timestamp = str(get_server_timestamp())
    signature_data = method + timestamp + path + query_string + payload
    signature = hmac.new(
        API_SECRET.encode("utf-8"),
        signature_data.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    headers = {
        "api-key": API_KEY,
        "signature": signature,
        "timestamp": timestamp,
        "User-Agent": "python-rest-client",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    url = f"{DELTA_BASE_URL}{path}{query_string}"
    return requests.request(method, url, headers=headers, data=payload if payload else None, proxies=PROXIES, timeout=15)

def get_delta_wallet():
    """Delta Authenticated Wallet Balance fetch karna aur cleanly format karke display karna"""
    print(f"\n==================================================")
    print(f"       DELTA EXCHANGE DEMO WALLET DETAILS")
    print(f"==================================================")
    
    if not API_KEY or not API_SECRET:
        print("❌ DELTA_API_KEY or DELTA_API_SECRET missing in .env")
        return False

    try:
        res = make_authenticated_request("GET", "/v2/wallet/balances")
        
        if res.status_code != 200:
            print(f"❌ Wallet Check Error: HTTP {res.status_code} - {res.text}")
            return False

        data = res.json()
        meta = data.get("meta", {})
        results = data.get("result", [])

        # 1. High-Level Account Equity
        net_equity = meta.get("net_equity", "0")
        print("\n💰 Account Equity Summary:")
        print(f"   • Total Net Equity   : {float(net_equity):,.4f} USDT")
        if "robo_trading_equity" in meta:
            print(f"   • Robo Trading Equity: {float(meta.get('robo_trading_equity', '0')):,.4f} USDT")
        if "tracker_equity" in meta:
            print(f"   • Tracker Equity     : {float(meta.get('tracker_equity', '0')):,.4f} USDT")

        # 2. Detailed Asset Balances
        print(f"\n📊 Asset Balances ({len(results)} assets total):")
        print(f"{'Asset':<10} | {'Total Balance':<18} | {'Available Balance':<18} | {'Order / Margin':<18}")
        print("-" * 72)

        has_positive_balance = False
        for item in results:
            asset = item.get("asset", {})
            symbol = asset.get("symbol", "N/A")
            total = float(item.get("balance", "0") or 0)
            available = float(item.get("available_balance", "0") or 0)
            order_margin = float(item.get("order_margin", "0") or 0) + float(item.get("position_margin", "0") or 0)

            # Highlight non-zero balances
            if total > 0 or available > 0:
                has_positive_balance = True
                print(f"{symbol:<10} | {total:<18.8f} | {available:<18.8f} | {order_margin:<18.8f}")

        if not has_positive_balance:
            print("   (No assets with positive balance found)")

        # 3. Check for Open Positions
        get_open_positions()

        return True

    except Exception as e:
        print(f"❌ Error fetching wallet: {e}")
        return False

def get_open_positions():
    """Demo account ke active positions fetch karna"""
    try:
        res = make_authenticated_request("GET", "/v2/positions/margined")
        if res.status_code == 200:
            positions = res.json().get("result", [])
            print(f"\n📈 Open Positions ({len(positions)} active):")
            if not positions:
                print("   (No open positions currently active)")
            else:
                for pos in positions:
                    product = pos.get("product", {})
                    symbol = product.get("symbol", "N/A")
                    size = pos.get("size", 0)
                    entry_price = pos.get("entry_price", 0)
                    pnl = pos.get("unrealized_pnl", 0)
                    print(f"   • {symbol}: Size={size}, Entry Price={entry_price}, Unrealized PnL={pnl}")
    except Exception:
        pass

if __name__ == "__main__":
    print("==================================================")
    print("Testing Outbound Connection to Delta Exchange...")
    print(f"Target Proxy: {proxy_host}:{proxy_port}")
    print(f"Active Base URL: {DELTA_BASE_URL}")
    print(f"API Key: {API_KEY[:6]}...{API_KEY[-4:] if len(API_KEY) > 10 else ''}")
    print("==================================================")

    if check_egress_ip():
        get_delta_wallet()
