# AI Bot Blocker Checker

Understand the `robots.txt` rules a website publishes for AI crawlers, then prepare a crawler policy that fits your goals.

[![CI](https://github.com/BMC-INC/ai-bot-checker/actions/workflows/ci.yml/badge.svg)](https://github.com/BMC-INC/ai-bot-checker/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[Hosted app](https://ai-bot-checker-exec.vercel.app) · [Report a problem](https://github.com/BMC-INC/ai-bot-checker/issues)

## What it does

A small, self-hostable diagnostic for site owners and developers. Enter a domain to see its published root-path rules for 30 distinct crawler tokens, organized into Search, User Fetch, and Training categories. The same Python core powers the browser interface, JSON API, and command-line tool.

- Fetches the site's `robots.txt` and shows a preview (up to 12,000 characters) alongside per-token results.
- Summarizes the rules without treating them as proof of indexing, citations, or training use.
- Generates three editable policies: allow the listed crawlers, restrict the Training category, or disallow every listed crawler.
- Uses only Python's standard library; no account, API key, database, or package installation is required.

**Status:** working diagnostic with an offline regression suite. The catalog includes legacy tokens and is not a complete inventory of AI crawlers. Category labels are a practical guide, not an operator's contractual policy.

## Run locally

Requires Python 3.10 or newer.

```bash
git clone https://github.com/BMC-INC/ai-bot-checker.git
cd ai-bot-checker
python3 app.py
```

Open [localhost:8765](http://localhost:8765). The local server binds to `127.0.0.1`; `--port` and `--host` can override this for a controlled deployment.

### Command line

```bash
python3 app.py --check https://example.com
```

Outputs JSON containing the normalized origin, `robots_url`, inspected text, bot results, posture summary, unscored tokens, and policy snippets. Fetch failures produce an error on stderr and a nonzero exit code.

### HTTP API

With the local server running:

```bash
curl 'http://localhost:8765/api/check?url=https://example.com'
```

The Vercel adapter uses the same `/api/check?url=...` route. [`vercel.json`](vercel.json) defines the repository's deployment configuration.

## Read the result correctly

The check evaluates **`/` on the submitted origin**, using Python's `urllib.robotparser`. A URL containing a deeper path is normalized to its origin. Rules for other paths may differ, and crawler-specific interpretation can differ from this parser. This is not a full RFC conformance validator.

A successful fetch with empty rules, or an HTTP 404/410, is treated as allowing the listed tokens. Other HTTP failures, unreachable sites, excessive redirects, and files exceeding 512 KiB return an error rather than a partial verdict.

`robots.txt` requests crawler behavior; it is not access control. A disallowed URL can still be indexed through other signals, and an allowed URL is not guaranteed to appear in any search product. See [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309) and [Google's robots.txt guidance](https://developers.google.com/search/docs/crawling-indexing/robots/intro).

The checker cannot inspect a site's firewall, login requirements, crawler logs, private content, or downstream data use.

## Apply a policy

The generated snippets cover the same catalog as the report. They deliberately omit a wildcard group so they do not replace rules for unrelated crawlers. Review and merge them with existing groups; simply appending duplicate groups may have different effects across parsers. Keep any existing path restrictions, sitemap directives, and non-AI crawler policies you still need.

## Network safeguards

Each fetch and redirect resolves the hostname, rejects non-public addresses, and connects to the validated IP while retaining HTTPS certificate verification for the original hostname. Fetches have a timeout, redirect limit, and body-size cap. These controls reduce server-side request forgery risk; a public deployment still needs appropriate rate limits and operational monitoring.

## Development

```bash
python3 -m unittest -v
python3 -m py_compile app.py api/check.py
```

The offline tests cover URL handling, crawler evaluation, generated-policy behavior, posture summaries, address restrictions, and oversized responses. CI runs tests on pushes and pull requests.

| File | Responsibility |
| --- | --- |
| [`app.py`](app.py) | Fetching, evaluation, policy generation, local server, CLI |
| [`public/index.html`](public/index.html) | Browser interface |
| [`api/check.py`](api/check.py) | Vercel HTTP adapter |
| [`test_app.py`](test_app.py) | Offline regression tests |

Contributions should keep the tool dependency-free and include a behavioral test for fixes. When updating the crawler catalog, verify names and purposes against operator documentation.

## License

[MIT](LICENSE). Part of the [BMC-INC portfolio](https://github.com/BMC-INC).
