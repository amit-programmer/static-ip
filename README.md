# 🌐 Delta Exchange Static IP Proxy Server & Trading Bot Gateway

A high-performance, lightweight Python proxy server and client designed to solve **IP whitelisting restrictions** and **dynamic IP challenges** on **Delta Exchange** (India & Global).

---

## 🎯 Problem It Solves

Delta Exchange requires API keys to be strictly bound to a whitelisted IP address for security. 
- **Dynamic Home/Office Wi-Fi**: Whenever your router restarts or ISP refreshes your lease, your IP changes, resulting in `ip_not_whitelisted_for_api_key`.
- **Cloud Containers (Render, Railway, Heroku, AWS)**: Most containerized services use ephemeral/rotating outbound IPs (`172.x.x.x`, `162.x.x.x`), which immediately get blocked by Delta Exchange.
- **Edge Functions (Cloudflare Workers)**: Serverless edge functions lack consistent outbound egress IPs and fail during TLS CONNECT handshakes to third-party proxies.

### ✅ The Solution
This project routes all Delta Exchange API traffic through a dedicated **Fixed Outbound Static Proxy (Webshare IP: `45.38.107.97`)**. It handles:
1. **Automatic HMAC-SHA256 Request Signing**: No need to manually calculate timestamps and signatures on every request.
2. **Clock Drift Synchronization**: Fetches live server headers from Delta Exchange to stay within Delta's strict 5-second signature validity window.
3. **Transparent HTTP Gateway**: Run `server.py` locally or in the cloud. Point your trading bot, charts, or browser to `http://localhost:5000/v2/...` and requests are automatically signed and tunneled through your static IP.

---

## 📁 Project Structure

```text
├── .env.example       # Safe template for environment variables (commit-safe)
├── .gitignore         # Ignores .env and temporary Python files
├── requirements.txt   # Lightweight Python dependencies (requests, python-dotenv)
├── server.py          # Local REST API proxy server (routes /v2/... to Delta)
├── test_delta.py      # Connection test, static IP validator & wallet inspector
└── README.md          # Documentation & quick start guide
```

---

## 🛠️ Installation & Setup

### 1. Clone Repository & Install Dependencies

```bash
git clone https://github.com/amit-programmer/static-ip.git
cd static-ip

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (`.env`)

Copy the template file:
```bash
copy .env.example .env     # Windows
# or: cp .env.example .env  # Linux / Mac
```

Edit `.env` with your credentials:
```env
# ==========================================
# Delta Exchange API (India Demo / Testnet)
# ==========================================
DELTA_BASE_URL=https://cdn-ind.testnet.deltaex.org
DELTA_API_KEY=your_delta_api_key
DELTA_API_SECRET=your_delta_api_secret

# ==========================================
# Outbound Static Proxy (Webshare)
# ==========================================
PROXY_HOST=45.38.107.97
PROXY_PORT=6014
PROXY_USERNAME=your_proxy_username
PROXY_PASSWORD=your_proxy_password

HTTP_PROXY=http://your_proxy_username:your_proxy_password@45.38.107.97:6014
HTTPS_PROXY=http://your_proxy_username:your_proxy_password@45.38.107.97:6014
```

> **Delta Base URLs:**
> - India Demo / Testnet: `https://cdn-ind.testnet.deltaex.org`
> - India Live: `https://api.india.delta.exchange`
> - Global Live: `https://api.delta.exchange`
> - Global Testnet: `https://testnet-api.delta.exchange`

---

## 🔐 Delta Exchange IP Whitelist Setup

In your [Delta Exchange Dashboard](https://india.delta.exchange) -> **API Management**:
1. Open your API key settings (`trader`).
2. Under **Whitelisted IP Address**, enter **only** your static egress IP:
   ```text
   45.38.107.97
   ```
3. Click **Update IP Address**.

*(Do **not** add Ngrok or local ISP IP addresses — only the Webshare static outbound IP must be whitelisted).*

---

## 🧪 Quick Test: Verify IP & Inspect Wallet

Run the standalone diagnostic tool:
```bash
python test_delta.py
```

### Expected Output:
```text
==================================================
Testing Outbound Connection to Delta Exchange...
Target Proxy: 45.38.107.97:6014
Active Base URL: https://cdn-ind.testnet.deltaex.org
==================================================

--- [Step 1] Checking Outbound Egress IP ---
Detected Outbound IP: 45.38.107.97
✅ Success! Static Outbound IP matches configured proxy (45.38.107.97).

==================================================
       DELTA EXCHANGE WALLET DETAILS
==================================================

💰 Account Equity Summary:
   • Total Net Equity   : 200.1698 USDT

📊 Asset Balances (1 assets total):
Asset      | Total Balance      | Available Balance  | Order / Margin    
------------------------------------------------------------------------
USDT       | 200.16979903       | 200.16979903       | 0.00000000        

📈 Open Positions (0 active):
   (No open positions currently active)
```

---

## 🚀 Running the Proxy Server

To start the local HTTP proxy gateway:
```bash
python server.py
```

Console Output:
```text
==================================================
🚀 Delta Static IP Proxy Server started on port 5000
👉 Open in browser: http://localhost:5000/v2/wallet/balances
👉 Outbound Proxy: 45.38.107.97:6014
==================================================
```

---

## 🌐 API Routes & URLs to Test

Once the server is running (`python server.py`), you can test these URLs in your browser or Postman:

| Route | Method | Description |
|---|---|---|
| `http://localhost:5000/` | `GET` | Health check & available endpoints list |
| `http://localhost:5000/test-ip` | `GET` | Verifies outbound egress IP is `45.38.107.97` |
| `http://localhost:5000/v2/wallet/balances` | `GET` | Auto-signs and returns live wallet balances |
| `http://localhost:5000/v2/positions/margined` | `GET` | Returns active open futures/options positions |
| `http://localhost:5000/v2/products` | `GET` | Public list of available symbols and tickers |
| `http://localhost:5000/v2/orders` | `POST` | Forwards and signs order placement requests |

### Example Browser Test:
Open `http://localhost:5000/v2/wallet/balances` in any browser:
```json
{
  "meta": {
    "net_equity": "200.16979903",
    "robo_trading_equity": "0.0",
    "tracker_equity": "0.0"
  },
  "result": [
    {
      "asset": {
        "id": 2,
        "symbol": "USDT"
      },
      "balance": "200.16979903",
      "available_balance": "200.16979903"
    }
  ],
  "success": true
}
```

---

## 🔒 Security

- All sensitive keys (`DELTA_API_KEY`, `DELTA_API_SECRET`, `PROXY_PASSWORD`) are loaded strictly from `.env`.
- `.env` is listed in `.gitignore` and is **never** committed to version control.
- Only `.env.example` with dummy values is tracked in the repository.

---

## 📜 License

MIT License. Free for algorithmic traders, webhook routing, and bot developers.
