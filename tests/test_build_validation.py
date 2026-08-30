"""canonicalize_and_validate_build: the guard between the LLM and the UI."""

import pytest
from conftest import killer_build, survivor_build
from pydantic import ValidationError

from generate_build import canonicalize_and_validate_build, enrich_build_entity_details
from schemas import DbDBuildSchema


def validate(payload, role, db):
    return canonicalize_and_validate_build(DbDBuildSchema.model_validate(payload), role, db=db)


def test_valid_survivor_build_passes(db):
    build, errors = validate(survivor_build(), "Survivor", db)

    assert errors == []
    assert build.character_name == "Meg Thomas"
    assert build.perks == [
        "Sprint Burst",
        "Adrenaline",
        "Windows of Opportunity",
        "Déjà Vu",
    ]


def test_valid_killer_build_passes(db):
    build, errors = validate(killer_build(), "Killer", db)

    assert errors == []
    # Killers are canonicalised to their Title, never to the real name.
    assert build.character_name == "The Huntress"
    assert all(kit.item_name is None for kit in build.item_kits)


def test_names_are_canonicalised_from_sloppy_casing(db):
    payload = survivor_build(
        character_name="meg thomas",
        perks=["sprint burst", "ADRENALINE", "windows of opportunity", "deja vu"],
    )
    build, errors = validate(payload, "Survivor", db)

    assert errors == []
    assert build.character_name == "Meg Thomas"
    assert build.perks[0] == "Sprint Burst"
    assert build.perks[3] == "Déjà Vu"


def test_killer_name_is_canonicalised_from_a_nickname(db):
    payload = killer_build(
        character_name="bubba",
        item_kits=[
            {
                "kit_title": "Базовий",
                "item_name": None,
                "addons": ["Depth Gauge Rake", "Carburettor Tuning Guide"],
            },
            {
                "kit_title": "Мобільний",
                "item_name": None,
                "addons": ["Grisly Chains", "Depth Gauge Rake"],
            },
        ],
    )
    build, errors = validate(payload, "Killer", db)

    assert errors == []
    assert build.character_name == "The Cannibal"


def test_perk_from_the_wrong_role_is_rejected(db):
    payload = survivor_build(
        perks=["Sprint Burst", "Adrenaline", "Windows of Opportunity", "Hex: Ruin"]
    )
    _, errors = validate(payload, "Survivor", db)

    assert "perk has wrong role: Hex: Ruin" in errors


def test_invented_perk_is_rejected(db):
    payload = survivor_build(
        perks=["Sprint Burst", "Adrenaline", "Windows of Opportunity", "Ultra Sprint"]
    )
    _, errors = validate(payload, "Survivor", db)

    assert "perk not found: Ultra Sprint" in errors


def test_addon_from_another_killer_is_rejected(db):
    payload = killer_build()
    payload["item_kits"][0]["addons"] = ["Judith's Tombstone", "Infantry Belt"]
    _, errors = validate(payload, "Killer", db)

    assert "addon Judith's Tombstone does not belong to selected Killer" in errors


def test_addon_from_another_item_is_rejected(db):
    payload = survivor_build()
    payload["item_kits"][0]["addons"] = ["Wire Spool", "Gauze Roll"]
    _, errors = validate(payload, "Survivor", db)

    assert "addon Wire Spool does not belong to Emergency Med-Kit" in errors


def test_same_addon_twice_in_one_kit_is_rejected(db):
    payload = survivor_build()
    payload["item_kits"][0]["addons"] = ["Gauze Roll", "gauze roll"]
    _, errors = validate(payload, "Survivor", db)

    assert "Each item kit must contain 2 different addons" in errors


def test_killer_kits_may_not_repeat_a_pair_in_reverse_order(db):
    payload = killer_build()
    payload["item_kits"][0]["addons"] = ["Iridescent Head", "Infantry Belt"]
    payload["item_kits"][1]["addons"] = ["Infantry Belt", "Iridescent Head"]
    _, errors = validate(payload, "Killer", db)

    assert "Killer item kits must use different addon pairs" in errors


def test_survivor_kits_may_not_repeat_the_same_item_and_pair(db):
    payload = survivor_build()
    payload["item_kits"][1] = {
        "kit_title": "Копія",
        "item_name": "Emergency Med-Kit",
        "addons": ["Medical Gauze", "Gauze Roll"],
    }
    _, errors = validate(payload, "Survivor", db)

    assert "Survivor item kits must not repeat the same item and addon pair" in errors


def test_survivor_kits_with_the_same_pair_on_different_items_are_allowed(db):
    payload = survivor_build()
    payload["item_kits"][1] = {
        "kit_title": "Другий медкіт",
        "item_name": "First Aid Kit",
        "addons": ["Gauze Roll", "Butterfly Tape"],
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
