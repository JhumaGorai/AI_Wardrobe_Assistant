"""Unit tests for the mock embedding provider itself (app/services/embedding/mock.py) -- no DB,
no FastAPI client. Covers the two properties process_garment/Phase 9 actually depend on:
correct, configured dimension (IMPLEMENTATION_PROMPT.md Phase 8: "Verify the returned dimension
equals EMBEDDING_DIMENSION"), and determinism (so re-embedding the same text is stable). Also a
basic sanity check of the hashing-trick's "shared words -> higher similarity" property, so a
regression that turns it back into pure noise doesn't go unnoticed."""
import math

import pytest

from app.core.config import get_settings
from app.services.embedding.mock import MockEmbeddingService

pytestmark = pytest.mark.asyncio


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def test_embed_returns_configured_dimension():
    service = MockEmbeddingService()
    vector = await service.embed("category: top\ndescription: a plain blue top")
    assert len(vector) == get_settings().embedding_dimension


async def test_embed_is_deterministic_for_the_same_text():
    service = MockEmbeddingService()
    text = "category: top\ncolors: blue\ndescription: a plain blue top"
    first = await service.embed(text)
    second = await service.embed(text)
    assert first == second


async def test_embed_similarity_is_higher_for_shared_words_than_unrelated_text():
    service = MockEmbeddingService()
    blue_top = await service.embed("category: top\ncolors: blue\ndescription: a plain blue top")
    blue_shirt = await service.embed("category: top\ncolors: blue\ndescription: a blue button-up shirt")
    red_boots = await service.embed("category: footwear\ncolors: red\ndescription: red leather boots")

    similar_pair = _cosine_similarity(blue_top, blue_shirt)
    unrelated_pair = _cosine_similarity(blue_top, red_boots)

    assert similar_pair > unrelated_pair
