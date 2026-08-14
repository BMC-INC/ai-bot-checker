# AI Bot Blocker Checker (Expanded 2026)

A lightweight web app that tells you **which AI crawlers a website blocks** via its `robots.txt`, and gives you **ready-to-copy recommendations** so bots can see (or stay blocked from) the site.

## Features

- Checks **32 major AI crawlers** (OpenAI, Anthropic, Google, Perplexity, Meta, Apple, ByteDance, Cohere, Diffbot, You.com, DuckDuckGo, Mistral, Phind, Allen AI, Webz.io, and more)
- Grouped by purpose: **Search**, **User Fetch**, **Training**
- Instant insight (e.g. “Visibility risk if search bots are blocked”)
- Three ready-to-use robots.txt templates:
  1. **Allow all** (maximum AI visibility / citations)
  2. **Balanced** (allow search & citations, block pure training)
  3. **Block everything** AI-related
- One-click copy of the recommended snippet
- Pure Python standard library — no dependencies

## Run it

```bash
python3 app.py
```

Open **http://localhost:8765**

## What the recommendations do

- **Allow all** — Explicit `Allow: /` for the important AI bots so ChatGPT Search, Perplexity, Claude, Gemini, etc. can index and cite you.
- **Balanced** — Keeps search/retrieval bots open (visibility) while `Disallow: /` on pure training crawlers (GPTBot, ClaudeBot, CCBot, Bytespider, etc.).
- **Block all** — Full opt-out (also removes you from most AI answer engines).

## Notes

- Only inspects `robots.txt`. Cloudflare / WAF rules are not visible here.
- Some user-triggered fetchers ignore robots.txt by design.
- Missing robots.txt = treat as allow-all for most bots.

## License

MIT
