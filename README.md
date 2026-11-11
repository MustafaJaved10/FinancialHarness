# Financial Harness

Ask for stock prices, company financials, comparisons, and what-if calculations. The first demo uses IBM. AAPL and MSFT price history can use the included snapshots.

## Run locally

Open PowerShell here with Docker Desktop running:

```powershell
$env:STOCK_DATA_MODE = 'saved'
docker compose up --build --wait
python tools/smoke_integration.py
```

Open http://127.0.0.1:8080. The saved mode makes testing repeatable, and answers label their sources. Use `docker compose down` to stop the project.

## Live data and hosting

Set `STOCK_DATA_MODE=auto` and set `ALPHAVANTAGE_API_KEY` in the host environment to enable provider requests. The connector uses labelled saved data when available if the provider rejects or cannot answer a request. Market charts show daily historical candles. Company statements come from the company-data tool. The frontend and API share one port, and only the worker receives the provider key.

Set `SEC_CONTACT_EMAIL` to a real contact email to enable SEC EDGAR for IBM, AAPL, and MSFT filings. This email identifies the app to the SEC. It is not an API key. The worker reuses filings within a 15-minute cache window. An earnings-only question uses the filing without a market-price request. A valuation question can use one price lookup for trailing P/E. If EDGAR is unavailable, the existing connector and saved-data fallback still apply.

The Compose stack can run on a Linux Docker host. Keep the app port bound to loopback and serve it behind an HTTPS reverse proxy with access control for a reviewer demo. Run the saved-data smoke test on the host, then confirm a live request identifies its source. The sandbox has no network and receives data over a Unix socket. It accepts approved calculations only.

- [Architecture](docs/architecture.md)
- [Backlog and Miro content](docs/delivery.md)
- [Presentation and demo](docs/demo.md)
- Open http://127.0.0.1:8080/presentation.html for the slides.
