from pathlib import Path
from typing import Optional, Tuple

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB default, mirror settings.MAX_UPLOAD_SIZE

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
}
ALLOWED_VIDEO_CONTENT_TYPES = {
    "video/mp4", "video/x-msvideo", "video/quicktime",
    "video/x-matroska", "video/webm",
}

_MAGIC = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF", b"WEBP"),
    "video/mp4": (b"\x00\x00\x00\x18ftyp",),
    "video/webm": (b"\x1aE\xdf\xa3",),
}


def guess_media_type(filename: str, content_type: Optional[str]) -> Optional[str]:
    ext = Path(filename or "").suffix.lower()
    if ext in ALLOWED_IMAGE_EXTENSIONS:
        return "image"
    if ext in ALLOWED_VIDEO_EXTENSIONS:
        return "video"
    if content_type and content_type in ALLOWED_IMAGE_CONTENT_TYPES:
        return "image"
    if content_type and content_type in ALLOWED_VIDEO_CONTENT_TYPES:
        return "video"
    return None


def _validate_image(data: bytes) -> None:
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data))
        img.verify()
    except ImportError:
        # Pillow unavailable: fall back to magic-byte checks.
        ok = any(data.startswith(sig) for sig in _MAGIC.get("image/jpeg", ())) or \
             any(data.startswith(sig) for sig in _MAGIC.get("image/png", ())) or \
             any(data.startswith(sig) for sig in _MAGIC.get("image/gif", ())) or \
             any(data.startswith(sig) for sig in _MAGIC.get("image/webp", ()))
        if not ok:
            raise ValueError("invalid image payload")


def _video_content_type(data: bytes, content_type: Optional[str], filename: str) -> str:
    ext = Path(filename).suffix.lower()
    for expected, signatures in _MAGIC.items():
        if any(data.startswith(sig) for sig in signatures):
            return expected
    # AVI / MKV / MOV are hard to fingerprint reliably; accept on extension.
    fallback = {
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".mov": "video/quicktime",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
    }
    return content_type or fallback.get(ext, "application/octet-stream")


def validate_media_file(
    filename: str,
    content_type: Optional[str],
    data: bytes,
    max_size: Optional[int] = None,
) -> Tuple[str, str]:
    """Pure validation: returns (media_type, effective_content_type).

    Raises ValueError with a human-readable reason when the file is
    invalid. Kept free of FastAPI imports so it can be unit-tested without
    a running app. The API layer converts ValueError into HTTP 4xx.
    """
    limit = max_size or MAX_UPLOAD_SIZE
    if not filename:
        raise ValueError("File is missing a filename")

    media_type = guess_media_type(filename, content_type)
    if media_type is None:
        raise ValueError(
            "Unsupported file type. Allowed: images "
            f"({', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}) and videos "
            f"({', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))})."
        )

    size = len(data)
    if size > limit:
        raise ValueError(f"File exceeds the maximum size of {limit // (1024 * 1024)} MB")
    if size == 0:
        raise ValueError("File is empty")

    if media_type == "image":
        try:
            _validate_image(data)
        except ValueError:
            raise
        except Exception:
            raise ValueError("Invalid image file")
    else:
        effective_content_type = _video_content_type(data, content_type, filename)
        return media_type, effective_content_type

    # Effective content type for images from Pillow.
    try:
        from PIL import Image
        import io
        fmt = (Image.open(io.BytesIO(data)).format or "").lower()
    except Exception:
        fmt = ""
    mapping = {
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
    }
    if fmt in mapping:
        return media_type, mapping[fmt]
    if content_type in ALLOWED_IMAGE_CONTENT_TYPES:
        return media_type, content_type
    raise ValueError("Unsupported image type")