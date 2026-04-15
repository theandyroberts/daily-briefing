#!/usr/bin/env python3
"""
generate_brief.py — Fetch live prices and write prices.json.

Rusty (OpenClaw agent) handles research and brief writing via his own
web_search and x_search tools. This script only provides the price data.

Usage:
    python generate_brief.py
"""

import json
import sys
from datetime import datetime, timezone, timedelta

import requests
import yfinance as yf

OUTPUT_FILE = "prices.json"

COINGECKO_BTC_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
)


def fetch_stock_prices() -> dict:
    """Fetch TSLA, SPY, LMND prices from Yahoo Finance."""
    results = {}
    for symbol in ("TSLA", "SPY", "LMND"):
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            price = info.last_price
            prev_close = info.previous_close
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
            results[symbol] = {"price": round(price, 2), "change_pct": round(change_pct, 2)}
            print(f"  {symbol}: ${price:.2f} ({change_pct:+.2f}%)")
        except Exception as e:
            print(f"  {symbol}: ERROR — {e}")
            results[symbol] = {"price": 0, "change_pct": 0}
    return results


def fetch_btc_price() -> dict:
    """Fetch BTC price from CoinGecko free API."""
    try:
        resp = requests.get(COINGECKO_BTC_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()["bitcoin"]
        price = round(data["usd"])
        change = round(data.get("usd_24h_change", 0), 2)
        print(f"  BTC: ${price:,} ({change:+.2f}%)")
        return {"price": price, "change_24h_pct": change}
    except Exception as e:
        print(f"  BTC: ERROR — {e}")
        return {"price": 0, "change_24h_pct": 0}


def main():
    et = timezone(timedelta(hours=-4))
    now = datetime.now(et)
    is_friday = now.weekday() == 4

    print("=== Prices Fetcher ===")
    print(f"Time: {now.strftime('%Y-%m-%d %I:%M %p ET')}")
    print(f"Friday: {'Yes' if is_friday else 'No'}\n")

    print("Fetching stock prices...")
    stocks = fetch_stock_prices()

    print("Fetching BTC price...")
    btc = fetch_btc_price()

    prices_data = {
        "fetched_at": now.isoformat(),
        "is_friday": is_friday,
        "prices": {
            **stocks,
            "BTC": btc,
        },
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(prices_data, f, indent=2)

    import shutil, os
    briefs_dir = os.path.join(os.path.dirname(OUTPUT_FILE), "briefs")
    os.makedirs(briefs_dir, exist_ok=True)
    html_src = os.path.join(os.path.dirname(OUTPUT_FILE), "brief.html")
    html_dst = os.path.join(briefs_dir, now.strftime("%Y-%m-%d") + ".html")
    if os.path.exists(html_src):
        shutil.copy2(html_src, html_dst)
        date_str = now.strftime("%Y-%m-%d")
        print(f"Copied brief.html → briefs/{date_str}.html")
    print(f"\nWrote {OUTPUT_FILE}")
    print("Done — Rusty handles the rest.")


if __name__ == "__main__":
    main()
