from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base
from app.api import weather, auth, dashboard, ingest, media, notifications, intelligence, websocket, admin, stories


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="National Weather Big Data Analytics Platform",
    description="Real-time weather event tracking, verification, and analytics for India",
    version="1.0.0",
    lifespan=lifespan,
)

upload_directory = Path(settings.UPLOAD_DIR)
upload_directory.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_directory), name="uploads")

cors_origins = settings.CORS_ORIGINS
allow_all_cors = "*" in cors_origins or "all" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if not allow_all_cors else ["*"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin Source Control"])
app.include_router(weather.router, prefix="/api/weather", tags=["Weather Events"])
app.include_router(stories.router, prefix="/api/stories", tags=["Weather Stories & News"])
app.include_router(media.router, prefix="/api/media", tags=["Report Media"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard & Analytics"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["Data Ingestion"])
app.include_router(intelligence.router, prefix="/api/intelligence", tags=["Intelligence & Explainability"])
app.include_router(websocket.router, tags=["WebSockets"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "national-weather-platform",
        "version": "1.0.0",
    }


@app.get("/api/health", tags=["Health"])
async def api_health_check():
    """Report app, database, and required weather schema health safely."""
    from sqlalchemy import text

    required_columns = {
        "incident_id",
        "verification_score",
        "priority_score",
        "source_trust_score",
        "data_quality_score",
        "lifecycle",
    }
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
            result = await connection.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = current_schema() AND table_name = 'weather_events'"
            ))
            available = {row[0] for row in result}
        missing = sorted(required_columns - available)
        if missing:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "degraded", "database": "reachable", "missing_weather_event_columns": missing},
            )
        return {"status": "healthy", "database": "reachable", "schema": "current"}
    except Exception:
        # Deliberately avoid disclosing a connection string or provider details.
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "degraded", "database": "unreachable"},
        )


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """Serve the compiled React app in the single-container deployment."""
    dist_dir = settings.FRONTEND_DIST_DIR
    requested_file = dist_dir / full_path

    if requested_file.is_file():
        return FileResponse(requested_file)

    index_file = dist_dir / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)

    return {
        "message": "Frontend has not been built. Run npm run dev in frontend/ for development.",
        "docs": "/docs",
    }