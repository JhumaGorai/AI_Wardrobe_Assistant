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
- [x] Phase 3 — Authentication
- [x] Phase 4 — Profile & avatar (this increment)
- [x] Phase 5 — Object storage (this increment, built alongside Phase 4 since avatar upload
      needs it; MinIO added to docker-compose as the local S3-compatible provider)
- [x] Phase 6 — Garment upload (`POST/GET/PUT/DELETE /api/v1/garments[/{id}]`, multipart image
      upload, soft delete)
- [x] Phase 7 — Garment vision analysis (this increment, built alongside Phase 6 since upload
      needs somewhere to send the image for analysis; mock vision provider, runs as a
      background task after the upload response is sent)
- [x] Wardrobe UI pulled forward from Phase 18 — `/wardrobe` (grid), `/wardrobe/upload`,
      `/wardrobe/[garmentId]` (detail/edit/delete). Uses a temporary "paste your access token"
      dev shim for auth since real `/login`/`/signup` pages don't exist yet.
- [ ] Phase 8+ — Embeddings, wardrobe search, stylist, outfit generation/scoring, try-on, full
      login/signup UI, tests, hardening

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
   - MinIO console (object storage, local dev only): http://localhost:9001
     (login with `STORAGE_ACCESS_KEY` / `STORAGE_SECRET_KEY` from `.env`, default
     `minioadmin` / `minioadmin`) — the `wardrobe-media` bucket is created automatically by the
     API container itself on startup (`app/core/bootstrap_storage.py`).

   Note on the `minio` image: MinIO stopped publishing free Docker Hub images in Oct 2025.
   `docker-compose.yml` pins a community-mirrored image on quay.io instead. If that tag ever
   stops resolving, check https://quay.io/repository/minio/minio?tab=tags for a current one.

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
- **Known limitation:** avatar (and future garment) images are stored with a plain, permanent
  public URL, not a presigned/expiring one — the local MinIO bucket is set to anonymous-read to
  match (`apps/api/app/services/storage/s3.py`). Fine for local dev; revisit with presigned URLs
  before deploying anywhere real.
- Server-side (SSR) code in the frontend and the API's own object-storage client both need a
  *different* URL to reach other services than the browser does, when running under Docker
  Compose (container-to-container traffic uses the compose service name; the browser needs
  `localhost`). See `apps/web/lib/api/base-url.ts` and the `STORAGE_ENDPOINT` /
  `STORAGE_PUBLIC_URL` split in `.env.example` — the same pattern would apply to any future
  service split the same way.
- **Garment upload is asynchronous by design:** `POST /api/v1/garments` returns immediately with
  `processing_status: "pending"` once the image is stored; vision analysis (currently the mock
  provider, `apps/api/app/services/vision/mock.py`) runs afterward as a FastAPI `BackgroundTask`.
  Poll `GET /api/v1/garments/{id}` to see it flip to `completed` (with `category`, `colors`,
  etc. filled in) or `failed` (with a safe `processing_error`, never the raw exception). The
  processing logic itself (`apps/api/app/services/garment_processor.py`) is a plain function that
  takes a DB session and a `VisionService` as arguments — it doesn't know or care whether it was
  called from a background task, a test, or (later) a Celery/RQ worker.
- **Deliberate schema deviation:** `garments.category` is nullable, even though CLAUDE.md
  specifies `NOT NULL` — see the comment in `apps/api/app/models/garment.py` and
  `apps/api/alembic/versions/0002_garment_category_nullable.py` for why (a garment is created
  before its category is known, and a failed analysis must be able to leave it unset).
- **Wardrobe UI has no login/signup page yet** (that's Phase 18) — visit `/wardrobe` and you'll
  see a box asking you to paste an `access_token`. Get one by signing up or logging in via
  http://localhost:8000/docs (`POST /api/v1/auth/signup` or `/login`), copying the
  `access_token` from the response, and pasting it into that box. It's stored in this browser's
  `localStorage` only (`apps/web/lib/auth-token.ts`) and attached as a Bearer header to every
  `/api/v1/garments*` request from then on. Clear it from the same box to "sign out".
- **`GET /api/v1/garments` (list) was added ahead of Phase 9**: CLAUDE.md's actual wardrobe
  listing/search endpoint (`GET /api/v1/wardrobe`, with filters/pagination) is Phase 9 and not
  built yet, but the wardrobe grid page needs *some* way to show "garments you own" today. This
  minimal, unfiltered version (`apps/api/app/repositories/garment_repository.py::list_for_user`)
  can be superseded or extended by the real Phase 9 endpoint later without changing the CRUD
  module's contract.
