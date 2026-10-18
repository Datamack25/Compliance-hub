"""Actualités conformité (flux RSS) avec repli hors-ligne."""
from __future__ import annotations

import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import pandas as pd
import requests
import streamlit as st

from core.data import load

UA = {"User-Agent": "Mozilla/5.0 (RegBridge Compliance Hub; +https://github.com)"}


def _parse_rss(xml: str, theme: str) -> list[dict]:
    import feedparser
    out = []
    for e in feedparser.parse(xml).entries:
        title = html.unescape(re.sub("<[^>]+>", "", e.get("title", "")))
        src = ""
        if " - " in title:
            title, src = title.rsplit(" - ", 1)
        try:
            pub = parsedate_to_datetime(e.get("published", "")).strftime("%Y-%m-%d")
        except Exception:
            pub = ""
        out.append({"title": title.strip(), "link": e.get("link", ""), "source": src or e.get("source", {}).get("title", ""),
                    "published": pub, "theme": theme})
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_news(max_per_feed: int = 8) -> tuple[pd.DataFrame, bool]:
    feeds = load("news_feeds.csv")
    items, online = [], False
    for f in feeds.itertuples():
        try:
            r = requests.get(f.url, headers=UA, timeout=6)
            if r.ok:
                items += _parse_rss(r.text, f.theme)[:max_per_feed]
                online = True
        except Exception:
            continue
    if not items:
        df = load("news_fallback.csv")
        return df, False
    df = pd.DataFrame(items).drop_duplicates("title")
    df = df.sort_values("published", ascending=False)
    return df, online


@st.cache_data(ttl=1800, show_spinner=False)
def search_news(query: str, lang: str = "fr", n: int = 25) -> tuple[list[dict], bool]:
    hl, gl, ceid = ("fr", "FR", "FR:fr") if lang == "fr" else ("en", "US", "US:en")
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}"
    try:
        r = requests.get(url, headers=UA, timeout=8)
        if r.ok:
            return _parse_rss(r.text, "Recherche")[:n], True
    except Exception:
        pass
    return [], False


def last_update() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")
