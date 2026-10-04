import logging
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.report_media import ReportMedia
from app.utils.media_validation import validate_media_file

logger = logging.getLogger(__name__)


async def read_and_validate_uploads(files: List[UploadFile]) -> List[dict]:
    """Read every uploaded file into memory and validate it."""
    entries = []
    for file in files or []:
        if not file.filename:
            continue
        data = await file.read()
        try:
            media_type, content_type = validate_media_file(
                file.filename,
                file.content_type,
                data,
                max_size=settings.MAX_UPLOAD_SIZE,
            )
        except ValueError as exc:
            raise HTTPException(status_code=415, detail=str(exc))
        entries.append({
            "filename": file.filename,
            "content_type": content_type,
            "media_type": media_type,
            "data": data,
        })
    return entries


def media_reference(media_id: int) -> str:
    return f"media:{media_id}"


async def store_media(
    db: AsyncSession,
    entries: List[dict],
    event_id: Optional[int] = None,
    uploaded_by_id: Optional[int] = None,
) -> Tuple[List[str], List[str]]:
    """Persist validated media rows and return lists of media references.

    Returns two lists: (photo_references, video_references). Reference format
    is ``media:<id>`` which the API layer resolves to authenticated URLs.
    """
    photos: List[str] = []
    videos: List[str] = []
    for entry in entries:
        media = ReportMedia(
            event_id=event_id,
            uploaded_by_id=uploaded_by_id,
            filename=entry["filename"],
            content_type=entry["content_type"],
            media_type=entry["media_type"],
            size_bytes=len(entry["data"]),
            data=entry["data"],
        )
        db.add(media)
        await db.flush()
        reference = media_reference(media.id)
        if entry["media_type"] == "image":
            photos.append(reference)
        else:
            videos.append(reference)
    return photos, videos


async def get_media(db: AsyncSession, media_id: int) -> Optional[ReportMedia]:
    result = await db.execute(select(ReportMedia).where(ReportMedia.id == media_id))
    return result.scalar_one_or_none()