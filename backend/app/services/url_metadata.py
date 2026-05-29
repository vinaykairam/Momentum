from __future__ import annotations

import json
import re

import httpx

YOUTUBE_PATTERN = re.compile(r"(youtube\.com|youtu\.be)", re.I)
URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)
TITLE_PATTERN = re.compile(r"<title[^>]*>([^<]+)</title>", re.I)
OG_TITLE_PATTERN = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)


def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_PATTERN.search(url))


def fetch_youtube_title(url: str) -> str | None:
    """Fetch video title via YouTube oEmbed (no API key required)."""
    try:
        response = httpx.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=10.0,
            headers={"User-Agent": "Momentum/1.0"},
        )
        response.raise_for_status()
        data = response.json()
        title = data.get("title")
        return str(title).strip() if title else None
    except (httpx.HTTPError, json.JSONDecodeError, TypeError):
        return None


def fetch_url_context(url: str) -> str | None:
    """Fetch page or video title for link captures."""
    if is_youtube_url(url):
        title = fetch_youtube_title(url)
        if title:
            return title

    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=10.0,
            headers={"User-Agent": "Momentum/1.0 (+https://localhost)"},
        )
        response.raise_for_status()
        html = response.text[:50000]
    except httpx.HTTPError:
        return None

    og_match = OG_TITLE_PATTERN.search(html)
    if og_match:
        return og_match.group(1).strip()

    title_match = TITLE_PATTERN.search(html)
    if title_match:
        return title_match.group(1).strip()

    return None
