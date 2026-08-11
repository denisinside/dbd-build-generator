import json
import os

from dotenv import load_dotenv
from pymongo import MongoClient


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
    return replace_collection(db, "perks", perks_data["perks"])


def save_killers_to_mongo(db, killers_data):
    return replace_collection(db, "killers", killers_data["killers"])


def save_survivors_to_mongo(db, survivors_data):
    return replace_collection(db, "survivors", survivors_data["survivors"])


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
