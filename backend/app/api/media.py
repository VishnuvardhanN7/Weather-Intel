from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.report_media import ReportMedia
from app.models.user import User
from app.models.user import UserRole
from app.services.media_service import get_media

router = APIRouter()


def _may_view_media(media, current_user: User | None) -> bool:
    """Weather evidence is public; any visitor can view it."""
    return True


async def _require_media_access(media_id: int, current_user: User | None, db: AsyncSession):
    result = await db.execute(select(ReportMedia).where(ReportMedia.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    return media


@router.get("/{media_id}", response_model=dict)
async def media_metadata(
    media_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Metadata for a stored media item (requires authentication)."""
    media = await _require_media_access(media_id, current_user, db)
    return media.to_dict()


@router.get("/{media_id}/content")
async def media_content(
    media_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Stream weather evidence content.

    Weather event evidence is publicly visible so that citizens and
    analysts can review media without an account.
    """
    media = await _require_media_access(media_id, None, db)

    content_disposition = "inline"
    return Response(
        content=media.data,
        media_type=media.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": content_disposition,
        },
    )
