# DBD Build Generator

AI-powered Dead by Daylight build generator.

It scrapes wiki data, stores it in MongoDB + ChromaDB, then uses an agentic RAG pipeline to
generate grounded Survivor/Killer builds with icons, rarity frames, and play tips. Every
selected perk, item, add-on and Killer is validated against MongoDB before it reaches the UI,
so the model cannot invent entities.

## Stack

- **Backend:** FastAPI, MongoDB, ChromaDB, LangChain + OpenRouter
- **Frontend:** Next.js (App Router)
- **Data:** parsers for Perks, Survivors, Killers, Items/Add-ons

## Setup

```bash
# Python deps (including dev tools: pytest, ruff)
uv sync

# Frontend deps
cd frontend
pnpm install
```

Copy `.env.example` to `.env` in the project root and fill in the keys:

```bash
cp .env.example .env
cp frontend/.env.example frontend/.env.local
```

The important ones:


| Variable                | Why it matters                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `MONGO_URI`             | MongoDB connection string                                                                                                                  |
| `ALLOWED_ORIGINS`       | Comma-separated browser origins allowed to call the API. **Add your deployed frontend origin**, otherwise every request from it fails CORS |
| `OPENROUTER_API_KEY`    | Chat + embeddings                                                                                                                          |
| `OPENROUTER_CHAT_MODEL` | Agent and structured-output model                                                                                                          |
| `AUTH_SECRET`           | Signs session tokens. Unset means sign-in is off entirely                                                                                  |
| `FRONTEND_URL`          | Where the OAuth callback sends the browser back to                                                                                         |
| `TAVILY_API_KEY`        | Optional; `search_web_meta` is skipped without it                                                                                          |
| `LANGSMITH_TRACING`     | Optional tracing. Enabling it sends every user prompt to LangSmith                                                                         |


MongoDB must be running (for example via Docker):

```bash
docker run -d --name dbd-mongo -p 127.0.0.1:27017:27017 mongo:7
```

Bind it to `127.0.0.1`, not `0.0.0.0`: an unauthenticated MongoDB on a public
port is found by scanners within hours. `docker compose` does not publish the
port at all.

## Data pipeline

```bash
# 1. Parse wiki pages into data/*.json and mirror every icon into
#    frontend/public/media (requests are throttled; see WIKI_*_DELAY in .env)
uv run python parsers/parse_perks.py
uv run python parsers/parse_survivors.py
uv run python parsers/parse_killers.py
uv run python parsers/parse_items.py

# 2. Load JSON into MongoDB + ChromaDB
uv run python ingest.py
```

If `data/*.json` is already up to date and you only need the images, skip the scrape:

```bash
uv run python download_media.py          # resumable; skips existing files
uv run python download_media.py --force  # re-download everything
```

Images are served from `frontend/public/media` so the app does not hotlink the wiki at
runtime. The remote URL is kept in the data as a fallback: if a file is missing, the UI falls
back to the wiki copy, and then to a text placeholder.

## Run

```bash
# API (http://localhost:8000)
uv run uvicorn main:app --reload --port 8000

# Frontend (http://localhost:3000)
cd frontend
pnpm dev
```

Or the whole stack, MongoDB included:

```bash
docker compose up --build
```

Compose mounts `./data` and `./chroma_db` into the API container, so run the data pipeline
at least once before starting it.

## Tests and linting

```bash
uv run pytest          # grounding, pipeline, streaming, name resolution, chunking
uv run ruff check .

cd frontend
pnpm lint
pnpm typecheck
```

CI runs all of the above on every push and pull request.

`tests/test_live_llm.py` is opt-in: it runs the real model against the real
MongoDB and ChromaDB, so it costs money and takes minutes. It asserts
invariants, never wording — a real model picks different perks every run, but
it may never pick a perk that does not exist.

```bash
RUN_LIVE_TESTS=1 uv run pytest tests/test_live_llm.py -v
```



## API

- `POST /api/builds/stream` — `{ "prompt": "..." }` → Server-Sent Events:
`step` frames as the agent researches, then one `build` frame, or one
`error` frame. This is what the UI uses: a build takes about a minute, and a
silent connection that long is cut by most proxies (Cloudflare at 100s).
- `POST /api/builds/generate` — the same thing without progress, for scripts
- `GET /api/builds?limit=30` — the shared feed, newest first
- `GET /api/builds?mine=1` — the caller's own builds: their account's when
signed in, this browser's anonymous ones otherwise
- `GET /api/builds/{id}` — one saved build
- `GET /health` — liveness plus a MongoDB round-trip

Send `X-Session-Id` (any 8-64 char token; the UI mints a UUID per browser and
keeps it in `localStorage`) to mark a build as yours while signed out. It is an
owner tag, not a credential, and it never appears in any response.

## Sign-in

Twitch, Discord and Google. Each appears only once its client id and secret are
configured, so a deployment never shows a button that cannot work — if the
header says "Sign-in is not configured", `AUTH_SECRET` or a provider's
credentials are missing.

**Generating a build requires an account**, enforced on the endpoint and not
just in the UI: it is a plain HTTP call anyone can make directly. The
requirement applies exactly where an account can be obtained — with no
`AUTH_SECRET` or no provider credentials, generation stays open to anonymous
callers, because demanding an account nobody can create would brick the app
rather than guard it. The API prints which mode it is in at startup.

Submitting a prompt while signed out saves it, offers the providers, and puts
it back in the field on the way back.

- `GET /auth/providers` — what the UI should offer; `[]` means sign-in is off
- `GET /auth/{provider}/login?next=/path` — starts the handshake
- `GET /auth/{provider}/callback` — provider lands here, then bounces to
`FRONTEND_URL/auth/callback#token=...`
- `GET /auth/me` — the signed-in account
- `POST /auth/claim` — moves this browser's anonymous builds onto the account

Sessions are Bearer tokens rather than cookies, so the frontend and the API can
live on different sites without depending on `SameSite=None`, which Safari's
ITP and the third-party cookie wind-down keep eroding. Send
`Authorization: Bearer <token>`. If you settle on one domain later, a cookie is
the stricter option and the swap is confined to `src/auth.py`.

Provider access tokens are read once, for the profile, and dropped: an account
holds an id, a display name and an avatar URL, nothing more. There is no
refresh flow to maintain and nothing worth stealing.

Signing in also changes what the hourly cap counts. Anonymous callers are
capped per IP, which punishes everyone behind one CGNAT address and is
sidestepped by any VPN; signed-in callers are capped per account.
`generate_limit_per_hour` on a user document raises the ceiling for one
account, and `disabled: true` locks it out on the next request — the user
document is read on every authenticated call, so neither waits for a token to
expire.

Accounts are per provider: signing in with Twitch and later with Google makes
two accounts. Linking them is a later problem.

At most `GENERATE_CONCURRENCY` builds run at once; the rest get a 503 with
`Retry-After` rather than queueing behind a minute-long request. One build has
a `BUILD_DEADLINE_SECONDS` wall-clock budget across research and every retry.

Image fields come in pairs: `icon_path` / `portrait_path` point at the local mirror under
`/media`, and `icon_url` / `portrait_url` keep the original wiki URL as a fallback.

## Frontend routes

- `/` — generator, the live feed of everyone's builds, and this browser's own
- `/build/{id}` — one build, with Open Graph tags and a generated link-preview image, so a
build can be shared in chat or on stream



## What a build contains

Beyond the four perks and two add-on kits, every generated build carries:

- a **reason per piece** — why this perk, item and add-on is in this build, as
opposed to what the wiki says it does. The two are kept visually apart so the
generator's opinion never reads like official text.
- the **source character** of each perk, so a new player knows whose Bloodweb
to grind for it.
- the **Killer power** for Killer builds. Add-ons are power modifiers, and the
page used to show them without ever naming what they modify. Shown once, not
per kit: unlike a Survivor item, the power is fixed by the Killer.
- **synergies** — 2-3 interactions between the pieces. Every name in one is
checked against the rest of the loadout (perks, add-ons, item, Killer power,
character), so a combo can only talk about things that are actually equipped.
- **counter perks** — 3 perks of the *opposing* role that blunt the build, with
what they do to you and how to play around them. Killer perks for a Survivor
build, Survivor perks for a Killer build. This is the mirror of counter
Killers, and the only grounded answer to "what beats a Killer build": maps
are not in the data, so listing bad maps would be invention, while every perk
here is validated like the rest.
- **four scored axes** instead of one opaque rating. Survivor builds are scored
on Chase, Information, Objective and Team Utility; Killer builds on Chase,
Map Pressure, Slowdown and Anti-Loop. The 1-10 headline is the average of
those, not a number the model gave itself — asked directly, a model answers
7 or 8 whatever the build is.

Counter Killers stay Survivor-only, and are rated Low / Medium / High. Three
levels rather than two, because with only Medium and High every one of the five
reads as a nightmare and the ranking carries no information.

Builds saved before any of this simply render without those sections. The
enrichment-only parts (power, perk character) are backfilled when an old build
is opened.

## RAG index

`chroma_loader.py` chunks every document to ~800 tokens with ~100 tokens of overlap and
tags each chunk with:

- `category` — `perk`, `item`, `addon`, `killer_power`, `killer_lore`, `survivor_lore`,
`game_mechanics`
- `owner` — the entity a chunk belongs to: the Killer title for a Killer add-on, the item
category for an item add-on, the character for a perk
- `section` — `Overview` / `Lore` / `Trivia` for lore chunks

`owner` is what makes add-on search usable: without it, a query for "chase add-on" returns
add-ons from all 44 Killers and the model has to guess which ones it may use.

Perk owners are canonicalised at ingest. The wiki's perk table names them in
short form ("Meg", "Artist") while every lookup uses the full name ("Meg
Thomas", "The Artist"); left as-is, an owner-filtered perk search matches
nothing at all, silently, because `resolve_owner` only ever produces the long
form.

## Notes

- Generated builds are stored in MongoDB collection `generated_builds`.
- Frontend uses `NEXT_PUBLIC_API_URL` if set; otherwise it defaults to `http://localhost:8000`.
- Data and icons come from the [Dead by Daylight Wiki](https://deadbydaylight.wiki.gg) and are
used under CC BY-SA 4.0. This is an unofficial fan project, not affiliated with Behaviour
Interactive.

