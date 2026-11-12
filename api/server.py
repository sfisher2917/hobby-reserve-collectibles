"""Read-only inventory API with owner OAuth bootstrap; no listing storage or payload logs."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import threading
from urllib.parse import urlsplit, parse_qs
from oauth_connect import handle as oauth_handle
from ebay_live import ProductionEbay, InventoryError, configured, live_catalog, live_item

SLOTS = threading.BoundedSemaphore(3)
ORIGIN = 'https://hobby-reserve-collectibles.onrender.com'

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send_json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store, private, max-age=0')
        self.send_header('CDN-Cache-Control', 'no-store')
        self.send_header('Pragma', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Access-Control-Allow-Origin', ORIGIN)
        self.send_header('Vary', 'Origin')
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path = urlsplit(self.path).path
        if path.startswith('/oauth/'):
            if oauth_handle(self,path,parse_qs(urlsplit(self.path).query)): return
        if path == '/health':
            return self.send_json(200, {'status':'ok', 'environment':'production',
                'configured':configured(), 'listingStorage':'none'})
        item = re.fullmatch(r'/api/items/(\d{9,15})', path)
        if path != '/api/inventory' and not item: return self.send_json(404, {'error':'not_found'})
        if not SLOTS.acquire(blocking=False): return self.send_json(429, {'error':'busy_retry'})
        try:
            api = ProductionEbay()
            data = live_item(api, item.group(1)) if item else live_catalog(api)
            self.send_json(200, data)
        except InventoryError as error:
            self.send_json(error.status, {'status':'unavailable', 'error':error.code})
        except Exception:
            self.send_json(503, {'status':'unavailable', 'error':'upstream_unavailable'})
        finally: SLOTS.release()
    def do_POST(self):
        path=urlsplit(self.path).path
        if path.startswith('/oauth/') and oauth_handle(self,path,{},'POST'): return
        self.send_json(405, {'error':'read_only'})
    def do_PUT(self): self.send_json(405, {'error':'read_only'})
    do_DELETE = do_PUT

if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '10000'))), Handler).serve_forever()
