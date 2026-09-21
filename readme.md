# AI Wardrobe

An AI-powered personal styling application. Upload your wardrobe once, describe what you're
dressing for, and get outfit combinations built only from clothes you actually own — with an
explanation for each suggestion and optional virtual try-on.

See `CLAUDE.md` for the full product/architecture spec and `docs/IMPLEMENTATION_PROMPT.md` for the
phased build plan this codebase follows.

## Status

Build is in progress, following the phased plan in `docs/IMPLEMENTATION_PROMPT.md`. Current state:

- [x] Phase 0 — Repo inspected, plan confirmed
- [x] Phase 1 — Project foundation (this increment)
- [x] Phase 2 — Database schema & migrations (this increment)
- [x] Phase 3 — Authentication (this increment)
- [ ] Phase 4 — Profile & avatar
- [ ] Phase 5 — Object storage
- [ ] Phase 6+ — Garment upload, vision analysis, embeddings, wardrobe search, stylist, outfit
      generation/scoring, try-on, full frontend, tests, hardening

All AI providers (LLM, vision, embeddings, try-on) default to local **mock** implementations so the
app runs end-to-end without any paid API keys. Swap in a real provider later by changing the
`*_PROVIDER` env vars and implementing the matching provider class.

## Repository layout

```text
apps/
├── web/                  # Next.js (TypeScript) frontend
└── api/                  # FastAPI backend
packages/
├── shared-types/         # TS types shared by frontend (mirrors backend schemas)
└── prompts/              # LLM prompt templates
infra/
├── docker/               # Dockerfiles
├── postgres/             # DB-related infra notes
└── terraform/            # (reserved for future infra-as-code)
scripts/                  # Dev/ops helper scripts
```

## Prerequisites

- Docker + Docker Compose
- Node.js 20+ (only needed if running the frontend outside Docker)
- Python 3.11+ (only needed if running the backend outside Docker)

## Local development

1. Copy the environment template and adjust as needed:

   ```bash
   cp .env.example .env
   ```

2. Start everything (Postgres + pgvector, API, web):

   ```bash
   docker compose up --build
   ```

3. Apply database migrations (first run, and after pulling new migrations):

   ```bash
   docker compose exec api alembic upgrade head
   ```

4. Open:
   - Frontend: http://localhost:3000
   - API health check: http://localhost:8000/health
   - API docs (Swagger): http://localhost:8000/docs

## Running the API without Docker

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example ../../.env   # if not already done, then edit DATABASE_URL to point at a local Postgres
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Running the backend tests

macOS often has no bare `pip` on PATH even when `python3` is installed — use a virtualenv (or
`python3 -m pip`) rather than a bare `pip` command:

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate   # skip if you already created this for the API
pip install -r requirements-dev.txt
pytest
```

If `python3` itself is not found, install Python first (`brew install python`, or from
python.org), then retry.


## Environment variables

See `.env.example` for the full list (database, JWT, object storage, and the four AI provider
slots: `LLM_*`, `VISION_*`, `EMBEDDING_*`, `TRYON_*`). Never commit a real `.env` file.

## Notes

- Every database query for user-owned data is scoped by the authenticated `user_id` — see
  `apps/api/app/core/deps.py` and `apps/api/app/repositories/`.
- AI providers are accessed only through interfaces defined in `apps/api/app/services/` (added as
  each phase needs them) — no provider SDK is imported outside its own implementation module.
- `EMBEDDING_DIMENSION` controls the pgvector column width at migration time; it is not
  hard-coded to 1536.
