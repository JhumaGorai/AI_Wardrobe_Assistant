"""Image-upload constants shared by every endpoint that accepts an image file (avatar, garment).

Centralized here so both call sites validate identically instead of maintaining two copies that
could silently drift apart. `app/schemas/avatar.py` re-exports the two constants under their
original names so existing imports (routes, tests) keep working unchanged.
"""

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

_EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def extension_for_content_type(content_type: str) -> str:
    return _EXTENSION_BY_CONTENT_TYPE[content_type]
