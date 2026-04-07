#!/usr/bin/env python3
"""
generate_brief.py — Daily market brief generator for Andy's Market Brief.

Fetches live prices from Yahoo Finance, generates AI-powered analysis
via the Grok API (xAI), and writes brief.json for the GitHub Pages site.

Usage:
    export XAI_API_KEY="your-key"
    python generate_brief.py
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

import requests
import yfinance as yf

# --- Config ---
WATCHLIST = ["TSLA", "LMND", "RIVN", "PONY", "MBLY", "SPY", "QQQ", "USO"]
OUTPUT_FILE = "brief.json"
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_MODEL = "grok-3-fast"
XAI_BASE_URL = "https://api.x.ai/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are Rusty, Andy's market brief AI. Andy is a retail investor focused on "
    "Tesla, Lemonade (LMND), EV/AV stocks, and emerging tech. Be direct, opinionated, "
    "and concise. No disclaimers."
)


def fetch_prices(tickers: list[str]) -> list[dict]:
    """Fetch current prices and daily change from Yahoo Finance."""
    results = []
    for ticker in tickers:
        try:
            t = yf.Ticker(ticker)
            info = t.fast_info
            price = info.last_price
            prev_close = info.previous_close
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0

            if change_pct > 2:
                signal = "🟢"
            elif change_pct < -2:
                signal = "🔴"
            else:
                signal = "🟡"

            results.append({
                "ticker": ticker,
                "price": round(price, 2),
                "change_pct": round(change_pct, 2),
                "signal": signal,
                "note": "",
            })
            print(f"  {ticker}: ${price:.2f} ({change_pct:+.2f}%)")
        except Exception as e:
            print(f"  {ticker}: ERROR — {e}")
            results.append({
                "ticker": ticker,
                "price": 0,
                "change_pct": 0,
                "signal": "⚪",
                "note": "Data unavailable",
            })
    return results


def call_grok(prompt: str) -> str:
    """Call the Grok API and return the response text."""
    if not XAI_API_KEY:
        print("  WARNING: XAI_API_KEY not set, using placeholder content")
        return ""

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": XAI_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 1500,
    }

    resp = requests.post(XAI_BASE_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_ai_content(watchlist_data: list[dict]) -> dict:
    """Generate macro summary, sector notes, opportunities, and trade setups via Grok."""
    price_summary = "\n".join(
        f"- {w['ticker']}: ${w['price']} ({w['change_pct']:+.2f}%)"
        for w in watchlist_data
    )

    # --- Macro + watchlist notes ---
    macro_prompt = f"""Here are today's prices for Andy's watchlist:

{price_summary}

Generate a JSON object with these fields:
1. "headline": A punchy one-line macro headline for today (max 15 words)
2. "bullets": Array of 3 concise macro bullet points covering market mood, key movers, and what to watch
3. "notes": Object mapping each ticker to a one-line note (what's happening, why it moved)

Return ONLY valid JSON, no markdown fences."""

    # --- EV/AV + Opportunities + Trade Setups ---
    sector_prompt = f"""Based on today's market data:

{price_summary}

Generate a JSON object with:
1. "ev_av": Array of 4-5 bullet strings about notable EV/AV sector moves and news today
2. "opportunity": Array of 1-2 objects with "title" and "body" fields — spotlight items worth watching (specific, actionable)
3. "trade_setups": Array of 4-5 objects with "ticker", "signal" (key level or pattern), and "action" (what to do)

Return ONLY valid JSON, no markdown fences."""

    macro_raw = call_grok(macro_prompt)
    sector_raw = call_grok(sector_prompt)

    # Defaults
    macro_data = {
        "headline": "Markets in motion — check back for AI analysis",
        "bullets": ["Waiting for Grok analysis..."],
        "notes": {},
    }
    sector_data = {
        "ev_av": ["EV/AV sector data pending..."],
        "opportunity": [{"title": "Loading...", "body": "AI analysis pending"}],
        "trade_setups": [],
    }

    if macro_raw:
        try:
            macro_data = json.loads(macro_raw)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = macro_raw.find("{")
            end = macro_raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    macro_data = json.loads(macro_raw[start:end])
                except json.JSONDecodeError:
                    print("  WARNING: Could not parse macro response")

    if sector_raw:
        try:
            sector_data = json.loads(sector_raw)
        except json.JSONDecodeError:
            start = sector_raw.find("{")
            end = sector_raw.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    sector_data = json.loads(sector_raw[start:end])
                except json.JSONDecodeError:
                    print("  WARNING: Could not parse sector response")

    return {
        "macro": {
            "headline": macro_data.get("headline", ""),
            "bullets": macro_data.get("bullets", []),
        },
        "notes": macro_data.get("notes", {}),
        "ev_av": sector_data.get("ev_av", []),
        "opportunity": sector_data.get("opportunity", []),
        "trade_setups": sector_data.get("trade_setups", []),
    }


def main():
    et = timezone(timedelta(hours=-4))
    now = datetime.now(et)
    print(f"=== Andy's Market Brief Generator ===")
    print(f"Time: {now.strftime('%Y-%m-%d %I:%M %p ET')}\n")

    # Fetch prices
    print("Fetching prices...")
    watchlist_data = fetch_prices(WATCHLIST)

    # Generate AI content
    print("\nGenerating AI analysis...")
    ai = generate_ai_content(watchlist_data)

    # Apply notes to watchlist
    notes = ai.get("notes", {})
    for item in watchlist_data:
        if item["ticker"] in notes and notes[item["ticker"]]:
            item["note"] = notes[item["ticker"]]
        elif not item["note"]:
            item["note"] = f"${item['price']} | {item['change_pct']:+.2f}%"

    # Build output
    brief = {
        "generated_at": now.isoformat(),
        "macro": ai["macro"],
        "watchlist": watchlist_data,
        "ev_av": ai["ev_av"],
        "opportunity": ai["opportunity"],
        "trade_setups": ai["trade_setups"],
    }

    # Write
    with open(OUTPUT_FILE, "w") as f:
        json.dump(brief, f, indent=2)

    print(f"\nBrief written to {OUTPUT_FILE}")
    print(f"\n--- HEADLINE ---")
    print(ai["macro"]["headline"])
    print(f"\n--- WATCHLIST ---")
    for w in watchlist_data:
        print(f"  {w['signal']} {w['ticker']}: ${w['price']} ({w['change_pct']:+.2f}%) — {w['note']}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
