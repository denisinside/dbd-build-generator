import json
import os

from dotenv import load_dotenv
from pymongo import MongoClient

from naming import killer_search_keys, perk_search_keys, survivor_search_keys


load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "dbd_generator"


def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_mongo_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
    client.admin.command("ping")
    return client[DB_NAME]


def replace_collection(db, collection_name, documents):
    collection = db[collection_name]
    deleted = collection.delete_many({})
    print(
        f"Cleared MongoDB collection '{collection_name}' "
        f"(removed {deleted.deleted_count} old documents)."
    )

    if not documents:
        print(f"No documents to insert into '{collection_name}'.")
        return 0

    result = collection.insert_many(documents)
    count = len(result.inserted_ids)
    print(f"Loaded {count} documents into MongoDB '{collection_name}'.")
    return count


def save_perks_to_mongo(db, perks_data):
    perks = perks_data["perks"]

    for perk in perks:
        perk["search_keys"] = perk_search_keys(perk)

    db["perks"].create_index("search_keys")
    return replace_collection(db, "perks", perks)


def save_killers_to_mongo(db, killers_data):
    killers = killers_data["killers"]

    for killer in killers:
        killer["search_keys"], killer["phrase_keys"] = killer_search_keys(killer)

    db["killers"].create_index("search_keys")
    db["killers"].create_index("phrase_keys")
    return replace_collection(db, "killers", killers)


def save_survivors_to_mongo(db, survivors_data):
    survivors = survivors_data["survivors"]

    for survivor in survivors:
        survivor["search_keys"] = survivor_search_keys(survivor)

    db["survivors"].create_index("search_keys")
    return replace_collection(db, "survivors", survivors)


def save_items_to_mongo(db, items_data):
    documents = []

    for item_type in items_data["item_types"]:
        documents.append(
            {
                "type_name": item_type["name"],
                "url": item_type["url"],
                "overview": item_type["overview"],
                "items": item_type["items"],
                "addons": item_type["addons"],
                "post_addons_text": item_type.get("post_addons_text"),
            }
        )

    return replace_collection(db, "items_addons", documents)


def save_all_to_mongo(data_dir):
    print("=== MongoDB ingestion ===")
    db = get_mongo_db()
    print(f"Connected to MongoDB: {MONGO_URI} / database '{DB_NAME}'")

    perks_data = load_json(os.path.join(data_dir, "perks.json"))
    killers_data = load_json(os.path.join(data_dir, "killers.json"))
    survivors_data = load_json(os.path.join(data_dir, "survivors.json"))
    items_data = load_json(os.path.join(data_dir, "items.json"))

    counts = {
        "perks": save_perks_to_mongo(db, perks_data),
        "killers": save_killers_to_mongo(db, killers_data),
        "survivors": save_survivors_to_mongo(db, survivors_data),
        "items_addons": save_items_to_mongo(db, items_data),
    }

    return counts
