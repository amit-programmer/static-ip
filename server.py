import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv

# Load functions and proxy configuration from test_delta
from test_delta import (
    make_authenticated_request,
    check_egress_ip,
    proxy_host,
    proxy_port,
    PROXIES,
    DELTA_BASE_URL,
    API_KEY,
    API_SECRET
)

PORT = int(os.getenv("PORT", "5000"))

class DeltaProxyHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        # 1. Health check endpoint
        if self.path == "/" or self.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            response = {
                "status": "ONLINE",
                "message": "Delta Exchange Static IP Proxy Server is Running",
                "outbound_static_ip": proxy_host,
                "target_delta_url": DELTA_BASE_URL,
                "endpoints": {
                    "wallet_balance": "/v2/wallet/balances",
                    "positions": "/v2/positions/margined",
                    "products": "/v2/products",
                    "test_static_ip": "/test-ip"
                }
            }
            self.wfile.write(json.dumps(response, indent=2).encode("utf-8"))
            return

        # 2. Test IP endpoint (verify outbound IP is 45.38.107.97)
        if self.path == "/test-ip":
            try:
                res = requests.get("https://ipv4.webshare.io/", proxies=PROXIES, timeout=10)
                current_ip = res.text.strip()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "SUCCESS",
                    "outbound_ip": current_ip,
                    "expected_ip": proxy_host,
                    "match": current_ip == proxy_host
                }, indent=2).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        # 3. Delta Exchange API Forwarding (GET)
        if self.path.startswith("/v2/"):
            self._forward_to_delta("GET")
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith("/v2/"):
            self._forward_to_delta("POST")
            return
        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        if self.path.startswith("/v2/"):
            self._forward_to_delta("PUT")
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        if self.path.startswith("/v2/"):
            self._forward_to_delta("DELETE")
            return
        self.send_response(404)
        self.end_headers()

    def _forward_to_delta(self, method):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            payload = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
            res = make_authenticated_request(method, self.path, payload=payload)
            self.send_response(res.status_code)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(res.content)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = HTTPServer(server_address, DeltaProxyHandler)
    print("==================================================")
    print(f"🚀 Delta Static IP Proxy Server started on port {PORT}")
    print(f"👉 Open in browser: http://localhost:{PORT}/v2/wallet/balances")
    print(f"👉 Outbound Proxy: {proxy_host}:{proxy_port}")
    print("==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
