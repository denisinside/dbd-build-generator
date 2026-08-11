import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import DESCENDING, MongoClient


load_dotenv()

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))

from generate_build import enrich_build_entity_details, run_generate_build  # noqa: E402


MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "dbd_generator"

mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000)
database = mongo_client[DB_NAME]
generated_builds = database["generated_builds"]

app = FastAPI(title="DBD Build Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateBuildRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)


def serialize_build(document):
    result = dict(document)
    result["id"] = str(result.pop("_id"))

    created_at = result.get("created_at")
    if isinstance(created_at, datetime):
        result["created_at"] = created_at.isoformat()

    return result


def needs_entity_descriptions(document):
    for perk in document.get("perks", []):
        if "description" not in perk:
            return True

    for kit in document.get("item_kits", []):
        if "item_description" not in kit or "item_rarity" not in kit:
            return True

        for addon in kit.get("addons", []):
            if "description" not in addon or "rarity" not in addon:
                return True

    return False


@app.on_event("startup")
def prepare_mongodb():
    mongo_client.admin.command("ping")
    generated_builds.create_index([("created_at", DESCENDING)])


@app.post("/api/builds/generate")
def generate_build(request: GenerateBuildRequest):
    build = run_generate_build(request.prompt)

    if "error" in build:
        error = build["error"]
        raise HTTPException(status_code=400, detail=error["message"])

    document = {
        **build,
        "prompt": request.prompt,
        "created_at": datetime.now(timezone.utc),
    }
    insert_result = generated_builds.insert_one(document)
    document["_id"] = insert_result.inserted_id

    return serialize_build(document)


@app.get("/api/builds")
def list_builds():
    projection = {
        "build_title": 1,
        "character_name": 1,
        "role": 1,
        "build_score": 1,
        "created_at": 1,
    }
    documents = generated_builds.find({}, projection).sort("created_at", DESCENDING)
    return [serialize_build(document) for document in documents]


@app.get("/api/builds/{build_id}")
def get_build(build_id: str):
    if not ObjectId.is_valid(build_id):
        raise HTTPException(status_code=404, detail="Build not found")

    document = generated_builds.find_one({"_id": ObjectId(build_id)})
    if document is None:
        raise HTTPException(status_code=404, detail="Build not found")

    if needs_entity_descriptions(document):
        document = enrich_build_entity_details(document)
        generated_builds.update_one(
            {"_id": document["_id"]},
            {
                "$set": {
                    "character_portrait_url": document["character_portrait_url"],
                    "perks": document["perks"],
                    "item_kits": document["item_kits"],
                    "counter_killers": document.get("counter_killers"),
                }
            },
        )

    return serialize_build(document)
