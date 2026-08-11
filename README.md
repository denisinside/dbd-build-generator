# DBD Build Generator

AI-powered Dead by Daylight build generator.

It scrapes wiki data, stores it in MongoDB + ChromaDB, then uses an agentic RAG pipeline to generate grounded Survivor/Killer builds with icons, rarity frames, and play tips.

## Stack

- **Backend:** FastAPI, MongoDB, ChromaDB, LangChain + OpenRouter
- **Frontend:** Next.js
- **Data:** parsers for Perks, Survivors, Killers, Items/Add-ons

## Setup

```bash
# Python deps
uv sync

# Frontend deps
cd frontend
npm install
```

Create a `.env` in the project root:

```env
MONGO_URI=mongodb://localhost:27017/
OPENROUTER_API_KEY=...
TAVILY_API_KEY=...
LANGSMITH_API_KEY=...
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=DBD Builder
```

MongoDB must be running locally (for example via Docker):

```bash
docker run -d --name dbd-mongo -p 27017:27017 mongo:7
```

## Data pipeline

```bash
# Parse wiki pages into data/*.json
uv run python parsers/parse_perks.py
uv run python parsers/parse_survivors.py
uv run python parsers/parse_killers.py
uv run python parsers/parse_items.py

# Load JSON into MongoDB + ChromaDB
uv run python ingest.py
```

## Run

```bash
# API (http://localhost:8000)
uv run uvicorn main:app --reload --port 8000

# Frontend (http://localhost:3000)
cd frontend
npm run dev
```

## API

- `POST /api/builds/generate` — `{ "prompt": "..." }` → full enriched build
- `GET /api/builds` — history summaries
- `GET /api/builds/{id}` — one saved build

## Notes

- Generated builds are stored in MongoDB collection `generated_builds`.
- Frontend uses `NEXT_PUBLIC_API_URL` if set; otherwise it defaults to `http://localhost:8000`.
