# -*- coding: utf-8 -*-
import hashlib, json, logging, os, re, sys, time, traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import feedparser
from dateutil import parser as dtparser
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from groq import Groq
    log_groq = True
except ImportError:
    Groq = None
    log_groq = False

try:
    from langdetect import detect as _lang_detect, DetectorFactory
    DetectorFactory.seed = 0
except ImportError:
    _lang_detect = None

ROOT     = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_PATH = DATA_DIR / "data.json"

MODEL            = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_ARTICLES     = 100
ARTICLE_BODY_CHARS = 1200
USER_AGENT       = "SovereignMind/1.0"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s :: %(message)s")
log = logging.getLogger("sovereign-mind")

GLOBAL_FEEDS = [
    ("Reuters World",       "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters Business",    "https://feeds.reuters.com/reuters/businessNews"),
    ("BBC World",           "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera English",  "https://www.aljazeera.com/xml/rss/all.xml"),
    ("AP World",            "https://feeds.apnews.com/rss/apf-worldnews"),
    ("Bloomberg Markets",   "https://feeds.bloomberg.com/markets/news.rss"),
]

REGIONAL_FEEDS = [
    ("Hespress EN",         "https://en.hespress.com/feed"),
    ("Morocco World News",  "https://www.moroccoworldnews.com/feed"),
    ("Saudi Gazette",       "https://saudigazette.com.sa/rssFeed/91"),
    ("Arab News",           "https://www.arabnews.com/rss.xml"),
    ("The National",        "https://www.thenationalnews.com/rss"),
    ("Gulf News",           "https://gulfnews.com/rss"),
    ("Middle East Eye",     "https://www.middleeasteye.net/rss"),
    ("Asharq Al-Awsat",     "https://english.aawsat.com/feed"),
]


@dataclass
class Article:
    id: str
    title: str
    summary: str
    link: str
    source: str
    published: str
    region: str
    lang: str
    body: str = ""
    entities: list = field(default_factory=list)
    geo_tags: list = field(default_factory=list)
    topics: list = field(default_factory=list)
    sentiment: dict = field(default_factory=dict)
    risk: dict = field(default_factory=dict)
    hidden_links: list = field(default_factory=list)
    arc_to: list = field(default_factory=list)
    arc_strength: dict = field(default_factory=dict)


def _stable_id(*parts):
    return hashlib.sha1("||".join(parts).encode("utf-8", errors="ignore")).hexdigest()[:16]

def _clean(text):
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _detect_lang(text):
    if not text or _lang_detect is None: return "und"
    try:
        c = _lang_detect(text)
        return "ar" if c.startswith("ar") else "fr" if c.startswith("fr") else "en" if c.startswith("en") else c[:2]
    except Exception:
        return "und"

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
def _fetch_feed(url):
    return feedparser.parse(url, agent=USER_AGENT)

def scrape_rss():
    out = []
    for region_label, feeds in [("global", GLOBAL_FEEDS), ("mena", REGIONAL_FEEDS)]:
        for source, url in feeds:
            try:
                parsed = _fetch_feed(url)
            except Exception as e:
                log.warning("feed %s failed: %s", source, e)
                continue
            for entry in parsed.entries[:25]:
                title   = _clean(getattr(entry, "title", ""))
                link    = getattr(entry, "link", "")
                if not title or not link: continue
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
                out.append(Article(
                    id=_stable_id(link, title), title=title,
                    summary=summary[:600], link=link, source=source,
                    published=published, region=region_label,
                    lang=_detect_lang(f"{title}. {summary}"),
                ))
    log.info("scraped %d articles via RSS", len(out))
    return out

def dedupe_and_window(articles, limit=MAX_ARTICLES):
    seen, keep = set(), []
    articles.sort(key=lambda a: a.published, reverse=True)
    for a in articles:
        sig = re.sub(r"[^a-z0-9]", "", a.title.lower())[:80]
        if sig in seen or not sig: continue
        seen.add(sig); keep.append(a)
        if len(keep) >= limit: break
    log.info("kept %d unique articles", len(keep))
    return keep


SCOUT_SYSTEM = """You are SCOUT — a senior geopolitical analyst inside the Sovereign Mind intelligence console.

Three sovereign personas:
  MA = Morocco (Atlas Strategist) — Green Hydrogen, Automotive/Aerospace, Phosphates, Africa-Atlantic Gateway, Tourism
  SA = Saudi Arabia (Visionary Architect) — Vision 2030/