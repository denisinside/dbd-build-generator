"""Name normalisation shared by the ingest step and the runtime lookups.

Lookup keys are computed once at ingest and stored on the documents, so the
finders can hit an index instead of scanning a collection (killers.json alone
is ~1 MB, and it used to be pulled in full on every name lookup).
"""

import re
import unicodedata


# A phrase this short inside a longer sentence is more likely to be a
# coincidence than a reference ("bear trap" is not a request for The Huntress).
MIN_PHRASE_KEY_LENGTH = 5


def normalize_name(value):
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


def tokenized(value):
    """Normalized text with punctuation flattened to single spaces."""
    return " ".join(re.sub(r"[^0-9a-z]+", " ", normalize_name(value)).split())


def name_variants(value):
    """Every spelling of one name worth indexing."""
    key = normalize_name(value)

    if not key:
        return set()

    # "Huntress" should resolve just as well as "The Huntress".
    variants = {key, key[4:]} if key.startswith("the ") else {key}

    return {form for variant in variants for form in (variant, tokenized(variant)) if form}


def word_spans(value):
    """Contiguous word spans of `value`, long enough to be a real reference.

    Used to look up a name embedded in a longer string ("the shape (michael
    myers)") with an indexed query instead of a scan.
    """
    words = tokenized(value).split()

    return {
        span
        for start in range(len(words))
        for end in range(start + 1, len(words) + 1)
        for span in [" ".join(words[start:end])]
        if len(span) >= MIN_PHRASE_KEY_LENGTH
    }


def perk_search_keys(perk):
    return sorted(name_variants(perk.get("name")))


def survivor_search_keys(survivor):
    metadata = survivor.get("metadata") or {}
    keys = name_variants(survivor.get("name")) | name_variants(metadata.get("Name"))

    return sorted(keys)


def killer_search_keys(killer):
    """(search_keys, phrase_keys) for one Killer.

    `phrase_keys` is the subset safe to look for inside a longer string: real
    names and titles only. Short in-game nicknames stay exact-match-only.
    """
    metadata = killer.get("metadata") or {}
    keys = set()
    phrase_keys = set()

    for value in [
        killer.get("name"),
        metadata.get("Name"),
        metadata.get("Title") or killer.get("name"),
    ]:
        for variant in name_variants(value):
            keys.add(variant)

            if len(variant) >= MIN_PHRASE_KEY_LENGTH:
                phrase_keys.add(tokenized(variant))

    # In-game aliases are stored as quoted strings: '"Banshee" "Bob"'.
    for alias in re.findall(r'"([^"]+)"', metadata.get("Game Alias(es)") or ""):
        keys |= name_variants(alias)

    return sorted(keys), sorted(phrase_keys)
