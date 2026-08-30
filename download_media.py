"""Mirror every wiki image referenced by data/*.json into frontend/public/media.

The parsers already do this for freshly scraped data. This script backfills an
existing JSON cache without re-scraping ~100 article pages, and is safe to
re-run: already downloaded files are skipped unless --force is passed.

    uv run python download_media.py
    uv run python download_media.py --force
"""

import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "parsers"))

from media_mirror import (  # noqa: E402
    mirror_items_media,
    mirror_killers_media,
    mirror_perks_media,
    mirror_survivors_media,
)
from wiki_utils import MEDIA_ROOT  # noqa: E402


DATA_DIR = os.path.join(PROJECT_ROOT, "data")

MIRRORS = [
    ("perks.json", mirror_perks_media),
    ("killers.json", mirror_killers_media),
    ("survivors.json", mirror_survivors_media),
    ("items.json", mirror_items_media),
]


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(data, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def main():
    force = "--force" in sys.argv

    print(f"Mirroring wiki media into: {MEDIA_ROOT}")
    print(f"Force re-download: {force}")
    print()

    total = 0

    for filename, mirror in MIRRORS:
        file_path = os.path.join(DATA_DIR, filename)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Missing cache file: {file_path}")

        print(f"=== {filename} ===")
        data = load_json(file_path)
        total += mirror(data, force=force)
        save_json(data, file_path)
        print(f"Updated local media paths in {filename}.")
        print()

    print(f"Done. {total} images available locally under /media.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
