import asyncio
import json
import os
import queue
import re
import sys
import threading
import time
import traceback
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pymongo import DESCENDING
from starlette.middleware.sessions import SessionMiddleware


load_dotenv()

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root / "src"))

import auth  # noqa: E402
from generate_build import (  # noqa: E402
    enrich_build_entity_details,
    get_mongo_db,
    run_generate_build,
)


DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"

# Generating a build costs real money. `require_account` (below) gates the
# endpoint behind an account wherever signing in is possible; this hourly cap
# is what still applies per account, or per IP when sign-in is unavailable.
GENERATE_LIMIT_PER_HOUR = int(os.getenv("GENERATE_LIMIT_PER_HOUR", "5"))
RATE_LIMIT_WINDOW_SECONDS = 3600

# One generation holds a worker thread for minutes. Without a cap, enough of
# them starve the thread pool and even GET /api/builds stops answering.
GENERATE_CONCURRENCY = int(os.getenv("GENERATE_CONCURRENCY", "3"))

FEED_DEFAULT_LIMIT = 30
FEED_MAX_LIMIT = 100

# Anonymous owner token minted by the browser. Not a credential: it only
# decides which builds a client calls "mine" until real accounts exist.
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

# A build outlives the request that asked for it, so its progress and result
# are kept under a job id the client can come back to. Without this, a phone
# that locks mid-generation loses a build that was already paid for.
#
# ponytail: in-process dict, so an API restart forgets running jobs and a
# second uvicorn worker would not see them. Redis if either changes.
JOB_RETENTION_SECONDS = 1800

_recent_generates = defaultdict(deque)
_generate_slots = threading.Semaphore(GENERATE_CONCURRENCY)
_jobs = {}
_jobs_lock = threading.Lock()


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


def clean_session_id(raw):
    """The caller's session token, or None when it is missing or malformed."""
    if isinstance(raw, str) and SESSION_ID_PATTERN.match(raw):
        return raw

    return None


def rate_limit_client(request, user):
    """The bucket key `enforce_generate_limit` counts a caller under.

    Shared with `refund_generate_hit` so a refund always targets the same
    bucket the charge was recorded against.
    """
    if user is not None:
        return f"user:{user['_id']}"

    return f"ip:{request.client.host if request.client else 'unknown'}"


def enforce_generate_limit(request: Request, user=Depends(auth.optional_user)):
    """Hourly cap on the one endpoint that costs money.

    Signed-in callers are counted per account, which is the whole reason the
    cap is worth having: an IP bucket punishes everyone behind one CGNAT
    address and is sidestepped by any VPN. `generate_limit_per_hour` on a user
    document raises the ceiling for a single account, for streamers.

    ponytail: in-process counter, so the cap is per worker. Run uvicorn with
    --proxy-headers behind a proxy, or every anonymous client looks like the
    proxy. Move to Redis if you ever run more than one worker.
    """
    if user is not None:
        limit = user.get("generate_limit_per_hour") or GENERATE_LIMIT_PER_HOUR
    else:
        limit = GENERATE_LIMIT_PER_HOUR

    client = rate_limit_client(request, user)

    if limit <= 0:
        return

    now = time.monotonic()
    hits = _recent_generates[client]

    while hits and now - hits[0] > RATE_LIMIT_WINDOW_SECONDS:
        hits.popleft()

    if len(hits) >= limit:
        retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - hits[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=(
                f"Too many builds. The limit is {limit} per hour. "
                f"Try again in {retry_after // 60 + 1} min."
            ),
            headers={"Retry-After": str(retry_after)},
        )

    hits.append(now)

    # Keep the map from growing forever on a long-lived process.
    for stale in [key for key, seen in _recent_generates.items() if not seen]:
        del _recent_generates[stale]


def refund_generate_hit(client):
    """Undo the quota charge for a build that failed on our side, not the caller's.

    ponytail: pops the bucket's most recent hit, so a second request from the
    same client racing in between could refund the wrong slot. Harmless at
    this scale (a handful of requests per hour per client); a per-request
    token would be needed to make it exact.
    """
    hits = _recent_generates.get(client)

    if hits:
        hits.pop()


def require_account(user=Depends(auth.optional_user)):
    """Generating spends real money, so it happens behind an account.

    Enforced only where signing in is possible at all — see
    `auth.sign_in_available`. Hiding the button in the UI is not enough: the
    endpoint is a plain HTTP call that anyone can make directly.
    """
    if auth.sign_in_available() and user is None:
        raise HTTPException(status_code=401, detail="Sign in to generate a build.")

    return user


@contextmanager
def generate_slot():
    """One of the limited generation slots, or a 503 that says so out loud."""
    if not _generate_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="The generator is busy right now. Try again in a moment.",
            headers={"Retry-After": "30"},
        )

    try:
        yield
    finally:
        _generate_slots.release()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    builds_collection().create_index([("created_at", DESCENDING)])
    # The "my builds" panel filters by owner on every page load, and an
    # anonymous browser and a signed-in account are two different owners.
    builds_collection().create_index([("session_id", 1), ("created_at", DESCENDING)])
    builds_collection().create_index([("user_id", 1), ("created_at", DESCENDING)])

    if auth.AUTH_SECRET:
        auth.ensure_indexes()

    yield
    builds_collection().database.client.close()


app = FastAPI(title="DBD Build Generator API", lifespan=lifespan)

allowed_origins = get_allowed_origins()
print(f"CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    # Sessions are Bearer tokens, not cookies, so no ambient credentials ever
    # ride along with a cross-origin request.
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if auth.AUTH_SECRET:
    # Only holds the OAuth `state` for the seconds between redirecting out to
    # a provider and coming back. The callback is a top-level navigation, so
    # "lax" is sent even when the provider is a different site.
    app.add_middleware(
        SessionMiddleware,
        secret_key=auth.AUTH_SECRET,
        session_cookie="dbd_oauth",
        max_age=600,
        same_site="lax",
        https_only=auth.FRONTEND_URL.startswith("https"),
    )
    app.include_router(auth.router)
    print(f"Sign-in providers: {sorted(auth.PROVIDERS) or 'none configured'}")
else:
    print("AUTH_SECRET is not set: sign-in is disabled, builds stay anonymous.")

if auth.sign_in_available():
    print("Generating a build requires an account.")
else:
    print(
        "Sign-in is unavailable, so generation stays open to anonymous callers. "
        "Set AUTH_SECRET and at least one provider's credentials to require an account."
    )


class GenerateBuildRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=1000)


def serialize_build(document):
    result = dict(document)
    result["id"] = str(result.pop("_id"))
    # Owner identifiers are not public data: the feed is shared, they are not.
    # `author_name` is the denormalised, publishable half of `user_id`.
    result.pop("session_id", None)
    result.pop("user_id", None)

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

    # The Killer power slot and a perk's source character are pure enrichment,
    # so builds saved before those existed can still pick them up.
    if document.get("role") == "Killer" and "character_power" not in document:
        return True

    for perk in document.get("perks", []):
        if "description" not in perk or "icon_path" not in perk:
            return True

        if "character" not in perk:
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


def create_build(prompt, session_id=None, user=None, on_step=None, rate_limit_client=None):
    """Run the pipeline, store the build, return it ready for the client.

    Raises HTTPException so both the plain and the streaming endpoint report
    the same failures the same way.
    """
    try:
        build = run_generate_build(prompt, on_step=on_step)
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
        # user has already waited a minute. This is our failure, not the
        # caller's, so give the quota hit back rather than making them lose an
        # attempt to a service outage.
        traceback.print_exc()
        if rate_limit_client:
            refund_generate_hit(rate_limit_client)
        raise HTTPException(
            status_code=502,
            detail="The build service is unavailable right now. Please try again.",
        ) from error

    if "error" in build:
        raise HTTPException(status_code=400, detail=build["error"]["message"])

    document = {
        **build,
        "prompt": prompt,
        "session_id": session_id,
        "user_id": user["_id"] if user else None,
        # Denormalised so the shared feed can credit an author without a join
        # per row. A renamed account keeps its old name on old builds, which
        # is the right trade for a feed.
        "author_name": user.get("display_name") if user else None,
        "author_avatar_url": user.get("avatar_url") if user else None,
        "created_at": datetime.now(timezone.utc),
    }
    insert_result = builds_collection().insert_one(document)
    document["_id"] = insert_result.inserted_id

    return serialize_build(document)


@app.get("/health")
def health():
    """Liveness plus a real MongoDB round-trip, for compose and any proxy."""
    try:
        get_mongo_db().client.admin.command("ping")
    except Exception as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error

    return {"status": "ok"}


@app.post("/api/builds/generate", dependencies=[Depends(enforce_generate_limit)])
def generate_build(
    request: GenerateBuildRequest,
    http_request: Request = None,
    x_session_id: Optional[str] = Header(default=None),
    user=Depends(require_account),
):
    with generate_slot():
        return create_build(
            request.prompt,
            clean_session_id(x_session_id),
            user,
            rate_limit_client=(
                rate_limit_client(http_request, user) if http_request else None
            ),
        )


def sse(event, payload):
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def start_build_worker(prompt, session_id, user, release_slot, rate_limit_client=None):
    """Run one build on its own thread, reporting progress two ways.

    The queue feeds the SSE stream of whoever is watching right now; the job
    record keeps the same events for whoever comes back later. The build
    deliberately outlives a disconnected client - it is already paid for by
    the time the first event goes out - and the job id is what makes the
    result reachable again after a phone locks or a browser is closed.
    """
    events = queue.Queue()
    job_id = uuid.uuid4().hex
    job = {"status": "running", "steps": [], "build": None, "error": None}

    with _jobs_lock:
        forget_stale_jobs()
        _jobs[job_id] = job

    def publish(event, payload):
        with _jobs_lock:
            if event == "step":
                job["steps"].append(payload)
            elif event == "build":
                job["status"] = "done"
                job["build"] = payload
            else:
                job["status"] = "error"
                job["error"] = payload

            job["finished_at"] = time.monotonic()

        events.put((event, payload))

    def worker():
        try:
            result = create_build(
                prompt,
                session_id,
                user,
                on_step=lambda stage, detail: publish(
                    "step", {"stage": stage, "detail": detail}
                ),
                rate_limit_client=rate_limit_client,
            )
            publish("build", result)
        except HTTPException as failure:
            publish("error", {"status": failure.status_code, "detail": failure.detail})
        except Exception:
            traceback.print_exc()
            publish(
                "error", {"status": 500, "detail": "The build service failed unexpectedly."}
            )
        finally:
            # Released before the sentinel, so a client that retries the
            # instant its stream ends never races the release into a 503. It
            # is still tied to the worker, not the stream, so hanging up
            # cannot free the slot while the build is still running.
            release_slot()
            events.put(None)

    threading.Thread(target=worker, daemon=True).start()

    return job_id, events


def forget_stale_jobs():
    """Drop jobs nobody is coming back for. The caller holds `_jobs_lock`.

    A job is only stale once it has finished: a running build has no deadline
    and must never be dropped from under the client waiting for it.
    """
    cutoff = time.monotonic() - JOB_RETENTION_SECONDS
    stale = [key for key, job in _jobs.items() if job.get("finished_at", cutoff + 1) < cutoff]

    for job_id in stale:
        del _jobs[job_id]


async def drain_events(job_id, events):
    # First frame, so a client that is about to lose its connection has the
    # job id stored before that happens.
    yield sse("job", {"job_id": job_id})

    while True:
        item = await asyncio.to_thread(events.get)

        if item is None:
            return

        yield sse(*item)


@app.post("/api/builds/stream", dependencies=[Depends(enforce_generate_limit)])
def stream_build(
    request: GenerateBuildRequest,
    http_request: Request,
    x_session_id: Optional[str] = Header(default=None),
    user=Depends(require_account),
):
    # Acquired here rather than inside the generator so a busy generator is a
    # plain 503 instead of an error delivered mid-stream.
    if not _generate_slots.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="The generator is busy right now. Try again in a moment.",
            headers={"Retry-After": "30"},
        )

    # The thread starts here, so the slot is released even if the client never
    # reads a single byte of the stream.
    job_id, events = start_build_worker(
        request.prompt,
        clean_session_id(x_session_id),
        user,
        _generate_slots.release,
        rate_limit_client=rate_limit_client(http_request, user),
    )

    return StreamingResponse(
        drain_events(job_id, events),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/builds/jobs/{job_id}")
def get_build_job(job_id: str):
    """Progress and result of a generation whose stream is gone.

    A phone that locks or a tab that is closed kills the SSE connection, not
    the build. Polling this is how the client picks the same build back up,
    instead of the user losing a minute of generation and one of their quota.

    No auth: the id is an unguessable token handed only to the caller that
    started the job, and the build it returns lands in the shared feed anyway.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)

        if job is None:
            raise HTTPException(
                status_code=404, detail="This generation is no longer being tracked."
            )

        return {
            "status": job["status"],
            "steps": list(job["steps"]),
            "build": job["build"],
            "error": job["error"],
        }


@app.get("/api/builds")
def list_builds(
    mine: bool = Query(default=False),
    limit: int = Query(default=FEED_DEFAULT_LIMIT, ge=1, le=FEED_MAX_LIMIT),
    x_session_id: Optional[str] = Header(default=None),
    user=Depends(auth.optional_user),
):
    """The shared feed, or the caller's own builds when `mine` is set.

    "Own" means the signed-in account when there is one, and this browser's
    anonymous token otherwise. The token travels in a header rather than the
    query string so it stays out of access logs and Referer headers.
    """
    query = {}

    if mine:
        if user is not None:
            query["user_id"] = user["_id"]
        else:
            session_id = clean_session_id(x_session_id)

            if session_id is None:
                return []

            query["session_id"] = session_id

    projection = {
        "build_title": 1,
        "character_name": 1,
        "role": 1,
        "build_score": 1,
        "created_at": 1,
        "author_name": 1,
        "author_avatar_url": 1,
    }
    documents = (
        builds_collection()
        .find(query, projection)
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
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
                    "character_power": document["character_power"],
                    "perks": document["perks"],
                    "item_kits": document["item_kits"],
                    "counter_killers": document.get("counter_killers"),
                }
            },
        )

    return serialize_build(document)
