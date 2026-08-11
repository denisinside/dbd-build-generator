import os
import sys

from chroma_loader import save_all_to_chroma
from mongo_loader import save_all_to_mongo


def main():
    project_root = os.path.dirname(__file__)
    data_dir = os.path.join(project_root, "data")

    required_files = [
        "perks.json",
        "killers.json",
        "survivors.json",
        "items.json",
    ]

    print("Starting DBD data ingestion...")
    print(f"Reading JSON cache from: {data_dir}")

    for filename in required_files:
        file_path = os.path.join(data_dir, filename)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Missing cache file: {file_path}")

        print(f"Found cache file: {filename}")

    print()
    mongo_counts = save_all_to_mongo(data_dir)
    print()
    chroma_counts = save_all_to_chroma(data_dir)
    print()

    print("=== FINAL SUMMARY ===")
    print(
        "Successfully ingested into MongoDB: "
        f"{mongo_counts['perks']} perks, "
        f"{mongo_counts['killers']} killers, "
        f"{mongo_counts['survivors']} survivors, "
        f"{mongo_counts['items_addons']} item types."
    )
    print(
        "Successfully ingested into ChromaDB: "
        f"{chroma_counts['perks']} perk docs, "
        f"{chroma_counts['killer_docs']} killer docs, "
        f"{chroma_counts['survivor_docs']} survivor docs, "
        f"{chroma_counts['item_docs']} item/addon docs "
        f"(total {chroma_counts['total']})."
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
