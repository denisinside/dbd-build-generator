import json
import os
import re

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

from naming import canonical_perk_character, perk_character_index


load_dotenv()

COLLECTION_NAME = "dbd_rag_knowledge"
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small"

# Roughly 800 tokens per chunk with ~100 tokens of overlap. Wiki lore articles
# reach 18k characters; embedding one of those as a single vector produces mush
# and floods the agent context, so everything long is chunked.
CHUNK_SIZE_CHARS = 3200
CHUNK_OVERLAP_CHARS = 400

LORE_SECTIONS = ["Overview", "Lore", "Trivia"]

# Perk classes are documented per role on the wiki.
ROLES_BY_AVAILABILITY = {
    "Both": ["Survivor", "Killer"],
    "Survivors": ["Survivor"],
    "Killers": ["Killer"],
}


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def slugify(text):
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text


def overlap_tail(text, overlap=CHUNK_OVERLAP_CHARS):
    """Last `overlap` characters of a chunk, cut at a word boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return text

    tail = text[-overlap:]
    space = tail.find(" ")

    if space == -1:
        return tail

    return tail[space + 1 :]


def split_oversized(text, size, overlap):
    """Hard-split a single block that is longer than one chunk."""
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))

        if end < len(text):
            # Prefer breaking on whitespace so words stay intact.
            boundary = text.rfind(" ", start + size // 2, end)

            if boundary != -1:
                end = boundary

        chunks.append(text[start:end].strip())

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return [chunk for chunk in chunks if chunk]


def chunk_text(text, size=CHUNK_SIZE_CHARS, overlap=CHUNK_OVERLAP_CHARS):
    """Split text into overlapping chunks, preferring paragraph boundaries."""
    text = (text or "").strip()

    if not text:
        return []

    if len(text) <= size:
        return [text]

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > size:
            if current:
                chunks.append(current)
                current = ""

            chunks.extend(split_oversized(paragraph, size, overlap))
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph

        if len(candidate) <= size:
            current = candidate
            continue

        chunks.append(current)
        carry = overlap_tail(current, overlap)
        current = f"{carry}\n\n{paragraph}" if carry else paragraph

    if current:
        chunks.append(current)

    return chunks


class RecordBuffer:
    """Collects chunked documents plus their metadata and stable ids."""

    def __init__(self):
        self.documents = []
        self.metadatas = []
        self.ids = []

    def add(self, base_id, text, entity_name, category, role, owner, section=None):
        chunks = chunk_text(text)

        for index, chunk in enumerate(chunks):
            metadata = {
                "entity_name": entity_name,
                "category": category,
                "role": role,
                "owner": owner or entity_name,
                "chunk_index": index,
                "chunk_count": len(chunks),
            }

            if section:
                metadata["section"] = section

            self.documents.append(chunk)
            self.metadatas.append(metadata)
            self.ids.append(base_id if len(chunks) == 1 else f"{base_id}_c{index}")

        return len(chunks)

    def __len__(self):
        return len(self.documents)


def get_openrouter_embedding_function():
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY is missing. Add it to the .env file."
        )

    print(f"Using OpenRouter embeddings: {EMBEDDING_MODEL}")

    return OpenAIEmbeddingFunction(
        api_key=OPENROUTER_API_KEY,
        api_base=OPENROUTER_API_BASE,
        model_name=EMBEDDING_MODEL,
    )


def get_or_reset_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_function = get_openrouter_embedding_function()

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing ChromaDB collection '{COLLECTION_NAME}'.")
    except Exception:
        print(f"ChromaDB collection '{COLLECTION_NAME}' did not exist yet.")

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embedding_function,
    )
    print(
        f"Created ChromaDB collection '{COLLECTION_NAME}' "
        f"with OpenRouter embedding function."
    )
    return collection


def add_in_batches(collection, documents, metadatas, ids, batch_size=100):
    total = len(documents)
    start = 0

    while start < total:
        end = min(start + batch_size, total)
        collection.add(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )
        print(f"  Added ChromaDB batch {start + 1}-{end} / {total}")
        start = end


def build_perk_records(perks_data, character_index):
    buffer = RecordBuffer()

    for perk in perks_data["perks"]:
        name = perk["name"]
        role = perk["role"]
        # Must match what `resolve_owner` produces at query time, or the owner
        # filter on perk chunks silently matches nothing.
        character = canonical_perk_character(perk, character_index)
        description = perk["description"]

        buffer.add(
            base_id="perk_" + slugify(name),
            text=(
                f"Perk: {name} | Role: {role} | Character: {character} "
                f"| Description: {description}"
            ),
            entity_name=name,
            category="perk",
            role=role,
            owner=character,
        )

    return buffer


def build_mechanics_records(perks_data):
    """Perk mechanics prose scraped from the Perks article.

    These documents are role-agnostic, so each one is indexed once per role:
    every RAG query filters on role, and a single 'Both' row would never match.
    """
    buffer = RecordBuffer()
    embedding_texts = perks_data.get("embedding_texts") or {}

    general_blocks = [
        ("Perk Slots", embedding_texts.get("overview_perk_slots")),
        ("Perk Classes", embedding_texts.get("perk_classes_intro")),
    ]

    for entity_name, text in general_blocks:
        if not text:
            continue

        for role in ["Survivor", "Killer"]:
            buffer.add(
                base_id=f"mechanics_{slugify(entity_name)}_{slugify(role)}",
                text=f"Game mechanics: {entity_name}\n\n{text}",
                entity_name=entity_name,
                category="game_mechanics",
                role=role,
                owner="Perks",
            )

    for perk_class in embedding_texts.get("perk_classes", []):
        class_name = perk_class["name"]
        roles = ROLES_BY_AVAILABILITY.get(perk_class.get("available_for"), [])
        text_parts = [
            part
            for part in [perk_class.get("summary"), perk_class.get("detail_text")]
            if part
        ]

        if not roles or not text_parts:
            continue

        for role in roles:
            buffer.add(
                base_id=f"mechanics_class_{slugify(class_name)}_{slugify(role)}",
                text=f"Perk class: {class_name}\n\n" + "\n\n".join(text_parts),
                entity_name=class_name,
                category="game_mechanics",
                role=role,
                owner="Perk Classes",
            )

    return buffer


def build_killer_records(killers_data):
    buffer = RecordBuffer()
    global_intro = killers_data.get("global_intro")

    if global_intro:
        buffer.add(
            base_id="mechanics_killers_overview_killer",
            text=f"Game mechanics: Killers\n\n{global_intro}",
            entity_name="Killers",
            category="game_mechanics",
            role="Killer",
            owner="Killers",
        )

    for killer in killers_data["killers"]:
        metadata = killer.get("metadata") or {}
        # The Title ("The Huntress") is what players, the LLM and the build
        # schema all use, so it is the canonical owner key.
        title = metadata.get("Title") or killer["name"]
        power = killer["power"]

        buffer.add(
            base_id="killer_power_" + slugify(title),
            text=(
                f"Killer: {title} ({killer['name']}) | Power: {power['name']} "
                f"| Description: {power['description']}"
            ),
            entity_name=title,
            category="killer_power",
            role="Killer",
            owner=title,
        )

        for section_name in LORE_SECTIONS:
            section = killer["sections"].get(section_name)
            text = (section or {}).get("text")

            if not text:
                continue

            buffer.add(
                base_id=f"killer_lore_{slugify(title)}_{slugify(section_name)}",
                text=f"Killer: {title} ({killer['name']}) — {section_name}\n\n{text}",
                entity_name=title,
                category="killer_lore",
                role="Killer",
                owner=title,
                section=section_name,
            )

        for addon in killer["addons"]:
            addon_name = addon["name"]
            rarity = addon.get("rarity") or "Unknown"

            buffer.add(
                base_id=(
                    "killer_addon_"
                    + slugify(title)
                    + "_"
                    + slugify(addon_name)
                ),
                text=(
                    f"Add-on for {title}: {addon_name} | Rarity: {rarity} "
                    f"| Description: {addon['description']}"
                ),
                entity_name=addon_name,
                category="addon",
                role="Killer",
                owner=title,
            )

    return buffer


def build_survivor_records(survivors_data):
    buffer = RecordBuffer()
    global_intro = survivors_data.get("global_intro")

    if global_intro:
        buffer.add(
            base_id="mechanics_survivors_overview_survivor",
            text=f"Game mechanics: Survivors\n\n{global_intro}",
            entity_name="Survivors",
            category="game_mechanics",
            role="Survivor",
            owner="Survivors",
        )

    for survivor in survivors_data["survivors"]:
        survivor_name = survivor["name"]

        for section_name in LORE_SECTIONS:
            section = survivor["sections"].get(section_name)
            text = (section or {}).get("text")

            if not text:
                continue

            buffer.add(
                base_id=(
                    f"survivor_lore_{slugify(survivor_name)}_{slugify(section_name)}"
                ),
                text=f"Survivor: {survivor_name} — {section_name}\n\n{text}",
                entity_name=survivor_name,
                category="survivor_lore",
                role="Survivor",
                owner=survivor_name,
                section=section_name,
            )

    return buffer


def build_item_records(items_data):
    buffer = RecordBuffer()

    for item_type in items_data["item_types"]:
        category_name = item_type["name"]
        overview = item_type.get("overview")

        if overview:
            buffer.add(
                base_id="item_type_" + slugify(category_name),
                text=f"Item category: {category_name}\n\n{overview}",
                entity_name=category_name,
                category="item",
                role="Survivor",
                owner=category_name,
            )

        for item in item_type["items"]:
            item_name = item["name"]
            rarity = item.get("rarity") or "Unknown"

            buffer.add(
                base_id="item_" + slugify(item_name),
                text=(
                    f"Item: {item_name} | Category: {category_name} "
                    f"| Rarity: {rarity} | Key-Value Stats: {item['description']}"
                ),
                entity_name=item_name,
                category="item",
                role="Survivor",
                owner=category_name,
            )

        for addon in item_type["addons"]:
            addon_name = addon["name"]
            rarity = addon.get("rarity") or "Unknown"

            buffer.add(
                base_id=(
                    "item_addon_"
                    + slugify(category_name)
                    + "_"
                    + slugify(addon_name)
                ),
                text=(
                    f"Add-on for {category_name}: {addon_name} "
                    f"| Rarity: {rarity} | Effect: {addon['description']}"
                ),
                entity_name=addon_name,
                category="addon",
                role="Survivor",
                owner=category_name,
            )

    return buffer


def save_all_to_chroma(data_dir):
    print("=== ChromaDB ingestion ===")
    collection = get_or_reset_collection()

    perks_data = load_json(os.path.join(data_dir, "perks.json"))
    killers_data = load_json(os.path.join(data_dir, "killers.json"))
    survivors_data = load_json(os.path.join(data_dir, "survivors.json"))
    items_data = load_json(os.path.join(data_dir, "items.json"))

    character_index = perk_character_index(survivors_data, killers_data)

    sources = [
        ("perks", build_perk_records(perks_data, character_index)),
        ("mechanics", build_mechanics_records(perks_data)),
        ("killer_docs", build_killer_records(killers_data)),
        ("survivor_docs", build_survivor_records(survivors_data)),
        ("item_docs", build_item_records(items_data)),
    ]

    all_documents = []
    all_metadatas = []
    all_ids = []
    counts = {}

    for label, buffer in sources:
        counts[label] = len(buffer)
        all_documents.extend(buffer.documents)
        all_metadatas.extend(buffer.metadatas)
        all_ids.extend(buffer.ids)
        print(f"Prepared {len(buffer)} {label} chunks for ChromaDB.")

    duplicates = len(all_ids) - len(set(all_ids))

    if duplicates:
        raise ValueError(f"Found {duplicates} duplicate ChromaDB ids")

    longest = max((len(document) for document in all_documents), default=0)
    print(f"Adding {len(all_documents)} chunks into ChromaDB (longest {longest} chars)...")
    add_in_batches(collection, all_documents, all_metadatas, all_ids)

    counts["total"] = collection.count()
    print(f"ChromaDB collection now has {counts['total']} documents.")
    return counts
