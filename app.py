#!/usr/bin/env python3
"""
AI Bot Blocker Checker, expanded 2026 edition.
Checks robots.txt for dozens of AI crawlers and generates recommended allow rules.

Run the web UI:      python3 app.py
One-shot CLI check:  python3 app.py --check https://example.com
"""

import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urljoin
from urllib.robotparser import RobotFileParser
import http.client
import ipaddress
import json
import re
import ssl
import socket
import sys
import os

# Comprehensive AI crawler list (mid-2026)
AI_BOTS = [
    # OpenAI
    {"ua": "GPTBot", "name": "GPTBot", "operator": "OpenAI", "category": "Training", "desc": "Primary training crawler for GPT models"},
    {"ua": "OAI-SearchBot", "name": "OAI-SearchBot", "operator": "OpenAI", "category": "Search", "desc": "ChatGPT Search / SearchGPT index"},
    {"ua": "ChatGPT-User", "name": "ChatGPT-User", "operator": "OpenAI", "category": "User Fetch", "desc": "Live user-initiated page fetches in ChatGPT"},
    
    # Anthropic
    {"ua": "ClaudeBot", "name": "ClaudeBot", "operator": "Anthropic", "category": "Training", "desc": "Claude model training crawler"},
    {"ua": "Claude-SearchBot", "name": "Claude-SearchBot", "operator": "Anthropic", "category": "Search", "desc": "Claude search quality & citation index"},
    {"ua": "Claude-User", "name": "Claude-User", "operator": "Anthropic", "category": "User Fetch", "desc": "User-directed retrieval inside Claude"},
    {"ua": "anthropic-ai", "name": "anthropic-ai", "operator": "Anthropic", "category": "Training", "desc": "Legacy Anthropic training UA"},
    {"ua": "claude-web", "name": "claude-web", "operator": "Anthropic", "category": "User Fetch", "desc": "Legacy live browsing UA"},
    
    # Google
    {"ua": "Google-Extended", "name": "Google-Extended", "operator": "Google", "category": "Training", "desc": "Gemini / AI training & grounding control (not Search ranking)"},
    {"ua": "GoogleOther", "name": "GoogleOther", "operator": "Google", "category": "Training", "desc": "Google research / AI-related crawling"},
    {"ua": "Google-CloudVertexBot", "name": "Google-CloudVertexBot", "operator": "Google", "category": "Search", "desc": "Vertex AI / Cloud AI platform crawler"},
    
    # Perplexity
    {"ua": "PerplexityBot", "name": "PerplexityBot", "operator": "Perplexity", "category": "Search", "desc": "Perplexity answer index (high citation value)"},
    {"ua": "Perplexity-User", "name": "Perplexity-User", "operator": "Perplexity", "category": "User Fetch", "desc": "Live user fetches (often ignores robots.txt)"},
    
    # Meta
    {"ua": "Meta-ExternalAgent", "name": "Meta-ExternalAgent", "operator": "Meta", "category": "Training", "desc": "Meta AI / Llama training collection"},
    {"ua": "meta-externalagent", "name": "meta-externalagent", "operator": "Meta", "category": "Training", "desc": "Lowercase variant of Meta-ExternalAgent"},
    {"ua": "Meta-ExternalFetcher", "name": "Meta-ExternalFetcher", "operator": "Meta", "category": "User Fetch", "desc": "Meta AI user-triggered fetcher"},
    {"ua": "FacebookBot", "name": "FacebookBot", "operator": "Meta", "category": "Training", "desc": "Facebook / Meta AI related crawler"},
    
    # Apple
    {"ua": "Applebot-Extended", "name": "Applebot-Extended", "operator": "Apple", "category": "Training", "desc": "Apple Intelligence training signal"},
    {"ua": "Applebot", "name": "Applebot", "operator": "Apple", "category": "Search", "desc": "Apple search + Siri / Intelligence indexing"},
    
    # Others
    {"ua": "CCBot", "name": "CCBot", "operator": "Common Crawl", "category": "Training", "desc": "Open web corpus used by many AI labs"},
    {"ua": "Bytespider", "name": "Bytespider", "operator": "ByteDance", "category": "Training", "desc": "TikTok / Doubao training (aggressive)"},
    {"ua": "Amazonbot", "name": "Amazonbot", "operator": "Amazon", "category": "Training", "desc": "Alexa & Amazon AI services"},
    {"ua": "cohere-ai", "name": "cohere-ai", "operator": "Cohere", "category": "Training", "desc": "Cohere enterprise model training"},
    {"ua": "Diffbot", "name": "Diffbot", "operator": "Diffbot", "category": "Training", "desc": "Structured knowledge-graph extraction"},
    {"ua": "YouBot", "name": "YouBot", "operator": "You.com", "category": "Search", "desc": "You.com AI search index"},
    {"ua": "DuckAssistBot", "name": "DuckAssistBot", "operator": "DuckDuckGo", "category": "Search", "desc": "DuckAssist AI answers"},
    {"ua": "MistralAI-User", "name": "MistralAI-User", "operator": "Mistral", "category": "User Fetch", "desc": "Mistral Le Chat live fetches"},
    {"ua": "PhindBot", "name": "PhindBot", "operator": "Phind", "category": "Search", "desc": "Phind developer-focused AI search"},
    {"ua": "AI2Bot", "name": "AI2Bot", "operator": "Allen Institute", "category": "Training", "desc": "Allen AI research / Semantic Scholar"},
    {"ua": "ai2bot", "name": "ai2bot", "operator": "Allen Institute", "category": "Training", "desc": "Lowercase AI2Bot variant"},
    {"ua": "omgili", "name": "omgili", "operator": "Webz.io", "category": "Training", "desc": "Webz.io data mining crawler"},
    {"ua": "Omgilibot", "name": "Omgilibot", "operator": "Webz.io", "category": "Training", "desc": "Webz.io variant"},
]

PORT = 8765

HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public', 'index.html')


def load_html() -> str:
    with open(HTML_PATH, encoding='utf-8') as f:
        return f.read()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(load_html().encode('utf-8'))
            return

        if parsed.path == '/api/check':
            qs = parse_qs(parsed.query)
            url = qs.get('url', [None])[0]
            if not url:
                self._json(400, {"error": "Missing url parameter"})
                return
            try:
                result = check_site(url)
                self._json(200, result)
            except ValueError as e:
                self._json(400, {"error": str(e)})
            except RuntimeError as e:
                self._json(502, {"error": str(e)})
            except Exception as e:
                print(f"[error] /api/check {url!r}: {e}")
                self._json(500, {"error": "Internal error while checking the site"})
            return

        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'Not found')

    def _json(self, code, obj):
        body = json.dumps(obj, indent=2).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def normalize_url(url: str) -> str:
    url = url.strip()
    if not re.match(r'^https?://', url, re.I):
        url = 'https://' + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError(f"Not a valid URL: {url!r}")
    return f"{parsed.scheme}://{parsed.netloc}"


def resolve_public_ip(host: str) -> str:
    """Resolve host and return one address, refusing the host outright if ANY
    resolved address is private, loopback, link-local, or otherwise non-public.
    The caller connects to the returned address directly (no second DNS lookup),
    which closes the DNS-rebinding window between check and fetch."""
    if not host:
        raise ValueError("Missing hostname")
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise RuntimeError(f"Could not resolve {host}: {e}")
    ips = []
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_multicast or ip.is_unspecified or ip.is_reserved):
            raise ValueError(f"{host} resolves to a private or local address; refusing to fetch it")
        ips.append(str(ip))
    if not ips:
        raise RuntimeError(f"Could not resolve {host}")
    return ips[0]


def assert_public_host(base_url: str) -> None:
    """Refuse URLs whose host resolves to any private or local address."""
    resolve_public_ip(urlparse(base_url).hostname or '')


class _PinnedHTTPConnection(http.client.HTTPConnection):
    """HTTP connection that connects to a pre-validated IP while keeping the
    original hostname for the Host header."""

    def __init__(self, host, ip, **kwargs):
        super().__init__(host, **kwargs)
        self._pinned_ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS connection pinned to a pre-validated IP. SNI and certificate
    validation still use the original hostname."""

    def __init__(self, host, ip, context=None, **kwargs):
        super().__init__(host, context=context, **kwargs)
        self._pinned_ip = ip

    def connect(self):
        sock = socket.create_connection((self._pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


MAX_REDIRECTS = 3
FETCH_TIMEOUT = 14
MAX_BODY_BYTES = 512 * 1024


def fetch_robots_txt(base_url: str) -> tuple[str, str]:
    """Fetch <base_url>/robots.txt with SSRF-safe semantics: every hop
    (including redirects) is resolved once, validated as public, and the TCP
    connection is made to that exact validated address."""
    robots_url = urljoin(base_url.rstrip('/') + '/', 'robots.txt')
    url = robots_url
    ctx = ssl.create_default_context()

    for _ in range(MAX_REDIRECTS + 1):
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Unsupported scheme in {url!r}")
        host = parsed.hostname or ''
        ip = resolve_public_ip(host)
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)

        if parsed.scheme == 'https':
            conn = _PinnedHTTPSConnection(host, ip, context=ctx, port=port, timeout=FETCH_TIMEOUT)
        else:
            conn = _PinnedHTTPConnection(host, ip, port=port, timeout=FETCH_TIMEOUT)

        path = parsed.path or '/'
        if parsed.query:
            path += '?' + parsed.query
        try:
            conn.request('GET', path, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; AIBotChecker/1.1; +https://execlayer.io)',
                'Accept': 'text/plain,*/*',
            })
            resp = conn.getresponse()
            if resp.status in (301, 302, 303, 307, 308):
                location = resp.headers.get('Location')
                resp.read(0)
                if not location:
                    raise RuntimeError(f"Redirect from {url} with no Location header")
                url = urljoin(url, location)
                continue
            if resp.status in (404, 410):
                return "", robots_url
            if resp.status >= 400:
                raise RuntimeError(f"HTTP {resp.status} fetching {url}")
            content = resp.read(MAX_BODY_BYTES).decode('utf-8', errors='replace')
            return content, robots_url
        except (OSError, http.client.HTTPException, ssl.SSLError) as e:
            raise RuntimeError(f"Could not reach {url}: {e}")
        finally:
            conn.close()

    raise RuntimeError(f"Too many redirects fetching {robots_url}")


def build_recommendations(bots_result: list) -> list:
    allow_all = """# Allow all major AI crawlers (maximum visibility / citations)
# Add these rules or remove any Disallow lines for these user-agents.

User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: GoogleOther
Allow: /

User-agent: Meta-ExternalAgent
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: YouBot
Allow: /

User-agent: DuckAssistBot
Allow: /

User-agent: *
Allow: /
"""

    balanced = """# Balanced 2026 posture: allow AI search & citations, restrict pure training scrapers
# Search/retrieval bots stay open → better chance of being cited in ChatGPT, Claude, Perplexity, etc.

# Allow search & user-triggered fetchers
User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: YouBot
Allow: /

User-agent: DuckAssistBot
Allow: /

User-agent: MistralAI-User
Allow: /

# Restrict pure training crawlers (optional)
User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: *
Allow: /
"""

    block_all = """# Block all major AI crawlers (no training, no AI search visibility)
# Warning: this removes the site from ChatGPT Search, Perplexity, Claude search, etc.

User-agent: GPTBot
Disallow: /

User-agent: OAI-SearchBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: Claude-SearchBot
Disallow: /

User-agent: Claude-User
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Perplexity-User
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: GoogleOther
Disallow: /

User-agent: Meta-ExternalAgent
Disallow: /

User-agent: FacebookBot
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Amazonbot
Disallow: /

User-agent: cohere-ai
Disallow: /

User-agent: Diffbot
Disallow: /

User-agent: YouBot
Disallow: /

User-agent: *
Allow: /
"""

    return [
        {
            "title": "1. Allow all major AI bots (recommended for visibility)",
            "description": "Best default if you want your content cited in ChatGPT, Claude, Perplexity, Gemini answers, etc. Explicit Allow rules make intent clear.",
            "snippet": allow_all.strip()
        },
        {
            "title": "2. Balanced: allow search/citations, block pure training",
            "description": "Popular publisher approach in 2026. Keeps you visible in AI answers while opting out of model-training crawls. Search bots stay open; training bots are disallowed.",
            "snippet": balanced.strip()
        },
        {
            "title": "3. Block everything AI-related",
            "description": "Use only if you want zero AI use of your content. This will also hide the site from AI search features and most citation surfaces.",
            "snippet": block_all.strip()
        },
    ]


def evaluate_bots(robots_content: str, base_url: str) -> list:
    """Pure evaluation of a robots.txt body against the AI crawler list.
    No network access, so it is directly unit-testable."""
    rp = RobotFileParser()
    rp.parse(robots_content.splitlines())
    test_path = base_url.rstrip('/') + '/'

    bots_result = []
    for bot in AI_BOTS:
        try:
            allowed = rp.can_fetch(bot["ua"], test_path)
            status = "allowed" if allowed else "blocked"
        except Exception:
            status = "unknown"
        bots_result.append({
            "ua": bot["ua"],
            "name": bot["name"],
            "operator": bot["operator"],
            "category": bot["category"],
            "desc": bot["desc"],
            "status": status,
        })
    return bots_result


def check_site(user_url: str) -> dict:
    base = normalize_url(user_url)
    content, robots_url = fetch_robots_txt(base)
    bots_result = evaluate_bots(content, base)

    return {
        "url": base,
        "robots_url": robots_url,
        "raw": content[:12000] if content else "",
        "bots": bots_result,
        "has_robots": bool(content.strip()),
        "recommendations": build_recommendations(bots_result),
    }


def main():
    parser = argparse.ArgumentParser(description="Check which AI crawlers a site blocks via robots.txt")
    parser.add_argument('--host', default='127.0.0.1', help="Bind address for the web UI (default: 127.0.0.1)")
    parser.add_argument('--port', type=int, default=PORT, help=f"Port for the web UI (default: {PORT})")
    parser.add_argument('--check', metavar='URL', help="One-shot CLI mode: check URL, print JSON, exit")
    args = parser.parse_args()

    if args.check:
        try:
            print(json.dumps(check_site(args.check), indent=2))
        except (ValueError, RuntimeError) as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        return

    server = HTTPServer((args.host, args.port), Handler)
    print(f"AI Bot Blocker Checker running at http://{args.host}:{args.port}")
    print(f"Checking {len(AI_BOTS)} AI crawlers")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down")
        server.server_close()


if __name__ == '__main__':
    main()
