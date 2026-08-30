import os
import sys
import time
import traceback
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pymongo import DESCENDING


load_dotenv()

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))

from generate_build import (  # noqa: E402
    enrich_build_entity_details,
    get_mongo_db,
    run_generate_build,
)


DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

# Generating a build costs real money, and the endpoint is unauthenticated.
GENERATE_LIMIT_PER_HOUR = int(os.getenv("GENERATE_LIMIT_PER_HOUR", "5"))
RATE_LIMIT_WINDOW_SECONDS = 3600

_recent_generates = defaultdict(deque)


def builds_collection():
    # Resolved lazily so the API can start before MongoDB is reachable.
    return get_mongo_db()["generated_builds"]


def get_allowed_origins():
    """Browser origins allowed to call this API.

    Deployment blocker if hardcoded: a frontend on any real domain gets a CORS
    error, so this has to come from the environment.
    """
    raw = os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    origins = [origin.strip().rstrip("/") for origin in raw.split(",")]

    return [origin for origin in origins if origin]


def enforce_generate_limit(request: Request):
    """Per-client hourly cap on the one endpoint that costs money.

    ponytail: in-process counter, so the cap is per worker. Run uvicorn with
    --proxy-headers behind a proxy, or every client looks like the proxy.
    Move to Redis if you ever run more than one worker.
    """
    if GENERATE_LIMIT_PER_HOUR <= 0:
        return

    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _recent_generates[client]

    while hits and now - hits[0] > RATE_LIMIT_WINDOW_SECONDS:
        hits.popleft()

    if len(hits) >= GENERATE_LIMIT_PER_HOUR:
        retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - hits[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=(
                f"Too many builds. The limit is {GENERATE_LIMIT_PER_HOUR} per hour. "
                f"Try again in {retry_after // 60 + 1} min."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    hits.append(now)

    # Keep the map from growing forever on a long-lived process.
    for stale in [key for key, seen in _recent_generates.items() if not seen]:
        del _recent_generates[stale]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    builds_collection().create_index([("created_at", DESCENDING)])
    yield
    builds_collection().database.client.close()


app = FastAPI(title="DBD Build Generator API", lifespan=lifespan)

allowed_origins = get_allowed_origins()
print(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
    """True when a stored build predates the current enrichment fields.

    `icon_path` is part of the check so builds saved before the wiki images
    were mirrored locally pick up the local copies the next time they open.
    """
    if "character_portrait_path" not in document:
        return True

    for perk in document.get("perks", []):
        if "description" not in perk or "icon_path" not in perk:
            return True

    for kit in document.get("item_kits", []):
        if "item_description" not in kit or "item_rarity" not in kit:
            return True

        if "item_icon_path" not in kit:
            return True

        for addon in kit.get("addons", []):
            if "description" not in addon or "rarity" not in addon:
                return True

            if "icon_path" not in addon:
                return True

    return False


@app.post("/api/builds/generate", dependencies=[Depends(enforce_generate_limit)])
def generate_build(request: GenerateBuildRequest):
    try:
        build = run_generate_build(request.prompt)
    except ValueError as error:
        # The model could not produce a build that survives validation.
        traceback.print_exc()
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not build a valid loadout for this request. "
                "Try describing the role and playstyle more concretely."
            ),
        ) from error
    except Exception as error:
        # Upstream model or search failure: never leak a bare 500 after the
        # user has already waited a minute.
        traceback.print_exc()
        raise HTTPException(
            status_code=502,
            detail="The build service is unavailable right now. Please try again.",
        ) from error

    if "error" in build:
        error = build["error"]
        raise HTTPException(status_code=400, detail=error["message"])

    document = {
        **build,
        "prompt": request.prompt,
        "created_at": datetime.now(timezone.utc),
    }
    insert_result = builds_collection().insert_one(document)
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
    documents = builds_collection().find({}, projection).sort("created_at", DESCENDING)
    return [serialize_build(document) for document in documents]


@app.get("/api/builds/{build_id}")
def get_build(build_id: str):
    if not ObjectId.is_valid(build_id):
        raise HTTPException(status_code=404, detail="Build not found")

    document = builds_collection().find_one({"_id": ObjectId(build_id)})
    if document is None:
        raise HTTPException(status_code=404, detail="Build not found")

    if needs_entity_descriptions(document):
        document = enrich_build_entity_details(document)
        builds_collection().update_one(
            {"_id": document["_id"]},
            {
                "$set": {
                    "character_portrait_url": document["character_portrait_url"],
                    "character_portrait_path": document["character_portrait_path"],
                    "perks": document["perks"],
                    "item_kits": document["item_kits"],
                    "counter_killers": document.get("counter_killers"),
                }
            },
        )

    return serialize_build(document)
