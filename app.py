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
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import ipaddress
import json
import re
import ssl
import socket
import sys

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

HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Bot Blocker Checker</title>
  <style>
    :root {
      --bg: #0c0c0f;
      --surface: #15151a;
      --surface2: #1c1c24;
      --border: #2a2a35;
      --text: #e8e8ed;
      --muted: #8b8b9a;
      --accent: #7c5cff;
      --accent-dim: #5a3fd4;
      --green: #22c55e;
      --red: #ef4444;
      --yellow: #eab308;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      line-height: 1.5;
    }
    .container {
      max-width: 960px;
      margin: 0 auto;
      padding: 2rem 1.25rem 4rem;
    }
    header {
      text-align: center;
      margin-bottom: 2.25rem;
    }
    h1 {
      font-size: 1.85rem;
      font-weight: 700;
      letter-spacing: -0.03em;
      margin-bottom: 0.4rem;
      background: linear-gradient(135deg, #a78bfa, #7c5cff, #60a5fa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .subtitle {
      color: var(--muted);
      font-size: 1rem;
    }
    .input-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      box-shadow: 0 4px 24px rgba(0,0,0,0.3);
    }
    .input-row {
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
    }
    input[type="url"], input[type="text"] {
      flex: 1;
      min-width: 200px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 0.85rem 1rem;
      color: var(--text);
      font-size: 1rem;
      outline: none;
      transition: border-color 0.15s;
    }
    input:focus { border-color: var(--accent); }
    button {
      background: var(--accent);
      color: white;
      border: none;
      border-radius: 10px;
      padding: 0.85rem 1.5rem;
      font-size: 1rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.15s, transform 0.1s;
      white-space: nowrap;
    }
    button:hover { background: var(--accent-dim); }
    button:active { transform: scale(0.98); }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .btn-secondary {
      background: var(--surface2);
      border: 1px solid var(--border);
      color: var(--text);
      font-size: 0.85rem;
      padding: 0.45rem 0.85rem;
    }
    .btn-secondary:hover { background: #252530; }
    .examples {
      margin-top: 0.85rem;
      font-size: 0.85rem;
      color: var(--muted);
    }
    .examples a {
      color: var(--accent);
      text-decoration: none;
      margin-right: 0.75rem;
      cursor: pointer;
    }
    .examples a:hover { text-decoration: underline; }
    #status {
      margin-top: 1rem;
      font-size: 0.9rem;
      color: var(--muted);
      min-height: 1.4em;
    }
    .results { display: none; }
    .results.visible { display: block; }
    .summary {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }
    .stat {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      text-align: center;
    }
    .stat-value { font-size: 1.75rem; font-weight: 700; }
    .stat-label { font-size: 0.8rem; color: var(--muted); margin-top: 0.25rem; }
    .stat.blocked .stat-value { color: var(--red); }
    .stat.allowed .stat-value { color: var(--green); }
    .stat.partial .stat-value { color: var(--yellow); }
    .section-title {
      font-size: 0.9rem;
      font-weight: 600;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin: 1.75rem 0 0.75rem;
    }
    .bot-grid { display: grid; gap: 0.55rem; }
    .bot-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 0.85rem 1.1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 1rem;
      transition: border-color 0.15s;
    }
    .bot-card:hover { border-color: #3a3a48; }
    .bot-info { display: flex; flex-direction: column; gap: 0.12rem; min-width: 0; }
    .bot-name { font-weight: 600; font-size: 0.95rem; }
    .bot-meta {
      font-size: 0.78rem;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .badge {
      flex-shrink: 0;
      padding: 0.28rem 0.65rem;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .badge.blocked {
      background: rgba(239, 68, 68, 0.15);
      color: var(--red);
      border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .badge.allowed {
      background: rgba(34, 197, 94, 0.15);
      color: var(--green);
      border: 1px solid rgba(34, 197, 94, 0.3);
    }
    .badge.unknown {
      background: rgba(234, 179, 8, 0.12);
      color: var(--yellow);
      border: 1px solid rgba(234, 179, 8, 0.25);
    }
    .raw-box, .rec-box {
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem;
      margin-top: 0.6rem;
      max-height: 320px;
      overflow: auto;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      font-size: 0.78rem;
      white-space: pre-wrap;
      word-break: break-all;
      color: #c4c4d4;
    }
    .error-box {
      background: rgba(239, 68, 68, 0.1);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 12px;
      padding: 1rem 1.25rem;
      color: #fca5a5;
      margin-bottom: 1rem;
    }
    .rec-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 1.25rem;
      margin-bottom: 1rem;
    }
    .rec-card h3 {
      font-size: 1.05rem;
      margin-bottom: 0.4rem;
    }
    .rec-card p {
      font-size: 0.88rem;
      color: var(--muted);
      margin-bottom: 0.75rem;
    }
    .rec-actions {
      display: flex;
      gap: 0.5rem;
      margin-bottom: 0.6rem;
      flex-wrap: wrap;
    }
    .insight {
      background: rgba(124, 92, 255, 0.1);
      border: 1px solid rgba(124, 92, 255, 0.25);
      border-radius: 10px;
      padding: 0.9rem 1rem;
      font-size: 0.9rem;
      margin-bottom: 1.25rem;
    }
    .insight strong { color: #c4b5fd; }
    footer {
      text-align: center;
      margin-top: 3rem;
      font-size: 0.8rem;
      color: var(--muted);
    }
    .note {
      font-size: 0.85rem;
      color: var(--muted);
      margin-top: 1.25rem;
      padding: 0.9rem 1rem;
      background: var(--surface);
      border-radius: 10px;
      border: 1px solid var(--border);
    }
    @media (max-width: 520px) {
      h1 { font-size: 1.5rem; }
      .input-row { flex-direction: column; }
      button { width: 100%; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>AI Bot Blocker Checker</h1>
      <p class="subtitle">Check which AI crawlers a site blocks, and get ready-to-use robots.txt recommendations</p>
    </header>

    <div class="input-card">
      <div class="input-row">
        <input type="url" id="urlInput" placeholder="https://example.com" autocomplete="url" spellcheck="false">
        <button id="checkBtn" onclick="runCheck()">Check</button>
      </div>
      <div class="examples">
        Try:
        <a onclick="fill('https://www.nytimes.com')">nytimes.com</a>
        <a onclick="fill('https://openai.com')">openai.com</a>
        <a onclick="fill('https://www.reddit.com')">reddit.com</a>
        <a onclick="fill('https://en.wikipedia.org')">wikipedia.org</a>
        <a onclick="fill('https://www.bbc.com')">bbc.com</a>
        <a onclick="fill('https://www.theguardian.com')">theguardian.com</a>
      </div>
      <div id="status"></div>
    </div>

    <div id="results" class="results">
      <div id="error" class="error-box" style="display:none;"></div>
      <div class="summary" id="summary"></div>
      <div id="insight" class="insight" style="display:none;"></div>
      <div id="bots"></div>

      <div class="section-title">Recommendations: control what AI bots can see</div>
      <div id="recommendations"></div>

      <div class="section-title">Raw robots.txt</div>
      <div class="raw-box" id="raw"></div>
      <div class="note">
        <strong>Note:</strong> This only inspects <code>robots.txt</code>. Cloudflare / WAF / Bot Fight Mode rules can still block AI traffic even when robots.txt allows it. User-triggered fetchers (ChatGPT-User, Claude-User, Perplexity-User) frequently ignore robots.txt by design. For stronger control consider Content-Signal directives and an <code>llms.txt</code> file.
      </div>
    </div>

    <footer>
      Expanded 2026 AI crawler list · Pure Python stdlib · Built for AI governance checks
    </footer>
  </div>

  <script>
    const input = document.getElementById('urlInput');
    const btn = document.getElementById('checkBtn');
    const status = document.getElementById('status');
    const results = document.getElementById('results');
    const errorEl = document.getElementById('error');
    const summaryEl = document.getElementById('summary');
    const botsEl = document.getElementById('bots');
    const rawEl = document.getElementById('raw');
    const insightEl = document.getElementById('insight');
    const recEl = document.getElementById('recommendations');

    function fill(u) {
      input.value = u;
      runCheck();
    }

    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') runCheck();
    });

    async function runCheck() {
      let url = input.value.trim();
      if (!url) {
        status.textContent = 'Please enter a URL';
        return;
      }
      if (!/^https?:\/\//i.test(url)) {
        url = 'https://' + url;
        input.value = url;
      }

      btn.disabled = true;
      status.textContent = 'Fetching robots.txt and evaluating 30+ AI crawlers…';
      results.classList.remove('visible');
      errorEl.style.display = 'none';
      insightEl.style.display = 'none';

      try {
        const res = await fetch('/api/check?url=' + encodeURIComponent(url));
        const data = await res.json();

        if (!res.ok || data.error) {
          throw new Error(data.error || 'Request failed');
        }

        render(data);
        results.classList.add('visible');
        status.textContent = 'Checked ' + data.robots_url + (data.has_robots ? '' : ' (no robots.txt found)');
      } catch (err) {
        status.textContent = '';
        errorEl.style.display = 'block';
        errorEl.textContent = err.message || 'Failed to check site';
        results.classList.add('visible');
      } finally {
        btn.disabled = false;
      }
    }

    function render(data) {
      const blocked = data.bots.filter(b => b.status === 'blocked').length;
      const allowed = data.bots.filter(b => b.status === 'allowed').length;
      const unknown = data.bots.filter(b => b.status === 'unknown').length;

      summaryEl.innerHTML = `
        <div class="stat blocked"><div class="stat-value">${blocked}</div><div class="stat-label">Blocked</div></div>
        <div class="stat allowed"><div class="stat-value">${allowed}</div><div class="stat-label">Allowed</div></div>
        <div class="stat partial"><div class="stat-value">${unknown}</div><div class="stat-label">Unknown</div></div>
        <div class="stat"><div class="stat-value">${data.bots.length}</div><div class="stat-label">Total checked</div></div>
      `;

      const searchBlocked = data.bots.filter(b => b.category === 'Search' && b.status === 'blocked');
      const trainingBlocked = data.bots.filter(b => b.category === 'Training' && b.status === 'blocked');
      let insightText = '';
      if (searchBlocked.length >= 3) {
        insightText = `<strong>Visibility risk:</strong> ${searchBlocked.length} search/retrieval bots are blocked (including ${searchBlocked.slice(0,3).map(b=>b.name).join(', ')}). This can remove the site from ChatGPT Search, Perplexity, Claude search results, and similar citation surfaces.`;
      } else if (blocked === 0) {
        insightText = `<strong>Fully open:</strong> No AI crawlers are blocked by robots.txt. The site is available for both training and AI search/citation.`;
      } else if (trainingBlocked.length > 0 && searchBlocked.length === 0) {
        insightText = `<strong>Balanced posture:</strong> Training bots are restricted while search/retrieval bots remain allowed. This is a common modern configuration for publishers who want citations without full training access.`;
      } else {
        insightText = `<strong>Mixed rules:</strong> Some AI bots are blocked. Review the categories below and use the recommendations to fine-tune.`;
      }
      insightEl.innerHTML = insightText;
      insightEl.style.display = 'block';

      const cats = {};
      data.bots.forEach(b => {
        if (!cats[b.category]) cats[b.category] = [];
        cats[b.category].push(b);
      });

      let html = '';
      const order = ['Search', 'User Fetch', 'Training', 'Other'];
      for (const cat of order) {
        if (!cats[cat] || cats[cat].length === 0) continue;
        html += `<div class="section-title">${cat} bots</div><div class="bot-grid">`;
        for (const b of cats[cat]) {
          const label = b.status === 'blocked' ? 'Blocked' : b.status === 'allowed' ? 'Allowed' : 'Unknown';
          html += `
            <div class="bot-card">
              <div class="bot-info">
                <div class="bot-name">${b.name}</div>
                <div class="bot-meta">${b.operator} · ${b.desc}</div>
              </div>
              <span class="badge ${b.status}">${label}</span>
            </div>`;
        }
        html += '</div>';
      }
      botsEl.innerHTML = html;

      const recs = data.recommendations || [];
      let recHtml = '';
      recs.forEach((r, idx) => {
        recHtml += `
          <div class="rec-card">
            <h3>${r.title}</h3>
            <p>${r.description}</p>
            <div class="rec-actions">
              <button class="btn-secondary" onclick="copyRec(${idx})">Copy robots.txt snippet</button>
            </div>
            <div class="rec-box" id="rec-${idx}">${escapeHtml(r.snippet)}</div>
          </div>`;
      });
      recEl.innerHTML = recHtml;
      window._recs = recs;

      rawEl.textContent = data.raw || '(empty or missing robots.txt, treated as allow all by most crawlers)';
    }

    function escapeHtml(s) {
      return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    function copyRec(idx) {
      const text = window._recs[idx].snippet;
      navigator.clipboard.writeText(text).then(() => {
        status.textContent = 'Copied recommendation to clipboard';
        setTimeout(() => status.textContent = '', 2000);
      });
    }

    input.focus();
  </script>
</body>
</html>
'''

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {args[0]}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ('/', '/index.html'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML.encode('utf-8'))
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


def assert_public_host(base_url: str) -> None:
    """Refuse hosts that resolve only to private, loopback, or link-local
    addresses so /api/check cannot be used as an internal-network probe."""
    host = urlparse(base_url).hostname or ''
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise RuntimeError(f"Could not resolve {host}: {e}")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
            return
    raise ValueError(f"{host} resolves to a private or local address; refusing to fetch it")


def fetch_robots_txt(base_url: str) -> tuple[str, str]:
    assert_public_host(base_url)
    robots_url = urljoin(base_url.rstrip('/') + '/', 'robots.txt')
    req = Request(robots_url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; AIBotChecker/1.1; +https://execlayer.io)',
        'Accept': 'text/plain,*/*',
    })
    ctx = ssl.create_default_context()
    try:
        with urlopen(req, timeout=14, context=ctx) as resp:
            content = resp.read().decode('utf-8', errors='replace')
            return content, robots_url
    except HTTPError as e:
        if e.code in (404, 410):
            return "", robots_url
        raise
    except (URLError, socket.timeout, ssl.SSLError) as e:
        raise RuntimeError(f"Could not reach {robots_url}: {e}")


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
