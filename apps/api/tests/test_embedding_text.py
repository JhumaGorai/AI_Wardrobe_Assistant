"""Pure unit tests for app/services/embedding_text.py -- no DB, no provider, no FastAPI client.
CLAUDE.md sec 14 calls out testing non-trivial business logic; the exact text format matters
here because it's what both the mock and a real embedding provider would ultimately encode."""
from types import SimpleNamespace

from app.services.embedding_text import build_embedding_text


def _garment(**overrides) -> SimpleNamespace:
    defaults = dict(
        category=None,
        subcategory=None,
        colors=[],
        pattern=None,
        material=None,
        fit=None,
        formality=None,
        seasons=[],
        style_tags=[],
        description=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_embedding_text_includes_all_filled_fields_in_order():
    garment = _garment(
        category="top",
        subcategory="blouse",
        colors=["cream", "black"],
        pattern="solid",
        material="cotton",
        fit="relaxed",
        formality=0.7,
        seasons=["spring", "summer"],
        style_tags=["minimalist", "elegant", "smart casual"],
        description="relaxed cream blouse with black trim",
    )
    text = build_embedding_text(garment)
    assert text == (
        "category: top\n"
        "subcategory: blouse\n"
        "colors: cream, black\n"
        "pattern: solid\n"
        "material: cotton\n"
        "fit: relaxed\n"
        "formality: 0.7\n"
        "seasons: spring, summer\n"
        "style_tags: minimalist, elegant, smart casual\n"
        "description: relaxed cream blouse with black trim"
    )


def test_build_embedding_text_omits_unset_fields_entirely():
    # A garment where analysis only partially filled things in (or failed partway) should never
    # produce lines like "category: None" -- that would itself become meaningless "content" fed
    # to the embedding provider/mock.
    garment = _garment(category="top", description="a plain top")
    text = build_embedding_text(garment)
    assert text == "category: top\ndescription: a plain top"
    assert "None" not in text


def test_build_embedding_text_empty_garment_returns_empty_string():
    garment = _garment()
    assert build_embedding_text(garment) == ""
