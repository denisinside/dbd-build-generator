"""The category argument the agent passes to search_dbd_rag."""

import pytest

from generate_build import ALLOWED_RAG_CATEGORIES, normalize_rag_category


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("perk", "perk"),
        # Plurals and other shapes the model tends to produce.
        ("perks", "perk"),
        ("addons", "addon"),
        ("Killer_Power", "killer_power"),
        ("power", "killer_power"),
        ("game-mechanics", "game_mechanics"),
        ("mechanics", "game_mechanics"),
        ("survivor_lore", "survivor_lore"),
    ],
)
def test_known_categories_are_canonicalised(raw, expected):
    canonical, group = normalize_rag_category(raw)

    assert canonical == expected
    assert canonical in ALLOWED_RAG_CATEGORIES
    assert group is None


@pytest.mark.parametrize(
    ("raw", "expected_group"),
    [
        ("items_addons", ["item", "addon"]),
        ("item_addon", ["item", "addon"]),
        # "builds" is not a category at all: search everything for the role.
        ("builds", None),
        ("loadout", None),
    ],
)
def test_category_groups_expand_or_clear_the_filter(raw, expected_group):
    canonical, group = normalize_rag_category(raw)

    assert canonical is None
    assert group == expected_group


def test_no_category_means_no_filter():
    assert normalize_rag_category(None) == (None, None)


@pytest.mark.parametrize("raw", ["nonsense", "killer", "meta"])
def test_unsupported_categories_are_rejected(raw):
    canonical, group = normalize_rag_category(raw)

    # False (not None) is the "reject and tell the model" signal.
    assert canonical is False
    assert group is None
