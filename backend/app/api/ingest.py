from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_admin
from app.core.database import get_db
from app.models.user import User
from app.services.ingestion_service import AVAILABLE_SOURCES, run_ingestion

router = APIRouter()


class IngestionRequest(BaseModel):
    sources: List[str] = Field(default=["social", "web", "public_api"])
    use_sample_data: bool = False


@router.get("/sources")
async def available_sources(current_user: User = Depends(get_current_admin)):
    return {"sources": sorted(AVAILABLE_SOURCES)}


@router.post("/run")
async def ingest(
    request: IngestionRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    requested_sources = list(request.sources)
    if any(s.lower() == "all" for s in requested_sources):
        sources_to_run = list(AVAILABLE_SOURCES)
    else:
        sources_to_run = requested_sources

    invalid_sources = set(sources_to_run) - AVAILABLE_SOURCES
    if invalid_sources:
        raise HTTPException(status_code=422, detail=f"Unsupported sources: {', '.join(sorted(invalid_sources))}")
    if not sources_to_run:
        raise HTTPException(status_code=422, detail="Select at least one source")
    return await run_ingestion(db, sources_to_run, request.use_sample_data)
