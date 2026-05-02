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
except ImportError:
    Groq = None

try:
    from langdetect import detect as _lang_detect, DetectorFactory
    DetectorFactory.seed = 0
except ImportError:
    _lang_detect = None

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
OUT_PATH = DATA_DIR / "data.json"

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_ARTICLES = 100
USER_AGENT = "SovereignMind/1.0"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s :: %(message)s")
log = logging.getLogger("sovereign-mind")

GLOBAL_FEEDS = [
    ("Reuters World",      "https://feeds.reuters.com/Reuters/worldNews"),
    ("Reuters Business",   "https://feeds.reuters.com/reuters/businessNews"),
    ("BBC World",          "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Al Jazeera English", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("AP World",           "https://feeds.apnews.com/rss/apf-worldnews"),
    ("Bloomberg Markets",  "https://feeds.bloomberg.com/markets/news.rss"),
]

REGIONAL_FEEDS = [
    ("Hespress EN",        "https://en.hespress.com/feed"),
    ("Morocco World News", "https://www.moroccoworldnews.com/feed"),
    ("Saudi Gazette",      "https://saudigazette.com.sa/rssFeed/91"),
    ("Arab News",          "https://www.arabnews.com/rss.xml"),
    ("The National",       "https://www.thenationalnews.com/rss"),
    ("Gulf News",          "https://gulfnews.com/rss"),
    ("Middle East Eye",    "https://www.middleeasteye.net/rss"),
    ("Asharq Al-Awsat",    "https://english.aawsat.com/feed"),
]

SCOUT_SYSTEM = (
    "You are SCOUT, a senior geopolitical analyst inside Sovereign Mind.\n\n"
    "Three sovereign personas:\n"
    "  MA = Morocco (Atlas Strategist): Green Hydrogen, Automotive/Aerospace, "
    "Phosphates, Africa-Atlantic Gateway, Tourism\n"
    "  SA = Saudi Arabia (Visionary Architect): Vision 2030/NEOM, Energy/PIF, "
    "Tourism, AI/Semiconductors, Regional Security\n"
    "  AE = UAE (Global Connector): AI Finance/G42/MGX, Logistics/Aviation, "
    "Crypto, Energy Diplomacy/ADNOC, Talent/Capital\n\n"
    "Analyze ALL articles together. Find hidden links across articles.\n\n"
    "Return ONLY valid JSON with this exact schema:\n"
    '{"articles":[{"id":"<echoed>","entities":[],"geo_tags":[],"topics":[],'
    '"sentiment":{"MA":0.0,"SA":0.0,"AE":0.0},'
    '"risk":{"MA":0.0,"SA":0.0,"AE":0.0},'
    '"arc_to":[],"arc_strength":{"MA":0.0,"SA":0.0,"AE":0.0},'
    '"hidden_links":[]}],'
    '"clusters":[{"id":"C1","label":"","narrative":"","member_ids":[],"personas":[]}],'
    '"recommendations":{"MA":[{"title":"","body":"","horizon":"7d","confidence":0.8}],'
    '"SA":[],"AE":[]},'
    '"advantage_index":{"MA":0.0,"SA":0.0,"AE":0.0},'
    '"risk_index":{"MA":0.0,"SA":0.0,"AE":0.0}}\n\n'
    "Sentiment/advantage: -1.0 to +1.0. Risk: 0.0 to 1.0. "
    "Use decisive non-zero values. Write recommendations in the sovereign voice."
)


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
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _detect_lang(text):
    if not text or _lang_detect is None:
        return "und"
    try:
        c = _lang_detect(text)
        if c.startswith("ar"): return "ar"
        if