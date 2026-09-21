# Claude Code Implementation Prompt — AI Wardrobe MVP

You are implementing the AI Wardrobe MVP described in `CLAUDE.md`.

Read `CLAUDE.md` completely before changing code.

## Goal

Build a production-quality MVP where a user can:

1. Sign up/login.
2. Create a basic style profile.
3. Upload clothing images.
4. Automatically classify/analyze clothing with AI.
5. Store clothing metadata and embeddings.
6. Search their own wardrobe semantically.
7. Describe what they want to wear in natural language.
8. Receive 3–5 outfit combinations using only their owned garments.
9. Receive an explanation for each outfit.
10. Like/dislike/save outfits.
11. Upload a full-body avatar.
12. Request virtual try-on through a provider abstraction.
13. Track the asynchronous try-on job.

Do not build features outside this MVP unless required to make the above work.

---

# Phase 0 — Inspect Before Implementing

First inspect the repository.

Determine:

- existing files
- existing framework/code
- package manager
- Python version
- Node version
- database setup
- existing environment configuration
- existing tests
- existing UI components
- whether any architecture already exists

Do not destroy or replace working code without a reason.

If the repository is empty, initialize the structure from `CLAUDE.md`.

Before implementation, produce a short plan in the terminal/response containing:

```text
Current state
Planned implementation
Files likely to be created
Files likely to be modified
Dependencies required
```

Then proceed with implementation.

---

# Phase 1 — Project Foundation

Create/configure:

```text
apps/web
apps/api
packages/shared-types
packages/prompts
infra
scripts
```

Set up:

- Next.js + TypeScript frontend
- FastAPI backend
- PostgreSQL
- pgvector
- Docker Compose
- environment configuration
- CORS
- health endpoint

Create:

```text
GET /health
```

Expected response:

```json
{
  "status": "ok"
}
```

Add `.env.example`.

Do not commit real credentials.

---

# Phase 2 — Database

Use:

- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- pgvector

Create migrations for:

```text
users
user_profiles
avatars
garments
garment_images
garment_embeddings
style_requests
outfits
outfit_items
outfit_feedback
try_on_jobs
```

Enable:

```sql
pgcrypto
vector
```

Create appropriate indexes.

For embeddings, use a configurable dimension:

```text
EMBEDDING_DIMENSION
```

The database vector dimension must match the configured embedding model.

Do not assume that every embedding provider returns 1536 dimensions.

Create SQLAlchemy relationships where useful, but avoid excessive bidirectional relationships that complicate queries.

---

# Phase 3 — Authentication

Implement:

```text
POST /api/v1/auth/signup
POST /api/v1/auth/login
POST /api/v1/auth/logout
```

Use a secure password hashing mechanism.

Never store plaintext passwords.

Implement an authenticated-user dependency.

All protected endpoints must obtain the current user from authentication.

Most importantly:

## User isolation

Every query involving user-owned data must be scoped to the authenticated user.

For example:

```python
select(Garment).where(
    Garment.id == garment_id,
    Garment.user_id == current_user.id,
)
```

Never:

```python
select(Garment).where(Garment.id == garment_id)
```

followed by filtering in Python.

Apply this rule to:

- garments
- garment images
- embeddings
- avatars
- profiles
- style requests
- outfits
- outfit items
- feedback
- try-on jobs

Add tests specifically proving cross-user access is impossible.

---

# Phase 4 — Profile and Avatar

Implement:

```text
GET /api/v1/profile
PUT /api/v1/profile

POST /api/v1/avatar
GET /api/v1/avatar
```

Profile fields:

```text
height_cm
body_shape
preferred_fit
preferred_styles
preferred_colors
disliked_colors
style_preferences
```

Avatar upload:

- validate image MIME type
- validate reasonable file size
- upload to object storage
- store only the URL/key in PostgreSQL
- support a primary avatar

Do not require sophisticated body measurement for the MVP.

---

# Phase 5 — Object Storage

Create a storage abstraction.

Example:

```python
class StorageService(Protocol):
    async def upload(
        self,
        file: BinaryIO,
        key: str,
        content_type: str,
    ) -> str:
        ...

    async def delete(self, key: str) -> None:
        ...
```

Support an S3-compatible implementation.

Keep storage provider details outside route handlers.

Do not store image bytes in PostgreSQL.

---

# Phase 6 — Garment Upload

Implement:

```text
POST /api/v1/garments
GET /api/v1/garments/{id}
PUT /api/v1/garments/{id}
DELETE /api/v1/garments/{id}
```

Upload should be multipart/form-data.

On upload:

```text
validate file
↓
create garment with pending status
↓
upload image
↓
create garment_image
↓
enqueue/process AI analysis
↓
return garment
```

The API should not block unnecessarily on a slow AI provider.

At minimum, structure the code so processing can run as a background task and later be moved to Celery/RQ/another worker without changing the API contract.

---

# Phase 7 — Garment Vision Analysis

Create:

```python
class VisionService(Protocol):
    async def analyze_garment(
        self,
        image_url: str,
    ) -> GarmentAnalysis:
        ...
```

The service must return:

```text
category
subcategory
colors
pattern
material
fit
formality
seasons
style_tags
description
```

Validate the result using Pydantic.

Allowed top-level categories:

```text
top
bottom
dress
outerwear
footwear
accessory
```

If the AI returns invalid data:

1. Do not corrupt the database.
2. Record a safe processing error.
3. Set processing status to `failed`.
4. Make retry possible.

The provider SDK must not be imported throughout the application. Only the provider implementation should know about it.

---

# Phase 8 — Embeddings

Create:

```python
class EmbeddingService(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...
```

Generate a textual representation of each garment.

Example:

```text
category: top
subcategory: blouse
colors: cream, black
pattern: solid
material: cotton
fit: relaxed
formality: 0.7
seasons: spring, summer
style_tags: minimalist, elegant, smart casual
description: relaxed cream blouse with black trim
```

Generate the embedding and store:

```text
garment_id
embedding
embedding_model
embedding_text
```

Do not silently truncate or pad vectors.

Verify the returned dimension equals:

```text
EMBEDDING_DIMENSION
```

before database insertion.

---

# Phase 9 — Wardrobe Search

Implement:

```text
GET /api/v1/wardrobe
POST /api/v1/wardrobe/search
```

Support:

```text
category
subcategory
color
style
processing_status
page
page_size
```

Semantic search:

```json
{
  "query": "minimal sophisticated dinner top",
  "category": "top",
  "limit": 10
}
```

Process:

```text
query
↓
embedding
↓
pgvector cosine similarity
↓
user_id filter
↓
optional structured filters
↓
results
```

Never perform vector search across all users.

Always scope by `user_id`.

---

# Phase 10 — Style Intent

Implement:

```text
POST /api/v1/stylist/generate
```

Create:

```python
class LLMService(Protocol):
    async def parse_style_intent(
        self,
        prompt: str,
        profile: UserProfile,
    ) -> StyleIntent:
        ...
```

Input:

```json
{
  "prompt": "Dinner date tonight. I want to look sophisticated but effortless.",
  "occasion": "date",
  "vibe": ["sophisticated", "relaxed"],
  "constraints": {}
}
```

Convert this into:

```python
StyleIntent(
    occasion=...,
    formality=...,
    vibes=[...],
    preferred_colors=[...],
    excluded_colors=[...],
    required_categories=[...],
    excluded_categories=[...],
    constraints={...},
)
```

Use structured LLM output if the provider supports it.

Validate with Pydantic.

If parsing fails, return a useful API error rather than passing malformed data downstream.

---

# Phase 11 — Outfit Generation

This is the core business logic.

The AI must suggest outfits, but it must ONLY use garments retrieved from the user's wardrobe.

Never allow the LLM to invent wardrobe items.

Implement an outfit generation service:

```python
class OutfitGenerator:
    async def generate(
        self,
        user_id: UUID,
        intent: StyleIntent,
    ) -> list[GeneratedOutfit]:
        ...
```

Pipeline:

```text
StyleIntent
↓
retrieve candidate tops
retrieve candidate bottoms
retrieve dresses
retrieve outerwear
retrieve footwear
retrieve accessories
↓
generate combinations
↓
remove incompatible combinations
↓
score combinations
↓
deduplicate
↓
return top 3–5
```

The exact retrieval strategy may use:

- structured SQL filters
- pgvector similarity
- style tags
- occasion
- formality
- user preferences

Do not send the entire wardrobe to the LLM.

---

# Phase 12 — Outfit Compatibility

Create deterministic compatibility logic.

At minimum evaluate:

### Category

Examples:

```text
top + bottom + footwear
dress + footwear
top + bottom + outerwear + footwear
```

Avoid nonsensical combinations.

### Color

Implement a simple initial color compatibility system.

Do not attempt a sophisticated fashion color model for the first version.

### Occasion

Compare:

```text
outfit formality
vs
requested formality
```

### Style

Compare style tags between:

```text
garments
vs
requested vibes
```

### Fit

Use profile preferred fit where available.

---

# Phase 13 — Outfit Scoring

Use this initial weighted score:

```text
style       0.30
color       0.20
occasion    0.20
fit         0.10
preference  0.10
novelty     0.10
```

Implement:

```python
score_outfit(...)
```

Return both:

```text
final_score
scoring_breakdown
```

Example:

```json
{
  "style": 0.94,
  "color": 0.91,
  "occasion": 0.96,
  "fit": 0.90,
  "preference": 0.93,
  "novelty": 0.71
}
```

Calculate the weighted total deterministically.

Do not use an LLM as the only ranking mechanism.

Write unit tests for scoring.

---

# Phase 14 — Outfit Persistence

Persist generated outfits:

```text
style_request
outfit
outfit_items
```

Every outfit item must reference an actual garment owned by the current user.

Use:

```text
role
position
```

Examples:

```text
top
bottom
outerwear
footwear
accessory
```

Prevent duplicate garment entries within one outfit.

---

# Phase 15 — Outfit Explanation

After deterministic outfit generation/ranking, optionally call the LLM to explain each selected outfit.

The LLM receives only the selected outfit's structured garment data and relevant style intent.

Example explanation:

```text
Why it works:
- The neutral blouse keeps the look polished.
- The tailored trousers make it appropriate for a dinner setting.
- The sneakers keep the outfit relaxed rather than overly formal.
```

The explanation must describe actual garments.

Do not let the LLM add garments that are not in the outfit.

If the explanation service fails, still return the outfit with a fallback explanation.

---

# Phase 16 — Feedback

Implement:

```text
POST /api/v1/outfits/{id}/feedback
```

Allowed:

```text
like
dislike
save
worn
```

Persist feedback.

The MVP does not need a machine-learning personalization model.

However, structure the service so feedback can later influence:

```text
preference score
novelty
style retrieval
```

---

# Phase 17 — Try-On

Implement:

```text
POST /api/v1/tryon
GET /api/v1/tryon/{job_id}
```

Input:

```json
{
  "outfit_id": "...",
  "avatar_id": "..."
}
```

Verify:

- outfit belongs to current user
- avatar belongs to current user
- every outfit garment belongs to current user

Create:

```text
try_on_job(status=pending)
```

Then invoke the provider asynchronously.

Use:

```python
class TryOnService(Protocol):
    async def create_try_on(
        self,
        avatar_url: str,
        garment_urls: list[str],
    ) -> TryOnResult:
        ...
```

Update:

```text
pending → processing → completed
```

or:

```text
pending → processing → failed
```

Store:

```text
provider
provider_job_id
result_image_url
error_message
```

For MVP, frontend polling is acceptable.

If no real VTON provider is configured, implement a mock provider for local development so the rest of the application can be tested.

Do not fake successful results in production.

---

# Phase 18 — Frontend

Build a clean MVP UI.

## Required pages

```text
/
/login
/signup
/onboarding
/wardrobe
/wardrobe/upload
/wardrobe/[garmentId]
/stylist
/outfits
/outfits/[outfitId]
/profile
```

## Wardrobe

Include:

- upload
- grid
- filters
- category labels
- processing state
- garment detail

## Stylist

Primary screen:

```text
What are you dressing for?

[ Dinner date tonight. Sophisticated but effortless. ]

[ Generate outfits ]
```

Results:

```text
Outfit 1
[items]
score
why it works
[Like] [Dislike] [Save] [Try on]

Outfit 2
...
```

## Loading states

Provide useful loading states for:

- upload
- garment processing
- stylist generation
- try-on generation

## Error states

Do not leave blank screens when requests fail.

---

# Phase 19 — API Client

Create a typed frontend API layer.

Do not call `fetch()` throughout components.

Prefer:

```text
lib/api/auth.ts
lib/api/profile.ts
lib/api/garments.ts
lib/api/wardrobe.ts
lib/api/stylist.ts
lib/api/outfits.ts
lib/api/tryon.ts
```

Keep request/response types centralized.

---

# Phase 20 — Testing

Add backend tests for:

```text
authentication
profile
garment CRUD
user isolation
wardrobe search
style intent validation
outfit scoring
outfit generation
feedback
try-on authorization
```

Critical security tests:

```text
User A cannot read User B's garment
User A cannot update User B's garment
User A cannot delete User B's garment
User A cannot read User B's outfit
User A cannot submit feedback on User B's outfit
User A cannot use User B's avatar
User A cannot start try-on using User B's outfit
```

Add frontend tests for the most important happy paths where the project setup supports them.

---

# Phase 21 — Quality Checks

Before declaring the MVP complete:

```text
docker compose up
database migration works
backend starts
frontend starts
health endpoint works
signup works
login works
garment upload works
wardrobe loads
AI processing path works or has a local mock
embedding path works or has a local mock
stylist returns outfits
outfits use only owned garments
feedback works
avatar upload works
try-on job works with configured/mock provider
```

Run available:

```text
tests
lint
format
type checks
```

Fix errors rather than ignoring them.

---

# Important Engineering Constraints

## Do not

- expose API keys to the frontend
- store passwords in plaintext
- store image binaries in PostgreSQL
- trust LLM output without validation
- allow LLMs to invent wardrobe items
- query user-owned records without `user_id`
- put provider SDK logic into route handlers
- hard-code provider-specific assumptions into business logic
- silently swallow exceptions
- add unnecessary infrastructure
- build non-MVP features

## Do

- use dependency injection
- use Pydantic validation
- use repository/service boundaries where useful
- write deterministic business logic for scoring
- isolate AI providers
- isolate storage providers
- keep API contracts stable
- write tests for business logic and authorization
- document meaningful architecture decisions

---

# Definition of Done

Do not say "complete" merely because the application starts.

The MVP is complete only when the complete flow works:

```text
Signup
  ↓
Profile
  ↓
Avatar
  ↓
Upload clothes
  ↓
AI garment analysis
  ↓
Wardrobe
  ↓
Semantic search
  ↓
Stylist prompt
  ↓
StyleIntent
  ↓
Wardrobe retrieval
  ↓
Outfit generation
  ↓
Deterministic scoring
  ↓
Top 3–5 outfits
  ↓
Explanation
  ↓
Feedback
  ↓
Try-on job
  ↓
Try-on result
```

At the end, provide:

1. Summary of what was implemented.
2. Files created/changed.
3. Commands to run locally.
4. Environment variables required.
5. Database migration command.
6. Test command.
7. Any provider APIs that must be configured.
8. Any remaining TODOs or known limitations.

Do not claim functionality works if it has not been tested.
