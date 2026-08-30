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

| Variable | Why it matters |
| --- | --- |
| `MONGO_URI` | MongoDB connection string |
| `ALLOWED_ORIGINS` | Comma-separated browser origins allowed to call the API. **Add your deployed frontend origin**, otherwise every request from it fails CORS |
| `OPENROUTER_API_KEY` | Chat + embeddings |
| `OPENROUTER_CHAT_MODEL` | Agent and structured-output model |
| `TAVILY_API_KEY` | Optional; `search_web_meta` is skipped without it |
| `LANGSMITH_TRACING` | Optional tracing. Enabling it sends every user prompt to LangSmith |

MongoDB must be running (for example via Docker):

```bash
docker run -d --name dbd-mongo -p 27017:27017 mongo:7
```

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
uv run pytest          # grounding, name resolution, chunking
uv run ruff check .

cd frontend
pnpm lint
pnpm typecheck
```

CI runs all of the above on every push and pull request.

## API

- `POST /api/builds/generate` — `{ "prompt": "..." }` → full enriched build
- `GET /api/builds` — history summaries
- `GET /api/builds/{id}` — one saved build

Image fields come in pairs: `icon_path` / `portrait_path` point at the local mirror under
`/media`, and `icon_url` / `portrait_url` keep the original wiki URL as a fallback.

## Frontend routes

- `/` — generator + build history
- `/build/{id}` — one build, with Open Graph tags and a generated link-preview image, so a
  build can be shared in chat or on stream

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

## Notes

- Generated builds are stored in MongoDB collection `generated_builds`.
- Frontend uses `NEXT_PUBLIC_API_URL` if set; otherwise it defaults to `http://localhost:8000`.
- Data and icons come from the [Dead by Daylight Wiki](https://deadbydaylight.wiki.gg) and are
  used under CC BY-SA 4.0. This is an unofficial fan project, not affiliated with Behaviour
  Interactive.
