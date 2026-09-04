"""canonicalize_and_validate_build: the guard between the LLM and the UI."""

import pytest
from conftest import choices, killer_build, survivor_build
from pydantic import ValidationError

from generate_build import canonicalize_and_validate_build, enrich_build_entity_details
from schemas import DbDBuildSchema


def validate(payload, role, db):
    return canonicalize_and_validate_build(DbDBuildSchema.model_validate(payload), role, db=db)


def test_valid_survivor_build_passes(db):
    build, errors = validate(survivor_build(), "Survivor", db)

    assert errors == []
    assert build.character_name == "Meg Thomas"
    assert [perk.name for perk in build.perks] == [
        "Sprint Burst",
        "Adrenaline",
        "Windows of Opportunity",
        "Déjà Vu",
    ]
    # The reason the model gave survives canonicalisation of the name.
    assert build.perks[0].reason == "Відрив на початку чейсу."


def test_valid_killer_build_passes(db):
    build, errors = validate(killer_build(), "Killer", db)

    assert errors == []
    # Killers are canonicalised to their Title, never to the real name.
    assert build.character_name == "The Huntress"
    assert all(kit.item_name is None for kit in build.item_kits)


def test_names_are_canonicalised_from_sloppy_casing(db):
    payload = survivor_build(
        character_name="meg thomas",
        perks=choices("sprint burst", "ADRENALINE", "windows of opportunity", "deja vu"),
        synergies=[
            {
                "entities": ["sprint burst", "windows of opportunity"],
                "explanation": "Синергія теж канонізується.",
            },
            {
                "entities": ["Emergency Med-Kit", "Gauze Roll"],
                "explanation": "Швидке лікування.",
            },
        ],
    )
    build, errors = validate(payload, "Survivor", db)

    assert errors == []
    assert build.character_name == "Meg Thomas"
    assert build.perks[0].name == "Sprint Burst"
    assert build.perks[3].name == "Déjà Vu"
    assert build.synergies[0].entities == ["Sprint Burst", "Windows of Opportunity"]


def test_killer_name_is_canonicalised_from_a_nickname(db):
    payload = killer_build(
        character_name="bubba",
        item_kits=[
            {
                "kit_title": "Базовий",
                "item_name": None,
                "addons": choices("Depth Gauge Rake", "Carburettor Tuning Guide"),
            },
            {
                "kit_title": "Мобільний",
                "item_name": None,
                "addons": choices("Grisly Chains", "Depth Gauge Rake"),
            },
        ],
        synergies=[
            {
                "entities": ["Depth Gauge Rake", "Carburettor Tuning Guide"],
                "explanation": "Довша пила і швидший замах.",
            },
            {
                "entities": ["Hex: Ruin", "Corrupt Intervention"],
                "explanation": "Уповільнення з двох боків.",
            },
        ],
    )
    build, errors = validate(payload, "Killer", db)

    assert errors == []
    assert build.character_name == "The Cannibal"


def test_perk_from_the_wrong_role_is_rejected(db):
    payload = survivor_build(
        perks=choices("Sprint Burst", "Adrenaline", "Windows of Opportunity", "Hex: Ruin")
    )
    _, errors = validate(payload, "Survivor", db)

    assert "perk has wrong role: Hex: Ruin" in errors


def test_invented_perk_is_rejected(db):
    payload = survivor_build(
        perks=choices("Sprint Burst", "Adrenaline", "Windows of Opportunity", "Ultra Sprint")
    )
    _, errors = validate(payload, "Survivor", db)

    assert "perk not found: Ultra Sprint" in errors


def test_addon_from_another_killer_is_rejected(db):
    payload = killer_build()
    payload["item_kits"][0]["addons"] = choices("Judith's Tombstone", "Infantry Belt")
    _, errors = validate(payload, "Killer", db)

    assert "addon Judith's Tombstone does not belong to selected Killer" in errors


def test_addon_from_another_item_is_rejected(db):
    payload = survivor_build()
    payload["item_kits"][0]["addons"] = choices("Wire Spool", "Gauze Roll")
    _, errors = validate(payload, "Survivor", db)

    assert "addon Wire Spool does not belong to Emergency Med-Kit" in errors


def test_same_addon_twice_in_one_kit_is_rejected(db):
    payload = survivor_build()
    payload["item_kits"][0]["addons"] = choices("Gauze Roll", "gauze roll")
    _, errors = validate(payload, "Survivor", db)

    assert "Each item kit must contain 2 different addons" in errors


def test_killer_kits_may_not_repeat_a_pair_in_reverse_order(db):
    payload = killer_build()
    payload["item_kits"][0]["addons"] = choices("Iridescent Head", "Infantry Belt")
    payload["item_kits"][1]["addons"] = choices("Infantry Belt", "Iridescent Head")
    _, errors = validate(payload, "Killer", db)

    assert "Killer item kits must use different addon pairs" in errors


def test_survivor_kits_may_not_repeat_the_same_item_and_pair(db):
    payload = survivor_build()
    payload["item_kits"][1] = {
        "kit_title": "Копія",
        "item_name": "Emergency Med-Kit",
        "addons": choices("Medical Gauze", "Gauze Roll"),
    }
    _, errors = validate(payload, "Survivor", db)

    assert "Survivor item kits must not repeat the same item and addon pair" in errors


def test_survivor_kits_with_the_same_pair_on_different_items_are_allowed(db):
    payload = survivor_build()
    payload["item_kits"][1] = {
        "kit_title": "Другий медкіт",
        "item_name": "First Aid Kit",
        "addons": choices("Gauze Roll", "Butterfly Tape"),
    }
    _, errors = validate(payload, "Survivor", db)

    assert errors == []


def test_role_mismatch_is_reported(db):
    _, errors = validate(survivor_build(), "Killer", db)

    assert "role must be Killer" in errors


def test_unknown_counter_killer_is_rejected(db):
    payload = survivor_build()
    payload["counter_killers"][0]["killer_name"] = "The Janitor"
    _, errors = validate(payload, "Survivor", db)

    assert "counter Killer not found: The Janitor" in errors


def test_counter_killers_are_canonicalised_to_titles(db):
    payload = survivor_build()
    payload["counter_killers"][0]["killer_name"] = "bubba"
    payload["counter_killers"][1]["killer_name"] = "Michael Myers"
    build, errors = validate(payload, "Survivor", db)

    assert errors == []
    assert [counter.killer_name for counter in build.counter_killers][:2] == [
        "The Cannibal",
        "The Shape",
    ]


def test_unknown_survivor_is_rejected(db):
    _, errors = validate(survivor_build(character_name="Nobody"), "Survivor", db)

    assert "Survivor not found: Nobody" in errors


def test_schema_rejects_a_survivor_build_without_counter_killers():
    with pytest.raises(ValidationError):
        DbDBuildSchema.model_validate(survivor_build(counter_killers=None))


def test_schema_rejects_a_killer_build_with_counter_killers():
    payload = killer_build(counter_killers=survivor_build()["counter_killers"])

    with pytest.raises(ValidationError):
        DbDBuildSchema.model_validate(payload)


def test_enrichment_prefers_local_media_paths(db):
    enriched = enrich_build_entity_details(survivor_build(), db=db)

    assert enriched["character_portrait_url"] == "https://wiki.example/meg.png"
    # Not mirrored locally yet: the remote URL is still the only source.
    assert enriched["character_portrait_path"] is None

    sprint_burst = enriched["perks"][0]
    assert sprint_burst["icon_path"] == "/media/perks/sprint-burst.png"
    assert enriched["perks"][1]["icon_path"] is None

    first_kit = enriched["item_kits"][0]
    assert first_kit["item_rarity"] == "Very Rare"
    assert [addon["rarity"] for addon in first_kit["addons"]] == ["Common", "Uncommon"]


# --- axes, synergies and the derived score ---------------------------------


def test_axes_must_be_the_four_for_the_role(db):
    payload = survivor_build(
        axes=[
            {"axis": "Chase", "score": 4, "reason": "ok"},
            {"axis": "Map Pressure", "score": 3, "reason": "ok"},
            {"axis": "Slowdown", "score": 3, "reason": "ok"},
            {"axis": "Anti-Loop", "score": 3, "reason": "ok"},
        ]
    )
    _, errors = validate(payload, "Survivor", db)

    assert any("a Survivor build must score exactly these axes" in e for e in errors)


def test_the_same_axis_twice_is_rejected(db):
    payload = survivor_build(
        axes=[
            {"axis": "Chase", "score": 4, "reason": "ok"},
            {"axis": "Chase", "score": 2, "reason": "ok"},
            {"axis": "Objective", "score": 3, "reason": "ok"},
            {"axis": "Team Utility", "score": 3, "reason": "ok"},
        ]
    )
    _, errors = validate(payload, "Survivor", db)

    assert any("once each" in e for e in errors)


def test_a_synergy_may_not_name_something_outside_the_build(db):
    """A combo about a perk that was never picked is worse than no combo."""
    payload = survivor_build(
        synergies=[
            {
                "entities": ["Sprint Burst", "Hex: Ruin"],
                "explanation": "Вигадана взаємодія.",
            },
            {
                "entities": ["Emergency Med-Kit", "Gauze Roll"],
                "explanation": "Ця справжня.",
            },
        ]
    )
    _, errors = validate(payload, "Survivor", db)

    assert "synergy mentions 'Hex: Ruin', which is not part of this build" in errors


def test_a_synergy_may_name_the_killer_power(db):
    """Add-ons modify the power, so the power has to count as part of the build."""
    build, errors = validate(killer_build(), "Killer", db)

    assert errors == []
    assert build.synergies[0].entities == ["Hunting Hatchets", "Iridescent Head"]


def test_a_synergy_may_name_the_character(db):
    """Rejecting it only cost a full retry; the character is part of the build."""
    payload = killer_build(
        synergies=[
            {
                "entities": ["The Huntress", "Iridescent Head"],
                "explanation": "Її сокири стають смертельними.",
            },
            {
                "entities": ["Hex: Ruin", "Corrupt Intervention"],
                "explanation": "Подвійне уповільнення.",
            },
        ]
    )
    build, errors = validate(payload, "Killer", db)

    assert errors == []
    assert build.synergies[0].entities == ["The Huntress", "Iridescent Head"]


def test_a_synergy_with_one_piece_repeated_is_rejected(db):
    payload = survivor_build(
        synergies=[
            {
                "entities": ["Sprint Burst", "sprint burst"],
                "explanation": "Сам із собою.",
            },
            {
                "entities": ["Emergency Med-Kit", "Gauze Roll"],
                "explanation": "Ця справжня.",
            },
        ]
    )
    _, errors = validate(payload, "Survivor", db)

    assert "a synergy must connect at least two different pieces" in errors


def test_the_headline_score_is_derived_from_the_axes(db):
    """Never asked of the model: it answers 7 or 8 whatever the build is."""
    from generate_build import derive_build_score

    enriched = enrich_build_entity_details(survivor_build(), db=db)

    # (4 + 2 + 3 + 2) / 4 = 2.75 -> 5.5 -> 6
    assert enriched["build_score"] == 6
    assert derive_build_score([{"score": 5}] * 4) == 10
    assert derive_build_score([{"score": 1}] * 4) == 2


# --- the new enrichment fields ---------------------------------------------


def test_a_killer_build_carries_the_power_its_addons_modify(db):
    enriched = enrich_build_entity_details(killer_build(), db=db)

    assert enriched["character_power"]["name"] == "Hunting Hatchets"
    assert enriched["character_power"]["description"] == "Throw hatchets."


def test_a_survivor_build_has_no_power_slot(db):
    assert enrich_build_entity_details(survivor_build(), db=db)["character_power"] is None


def test_a_very_long_power_description_is_trimmed_for_the_card(db):
    from generate_build import POWER_SUMMARY_CHARS, killer_power

    power = killer_power({"power": {"name": "Wall of Text", "description": "word " * 2000}})

    assert power["description"].endswith("...")
    assert len(power["description"]) <= POWER_SUMMARY_CHARS + 10


def test_a_long_description_is_cut_on_a_sentence_not_mid_mechanic():
    from generate_build import POWER_SUMMARY_CHARS, truncate_at_sentence

    sentence = "The Killer gains a 20% Haste status effect. "
    description = sentence * 30  # well past POWER_SUMMARY_CHARS

    result = truncate_at_sentence(description, POWER_SUMMARY_CHARS)

    assert result.endswith("...")
    # Cut right after a ". ", not mid-word/mid-sentence.
    assert result[:-4].endswith(".")


def test_enrichment_says_which_character_teaches_each_perk(db):
    """Without it a new player cannot tell whose Bloodweb to grind."""
    enriched = enrich_build_entity_details(survivor_build(), db=db)

    assert enriched["perks"][0]["character"] == "Meg"
    assert enriched["perks"][0]["reason"] == "Відрив на початку чейсу."


def test_enrichment_keeps_addon_and_item_reasons(db):
    enriched = enrich_build_entity_details(survivor_build(), db=db)
    kit = enriched["item_kits"][0]

    assert kit["item_reason"] == "Швидке самолікування після чейсу."
    assert kit["addons"][0]["reason"] == "Пришвидшує лікування."


def test_enriching_a_build_saved_before_reasons_existed_does_not_crash(db):
    """Old stored builds hold bare name strings where objects now go."""
    legacy = survivor_build(
        perks=["Sprint Burst", "Adrenaline", "Windows of Opportunity", "Déjà Vu"]
    )
    enriched = enrich_build_entity_details(legacy, db=db)

    assert enriched["perks"][0]["name"] == "Sprint Burst"
    assert enriched["perks"][0]["reason"] is None


# --- counter perks: the mirror of counter killers ---------------------------


def test_a_survivor_build_is_countered_by_killer_perks(db):
    build, errors = validate(survivor_build(), "Survivor", db)

    assert errors == []
    assert [counter.perk_name for counter in build.counter_perks] == [
        "Hex: Ruin",
        "Lethal Pursuer",
        "Corrupt Intervention",
    ]


def test_a_killer_build_is_countered_by_survivor_perks(db):
    """The gap this fills: a Killer build used to show nothing at all here."""
    build, errors = validate(killer_build(), "Killer", db)

    assert errors == []
    assert [counter.perk_name for counter in build.counter_perks] == [
        "Sprint Burst",
        "Windows of Opportunity",
        "Adrenaline",
    ]


def test_a_counter_perk_from_your_own_role_is_rejected(db):
    """Your own perks cannot counter you; that would just be a second loadout."""
    payload = survivor_build()
    payload["counter_perks"][0]["perk_name"] = "Sprint Burst"
    _, errors = validate(payload, "Survivor", db)

    assert "counter perk Sprint Burst must be a Killer perk" in errors


def test_an_invented_counter_perk_is_rejected(db):
    payload = killer_build()
    payload["counter_perks"][0]["perk_name"] = "Ultra Dodge"
    _, errors = validate(payload, "Killer", db)

    assert "counter perk not found: Ultra Dodge" in errors


def test_counter_perk_names_are_canonicalised(db):
    payload = killer_build()
    payload["counter_perks"][0]["perk_name"] = "sprint BURST"
    build, errors = validate(payload, "Killer", db)

    assert errors == []
    assert build.counter_perks[0].perk_name == "Sprint Burst"


def test_counter_perks_are_enriched_for_the_card(db):
    enriched = enrich_build_entity_details(killer_build(), db=db)
    counter = enriched["counter_perks"][0]

    assert counter["perk_name"] == "Sprint Burst"
    assert counter["icon_path"] == "/media/perks/sprint-burst.png"
    assert counter["description"] == "Break into a sprint."
    assert counter["character"] == "Meg"
    assert counter["explanation"]


def test_a_matchup_may_now_be_merely_inconvenient(db):
    """Two levels made every one of the five look like a nightmare."""
    payload = survivor_build()
    payload["counter_killers"][0]["difficulty_level"] = "Low Difficulty"
    build, errors = validate(payload, "Survivor", db)

    assert errors == []
    assert build.counter_killers[0].difficulty_level == "Low Difficulty"


def test_enriching_a_build_saved_before_counter_perks_existed(db):
    legacy = survivor_build()
    del legacy["counter_perks"]
    enriched = enrich_build_entity_details(legacy, db=db)

    assert enriched["counter_perks"] == []
