# Andy's Daily Intelligence Brief

A daily AI intelligence briefing dashboard published on GitHub Pages.

## Live Site

Visit the GitHub Pages deployment to see the latest brief.

## How It Works

1. `generate_brief.py` fetches live prices (TSLA, SPY, LMND via Yahoo Finance; BTC via CoinGecko) and writes `prices.json`
2. **Rusty** (OpenClaw agent) reads prices, searches the web and X/Twitter for news, and writes `brief.json`
3. `index.html` reads `brief.json` and renders the briefing dashboard
4. GitHub Pages serves the static site from the `main` branch

## Running the Price Fetcher

```bash
pip install -r requirements.txt
python generate_brief.py
```

This writes `prices.json` with current prices and daily changes.

## Automation

The brief is generated automatically via OpenClaw cron, running weekdays at 7:30 AM ET. Rusty fetches prices, researches news using his web_search and x_search tools, writes `brief.json`, and pushes to `main` — GitHub Pages picks up the change automatically.

## Tracked Prices

| Ticker | Focus |
|--------|-------|
| TSLA | Core position, robotaxi catalyst |
| SPY | Broad market benchmark |
| LMND | Insurance disruption, growth story |
| BTC | $10 DCA every Friday |
