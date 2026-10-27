from typing import Protocol


class EmbeddingService(Protocol):
    """CLAUDE.md sec 8 / IMPLEMENTATION_PROMPT.md Phase 8. `model_name` is stored alongside each
    embedding (garment_embeddings.embedding_model) so a later switch of provider/model doesn't
    silently mix incomparable vectors in the same table without a record of which model produced
    which row."""

    model_name: str

    async def embed(self, text: str) -> list[float]:
        ...
