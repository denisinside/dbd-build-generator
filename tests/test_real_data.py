"""Smoke tests against the real scraped cache, to catch data drift.

These use data/*.json directly (no MongoDB), so a wiki change that breaks name
resolution or leaves a required field empty fails here instead of in production.
"""

import json
import pathlib

import pytest
from conftest import indexed_db

from generate_build import (
    KILLER_ALIASES,
    find_killer_document,
    find_perk_document,
    killer_title,
)


DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"


def load(filename):
    path = DATA_DIR / filename

    if not path.exists():
        pytest.skip(f"{filename} is not present; run the parsers first")

    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def real_db():
    return indexed_db(
        load("perks.json")["perks"],
        load("killers.json")["killers"],
        load("survivors.json")["survivors"],
        [
            {
                "type_name": item_type["name"],
                "items": item_type["items"],
                "addons": item_type["addons"],
            }
            for item_type in load("items.json")["item_types"]
        ],
    )


def test_every_killer_title_resolves_to_itself(real_db):
    killers = load("killers.json")["killers"]
    mismatched = []

    for killer in killers:
        title = killer_title(killer)
        resolved = killer_title(find_killer_document(real_db, title))

        if resolved != title:
            mismatched.append((title, resolved))

    assert mismatched == []


def test_every_killer_real_name_resolves_to_its_title(real_db):
    killers = load("killers.json")["killers"]
    mismatched = []

    for killer in killers:
        title = killer_title(killer)
        resolved = killer_title(find_killer_document(real_db, killer["name"]))

        if resolved != title:
            mismatched.append((killer["name"], title, resolved))

    assert mismatched == []


def test_every_curated_nickname_resolves(real_db):
    unresolved = []

    for nickname, expected_title in KILLER_ALIASES.items():
        resolved = killer_title(find_killer_document(real_db, nickname))

        if resolved is None:
            unresolved.append((nickname, expected_title))

    assert unresolved == []


def test_every_perk_has_the_fields_the_ui_needs():
    incomplete = [
        perk["name"]
        for perk in load("perks.json")["perks"]
        if not perk.get("description") or not perk.get("icon_url")
    ]

    assert incomplete == []


def test_perk_names_are_unique(real_db):
    perks = load("perks.json")["perks"]
    names = [perk["name"] for perk in perks]

    assert len(names) == len(set(names))
    # Resolution must survive the diacritics the wiki uses.
    assert find_perk_document(real_db, names[0].lower())["name"] == names[0]
