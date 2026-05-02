# -*- coding: utf-8 -*-
"""
processor.py
============
Hourly intelligence pipeline for Sovereign Mind :: MENA Command.

Pipeline:
    1. Scrape ~100 articles from global + MENA-regional RSS feeds
    2. (optional) Pull recent posts from public Telegram channels
    3. Deduplicate, normalize, enrich with metadata (lang, region tags)
    4. Run a SINGLE Scout pass with ALL articles stuffed into context
       — Scout returns: per-article sentiment per persona, hidden-link
         clusters, suggested arc edges for the butterfly map, and
         strategic recommendations for each of the three personas.
    5. Persist to data/data.json (atomic write).

Designed to run in GitHub Actions on a free runner (cron: every hour).

Required env vars:
    GROQ_API_KEY           — required
    TELEGRAM_API_ID        — optional, enables Telethon
    TELEGRAM_API_HASH      — optional
    TELEGRAM_SESSION       — optional, base64 string session

Run locally:
    GROQ_API_KEY=... python processor.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
import requests
from dateutil import parser as dtparser
from tenacity import retry, stop_after_attempt, wait_exponential

# Optional imports — soft fail
try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None  # type: ignore

try:
    import httpx
    import groq
    # Force httpx client without proxies argument (fixes groq 0.11 + httpx 0.28 conflict)
    if not hasattr(httpx.Client.__init__, '_patched'):
        _orig_httpx_init = httpx.Client.__init__
        def _patched_init(self, **kwargs):
            kwargs.pop('proxies', None)
            _orig_httpx_init(self, **kwargs)
        _patched_init._patched = True
        httpx.Client.__init__ = _patched_init
    from groq import Groq
except ImportError:
    Groq = None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_PATH = DATA_DIR / "data.json"

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_ARTICLES = 100
ARTICLE_BODY_CHARS = 1200          # truncation per article inside Scout prompt
USER_AGENT = "SovereignMind/1.0 (+https://example.org)"
REQUEST_TIMEOUT = 15

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("sovereign-mind")


# ---------------------------------------------------------------------------
# Source registry  (zero-cost public RSS only)
# ---------------------------------------------------------------------------
GLOBAL_FEEDS = [
    ("Reuters World",      "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters Business",   "https://feeds.reuters.com/reuters/businessNews"),
    ("BBC World",          "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera English", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("FT World",           "https://www.ft.com/world?format=rss"),
    ("Bloomberg Markets",  "https://feeds.bloomberg.com/markets/news.rss"),
    ("AP World",           "https://feeds.apnews.com/rss/apf-worldnews"),
]

REGIONAL_FEEDS = [
    # Morocco
    ("Hespress EN",     "https://en.hespress.com/feed"),
    ("Morocco World News", "https://www.moroccoworldnews.com/feed"),
    ("Le Matin MA",     "https://lematin.ma/rss"),
    # KSA
    ("Saudi Gazette",   "https://saudigazette.com.sa/rssFeed/91"),
    ("Arab News",       "https://www.arabnews.com/rss.xml"),
    # UAE
    ("The National",    "https://www.thenationalnews.com/rss"),
    ("Khaleej Times",   "https://www.khaleejtimes.com/rss"),
    ("Gulf News",       "https://gulfnews.com/rss"),
    # Pan-regional
    ("Middle East Eye", "https://www.middleeasteye.net/rss"),
    ("Asharq Al-Awsat", "https://english.aawsat.com/feed"),
]

# Public Telegram channels that publish news headlines
# Telethon path is optional — most users will run on RSS only.
TELEGRAM_CHANNELS = [
    "AJABreaking",
    "spa_news",
    "WAMNEWS",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class Article:
    id: str
    title: str
    summary: str
    link: str
    source: str
    published: str
    region: str           # "global" | "mena"
    lang: str             # "en" | "fr" | "ar" | "und"
    body: str = ""
    # Enrichment fields populated by Scout
    entities: list[str] = field(default_factory=list)
    geo_tags: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    sentiment: dict[str, float] = field(default_factory=dict)   # per-persona advantage score [-1..1]
    risk: dict[str, float] = field(default_factory=dict)        # per-persona risk score [0..1]
    hidden_links: list[str] = field(default_factory=list)       # cluster IDs
    arc_to: list[str] = field(default_factory=list)             # ["MA","SA","AE"] subset
    arc_strength: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Scraping layer
# ---------------------------------------------------------------------------
def _stable_id(*parts: str) -> str:
    h = hashlib.sha1("||".join(parts).encode("utf-8", errors="ignore")).hexdigest()
    return h[:16]


def _detect_lang(text: str) -> str:
    if not text or not _lang_detect:
        return "und"
    try:
        code = _lang_detect(text)
        if code.startswith("ar"):
            return "ar"
        if code.startswith("fr"):
            return "fr"
        if code.startswith("en"):
            return "en"
        return code[:2]
    except Exception:
        return "und"


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
def _fetch_feed(url: str) -> Any:
    return feedparser.parse(url, agent=USER_AGENT)


def scrape_rss() -> list[Article]:
    out: list[Article] = []
    for region_label, feeds in [("global", GLOBAL_FEEDS), ("mena", REGIONAL_FEEDS)]:
        for source, url in feeds:
            try:
                parsed = _fetch_feed(url)
            except Exception as e:
                log.warning("feed %s failed: %s", source, e)
                continue
            for entry in parsed.entries[:25]:
                title = _clean(getattr(entry, "title", ""))
                link = getattr(entry, "link", "")
                if not title or not link:
                    continue
                summary = _clean(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                published = ""
                for cand in ("published", "updated", "created"):
                    raw = getattr(entry, cand, None)
                    if raw:
                        try:
                            published = dtparser.parse(raw).astimezone(timezone.utc).isoformat()
                            break
                        except Exception:
                            continue
                if not published:
                    published = datetime.now(timezone.utc).isoformat()
                lang = _detect_lang(f"{title}. {summary}")
                out.append(
                    Article(
                        id=_stable_id(link, title),
                        title=title,
                        summary=summary[:600],
                        link=link,
                        source=source,
                        published=published,
                        region=region_label,
                        lang=lang,
                    )
                )
    log.info("scraped %d articles via RSS", len(out))
    return out


def scrape_telegram() -> list[Article]:
    """Optional Telegram pull — only runs if Telethon credentials are present."""
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_b64 = os.getenv("TELEGRAM_SESSION")
    if not (api_id and api_hash and session_b64):
        log.info("telegram credentials not set — skipping")
        return []
    try:
        from telethon.sessions import StringSession
        from telethon.sync import TelegramClient
    except ImportError:
        log.info("telethon not installed — skipping")
        return []

    out: list[Article] = []
    try:
        with TelegramClient(StringSession(session_b64), int(api_id), api_hash) as client:
            for handle in TELEGRAM_CHANNELS:
                try:
                    for msg in client.iter_messages(handle, limit=10):
                        if not msg.message:
                            continue
                        text = _clean(msg.message)[:500]
                        if not text:
                            continue
                        out.append(
                            Article(
                                id=_stable_id(handle, str(msg.id)),
                                title=text[:120],
                                summary=text,
                                link=f"https://t.me/{handle}/{msg.id}",
                                source=f"Telegram :: {handle}",
                                published=msg.date.astimezone(timezone.utc).isoformat()
                                if msg.date else datetime.now(timezone.utc).isoformat(),
                                region="mena",
                                lang=_detect_lang(text),
                            )
                        )
                except Exception as e:
                    log.warning("tg channel %s failed: %s", handle, e)
    except Exception as e:
        log.warning("telegram pull failed: %s", e)
    log.info("scraped %d articles via Telegram", len(out))
    return out


# ---------------------------------------------------------------------------
# Dedup + window
# ---------------------------------------------------------------------------
def dedupe_and_window(articles: list[Article], limit: int = MAX_ARTICLES) -> list[Article]:
    seen: set[str] = set()
    keep: list[Article] = []
    # Prefer freshest first
    articles.sort(key=lambda a: a.published, reverse=True)
    for a in articles:
        sig = re.sub(r"[^a-z0-9]", "", a.title.lower())[:80]
        if sig in seen or not sig:
            continue
        seen.add(sig)
        keep.append(a)
        if len(keep) >= limit:
            break
    log.info("kept %d unique articles in window", len(keep))
    return keep


# ---------------------------------------------------------------------------
# Scout enrichment — single pass, full-context
# ---------------------------------------------------------------------------
SCOUT_SYSTEM = """You are SCOUT — a senior geopolitical analyst inside the Sovereign Mind \
intelligence console. Three sovereign personas consume your output:

  MA = Morocco (The Atlas Strategist) — pillars: Green Hydrogen, Automotive/Aerospace, \
Phosphates/Food Security, Africa-Atlantic Gateway, Tourism.
  SA = Saudi Arabia (The Visionary Architect) — pillars: Vision 2030 / NEOM, Energy Transition / PIF, \
Tourism & Soft Power, AI & Semiconductor Sovereignty, Regional Security.
  AE = UAE (The Global Connector) — pillars: AI Finance / Sovereign Tech (G42, MGX), Logistics & Aviation, \
Crypto / Digital Assets, Energy Diplomacy (ADNOC, Masdar), Talent & Capital.

You will receive a JSON array of news articles. Use the FULL context window — find non-obvious \
"hidden links" across articles (e.g., a US chip-export rule + a Korean shipyard fire + an ADNOC \
LNG deal can together reshape MA's renewable financing window).

Return STRICT JSON, no prose, no markdown fences, exactly this schema:
{
  "articles": [
     {
       "id": "<echoed>",
       "entities": ["..."],          // 0-6 named orgs/people/states
       "geo_tags": ["..."],           // ISO-3166 alpha-2 country codes mentioned
       "topics": ["..."],             // 1-4 short topic tags
       "sentiment": {"MA": -1..1, "SA": -1..1, "AE": -1..1},   // sovereign advantage
       "risk":      {"MA": 0..1,  "SA": 0..1,  "AE": 0..1},    // sovereign risk
       "arc_to":    ["MA"|"SA"|"AE"], // which capitals this event most plausibly arcs to
       "arc_strength": {"MA": 0..1, "SA": 0..1, "AE": 0..1},
       "hidden_links": ["<cluster_id>", ...]  // tag membership
     }
  ],
  "clusters": [
     {
       "id": "C1",
       "label": "<short noun phrase>",
       "narrative": "<2-3 sentence hidden-link explanation>",
       "member_ids": ["<article id>", ...],
       "personas": ["MA","SA","AE"]   // who this cluster matters most to
     }
  ],
  "recommendations": {
     "MA": [{"title":"...", "body":"...", "horizon":"24h|7d|30d", "confidence":0..1}],
     "SA": [...], "AE": [...]
  },
  "advantage_index": {"MA": -1..1, "SA": -1..1, "AE": -1..1},
  "risk_index":      {"MA": 0..1,  "SA": 0..1,  "AE": 0..1}
}

Be specific, decisive, and write recommendations in the voice of the sovereign \
(MA = patient strategist, SA = visionary architect, AE = global connector)."""


def _build_scout_payload(articles: list[Article]) -> str:
    slim = []
    for a in articles:
        slim.append(
            {
                "id": a.id,
                "title": a.title[:240],
                "summary": (a.summary or a.body)[:ARTICLE_BODY_CHARS],
                "source": a.source,
                "region": a.region,
                "lang": a.lang,
                "published": a.published,
            }
        )
    return json.dumps(slim, ensure_ascii=False)


def _strip_fences(s: str) -> str:
    s = s.strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    return s.strip()


def enrich_with_scout(articles: list[Article]) -> dict[str, Any]:
    if Groq is None:
        log.warning("groq SDK not installed — returning skeleton enrichment")
        return _empty_enrichment(articles)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        log.warning("GROQ_API_KEY not set — returning skeleton enrichment")
        return _empty_enrichment(articles)

    client = Groq(api_key=api_key)
    payload = _build_scout_payload(articles)

    log.info("calling Scout with %d articles (~%d chars)", len(articles), len(payload))
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SCOUT_SYSTEM},
                {
                    "role": "user",
                    "content": f"Articles JSON follows. Analyze and return the schema:\n\n{payload}",
                },
            ],
            temperature=0.2,
            max_completion_tokens=8000,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(_strip_fences(raw))
        log.info("Scout returned in %.1fs", time.time() - t0)
        return data
    except Exception as e:
        log.error("Scout call failed: %s\n%s", e, traceback.format_exc())
        return _empty_enrichment(articles)


def _empty_enrichment(articles: list[Article]) -> dict[str, Any]:
    return {
        "articles": [
            {
                "id": a.id,
                "entities": [],
                "geo_tags": [],
                "topics": [],
                "sentiment": {"MA": 0.0, "SA": 0.0, "AE": 0.0},
                "risk": {"MA": 0.0, "SA": 0.0, "AE": 0.0},
                "arc_to": [],
                "arc_strength": {"MA": 0.0, "SA": 0.0, "AE": 0.0},
                "hidden_links": [],
            }
            for a in articles
        ],
        "clusters": [],
        "recommendations": {"MA": [], "SA": [], "AE": []},
        "advantage_index": {"MA": 0.0, "SA": 0.0, "AE": 0.0},
        "risk_index": {"MA": 0.0, "SA": 0.0, "AE": 0.0},
    }


def merge_enrichment(articles: list[Article], enrichment: dict[str, Any]) -> list[Article]:
    by_id = {a.id: a for a in articles}
    for row in enrichment.get("articles", []):
        a = by_id.get(row.get("id", ""))
        if not a:
            continue
        a.entities = row.get("entities", []) or []
        a.geo_tags = row.get("geo_tags", []) or []
        a.topics = row.get("topics", []) or []
        a.sentiment = row.get("sentiment", {}) or {}
        a.risk = row.get("risk", {}) or {}
        a.arc_to = row.get("arc_to", []) or []
        a.arc_strength = row.get("arc_strength", {}) or {}
        a.hidden_links = row.get("hidden_links", []) or []
    return articles


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def write_atomic(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    log.info("wrote %s (%.1f KB)", path, path.stat().st_size / 1024)


def run() -> int:
    started = time.time()
    log.info("=== Sovereign Mind processor starting ===")

    articles = scrape_rss() + scrape_telegram()
    if not articles:
        log.error("no articles scraped — aborting")
        return 1

    articles = dedupe_and_window(articles, MAX_ARTICLES)
    enrichment = enrich_with_scout(articles)
    articles = merge_enrichment(articles, enrichment)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL,
        "article_count": len(articles),
        "articles": [asdict(a) for a in articles],
        "clusters": enrichment.get("clusters", []),
        "recommendations": enrichment.get("recommendations", {}),
        "advantage_index": enrichment.get("advantage_index", {}),
        "risk_index": enrichment.get("risk_index", {}),
    }
    write_atomic(OUT_PATH, payload)
    log.info("=== done in %.1fs ===", time.time() - started)
    return 0


if __name__ == "__main__":
    sys.exit(run())
