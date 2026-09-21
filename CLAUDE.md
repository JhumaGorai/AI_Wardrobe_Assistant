# AI Wardrobe — Claude Code Project Guide

## 1. Project Overview

AI Wardrobe is an AI-powered personal styling application.

### Product promise

> Upload my wardrobe once. Tell my AI stylist what I’m dressing for. It searches my digital wardrobe, creates the best combinations using only clothes I own, and shows me what they look like on my avatar.

### Core MVP flow

```text
User
  ↓
Uploads clothing + avatar
  ↓
AI analyzes each garment
  ↓
Structured wardrobe stored in PostgreSQL
  ↓
Embeddings stored in pgvector
  ↓
User describes desired outfit/vibe
  ↓
LLM converts request → StyleIntent
  ↓
Semantic + structured wardrobe retrieval
  ↓
Outfit combinations generated
  ↓
Compatibility + scoring/ranking
  ↓
Top 3–5 outfits
  ↓
LLM explanation
  ↓
Optional virtual try-on
```

The MVP is a web application. Do not build a mobile app, marketplace, social network, shopping system, weather integration, 3D avatar system, or sophisticated body-measurement system.

---

## 2. Architecture

```text
apps/
├── web/                  # Next.js frontend
└── api/                  # FastAPI backend

PostgreSQL + pgvector     # relational data + semantic search
S3-compatible storage     # garment/avatar/generated images
LLM                       # intent parsing + explanations
Vision model              # garment analysis
Embedding model           # garment/query embeddings
VTON provider             # virtual try-on, behind an interface
```

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui where useful
- Use server/client components appropriately.
- Keep API communication isolated in `lib/api`.
- Avoid putting business logic in React components.

### Backend

- Python
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- pgvector
- Async-compatible implementation where practical

### Storage

Use an S3-compatible object storage abstraction.

Do not store binary images directly in PostgreSQL.

### AI

All external AI providers must be hidden behind service interfaces.

Example:

```python
class VisionService(Protocol):
    async def analyze_garment(self, image_url: str) -> GarmentAnalysis:
        ...

class EmbeddingService(Protocol):
    async def embed(self, text: str) -> list[float]:
        ...

class LLMService(Protocol):
    async def parse_style_intent(self, prompt: str, profile: UserProfile) -> StyleIntent:
        ...

class TryOnService(Protocol):
    async def create_try_on(self, avatar_url: str, garment_urls: list[str]) -> str:
        ...
```

The application must not directly depend on a provider SDK throughout the codebase.

---

## 3. Repository Structure

```text
ai-wardrobe/
├── apps/
│   ├── web/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── signup/page.tsx
│   │   │   ├── onboarding/page.tsx
│   │   │   ├── wardrobe/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── upload/page.tsx
│   │   │   │   └── [garmentId]/page.tsx
│   │   │   ├── stylist/page.tsx
│   │   │   ├── outfits/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [outfitId]/page.tsx
│   │   │   ├── profile/page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── wardrobe/
│   │   │   ├── stylist/
│   │   │   ├── outfit/
│   │   │   ├── avatar/
│   │   │   └── common/
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   ├── types/
│   │   │   └── utils.ts
│   │   └── hooks/
│   │
│   └── api/
│       ├── app/
│       │   ├── main.py
│       │   ├── api/v1/
│       │   │   ├── auth.py
│       │   │   ├── profile.py
│       │   │   ├── avatar.py
│       │   │   ├── garments.py
│       │   │   ├── wardrobe.py
│       │   │   ├── stylist.py
│       │   │   ├── outfits.py
│       │   │   └── tryon.py
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   │   ├── wardrobe/
│       │   │   ├── stylist/
│       │   │   ├── outfit/
│       │   │   ├── vision/
│       │   │   ├── embeddings/
│       │   │   └── tryon/
│       │   ├── repositories/
│       │   └── core/
│       └── tests/
│
├── packages/
│   ├── shared-types/
│   └── prompts/
├── infra/
│   ├── docker/
│   ├── postgres/
│   └── terraform/
├── scripts/
├── docker-compose.yml
├── .env.example
├── CLAUDE.md
└── README.md
```

Claude Code may adjust this structure if there is a strong technical reason, but must document the change.

---

## 4. Database

Enable:

```sql
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS vector;
```

### users

```text
id UUID PK
email VARCHAR(255) UNIQUE NOT NULL
name VARCHAR(100)
created_at TIMESTAMPTZ
updated_at TIMESTAMPTZ
```

### user_profiles

```text
id UUID PK
user_id UUID UNIQUE FK users
height_cm NUMERIC
body_shape VARCHAR
preferred_fit VARCHAR DEFAULT "regular"
preferred_styles JSONB
preferred_colors JSONB
disliked_colors JSONB
style_preferences JSONB
created_at
updated_at
```

### avatars

```text
id UUID PK
user_id UUID FK users
image_url TEXT
type VARCHAR DEFAULT "full_body"
is_primary BOOLEAN
metadata JSONB
created_at
```

### garments

```text
id UUID PK
user_id UUID FK users
name VARCHAR
category VARCHAR NOT NULL
subcategory VARCHAR
colors JSONB
pattern VARCHAR
material VARCHAR
fit VARCHAR
formality NUMERIC(3,2)
seasons JSONB
style_tags JSONB
description TEXT
processing_status VARCHAR DEFAULT "pending"
processing_error TEXT
is_active BOOLEAN DEFAULT TRUE
created_at
updated_at
```

Categories:

```text
top
bottom
dress
outerwear
footwear
accessory
```

### garment_images

```text
id UUID PK
garment_id UUID FK garments
image_url TEXT
image_type VARCHAR DEFAULT "original"
is_primary BOOLEAN
width INTEGER
height INTEGER
created_at
```

Image types:

```text
original
thumbnail
processed
transparent
```

### garment_embeddings

```text
id UUID PK
garment_id UUID UNIQUE FK garments
embedding VECTOR(1536)
embedding_model VARCHAR
embedding_text TEXT
created_at
```

The vector dimension must match the selected embedding model. Do not hard-code 1536 if the configured provider uses another dimension.

Use an HNSW cosine index.

### style_requests

```text
id UUID PK
user_id UUID FK users
prompt TEXT
occasion VARCHAR
formality NUMERIC(3,2)
vibes JSONB
constraints JSONB
parsed_intent JSONB
created_at
```

### outfits

```text
id UUID PK
user_id UUID FK users
style_request_id UUID FK style_requests nullable
occasion VARCHAR
vibe VARCHAR
description TEXT
score NUMERIC(5,4)
scoring_breakdown JSONB
status VARCHAR DEFAULT "generated"
created_at
```

### outfit_items

```text
id UUID PK
outfit_id UUID FK outfits
garment_id UUID FK garments
role VARCHAR
position INTEGER
UNIQUE(outfit_id, garment_id)
```

### outfit_feedback

```text
id UUID PK
user_id UUID FK users
outfit_id UUID FK outfits
feedback VARCHAR
created_at
UNIQUE(user_id, outfit_id, feedback)
```

Allowed feedback:

```text
like
dislike
save
worn
```

### try_on_jobs

```text
id UUID PK
user_id UUID FK users
outfit_id UUID FK outfits
avatar_id UUID FK avatars
status VARCHAR DEFAULT "pending"
result_image_url TEXT
provider VARCHAR
provider_job_id VARCHAR
error_message TEXT
created_at
started_at
completed_at
```

Statuses:

```text
pending
processing
completed
failed
```

---

## 5. Pydantic Contracts

Use Pydantic v2.

Important request/response models:

```python
class UserCreate(BaseModel):
    email: EmailStr
    name: str | None = None
    password: str


class UserProfileUpdate(BaseModel):
    height_cm: float | None = Field(default=None, gt=50, lt=300)
    body_shape: str | None = None
    preferred_fit: str = "regular"
    preferred_styles: list[str] = []
    preferred_colors: list[str] = []
    disliked_colors: list[str] = []
    style_preferences: dict = {}


class GarmentAnalysis(BaseModel):
    category: str
    subcategory: str | None = None
    colors: list[str]
    pattern: str | None = None
    material: str | None = None
    fit: str | None = None
    formality: float = Field(ge=0, le=1)
    seasons: list[str]
    style_tags: list[str]
    description: str


class StyleRequestCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    occasion: str | None = None
    vibe: list[str] = []
    constraints: dict = {}


class StyleIntent(BaseModel):
    occasion: str | None = None
    formality: float = Field(default=0.5, ge=0, le=1)
    vibes: list[str] = []
    preferred_colors: list[str] = []
    excluded_colors: list[str] = []
    required_categories: list[str] = []
    excluded_categories: list[str] = []
    constraints: dict = {}


class OutfitFeedbackCreate(BaseModel):
    feedback: Literal["like", "dislike", "save", "worn"]


class TryOnCreate(BaseModel):
    outfit_id: UUID
    avatar_id: UUID
```

Use `ConfigDict(from_attributes=True)` on response models where ORM conversion is required.

Avoid mutable defaults in production models. Prefer `Field(default_factory=list)` and `Field(default_factory=dict)`.

---

## 6. API Contract

### Auth

```text
POST /api/v1/auth/signup
POST /api/v1/auth/login
POST /api/v1/auth/logout
```

### Profile

```text
GET /api/v1/profile
PUT /api/v1/profile
```

### Avatar

```text
POST /api/v1/avatar
GET /api/v1/avatar
```

Avatar upload is multipart/form-data.

### Garments

```text
POST /api/v1/garments
GET /api/v1/garments/{id}
PUT /api/v1/garments/{id}
DELETE /api/v1/garments/{id}
```

Garment creation accepts an image upload and returns quickly with:

```json
{
  "processing_status": "pending"
}
```

AI processing should happen asynchronously.

### Wardrobe

```text
GET /api/v1/wardrobe
POST /api/v1/wardrobe/search
```

Filters:

```text
category
subcategory
color
style
processing_status
page
page_size
```

Semantic search request:

```json
{
  "query": "smart casual neutral outfit",
  "category": "top",
  "limit": 10
}
```

### Stylist

```text
POST /api/v1/stylist/generate
```

Example:

```json
{
  "prompt": "Dinner date tonight. I want to look sophisticated but effortless.",
  "occasion": "date",
  "vibe": ["sophisticated", "relaxed"],
  "constraints": {}
}
```

Return 3–5 outfits.

### Outfits

```text
GET /api/v1/outfits
GET /api/v1/outfits/{id}
POST /api/v1/outfits/{id}/feedback
```

### Try-on

```text
POST /api/v1/tryon
GET /api/v1/tryon/{job_id}
```

Try-on is asynchronous.

---

## 7. Authentication and Authorization

For the MVP, implement a secure authenticated-user dependency.

Every protected query MUST scope records by authenticated `user_id` at the database/repository layer.

Correct:

```python
select(Garment).where(
    Garment.id == garment_id,
    Garment.user_id == current_user.id,
)
```

Incorrect:

```python
garment = await get_garment(garment_id)
if garment.user_id != current_user.id:
    ...
```

Do not fetch another user's data and filter it afterward.

Never expose passwords, provider secrets, internal errors, or storage credentials to the frontend.

---

## 8. Garment AI Processing

When a garment is uploaded:

```text
upload image
  ↓
create garment(status=pending)
  ↓
store image
  ↓
background job
  ↓
vision analysis
  ↓
validate GarmentAnalysis
  ↓
update garment attributes
  ↓
construct embedding text
  ↓
generate embedding
  ↓
store vector
  ↓
status=completed
```

If AI processing fails:

```text
status=failed
processing_error=<safe error>
```

The user should still be able to see/retry the garment.

Example embedding text:

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

---

## 9. Stylist Algorithm

Do NOT ask the LLM to invent clothing that the user does not own.

The backend must retrieve real garments first.

### Flow

```text
prompt
 ↓
LLM → StyleIntent
 ↓
structured filters
 ↓
semantic vector retrieval
 ↓
candidate garments
 ↓
outfit combination generation
 ↓
compatibility rules
 ↓
scoring
 ↓
deduplicate
 ↓
top 3–5
 ↓
LLM explanations
```

### Candidate retrieval

Combine:

1. Structured filters
2. Semantic similarity
3. User preferences

Example:

```text
occasion compatibility
category compatibility
color compatibility
style compatibility
fit compatibility
preference compatibility
```

### Outfit scoring

Start with:

```text
style       30%
color       20%
occasion    20%
fit         10%
preference  10%
novelty     10%
```

This is a heuristic, not a final ML model.

Store the individual values in:

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

Then calculate the weighted score.

Do not use an LLM as the only ranking mechanism.

---

## 10. LLM Responsibilities

The LLM may:

- interpret natural-language style requests
- produce structured `StyleIntent`
- explain why an outfit works
- suggest styling variations using the retrieved garments

The LLM must NOT:

- invent garments
- access the database directly
- bypass authorization
- decide ownership
- be the sole outfit ranking mechanism
- receive unnecessary private user data

Use structured output wherever supported.

Validate every LLM response with Pydantic.

---

## 11. Virtual Try-On

VTON must be behind an interface.

```python
class TryOnService(Protocol):
    async def create_try_on(
        self,
        avatar_url: str,
        garment_urls: list[str],
    ) -> TryOnResult:
        ...
```

Do not tightly couple the application to one provider.

The API should create a `try_on_job` and return immediately.

The frontend polls the job endpoint for the MVP.

Later, replace polling with WebSockets/SSE if needed.

---

## 12. Frontend UX

### Home

Simple entry point:

- wardrobe count
- primary avatar
- "What are you dressing for?" stylist prompt
- recent outfits

### Wardrobe

Show:

- garment cards
- image
- category
- colors
- style tags
- processing status
- upload button
- filters

### Stylist

Primary MVP screen.

Example:

```text
What are you dressing for?

[ Dinner date tonight. Sophisticated but effortless. ]

              [ Generate outfits ]
```

Then show 3–5 outfit cards.

Each card:

- garment images
- outfit name
- score
- explanation
- Save
- Like
- Dislike
- Try on

### Try-on

Show:

- avatar
- generated outfit
- loading state
- result image
- retry/failure state

---

## 13. Error Handling

Use consistent API errors.

Do not expose stack traces.

Handle:

- invalid uploads
- unsupported image types
- oversized images
- AI provider errors
- malformed AI output
- missing avatar
- insufficient wardrobe
- failed try-on
- unauthorized resources
- rate limits

If there are not enough garments to produce 3 outfits, return the best available outfits and a helpful message.

Example:

```json
{
  "outfits": [],
  "message": "You don't have enough suitable items for this request."
}
```

---

## 14. Testing Requirements

At minimum:

### Backend unit tests

- Pydantic validation
- style intent parsing
- scoring
- color compatibility
- category compatibility
- repository user isolation
- duplicate outfit prevention

### API tests

- signup/login
- garment upload
- wardrobe listing
- wardrobe search
- stylist generation
- feedback
- try-on job creation

### Security tests

Explicitly test that:

- User A cannot read User B's garment
- User A cannot update User B's garment
- User A cannot read User B's outfit
- User A cannot trigger try-on for User B's avatar/outfit

### Frontend

Test critical user flows:

```text
signup → onboarding → upload garment → wardrobe
wardrobe → stylist → outfit → try-on
```

---

## 15. Environment Variables

Create `.env.example`.

Expected categories:

```text
DATABASE_URL=
JWT_SECRET=
STORAGE_ENDPOINT=
STORAGE_BUCKET=
STORAGE_ACCESS_KEY=
STORAGE_SECRET_KEY=

LLM_PROVIDER=
LLM_API_KEY=
LLM_MODEL=

VISION_PROVIDER=
VISION_API_KEY=
VISION_MODEL=

EMBEDDING_PROVIDER=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
EMBEDDING_DIMENSION=

TRYON_PROVIDER=
TRYON_API_KEY=
```

Never commit actual secrets.

---

## 16. Docker

Local development must work with:

```bash
docker compose up
```

At minimum provide PostgreSQL + pgvector.

Keep external AI providers configurable through environment variables.

---

## 17. Implementation Rules

1. Build incrementally.
2. Keep commits/changes logically separated when possible.
3. Do not rewrite working code unnecessarily.
4. Do not add dependencies without a reason.
5. Prefer simple implementations over premature abstractions.
6. Keep provider-specific code behind interfaces.
7. Validate external input.
8. Validate AI output.
9. Scope database queries by authenticated user.
10. Add tests for non-trivial business logic.
11. Run formatting/linting/type checks where configured.
12. Run tests after meaningful changes.
13. Update README when setup or architecture changes.
14. Keep TODOs explicit.
15. Do not silently change API contracts.

---

## 18. MVP Definition of Done

The MVP is complete when a user can:

1. Create an account.
2. Complete a basic profile.
3. Upload a full-body avatar.
4. Upload clothing images.
5. See uploaded garments in the wardrobe.
6. Have garments automatically categorized.
7. Search the wardrobe semantically.
8. Enter a natural-language styling request.
9. Receive 3–5 outfit suggestions using only owned garments.
10. See an explanation for each suggestion.
11. Like/dislike/save an outfit.
12. Request virtual try-on.
13. See asynchronous try-on status.
14. View the generated try-on result.
15. Never access another user's data.

---

## 19. Priority Order

Implement in this order:

```text
P0
Foundation
Database
Auth
Docker
API structure

P1
Garment upload
Object storage
Wardrobe UI
Garment CRUD

P2
Vision analysis
Embedding generation
pgvector search

P3
StyleIntent
Outfit generation
Scoring
Stylist UI

P4
Feedback
Saved outfits

P5
Avatar
Virtual try-on

P6
Personalization improvements
```

Do not implement P5/P6 before P0–P4 are stable.
