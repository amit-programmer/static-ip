import os
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import requests
from dotenv import load_dotenv

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
    # HTTP/1.0 hi rakho - har request ke baad connection band, Locust / curl se 100% compatible
    # HTTP/1.1 me Content-Length bhejna padta hai warna client hang ho jata hai

    def log_message(self, format, *args):
        return

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def _send_json(self, status, obj):
        body = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        print(f"📥 Incoming GET: {self.path} (from {self.client_address[0]})")
        if self.path in ("/", "", "/health", "/v2/health"):
            self._send_json(200, {
                "status": "ONLINE",
                "message": "Delta Exchange Static IP Proxy Server is Running",
                "outbound_static_ip": proxy_host,
                "target_delta_url": DELTA_BASE_URL,
                "endpoints": {
                    "health": "/v2/health (or /health)",
                    "wallet_balance": "/v2/wallet/balances",
                    "positions": "/v2/positions/margined",
                    "products": "/v2/products",
                    "test_static_ip": "/test-ip"
                }
            })
            return

        if self.path == "/test-ip":
            try:
                res = requests.get("https://ipv4.webshare.io/", proxies=PROXIES, timeout=10)
                current_ip = res.text.strip()
                self._send_json(200, {
                    "status": "SUCCESS",
                    "outbound_ip": current_ip,
                    "expected_ip": proxy_host,
                    "match": current_ip == proxy_host
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        if self.path.startswith("/v2/"):
            self._forward_to_delta("GET")
            return

        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        print(f"📥 Incoming POST: {self.path} (from {self.client_address[0]})")
        if self.path.startswith("/v2/"):
            self._forward_to_delta("POST")
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_PUT(self):
        print(f"📥 Incoming PUT: {self.path} (from {self.client_address[0]})")
        if self.path.startswith("/v2/"):
            self._forward_to_delta("PUT")
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_DELETE(self):
        print(f"📥 Incoming DELETE: {self.path} (from {self.client_address[0]})")
        if self.path.startswith("/v2/"):
            self._forward_to_delta("DELETE")
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _forward_to_delta(self, method):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            payload = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
            res = make_authenticated_request(method, self.path, payload=payload)
            print(f"📤 Delta API Response: HTTP {res.status_code}")
            body = res.content
            self.send_response(res.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            print(f"❌ Forwarding Error: {e}")
            self._send_json(502, {"error": str(e)})

def run_server():
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer.request_queue_size = 128

    server_address = ("0.0.0.0", PORT)
    httpd = ThreadingHTTPServer(server_address, DeltaProxyHandler)
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
