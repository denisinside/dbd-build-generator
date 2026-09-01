"""Name resolution: normalize_name and the Killer/item/perk finders."""

import pytest

from generate_build import (
    find_item_type_document,
    find_killer_document,
    find_perk_document,
    find_survivor_document,
    killer_title,
    normalize_name,
    resolve_owner,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Déjà Vu", "deja vu"),
        ("The Onryō", "the onryo"),
        ("  SPRINT   burst ", "sprint burst"),
        ("Tarhos Kovács", "tarhos kovacs"),
        (None, ""),
        ("", ""),
    ],
)
def test_normalize_name_strips_diacritics_and_whitespace(raw, expected):
    assert normalize_name(raw) == expected


def test_find_perk_document_matches_across_diacritics(db):
    perk = find_perk_document(db, "deja vu")

    assert perk is not None
    assert perk["name"] == "Déjà Vu"


def test_find_perk_document_returns_none_for_unknown(db):
    assert find_perk_document(db, "Not A Perk") is None


def test_find_survivor_document_matches_metadata_name(db):
    assert find_survivor_document(db, "meg thomas")["name"] == "Meg Thomas"


@pytest.mark.parametrize(
    ("query", "expected_title"),
    [
        # Canonical title, exactly as the schema stores it.
        ("The Huntress", "The Huntress"),
        # Title without the article: how players usually write it.
        ("Huntress", "The Huntress"),
        # Real name from the infobox.
        ("Bubba Sawyer", "The Cannibal"),
        # Community nickname that the wiki does not list.
        ("bubba", "The Cannibal"),
        ("myers", "The Shape"),
        # In-game alias from the infobox.
        ("Leatherface", "The Cannibal"),
        # Diacritics dropped by the user.
        ("The Onryo", "The Onryō"),
        # Parenthetical form the LLM likes to produce.
        ("The Shape (Michael Myers)", "The Shape"),
        # Title that is a superstring of the stored name.
        ("The Unknown", "The Unknown"),
        # Typo, resolved by the fuzzy stage.
        ("The Huntres", "The Huntress"),
    ],
)
def test_find_killer_document_resolves_known_forms(db, query, expected_title):
    assert killer_title(find_killer_document(db, query)) == expected_title


@pytest.mark.parametrize(
    "query",
    [
        "",
        None,
        "The Onryu Ring",
        # Contains "anna", which used to resolve to The Huntress.
        "Susanna Hoffs",
        # Contains the in-game alias "Bear"; nicknames are exact-match only.
        "bear trap build",
        "Generator",
    ],
)
def test_find_killer_document_rejects_non_killers(db, query):
    """Previously "first substring wins" made these silently match a Killer."""
    assert find_killer_document(db, query) is None


def test_find_item_type_document_tolerates_singular(db):
    assert find_item_type_document(db, "Med-Kit")["type_name"] == "Med-Kits"
    assert find_item_type_document(db, "med-kits")["type_name"] == "Med-Kits"


@pytest.mark.parametrize(
    ("role", "owner", "expected"),
    [
        ("Killer", "huntress", "The Huntress"),
        ("Killer", "Bubba Sawyer", "The Cannibal"),
        ("Killer", "Not A Killer", None),
        ("Survivor", "Med-Kit", "Med-Kits"),
        ("Survivor", "Toolboxes", "Toolboxes"),
        ("Survivor", "Meg Thomas", "Meg Thomas"),
        ("Survivor", "Nobody At All", None),
        # Perk characters are owners too: "Meg" owns Sprint Burst.
        ("Survivor", "Meg", "Meg"),
        ("Killer", "Killers", "Killers"),
        ("Survivor", "Perks", "Perks"),
        ("Survivor", "", None),
    ],
)
def test_resolve_owner(db, role, owner, expected):
    assert resolve_owner(db, role, owner) == expected


# --- perk owners ------------------------------------------------------------


PERK_OWNER_DATA = (
    {"survivors": [{"name": "Meg Thomas"}, {"name": "Eleven"}]},
    {
        "killers": [
            {"name": "Anna", "metadata": {"Title": "The Huntress", "Name": "Anna"}},
            {"name": "Carmina Mora", "metadata": {"Title": "The Artist"}},
        ]
    },
)


@pytest.fixture(scope="module")
def owner_index():
    from naming import perk_character_index

    return perk_character_index(*PERK_OWNER_DATA)


@pytest.mark.parametrize(
    "role, wiki_name, expected",
    [
        ("Survivor", "Meg", "Meg Thomas"),
        ("Survivor", "Eleven", "Eleven"),
        ("Killer", "Artist", "The Artist"),
        ("Killer", "Anna", "The Huntress"),
        # Shared perks have no character page to canonicalise against.
        ("Survivor", "General", "General"),
        ("Killer", "General", "General"),
    ],
)
def test_perk_owners_are_canonicalised(owner_index, role, wiki_name, expected):
    from naming import canonical_perk_character

    perk = {"role": role, "character": wiki_name}

    assert canonical_perk_character(perk, owner_index) == expected


def test_a_survivor_first_name_is_never_read_as_a_killer(owner_index):
    """Indexed per role, so "Anna" means The Huntress only on a Killer perk."""
    from naming import canonical_perk_character

    assert canonical_perk_character({"role": "Survivor", "character": "Anna"}, owner_index) == (
        "Anna"
    )


def test_the_wiki_patch_banner_is_stripped_from_descriptions():
    """Editorial wiki chrome that was ending up in perk tooltips."""
    from wiki_utils import PATCH_BANNER

    raw = (
        "This description is based on the changes announced for or featured in "
        "the upcoming Patch 10.1.0 Starting to run triggers Sprint Burst."
    )

    assert PATCH_BANNER.sub("", raw) == "Starting to run triggers Sprint Burst."
    # Only as a prefix, and only the real banner.
    assert PATCH_BANNER.sub("", "A perk. This description is based on X") == (
        "A perk. This description is based on X"
    )
