#!/usr/bin/env python3
"""Collect Fugazi Live Series show metadata from Dischord (HTML only).

This script never requests audio, sample, image, or download URLs. It reads the
public itinerary and its individual show pages and writes one JSON document.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup, Tag


BASE_URL = "https://dischord.com"
LISTING_URL = f"{BASE_URL}/fugazi_live_series"
USER_AGENT = "FugaziLiveSeriesMetadataResearch/1.0 (polite metadata-only crawler)"
SHOW_SLUG_RE = re.compile(r"-[0-9]{4,6}$")
FLS_ID_RE = re.compile(r"\bFLS\s*0*(\d+)\b", re.IGNORECASE)
DATE_FORMATS = ("%b %d, %Y", "%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d")


@dataclass
class Track:
    position: int
    title: str


@dataclass
class Show:
    show_id: str | None = None
    slug: str = ""
    event_date: str | None = None
    venue: str | None = None
    city: str | None = None
    subdivision: str | None = None
    country: str | None = None
    opening_acts: list[str] = field(default_factory=list)
    opening_acts_as_listed: str | None = None
    setlist: list[Track] = field(default_factory=list)
    source_url: str = ""
    listing_url: str = ""


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.replace("\xa0", " ").split())
    normalized = re.sub(r"\s+,", ",", normalized)
    return normalized or None


def normalize_date(value: str | None) -> str | None:
    value = clean(value)
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return value


def load_robots(session: requests.Session) -> RobotFileParser:
    robots_url = urljoin(BASE_URL, "/robots.txt")
    response = session.get(robots_url, timeout=30)
    response.raise_for_status()
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(response.text.splitlines())
    return parser


def get_html(session: requests.Session, url: str, delay: float, cache_dir: Path) -> str:
    parsed = urlparse(url)
    cache_key = re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.path.strip("/") or "index")
    if parsed.query:
        cache_key += "_" + re.sub(r"[^A-Za-z0-9._-]+", "_", parsed.query)
    cache_path = cache_dir / f"{cache_key}.html"
    if cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    time.sleep(max(0.0, delay))
    response = session.get(url, timeout=45)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        raise ValueError(f"Expected HTML at {url}; received {content_type or 'unknown content type'}")
    html = response.text
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")
    return html


def is_show_url(href: str) -> bool:
    path = urlparse(href).path.rstrip("/")
    prefix = "/fugazi_live_series/"
    if not path.startswith(prefix):
        return False
    slug = path[len(prefix):]
    return "/" not in slug and bool(SHOW_SLUG_RE.search(slug))


def listing_page_count(soup: BeautifulSoup) -> int:
    pages = [1]
    for anchor in soup.select("a[href]"):
        parsed = urlparse(anchor.get("href", ""))
        query = parse_qs(parsed.query)
        for value in query.get("page", []):
            if value.isdigit():
                pages.append(int(value))
    return max(pages)


def row_for_anchor(anchor: Tag) -> Tag | None:
    return anchor.find_parent("tr") or anchor.find_parent(class_=re.compile(r"tour.?date|show.?row", re.I))


def listing_fields(anchor: Tag) -> dict[str, Any]:
    row = row_for_anchor(anchor)
    if not row:
        return {}
    cells = row.find_all(["td", "th"], recursive=False)
    if len(cells) < 4:
        cells = row.find_all(["td", "th"])
    values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
    values = [value for value in values if value]
    result: dict[str, Any] = {}
    if len(values) >= 4:
        result["event_date"] = normalize_date(values[0])
        city_state = values[1]
        # The itinerary puts US/Canadian/Australian subdivisions beside cities.
        match = re.match(r"^(.*?)\s+([A-Z]{2})$", city_state)
        if match:
            result["city"], result["subdivision"] = match.group(1), match.group(2)
        else:
            result["city"] = city_state
        result["country"] = values[2]
        result["venue"] = values[3]
    return result


def get_show_links(soup: BeautifulSoup, page_url: str) -> dict[str, tuple[str, dict[str, Any]]]:
    shows: dict[str, tuple[str, dict[str, Any]]] = {}
    for anchor in soup.select("a[href]"):
        href = urljoin(page_url, anchor.get("href", ""))
        if not is_show_url(href):
            continue
        slug = urlparse(href).path.rstrip("/").rsplit("/", 1)[-1]
        fields = listing_fields(anchor)
        if slug not in shows:
            shows[slug] = (href, fields)
        elif fields:
            existing_url, existing_fields = shows[slug]
            shows[slug] = (existing_url, {**existing_fields, **fields})
    return shows


def detail_geo(soup: BeautifulSoup) -> dict[str, str]:
    values: dict[str, str] = {}
    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "")
        query = parse_qs(urlparse(href).query)
        for key in ("city", "state", "country"):
            candidate = query.get(f"filter[{key}]", [None])[0]
            if candidate:
                values[{"city": "city", "state": "subdivision", "country": "country"}[key]] = candidate
    return values


def detail_fields(soup: BeautifulSoup) -> dict[str, Any]:
    result: dict[str, Any] = detail_geo(soup)
    product_info = soup.select_one(".productInfo") or soup
    headings = product_info.find_all(["h1", "h2", "h3"])
    heading_text = " ".join(clean(h.get_text(" ", strip=True)) or "" for h in headings)
    id_match = FLS_ID_RE.search(heading_text)
    if id_match:
        result["show_id"] = f"FLS{int(id_match.group(1)):04d}"

    for dt in product_info.find_all("dt"):
        label = clean(dt.get_text(" ", strip=True))
        dd = dt.find_next_sibling("dd")
        if not label or not dd:
            continue
        value = clean(dd.get_text(" ", strip=True))
        if not value:
            continue
        key = label.rstrip(":").casefold()
        if key == "show date":
            result["event_date"] = normalize_date(value)
        elif key == "venue":
            result["venue"] = value
        elif key == "played with":
            result["opening_acts_as_listed"] = value
            result["opening_acts"] = [part.strip() for part in value.split(",") if part.strip()]

    # The page's ordered track table is metadata. Audio elements are never fetched.
    for table in product_info.find_all("table"):
        tracks: list[Track] = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            number = clean(cells[0].get_text(" ", strip=True)) or ""
            title = clean(cells[1].get_text(" ", strip=True))
            match = re.search(r"\d+", number)
            if match and title:
                tracks.append(Track(position=int(match.group()), title=title))
        if tracks:
            result["setlist"] = tracks
            break
    return result


def collect(args: argparse.Namespace) -> list[Show]:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "text/html"})
    cache_dir = Path(args.cache_dir)

    robots = load_robots(session)
    if not robots.can_fetch(USER_AGENT, LISTING_URL):
        raise RuntimeError(f"robots.txt disallows crawling {LISTING_URL} for this User-Agent")

    first_html = get_html(session, LISTING_URL, args.delay, cache_dir)
    first_soup = BeautifulSoup(first_html, "html.parser")
    page_count = listing_page_count(first_soup)
    listing_by_slug: dict[str, tuple[str, dict[str, Any]]] = get_show_links(first_soup, LISTING_URL)

    for page_number in range(2, page_count + 1):
        url = f"{LISTING_URL}?page={page_number}"
        if not robots.can_fetch(USER_AGENT, url):
            raise RuntimeError(f"robots.txt disallows crawling {url} for this User-Agent")
        soup = BeautifulSoup(get_html(session, url, args.delay, cache_dir), "html.parser")
        listing_by_slug.update(get_show_links(soup, url))
        print(f"Collected itinerary page {page_number}/{page_count}; {len(listing_by_slug)} shows found", file=sys.stderr)

    shows: list[Show] = []
    items = list(listing_by_slug.items())
    for index, (slug, (url, listed)) in enumerate(items, start=1):
        show = Show(slug=slug, source_url=url, listing_url=LISTING_URL)
        for key, value in listed.items():
            setattr(show, key, value)
        try:
            if not robots.can_fetch(USER_AGENT, url):
                print(f"Skipping disallowed show page: {url}", file=sys.stderr)
            else:
                soup = BeautifulSoup(get_html(session, url, args.delay, cache_dir), "html.parser")
                for key, value in detail_fields(soup).items():
                    setattr(show, key, value)
        except (requests.RequestException, ValueError) as exc:
            print(f"Could not read {url}: {exc}", file=sys.stderr)
        shows.append(show)
        if index % 25 == 0 or index == len(items):
            print(f"Collected show pages {index}/{len(items)}", file=sys.stderr)
    return shows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/fugazi_shows.json", help="Output JSON file")
    parser.add_argument("--cache-dir", default=".cache/dischord", help="Directory for cached HTML pages")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds to wait before each uncached page request")
    args = parser.parse_args()

    shows = collect(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(show) for show in shows]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tracks = sum(len(show.setlist) for show in shows)
    print(f"Wrote {len(shows)} shows and {tracks} setlist entries to {output}")


if __name__ == "__main__":
    main()
