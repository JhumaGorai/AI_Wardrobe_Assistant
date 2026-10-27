"""Builds the textual representation of a garment that gets embedded (CLAUDE.md sec 8 /
IMPLEMENTATION_PROMPT.md Phase 8). Deliberately a pure function with no DB/provider knowledge --
easy to unit test on its own (tests/test_embedding_text.py), and the same text format is used
both when an embedding is first generated and (if needed later) when re-generating one after an
edit, so the two can never drift apart.

Format matches the example in CLAUDE.md sec 8 / IMPLEMENTATION_PROMPT.md Phase 8 line-for-line:
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
Fields the garment doesn't have a value for (e.g. analysis failed to fill one in) are omitted
from the text entirely rather than printed as "category: None" -- that would otherwise become a
token the hashing-trick mock (and a real embedding model) would treat as meaningful content.
"""
from typing import Any


def build_embedding_text(garment: Any) -> str:
    lines: list[str] = []

    if garment.category:
        lines.append(f"category: {garment.category}")
    if garment.subcategory:
        lines.append(f"subcategory: {garment.subcategory}")
    if garment.colors:
        lines.append(f"colors: {', '.join(garment.colors)}")
    if garment.pattern:
        lines.append(f"pattern: {garment.pattern}")
    if garment.material:
        lines.append(f"material: {garment.material}")
    if garment.fit:
        lines.append(f"fit: {garment.fit}")
    if garment.formality is not None:
        lines.append(f"formality: {float(garment.formality)}")
    if garment.seasons:
        lines.append(f"seasons: {', '.join(garment.seasons)}")
    if garment.style_tags:
        lines.append(f"style_tags: {', '.join(garment.style_tags)}")
    if garment.description:
        lines.append(f"description: {garment.description}")

    return "\n".join(lines)
