# AI Bot Blocker Checker (Expanded 2026)

A lightweight web app that tells you **which AI crawlers a website blocks** via its `robots.txt`, and gives you **ready-to-copy recommendations** so bots can see (or stay blocked from) the site.

## Features

- Checks **32 major AI crawlers** (OpenAI, Anthropic, Google, Perplexity, Meta, Apple, ByteDance, Cohere, Diffbot, You.com, DuckDuckGo, Mistral, Phind, Allen AI, Webz.io, and more)
- Grouped by purpose: **Search**, **User Fetch**, **Training**
- Instant insight (e.g. "Visibility risk if search bots are blocked")
- Three ready-to-use robots.txt templates:
  1. **Allow all** (maximum AI visibility / citations)
  2. **Balanced** (allow search & citations, block pure training)
  3. **Block everything** AI-related
- One-click copy of the recommended snippet
- One-shot CLI mode with JSON output, easy to pipe into other tools
- SSRF guard: refuses to probe private, loopback, or link-local addresses
- Pure Python standard library, no dependencies

## Run the web UI

```bash
python3 app.py
```

Open **http://localhost:8765**

Binds to `127.0.0.1` by default. Use `--host 0.0.0.0 --port 9000` to expose it elsewhere.

## CLI mode

```bash
python3 app.py --check https://www.nytimes.com
```

Prints the full result as JSON: per-bot verdicts, the raw robots.txt, and the three recommendation templates. Exits non-zero on failure, so it works in scripts and CI.

```bash
python3 app.py --check reddit.com | jq '[.bots[] | select(.status=="blocked").name]'
```

## Tests

```bash
python3 -m unittest -v
```

Fully offline, stdlib `unittest` only. CI runs them on every push and PR.

## What the recommendations do

- **Allow all**: explicit `Allow: /` for the important AI bots so ChatGPT Search, Perplexity, Claude, Gemini, etc. can index and cite you.
- **Balanced**: keeps search/retrieval bots open (visibility) while `Disallow: /` on pure training crawlers (GPTBot, ClaudeBot, CCBot, Bytespider, etc.).
- **Block all**: full opt-out (also removes you from most AI answer engines).

## Notes

- Only inspects `robots.txt`. Cloudflare / WAF rules are not visible here.
- Some user-triggered fetchers ignore robots.txt by design.
- Missing robots.txt = treat as allow-all for most bots.

## License

MIT
