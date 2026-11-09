# 🌐 Static IP Proxy Gateway & Delta Exchange Trading Bot Connector

A production-ready solution to solve dynamic IP and IP whitelisting restrictions for algorithmic trading and cloud webhooks. 

This repository provides two powerful tools:
1. **Delta Exchange Outbound Static IP Connector (`test_delta.py`)**: Directly routes trading requests through a dedicated fixed egress proxy (Webshare) with HMAC-SHA256 signature generation and automatic server clock drift synchronization.
2. **Cloudflare Worker Static IP Gateway (`app.js`)**: A serverless TCP socket proxy (`cloudflare:sockets`) that tunnels incoming HTTP/HTTPS requests through an outbound static IP to upstream services or Ngrok tunnels.

---

## 🚀 Key Features

- **Fixed Outbound Egress IP (`45.38.107.97`)**: Eliminates `invalid_api_key` and IP whitelist errors caused by dynamic home Wi-Fi or auto-restarting cloud containers (Render, Railway, AWS).
- **HMAC-SHA256 Request Signing**: Implements Delta Exchange API authentication compatible with Delta Exchange India & Global.
- **Server Timestamp Synchronization**: Automatically queries live HTTP `Date` headers from Delta Exchange to eliminate clock drift and expired signature issues within the strict 5-second window.
- **Full Wallet & Position Inspector**: Fetches real-time Net Equity, Available Balances, Margin used, and Open Futures/Options positions.
- **Zero-Secret Cloudflare Worker**: Reads all configuration dynamically from runtime environment variables.
- **Chunked Transfer Stream Decoding**: Decodes HTTP/1.1 chunked streams over raw TCP sockets without corrupting response payloads.

---

## 📁 Project Structure

```text
├── .env.example       # Template for required environment variables
├── .gitignore          # Keeps secrets and node_modules safe
├── app.js             # Cloudflare Worker raw TCP proxy gateway
├── package.json       # Scripts for local development and deployment
├── requirements.txt   # Python dependencies
├── test_delta.py      # Delta Exchange static IP test & wallet inspector
└── wrangler.toml      # Cloudflare Worker runtime configuration
```

---

## 🛠️ Quick Start

### 1. Clone & Setup Environment

```bash
git clone https://github.com/<your-username>/static-ip-proxy.git
cd static-ip-proxy

# Copy example environment file
copy .env.example .env
```

Edit `.env` with your credentials:
```env
# Delta Exchange (India Demo / Testnet)
DELTA_BASE_URL=https://cdn-ind.testnet.deltaex.org
DELTA_API_KEY=your_api_key_here
DELTA_API_SECRET=your_api_secret_here

# Webshare Static Proxy
PROXY_HOST=45.38.107.97
PROXY_PORT=6014
PROXY_USERNAME=your_proxy_username
PROXY_PASSWORD=your_proxy_password

HTTP_PROXY=http://username:password@45.38.107.97:6014
HTTPS_PROXY=http://username:password@45.38.107.97:6014
```

---

### 2. Delta Exchange IP Whitelist

In your [Delta Exchange API Management](https://india.delta.exchange) dashboard:
1. Open your API Key settings.
2. Under **Whitelisted IP Address**, enter your static IP:
   ```text
   45.38.107.97
   ```
3. Click **Update IP Address**.

---

### 3. Run the Delta Wallet Inspector (Python)

```bash
pip install -r requirements.txt
python test_delta.py
```

#### Output:
```text
==================================================
Testing Outbound Connection to Delta Exchange...
Target Proxy: 45.38.107.97:6014
Active Base URL: https://cdn-ind.testnet.deltaex.org
==================================================

--- [Step 1] Checking Outbound Egress IP ---
Detected Outbound IP: 45.38.107.97
✅ Success! Static Outbound IP matches 45.38.107.97.

==================================================
       DELTA EXCHANGE DEMO WALLET DETAILS
==================================================

💰 Account Equity Summary:
   • Total Net Equity   : 200.1698 USDT

📊 Asset Balances:
Asset      | Total Balance      | Available Balance  | Order / Margin    
------------------------------------------------------------------------
USDT       | 200.16979903       | 200.16979903       | 0.00000000        

📈 Open Positions:
   (No open positions currently active)
```

---

### 4. Deploy Cloudflare Worker (Optional - 24/7 Serverless)

```bash
# Login to Cloudflare
npx wrangler login

# Deploy
npx wrangler deploy
```

---

## 🔒 Security Best Practices

- **Never commit `.env` or `.dev.vars`** to version control.
- In production, set secrets on Cloudflare Workers using:
  ```bash
  npx wrangler secret put PROXY_AUTH
  npx wrangler secret put DELTA_API_SECRET
  ```

---

## 📄 License

MIT License. Free to use and modify for algorithmic trading and webhook routing.
