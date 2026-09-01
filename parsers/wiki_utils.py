import json
import os
import re
import time
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "DbDBuildGenerator/0.1 (educational project; "
    "contact: https://github.com/denisinside/dbd-build-generator)"
)

# Politeness: the wiki is a free community resource, so keep a floor between
# requests instead of hammering ~100 article pages and ~1400 images at once.
PAGE_DELAY_SECONDS = float(os.getenv("WIKI_PAGE_DELAY", "0.75"))
MEDIA_DELAY_SECONDS = float(os.getenv("WIKI_MEDIA_DELAY", "0.15"))

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
MEDIA_ROOT = os.path.join(PROJECT_ROOT, "frontend", "public", "media")
MEDIA_URL_PREFIX = "/media"
ALLOWED_MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

_session = None
_last_request_at = 0.0


RARITY_FROM_CLASS = {
    "common-item-element": "Common",
    "uncommon-item-element": "Uncommon",
    "rare-item-element": "Rare",
    "very-rare-item-element": "Very Rare",
    "visceral-item-element": "Visceral",
    "ultra-rare-item-element": "Ultra Rare",
    "event-item-element": "Event",
}


def get_session():
    """One pooled HTTP session for every wiki request."""
    global _session

    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": USER_AGENT})

    return _session


def polite_get(url, delay=PAGE_DELAY_SECONDS, timeout=30, stream=False):
    """GET a wiki URL, keeping at least `delay` seconds between requests."""
    global _last_request_at

    waited = time.monotonic() - _last_request_at

    if waited < delay:
        time.sleep(delay - waited)

    response = get_session().get(url, timeout=timeout, stream=stream)
    _last_request_at = time.monotonic()
    response.raise_for_status()

    return response


def get_page_soup(url):
    """Fetch a wiki article and parse it into soup."""
    response = polite_get(url)

    return BeautifulSoup(response.text, "html.parser")


def media_slug(text):
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower().strip())

    return slug.strip("-") or "unnamed"


def media_extension(url):
    path = urlparse(url).path
    _, extension = os.path.splitext(path)
    extension = extension.lower()

    if extension in ALLOWED_MEDIA_EXTENSIONS:
        return extension

    # Wiki thumbnails look like ".../96px-IconPerks_x.png/96px-....png?abc";
    # fall back to any allowed extension found anywhere in the path.
    for candidate in ALLOWED_MEDIA_EXTENSIONS:
        if candidate in path.lower():
            return candidate

    return ".png"


def thumbnail_url(url, width):
    """MediaWiki thumbnail URL for a full-size image, or None if not derivable.

    The wiki serves originals as /images/FILE.png and scaled copies as
    /images/thumb/FILE.png/<width>px-FILE.png. Portraits and add-on icons are
    linked at full size, which is 5-10x larger than anything the UI renders.
    """
    parsed = urlparse(url)
    parts = parsed.path.split("/")

    # ["", "images", "FILE.png"] — anything else is already a thumb or unknown.
    if len(parts) != 3 or parts[1] != "images" or not parts[2]:
        return None

    filename = parts[2]

    return parsed._replace(
        path=f"/images/thumb/{filename}/{width}px-{filename}"
    ).geturl()


def media_target_path(category, name, url):
    filename = media_slug(name) + media_extension(url)

    return os.path.join(MEDIA_ROOT, category, filename)


def download_media(url, category, name, force=False, width=None):
    """Mirror one wiki image into frontend/public/media.

    `width` requests a scaled thumbnail and falls back to the original if the
    wiki has no such size. Returns the public path ("/media/perks/x.png"), or
    None when every attempt failed. Failures are never fatal: the API still
    ships the remote URL as a fallback, so a missing mirror degrades instead of
    breaking the page.
    """
    if not url:
        return None

    target_path = media_target_path(category, name, url)
    public_path = "/".join(
        [MEDIA_URL_PREFIX, category, os.path.basename(target_path)]
    )

    if os.path.exists(target_path) and not force:
        return public_path

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    candidates = []

    if width:
        scaled = thumbnail_url(url, width)

        if scaled:
            candidates.append(scaled)

    candidates.append(url)
    last_error = None

    for candidate in candidates:
        try:
            response = polite_get(candidate, delay=MEDIA_DELAY_SECONDS, stream=True)

            with open(target_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=65536):
                    file.write(chunk)

            return public_path
        except Exception as error:
            last_error = error

            if os.path.exists(target_path):
                os.remove(target_path)

    print(f"  ! Could not download media for {name}: {last_error}")
    return None


# An editorial banner the wiki prepends while a PTB patch is unreleased. It is
# a note to wiki readers, not part of the entity, and it was ending up in perk
# tooltips and in the embedded text. Stripped here rather than in each parser
# because it shows up on perk rows and Killer pages alike.
PATCH_BANNER = re.compile(
    r"^This description is based on the changes announced for or featured in "
    r"the upcoming Patch [\d.]+\s*",
)


def clean_text(element):
    text = element.get_text(" ", strip=True)
    text = " ".join(text.split())
    text = re.sub(r"\s+([.,:;!?])", r"\1", text)
    text = PATCH_BANNER.sub("", text)

    return text


def parse_rarity(row):
    rarity_div = row.select_one(".game-element-bg-settings")

    if rarity_div is None:
        return None

    for class_name in rarity_div.get("class", []):
        if class_name in RARITY_FROM_CLASS:
            return RARITY_FROM_CLASS[class_name]

    return None


def save_json(data, filename):
    project_root = os.path.dirname(os.path.dirname(__file__))
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)

    file_path = os.path.join(data_dir, filename)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    print(f"Saved JSON cache: {file_path}")
    return file_path


def expand_table_grid(table):
    rows = table.select("tr")
    grid = []
    # Tracks unfinished rowspans: column_index -> [rows_left, value]
    active_rowspans = {}

    for row in rows:
        grid_row = []
        cells = row.select("th, td")
        cell_index = 0
        col = 0

        while True:
            if col in active_rowspans and active_rowspans[col][0] > 0:
                value = active_rowspans[col][1]
                grid_row.append(value)
                active_rowspans[col][0] -= 1

                if active_rowspans[col][0] == 0:
                    del active_rowspans[col]

                col += 1
                continue

            if cell_index >= len(cells):
                break

            cell = cells[cell_index]
            cell_index += 1

            value = clean_text(cell)
            rowspan = int(cell.get("rowspan") or 1)
            colspan = int(cell.get("colspan") or 1)

            for offset in range(colspan):
                current_col = col + offset
                grid_row.append(value)

                if rowspan > 1:
                    active_rowspans[current_col] = [rowspan - 1, value]

            col += colspan

        while col in active_rowspans and active_rowspans[col][0] > 0:
            value = active_rowspans[col][1]
            grid_row.append(value)
            active_rowspans[col][0] -= 1

            if active_rowspans[col][0] == 0:
                del active_rowspans[col]

            col += 1

        grid.append(grid_row)

    return grid


def format_table_as_key_value(table):
    grid = expand_table_grid(table)

    if not grid:
        return ""

    headers = grid[0]

    if not headers:
        return clean_text(table)

    if len(grid) == 1:
        return clean_text(table)

    formatted_rows = []

    for row_values in grid[1:]:
        pairs = []

        for index, value in enumerate(row_values):
            if index >= len(headers):
                break

            header = headers[index]

            if not header or not value:
                continue

            pairs.append(f"{header}: {value}")

        if pairs:
            formatted_rows.append(" | ".join(pairs))

    return "\n".join(formatted_rows)


def embedding_element_text(element):
    if element.name == "table":
        return format_table_as_key_value(element)

    return clean_text(element)
