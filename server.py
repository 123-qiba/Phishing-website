import http.server
import socketserver
import json
import os

PORT = 8000
BLACKLIST_FILE = 'blacklist.txt'

class BlacklistRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path == '/blacklist':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            try:
                if os.path.exists(BLACKLIST_FILE):
                    with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip()]
                    self.wfile.write(json.dumps(lines).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps([]).encode('utf-8'))
            except Exception as e:
                self.send_error(500, str(e))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/blacklist':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                # data should be a list of strings
                if isinstance(data, list):
                    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
                        for url in data:
                            f.write(f"{url}\n")
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
                else:
                    self.send_error(400, "Invalid data format. Expected a list.")
            except Exception as e:
                self.send_error(500, str(e))
        else:
            self.send_error(404, "Endpoint not found")

print(f"Server started at http://localhost:{PORT}")
print(f"Monitoring file: {os.path.abspath(BLACKLIST_FILE)}")

with socketserver.TCPServer(("", PORT), BlacklistRequestHandler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
