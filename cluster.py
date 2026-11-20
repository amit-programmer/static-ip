"""
Cluster + Load Balancer - 1 process ki jagah 4 process
Run: python cluster.py
Phir test karo: http://127.0.0.1:8000/health  (8000 = Load Balancer)
Workers chalenge: 5001, 5002, 5003, 5004 pe
"""
import os
import subprocess
import sys
import time
import threading
import http.client
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

WORKER_PORTS = [5001, 5002, 5003, 5004]
LB_PORT = 8000

# Round-robin counter
_counter = 0
_lock = threading.Lock()

def get_next_worker():
    global _counter
    with _lock:
        port = WORKER_PORTS[_counter % len(WORKER_PORTS)]
        _counter += 1
        return port

class LoadBalancerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _handle(self, method):
        # 4 workers me se ek chuno, agar ek fail ho to dusra try karo
        for _ in range(len(WORKER_PORTS)):
            port = get_next_worker()
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) if length > 0 else None
                # Headers forward karo (Host chhod ke)
                headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
                conn.request(method, self.path, body=body, headers=headers)
                resp = conn.getresponse()
                data = resp.read()
                self.send_response(resp.status)
                for k, v in resp.getheaders():
                    if k.lower() not in ("connection", "transfer-encoding"):
                        self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                conn.close()
                return
            except Exception as e:
                print(f"Worker {port} fail: {e}, next try kar raha hu...")
                continue
        # Sab worker fail
        self.send_response(502)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", "27")
        self.end_headers()
        self.wfile.write(b'{"error": "all workers down"}')

    def do_GET(self): self._handle("GET")
    def do_POST(self): self._handle("POST")
    def do_PUT(self): self._handle("PUT")
    def do_DELETE(self): self._handle("DELETE")
    def do_OPTIONS(self): self._handle("OPTIONS")

def main():
    print("="*50)
    print("Starting 4 workers + Load Balancer...")
    procs = []
    env = os.environ.copy()
    # Workers start karo - har ek alag PORT pe
    for port in WORKER_PORTS:
        e = env.copy()
        e["PORT"] = str(port)
        p = subprocess.Popen([sys.executable, "server.py"], env=e)
        procs.append(p)
        print(f"Worker started on port {port} (PID {p.pid})")
    time.sleep(2)
    print(f"Load Balancer started on port {LB_PORT}")
    print(f"Test karo: http://127.0.0.1:{LB_PORT}/health")
    print("Band karne ke liye: Ctrl + C")
    print("="*50)
    try:
        ThreadingHTTPServer.allow_reuse_address = True
        ThreadingHTTPServer.daemon_threads = True
        ThreadingHTTPServer.request_queue_size = 256
        httpd = ThreadingHTTPServer(("0.0.0.0", LB_PORT), LoadBalancerHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping all workers...")
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()

if __name__ == "__main__":
    main()
