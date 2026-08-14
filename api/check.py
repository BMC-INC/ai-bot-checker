"""Vercel serverless entry for /api/check. Thin wrapper around app.check_site."""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app import check_site  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        url = qs.get('url', [None])[0]
        if not url:
            self._json(400, {"error": "Missing url parameter"})
            return
        try:
            self._json(200, check_site(url))
        except ValueError as e:
            self._json(400, {"error": str(e)})
        except RuntimeError as e:
            self._json(502, {"error": str(e)})
        except Exception as e:
            print(f"[error] /api/check {url!r}: {e}")
            self._json(500, {"error": "Internal error while checking the site"})

    def _json(self, code, obj):
        body = json.dumps(obj, indent=2).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
