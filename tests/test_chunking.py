"""Chunking and RAG metadata: the two things that decide retrieval quality."""

import pytest

from chroma_loader import (
    CHUNK_OVERLAP_CHARS,
    CHUNK_SIZE_CHARS,
    build_item_records,
    build_killer_records,
    build_mechanics_records,
    build_perk_records,
    chunk_text,
)


def paragraphs(count, sentence="Dead by Daylight mechanics sentence. "):
    return "\n\n".join(sentence * 8 for _ in range(count))


def test_short_text_is_a_single_chunk():
    assert chunk_text("Short mechanics note.") == ["Short mechanics note."]


def test_blank_text_produces_no_chunks():
    assert chunk_text("") == []
    assert chunk_text(None) == []


def test_long_text_is_split_into_bounded_chunks():
    chunks = chunk_text(paragraphs(20))

    assert len(chunks) > 1
    # Overlap is carried into the next chunk, so size is a target plus overlap.
    assert max(len(chunk) for chunk in chunks) <= CHUNK_SIZE_CHARS + CHUNK_OVERLAP_CHARS


def test_consecutive_chunks_overlap():
    chunks = chunk_text(paragraphs(20))
    first_tail_word = chunks[0].split()[-1]

    assert first_tail_word in chunks[1]


def test_a_single_oversized_paragraph_is_still_split():
    one_paragraph = "word " * 3000
    chunks = chunk_text(one_paragraph)

    assert len(chunks) > 1
    assert all(len(chunk) <= CHUNK_SIZE_CHARS for chunk in chunks)


def test_no_words_are_lost_when_splitting():
    text = paragraphs(12)
    chunks = chunk_text(text)
    joined = " ".join(chunks)

    for word in set(text.split()):
        assert word in joined


PERKS_DATA = {
    "perks": [
        {
            "name": "Sprint Burst",
            "role": "Survivor",
            "character": "Meg",
            "description": "Break into a sprint.",
        }
    ],
    "embedding_texts": {
        "overview_perk_slots": "A Character can equip up to 4 Perks.",
        "perk_classes_intro": "Perks are grouped into classes.",
        "perk_classes": [
            {
                "name": "General Perks",
                "available_for": "Both",
                "summary": "Available to everyone.",
                "detail_text": "Unlocked through the Bloodweb.",
            },
            {
                "name": "Hex Perks",
                "available_for": "Killers",
                "summary": "Tied to a Totem.",
                "detail_text": "Cleansing the Totem disables the Perk.",
            },
        ],
    },
}

KILLERS_DATA = {
    "global_intro": "Killers hunt Survivors.",
    "killers": [
        {
            "name": "Anna",
            "metadata": {"Title": "The Huntress", "Name": "Anna"},
            "sections": {"Overview": {"text": "Ranged Killer."}, "Lore": None, "Trivia": None},
            "power": {"name": "Hunting Hatchets", "description": "Throw hatchets."},
            "addons": [
                {"name": "Infantry Belt", "description": "More hatchets.", "rarity": "Rare"}
            ],
        }
    ],
}

ITEMS_DATA = {
    "item_types": [
        {
            "name": "Med-Kits",
            "overview": "Used for healing.",
            "items": [{"name": "First Aid Kit", "description": "Heal.", "rarity": "Uncommon"}],
            "addons": [
                {"name": "Gauze Roll", "description": "Faster healing.", "rarity": "Common"}
            ],
        }
    ]
}


def metadata_for(buffer, entity_name):
    return next(
        metadata
        for metadata in buffer.metadatas
        if metadata["entity_name"] == entity_name
    )


def test_killer_addons_carry_their_owner():
    """Without an owner, a search for add-ons returns all 44 Killers' add-ons."""
    metadata = metadata_for(build_killer_records(KILLERS_DATA), "Infantry Belt")

    assert metadata["category"] == "addon"
    assert metadata["owner"] == "The Huntress"


def test_killer_records_use_the_title_as_the_entity_name():
    metadata = metadata_for(build_killer_records(KILLERS_DATA), "The Huntress")

    assert metadata["category"] in {"killer_power", "killer_lore"}
    assert metadata["owner"] == "The Huntress"


def test_lore_chunks_keep_their_section():
    buffer = build_killer_records(KILLERS_DATA)
    lore = [
        metadata for metadata in buffer.metadatas if metadata["category"] == "killer_lore"
    ]

    assert [metadata["section"] for metadata in lore] == ["Overview"]


def test_item_addons_carry_their_item_category():
    metadata = metadata_for(build_item_records(ITEMS_DATA), "Gauze Roll")

    assert metadata["category"] == "addon"
    assert metadata["owner"] == "Med-Kits"


def test_perk_owner_is_the_character():
    metadata = metadata_for(build_perk_records(PERKS_DATA), "Sprint Burst")

    assert metadata["owner"] == "Meg"


def test_perk_mechanics_prose_is_indexed_for_both_roles():
    """embedding_texts used to be scraped and then never read."""
    buffer = build_mechanics_records(PERKS_DATA)
    roles = {
        metadata["entity_name"]: set()
        for metadata in buffer.metadatas
    }

    for metadata in buffer.metadatas:
        assert metadata["category"] == "game_mechanics"
        roles[metadata["entity_name"]].add(metadata["role"])

    assert roles["Perk Slots"] == {"Survivor", "Killer"}
    assert roles["General Perks"] == {"Survivor", "Killer"}
    # Hex Perks are Killer-only on the wiki, so they stay out of Survivor search.
    assert roles["Hex Perks"] == {"Killer"}


@pytest.mark.parametrize(
    "buffer_factory",
    [
        lambda: build_perk_records(PERKS_DATA),
        lambda: build_mechanics_records(PERKS_DATA),
        lambda: build_killer_records(KILLERS_DATA),
        lambda: build_item_records(ITEMS_DATA),
    ],
)
def test_record_ids_are_unique(buffer_factory):
    buffer = buffer_factory()

    assert len(buffer.ids) == len(set(buffer.ids))
    assert len(buffer.ids) == len(buffer.documents) == len(buffer.metadatas)
