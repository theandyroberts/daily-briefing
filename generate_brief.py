#!/usr/bin/env python3
"""
generate_brief.py — Andy's Daily AI Intelligence Brief generator.

Fetches live prices, calls Grok for narrative content across 6 sections,
and writes brief.json for the GitHub Pages site.

Usage:
    export XAI_API_KEY="your-key"
    python generate_brief.py
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import yfinance as yf

# --- Config ---
OUTPUT_FILE = "brief.json"
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_MODEL = "grok-3"
XAI_BASE_URL = "https://api.x.ai/v1/chat/completions"

COINGECKO_BTC_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
)

SYSTEM_PROMPT = """You are Rusty, Andy's daily intelligence briefing AI. Andy is an AI builder and entrepreneur — NOT a trader. He builds AI agents (his platform is OpenClaw, running on Claude and xAI APIs). He wants to stay on top of:
- AI research, new models, and capabilities
- Agent frameworks, MCP, prompt engineering
- Tesla/SpaceX/xAI ecosystem
- Movies & streaming
- AI-powered marketing automation
- Macro markets (minimal, just prices and mood)

Be direct, opinionated, and builder-focused. No disclaimers. No investor advice. Think "what can Andy learn or try today to build better agents?"."""


def fetch_stock_prices() -> dict:
    """Fetch TSLA, SPY, LMND prices from Yahoo Finance."""
    tickers = {"tsla": "TSLA", "spy": "SPY", "lmnd": "LMND"}
    results = {}
    for key, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            price = info.last_price
            prev_close = info.previous_close
            change_pct = ((price - prev_close) / prev_close) * 100 if prev_close else 0
            results[key] = {"price": round(price, 2), "change_pct": round(change_pct, 2)}
            print(f"  {symbol}: ${price:.2f} ({change_pct:+.2f}%)")
        except Exception as e:
            print(f"  {symbol}: ERROR — {e}")
            results[key] = {"price": 0, "change_pct": 0}
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
        return {"price": price, "change_pct": change}
    except Exception as e:
        print(f"  BTC: ERROR — {e}")
        return {"price": 0, "change_pct": 0}


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
        "max_tokens": 4000,
    }

    resp = requests.post(XAI_BASE_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def parse_json_response(raw: str):
    """Extract JSON from a Grok response, handling markdown fences."""
    if not raw:
        return None
    # Try direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown fences
    if "```" in raw:
        start = raw.find("```")
        # Skip the language tag line
        start = raw.find("\n", start) + 1
        end = raw.find("```", start)
        if end > start:
            try:
                return json.loads(raw[start:end].strip())
            except json.JSONDecodeError:
                pass
    # Try finding JSON object
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass
    return None


def generate_brief_content(prices: dict, btc: dict, is_friday: bool, today_str: str) -> dict:
    """Generate all 6 sections via Grok."""

    price_context = (
        f"Today is {today_str}.\n"
        f"TSLA: ${prices['tsla']['price']} ({prices['tsla']['change_pct']:+.2f}%)\n"
        f"SPY: ${prices['spy']['price']} ({prices['spy']['change_pct']:+.2f}%)\n"
        f"LMND: ${prices['lmnd']['price']} ({prices['lmnd']['change_pct']:+.2f}%)\n"
        f"BTC: ${btc['price']:,} ({btc['change_pct']:+.2f}%)\n"
    )

    friday_instruction = ""
    if is_friday:
        friday_instruction = """
For the macro.btc_friday_note field: Andy buys $10 of BTC every Friday morning. Based on the current BTC price and weekly trend, give him a one-line note like "Good entry — DCA into weakness" or "Buying into strength, but $10 is $10"."""

    prompt = f"""Search your knowledge for the latest AI news, tech news, movie releases, and market data from the past week. Generate Andy's Daily Intelligence Brief.

Context — live prices:
{price_context}

Generate a JSON object with EXACTLY this structure (no extra keys, no missing keys):

{{
  "ai_research": {{
    "headline": "Punchy one-line headline about the biggest AI news",
    "items": [
      {{"title": "...", "body": "2-3 sentences", "tag": "model|paper|china|xai", "learn_url": "https://..."}}
    ],
    "learn_today": "One sentence: the most important thing to learn or try today"
  }},
  "openclaw_agents": {{
    "headline": "One-line headline about agent/tool news",
    "items": [
      {{"title": "...", "body": "2-3 sentences", "try_this": "Optional actionable tip"}}
    ],
    "try_today": "One sentence: what to try in your agent setup today"
  }},
  "tesla_spacex_xai": {{
    "tesla": {{"note": "One line on Tesla news (price is injected separately)"}},
    "spacex": "One line on SpaceX",
    "xai": "One line on xAI/Grok"
  }},
  "movies": {{
    "items": [
      {{"title": "Movie/Show Name", "platform": "Netflix|Theaters|etc", "verdict": "watch|skip|wait", "note": "One sentence opinion"}}
    ]
  }},
  "marketing": {{
    "items": [
      {{"title": "...", "body": "2-3 sentences", "tool": "optional tool name"}}
    ]
  }},
  "macro_mood": "One sentence macro mood for today"{', "btc_friday_note": "..."' if is_friday else ''}
}}

Rules:
- ai_research: 4-6 items covering new models (US + China), papers, xAI/Grok news, DeepSeek/Qwen/etc. Tags: model (new model releases), paper (research papers), china (Chinese AI), xai (xAI/Grok specific).
- openclaw_agents: 3-5 items about Claude API, Anthropic news, agent frameworks (LangGraph, CrewAI, AutoGen), MCP developments, prompt engineering.
- tesla_spacex_xai: One line each. For Tesla include key catalyst (robotaxi, FSD, deliveries, Elon drama).
- movies: 3-5 items that are actually new this week in theaters or streaming. Be opinionated — watch/skip/wait.
- marketing: 3-4 items about AI-powered marketing tools, social media automation (TikTok, Instagram, Reddit), growth hacking with AI. Relevant to marketing mobile apps and quiz games.
- macro_mood: One sentence vibes check on markets.
{friday_instruction}
- learn_url: Real URLs to papers, blog posts, or announcements. If you're not sure of the exact URL, use a search URL like https://scholar.google.com/scholar?q=...
- Be opinionated and direct. This is for a builder, not an investor.

Return ONLY valid JSON, no markdown fences, no commentary."""

    raw = call_grok(prompt)
    data = parse_json_response(raw)

    if not data:
        print("  WARNING: Could not parse Grok response, using defaults")
        return get_defaults(is_friday)

    return data


def get_defaults(is_friday: bool) -> dict:
    """Return placeholder content when Grok is unavailable."""
    result = {
        "ai_research": {
            "headline": "AI intelligence brief loading...",
            "items": [{"title": "Waiting for Grok", "body": "XAI_API_KEY may not be set.", "tag": "model", "learn_url": ""}],
            "learn_today": "Set your XAI_API_KEY to get the full brief.",
        },
        "openclaw_agents": {
            "headline": "Agent news loading...",
            "items": [{"title": "Waiting for Grok", "body": "Check back soon.", "try_this": ""}],
            "try_today": "Check back soon.",
        },
        "tesla_spacex_xai": {
            "tesla": {"note": "Data pending"},
            "spacex": "Data pending",
            "xai": "Data pending",
        },
        "movies": {
            "items": [{"title": "Loading...", "platform": "—", "verdict": "wait", "note": "Check back soon."}],
        },
        "marketing": {
            "items": [{"title": "Loading...", "body": "Check back soon.", "tool": ""}],
        },
        "macro_mood": "Brief loading — check back soon.",
    }
    if is_friday:
        result["btc_friday_note"] = "Brief loading — check back soon."
    return result


def main():
    et = timezone(timedelta(hours=-4))
    now = datetime.now(et)
    is_friday = now.weekday() == 4
    today_str = now.strftime("%A, %B %d, %Y")

    print(f"=== Andy's Daily Intelligence Brief Generator ===")
    print(f"Time: {now.strftime('%Y-%m-%d %I:%M %p ET')}")
    print(f"Friday: {'Yes' if is_friday else 'No'}\n")

    # Fetch prices
    print("Fetching prices...")
    prices = fetch_stock_prices()
    btc = fetch_btc_price()

    # Generate AI content
    print("\nGenerating intelligence brief via Grok...")
    ai = generate_brief_content(prices, btc, is_friday, today_str)

    # Build output
    brief = {
        "generated_at": now.isoformat(),
        "title": "Andy's Daily Intelligence Brief",
        "ai_research": ai.get("ai_research", get_defaults(is_friday)["ai_research"]),
        "openclaw_agents": ai.get("openclaw_agents", get_defaults(is_friday)["openclaw_agents"]),
        "tesla_spacex_xai": {
            "tesla": {
                "price": prices["tsla"]["price"],
                "change_pct": prices["tsla"]["change_pct"],
                "note": ai.get("tesla_spacex_xai", {}).get("tesla", {}).get("note", ""),
            },
            "spacex": ai.get("tesla_spacex_xai", {}).get("spacex", ""),
            "xai": ai.get("tesla_spacex_xai", {}).get("xai", ""),
        },
        "movies": ai.get("movies", get_defaults(is_friday)["movies"]),
        "marketing": ai.get("marketing", get_defaults(is_friday)["marketing"]),
        "macro": {
            "spy": prices["spy"],
            "tsla": prices["tsla"],
            "lmnd": prices["lmnd"],
            "btc": btc,
            "mood": ai.get("macro_mood", ""),
        },
    }

    # Add Friday BTC note
    if is_friday and "btc_friday_note" in ai:
        brief["macro"]["btc_friday_note"] = ai["btc_friday_note"]

    # Write main brief.json
    with open(OUTPUT_FILE, "w") as f:
        json.dump(brief, f, indent=2)

    # Write dated archive copies
    script_dir = Path(__file__).resolve().parent
    briefs_dir = script_dir / "briefs"
    briefs_dir.mkdir(exist_ok=True)

    date_str = now.strftime("%Y-%m-%d")
    dated_json = briefs_dir / f"{date_str}.json"
    with open(dated_json, "w") as f:
        json.dump(brief, f, indent=2)

    # Copy brief.html template as the dated HTML page
    brief_template = script_dir / "brief.html"
    dated_html = briefs_dir / f"{date_str}.html"
    if brief_template.exists():
        shutil.copy2(brief_template, dated_html)

    print(f"\nBrief written to {OUTPUT_FILE}")
    print(f"Archive written to {dated_json} and {dated_html}")
    print(f"\n--- HEADLINE ---")
    print(brief["ai_research"].get("headline", ""))
    print(f"\nDone.")


if __name__ == "__main__":
    main()
