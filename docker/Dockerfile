FROM node:20-alpine AS frontend-build

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /frontend/dist /frontend/dist

RUN mkdir -p /app/uploads
EXPOSE 8000
# Alembic migrations are idempotent (IF NOT EXISTS) so this is safe on both
# fresh and pre-existing databases. Citizen evidence is now stored in
# Postgres (report_media), so the uploads volume is kept only for legacy files.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]