# AI Bot Blocker Checker

**Live demo: https://ai-bot-checker-exec.vercel.app**

[![CI](https://github.com/BMC-INC/ai-bot-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/BMC-INC/ai-bot-checker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Enter any website and instantly see **which AI crawlers it blocks** via `robots.txt`, with **ready-to-copy robots.txt templates** to open the site up to AI search, lock it down, or land in between.

## Why

AI answer engines (ChatGPT Search, Perplexity, Claude, Gemini) are becoming a real traffic and citation channel. Whether a site appears there is largely decided by a handful of `robots.txt` lines most people have never audited. This tool makes that posture visible in one click and hands you the fix.

## Features

- Checks **32 major AI crawlers**: OpenAI, Anthropic, Google, Perplexity, Meta, Apple, ByteDance, Amazon, Common Crawl, Cohere, Diffbot, You.com, DuckDuckGo, Mistral, Phind, Allen AI, Webz.io, and more
- Grouped by purpose: **Search**, **User Fetch**, **Training**, with an instant posture insight (e.g. "Visibility risk: search bots are blocked")
- Three ready-to-copy robots.txt templates: **Allow all**, **Balanced** (allow search and citations, block pure training), **Block everything**
- One-shot **CLI mode** with JSON output, pipes cleanly into `jq` and CI
- **SSRF-hardened** fetcher: strict public-address validation, IP-pinned connections (no DNS-rebinding window), re-validated redirects, body size cap
- **Zero dependencies**: pure Python standard library

## Use the hosted version

https://ai-bot-checker-exec.vercel.app

The API is public too:

```bash
curl "https://ai-bot-checker-exec.vercel.app/api/check?url=https://www.nytimes.com"
```

## Run locally

```bash
git clone https://github.com/BMC-INC/ai-bot-checker.git
cd ai-bot-checker
python3 app.py
```

Open **http://localhost:8765**. Binds to `127.0.0.1` by default; use `--host 0.0.0.0 --port 9000` to expose it elsewhere.

## CLI mode

```bash
python3 app.py --check https://www.nytimes.com
```

Prints the full result as JSON: per-bot verdicts, the raw robots.txt, and the three recommendation templates. Exits non-zero on failure.

```bash
python3 app.py --check reddit.com | jq '[.bots[] | select(.status=="blocked").name]'
```

## Project layout

| Path | Purpose |
|---|---|
| `app.py` | Core logic plus the local dev server and CLI |
| `public/index.html` | The web UI, served statically in production |
| `api/check.py` | Vercel serverless function wrapping the same core |
| `test_app.py` | Offline unit tests, stdlib `unittest` only |

Pushes to `main` auto-deploy to Vercel.

## Tests

```bash
python3 -m unittest -v
```

Fully offline, no network access. CI runs the suite plus a byte-compile check on every push and PR.

## What the recommendations do

- **Allow all**: explicit `Allow: /` for the important AI bots so ChatGPT Search, Perplexity, Claude, Gemini, etc. can index and cite you.
- **Balanced**: keeps search/retrieval bots open (visibility) while `Disallow: /` on pure training crawlers (GPTBot, ClaudeBot, CCBot, Bytespider, etc.).
- **Block all**: full opt-out (also removes you from most AI answer engines).

## Limitations

- Only inspects `robots.txt`. Cloudflare / WAF rules are not visible here.
- Some user-triggered fetchers ignore robots.txt by design.
- Missing robots.txt is treated as allow-all, matching most crawlers' behavior.

## Contributing

Issues and PRs welcome. Keep it stdlib-only, add a test for any behavior change, and make sure `python3 -m unittest` passes.

## License

[MIT](LICENSE)
