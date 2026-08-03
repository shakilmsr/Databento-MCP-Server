# databento — CME futures & market data MCP server

One endpoint, **https://mcp.epl.solutions/databento/mcp**, wrapping the
[Databento](https://databento.com) Historical and Live REST APIs
(`hist.databento.com` / `live.databento.com`) as an MCP server. Python +
FastMCP, streamable-http, single `databento_core.py` client + a thin
`server.py`.

- code: `/root/mcp-stack/databento/`
- container: `databento-container` on `127.0.0.1:8008`
- nginx: `location = /databento/mcp` in `/etc/nginx/sites-available/mcp.epl.solutions`
- auth: HTTP Basic, API key as username (Databento's documented scheme)

## Setup

```bash
cp .env.example .env   # fill in DATABENTO_API_KEY (must start with "db-")
docker compose up -d --build
```

`MCP_PORT` defaults to `8008`. There is no stdio mode — `server.py` always
starts the FastMCP streamable-http transport; the Docker/nginx path above is
the only supported way to run this deployment.

## Tools (13)

| category | tool | what it does |
| --- | --- | --- |
| Quotes & bars (ES/NQ only) | `get_futures_quote` | Current price for `ES` or `NQ` continuous front-month, from Databento's live feed during the NY session, historical `mbp-1` otherwise |
| | `get_historical_bars` | OHLCV bars (`1h`, `H4`, `1d`) for `ES`/`NQ` |
| | `get_session_info` | Classifies a timestamp (default: now) into Asian/London/NY trading sessions (UTC-hour buckets, not exchange calendars) |
| Timeseries | `timeseries_get_range` | Raw historical data for any dataset/schema/symbol/date range |
| Symbology | `symbology_resolve` | Resolve symbols to instrument IDs (or other symbol types) across a date range, any dataset |
| Metadata | `metadata_list_datasets`, `metadata_list_schemas`, `metadata_list_publishers`, `metadata_list_fields`, `metadata_get_cost`, `metadata_get_dataset_range` | Dataset/schema/publisher/field discovery and pre-download cost estimation |
| Batch | `batch_submit_job`, `batch_list_jobs` | Submit and track large historical downloads |

`get_futures_quote` and `get_historical_bars` are hardcoded to `GLBX.MDP3`
(CME Globex) and only know `ES`→`ES.c.0` and `NQ`→`NQ.c.0`. Every other tool
takes `dataset` as a parameter and works with any of Databento's ~29 datasets.

## `get_futures_quote` freshness — read this before treating it as live

This tool's "current" quote is only as fresh as **your API key's Databento
entitlement allows**, not a fixed delay. Two independent things can cap it:

1. **Ingestion lag** — the historical API's data horizon trails real time by a
   few minutes.
2. **Licensing embargo** — GLBX.MDP3 requires a real-time (or better) license
   to access recent data; without one, the API rejects any `end` past the
   licensed horizon with an HTTP 422 that names the exact cutoff.

The client treats both the same way: it starts with a tight lookback (15 min),
and on a rejected `end` it reads the server-reported cutoff from the error
body and re-queries against that — widening the lookback (4h → 1d → 3d) only
if that still comes back empty (e.g. a real market closure over a weekend).
`dataAge` in the response is always the true gap in milliseconds, so callers
can see exactly how stale a given quote is rather than assuming "current".

**Measured against the API key currently in `.env`: this account has a
~12-hour delayed entitlement for GLBX.MDP3**, so `get_futures_quote` and
`get_historical_bars`'s most recent bar will consistently lag live price by
about 12 hours during and outside the NY session alike. That's a Databento
subscription/plan limit, not something fixable in this client — a real-time
GLBX.MDP3 license on the account would remove it.

(Earlier versions of this client fetched a flat 7-day window with `limit=100`
on the tick-level `mbp-1` schema; since `timeseries.get_range` streams
chronologically from `start`, that returned the first 100 ticks after a
week-old `start`, not the newest ones — quotes could silently be several
*days* stale rather than the ~12 hours the account's license actually allows.
Fixed 2026-08-03.)
