from __future__ import annotations

import html
import json
import re

import httpx

YOUTUBE_PATTERN = re.compile(r"(youtube\.com|youtu\.be)", re.I)
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.I)
TITLE_PATTERN = re.compile(r"<title[^>]*>([^<]+)</title>", re.I)
META_TAG_PATTERN = re.compile(r"<meta[^>]+>", re.I)
TRAILING_URL_PUNCT = re.compile(r"[.,;:!?)'\]]+$")


def is_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_PATTERN.search(url))


def normalize_extracted_url(url: str) -> str:
    cleaned = url.strip()
    while True:
        trimmed = TRAILING_URL_PUNCT.sub("", cleaned)
        if trimmed == cleaned:
            return cleaned
        cleaned = trimmed


def extract_url(content: str) -> str | None:
    match = URL_PATTERN.search(content)
    if not match:
        return None
    return normalize_extracted_url(match.group(0))


def _meta_content(tag: str, *, name: str | None = None, prop: str | None = None) -> str | None:
    if name and not re.search(rf'name=["\']{re.escape(name)}["\']', tag, re.I):
        return None
    if prop and not re.search(rf'property=["\']{re.escape(prop)}["\']', tag, re.I):
        return None
    match = re.search(r'content=["\']([^"\']+)["\']', tag, re.I)
    return html.unescape(match.group(1).strip()) if match else None


def _extract_page_title(html_text: str) -> str | None:
    for tag in META_TAG_PATTERN.findall(html_text):
        for meta in (("og:title", None), (None, "twitter:title")):
            prop, name = meta
            title = _meta_content(tag, prop=prop, name=name)
            if title:
                return title

    title_match = TITLE_PATTERN.search(html_text)
    if title_match:
        return html.unescape(title_match.group(1).strip())

    return None


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
    normalized = normalize_extracted_url(url)
    if is_youtube_url(normalized):
        title = fetch_youtube_title(normalized)
        if title:
            return title

    try:
        response = httpx.get(
            normalized,
            follow_redirects=True,
            timeout=10.0,
            headers={"User-Agent": "Momentum/1.0 (+https://localhost)"},
        )
        response.raise_for_status()
        page_html = response.text[:50000]
    except httpx.HTTPError:
        return None

    return _extract_page_title(page_html)


def enrich_content_with_url_context(content: str) -> tuple[str, str | None, str | None]:
    """Return content enriched with fetched link title, plus url and title if found."""
    url = extract_url(content)
    if not url:
        return content, None, None

    title = fetch_url_context(url)
    if not title:
        return content, url, None

    stripped = content.strip()
    if stripped == url or stripped.startswith(url):
        enriched = f"{title}\n{url}"
    else:
        enriched = f"{content.strip()}\n\nLink: {title} ({url})"

    return enriched, url, title
