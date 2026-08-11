import json
import os
import re

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv


load_dotenv()

COLLECTION_NAME = "dbd_rag_knowledge"
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small"


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = text.strip("_")
    return text


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


def build_perk_records(perks_data):
    documents = []
    metadatas = []
    ids = []

    for perk in perks_data["perks"]:
        name = perk["name"]
        role = perk["role"]
        character = perk["character"]
        description = perk["description"]

        documents.append(
            f"Perk: {name} | Role: {role} | Character: {character} | Description: {description}"
        )
        metadatas.append(
            {
                "entity_name": name,
                "category": "perk",
                "role": role,
            }
        )
        ids.append("perk_" + slugify(name))

    return documents, metadatas, ids


def build_killer_records(killers_data):
    documents = []
    metadatas = []
    ids = []

    for killer in killers_data["killers"]:
        killer_name = killer["name"]
        power = killer["power"]

        documents.append(
            f"Killer: {killer_name} | Power: {power['name']} | Description: {power['description']}"
        )
        metadatas.append(
            {
                "entity_name": killer_name,
                "category": "killer_power",
                "role": "Killer",
            }
        )
        ids.append("killer_power_" + slugify(killer_name))

        lore_parts = []

        for section_name in ["Overview", "Lore", "Trivia"]:
            section = killer["sections"].get(section_name)

            if section is None:
                continue

            text = section.get("text")

            if text:
                lore_parts.append(f"{section_name}:\n{text}")

        if lore_parts:
            documents.append(
                f"Killer: {killer_name}\n" + "\n\n".join(lore_parts)
            )
            metadatas.append(
                {
                    "entity_name": killer_name,
                    "category": "killer_lore",
                    "role": "Killer",
                }
            )
            ids.append("killer_lore_" + slugify(killer_name))

        for addon in killer["addons"]:
            addon_name = addon["name"]
            documents.append(
                f"Addon for {killer_name}: {addon_name} | Description: {addon['description']}"
            )
            metadatas.append(
                {
                    "entity_name": addon_name,
                    "category": "addon",
                    "role": "Killer",
                }
            )
            ids.append(
                "killer_addon_"
                + slugify(killer_name)
                + "_"
                + slugify(addon_name)
            )

    return documents, metadatas, ids


def build_survivor_records(survivors_data):
    documents = []
    metadatas = []
    ids = []

    for survivor in survivors_data["survivors"]:
        survivor_name = survivor["name"]
        lore_parts = []

        for section_name in ["Overview", "Lore", "Trivia"]:
            section = survivor["sections"].get(section_name)

            if section is None:
                continue

            text = section.get("text")

            if text:
                lore_parts.append(f"{section_name}:\n{text}")

        if not lore_parts:
            continue

        documents.append(
            f"Survivor: {survivor_name}\n" + "\n\n".join(lore_parts)
        )
        metadatas.append(
            {
                "entity_name": survivor_name,
                "category": "survivor_lore",
                "role": "Survivor",
            }
        )
        ids.append("survivor_lore_" + slugify(survivor_name))

    return documents, metadatas, ids


def build_item_records(items_data):
    documents = []
    metadatas = []
    ids = []

    for item_type in items_data["item_types"]:
        category = item_type["name"]

        for item in item_type["items"]:
            item_name = item["name"]
            documents.append(
                f"Item: {item_name} | Category: {category} | Key-Value Stats: {item['description']}"
            )
            metadatas.append(
                {
                    "entity_name": item_name,
                    "category": "item",
                    "role": "Survivor",
                }
            )
            ids.append("item_" + slugify(item_name))

        for addon in item_type["addons"]:
            addon_name = addon["name"]
            documents.append(
                f"Item Addon: {addon_name} | Category: {category} | Effect: {addon['description']}"
            )
            metadatas.append(
                {
                    "entity_name": addon_name,
                    "category": "addon",
                    "role": "Survivor",
                }
            )
            ids.append(
                "item_addon_" + slugify(category) + "_" + slugify(addon_name)
            )

    return documents, metadatas, ids


def save_all_to_chroma(data_dir):
    print("=== ChromaDB ingestion ===")
    collection = get_or_reset_collection()

    perks_data = load_json(os.path.join(data_dir, "perks.json"))
    killers_data = load_json(os.path.join(data_dir, "killers.json"))
    survivors_data = load_json(os.path.join(data_dir, "survivors.json"))
    items_data = load_json(os.path.join(data_dir, "items.json"))

    all_documents = []
    all_metadatas = []
    all_ids = []
    counts = {
        "perks": 0,
        "killer_docs": 0,
        "survivor_docs": 0,
        "item_docs": 0,
    }

    docs, metas, ids = build_perk_records(perks_data)
    counts["perks"] = len(docs)
    all_documents.extend(docs)
    all_metadatas.extend(metas)
    all_ids.extend(ids)
    print(f"Prepared {counts['perks']} perk documents for ChromaDB.")

    docs, metas, ids = build_killer_records(killers_data)
    counts["killer_docs"] = len(docs)
    all_documents.extend(docs)
    all_metadatas.extend(metas)
    all_ids.extend(ids)
    print(f"Prepared {counts['killer_docs']} killer documents for ChromaDB.")

    docs, metas, ids = build_survivor_records(survivors_data)
    counts["survivor_docs"] = len(docs)
    all_documents.extend(docs)
    all_metadatas.extend(metas)
    all_ids.extend(ids)
    print(f"Prepared {counts['survivor_docs']} survivor documents for ChromaDB.")

    docs, metas, ids = build_item_records(items_data)
    counts["item_docs"] = len(docs)
    all_documents.extend(docs)
    all_metadatas.extend(metas)
    all_ids.extend(ids)
    print(f"Prepared {counts['item_docs']} item/addon documents for ChromaDB.")

    print(f"Adding {len(all_documents)} documents into ChromaDB...")
    add_in_batches(collection, all_documents, all_metadatas, all_ids)

    counts["total"] = collection.count()
    print(f"ChromaDB collection now has {counts['total']} documents.")
    return counts
