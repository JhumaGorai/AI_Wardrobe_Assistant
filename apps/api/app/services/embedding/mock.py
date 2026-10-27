"""Mock embedding provider -- no real AI/API key required (user's explicit "mocks for now"
choice), same spirit as app/services/vision/mock.py.

Unlike the vision mock (which only needs to be deterministic, not semantically meaningful --
nothing downstream compares two analyses to each other), this one backs real pgvector cosine
search (Phase 9), so pure random noise per text would make every semantic search look broken:
unrelated garments would end up equally "similar" to a query, purely by chance. Instead this
uses the classic feature-hashing trick -- a standard, legitimate technique (not just a stopgap):
hash each word into one of `dim` buckets with a pseudo-random sign, sum, then normalize. Two
texts that share words get positive cosine similarity; texts sharing no words tend toward ~0
similarity (not guaranteed orthogonal, but statistically small at typical embedding dimensions).
This is NOT a real semantic embedding -- "elegant" and "sophisticated" won't be considered
similar unless they literally share a token -- but it gives directionally sensible, demoable
search behavior instead of noise, while staying deterministic and provider-free.
"""
import hashlib
import math
import re

from app.core.config import get_settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _token_bucket(token: str, dim: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % dim


def _token_sign(token: str) -> float:
    digest = hashlib.sha256((token + ":sign").encode("utf-8")).hexdigest()
    return 1.0 if int(digest, 16) % 2 == 0 else -1.0


class MockEmbeddingService:
    model_name = "mock-hashing-embedding-v1"

    async def embed(self, text: str) -> list[float]:
        dim = get_settings().embedding_dimension
        vector = [0.0] * dim
        for token in _TOKEN_RE.findall(text.lower()):
            idx = _token_bucket(token, dim)
            vector[idx] += _token_sign(token)

        norm = math.sqrt(sum(component * component for component in vector))
        if norm == 0.0:
            # Empty/unrecognized text (e.g. all punctuation) -- return a zero vector rather than
            # dividing by zero. A garment with no usable text still gets *some* vector so storage
            # never fails; it just won't be near anything in cosine space (cosine distance from
            # the zero vector is conventionally treated as orthogonal/undefined by pgvector,
            # which is an acceptable edge case here).
            return vector
        return [component / norm for component in vector]
