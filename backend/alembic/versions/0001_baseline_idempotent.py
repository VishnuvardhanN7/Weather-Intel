"""Baseline: create users and weather_events tables if missing

This baseline is idempotent so it can be stamped against an existing
Neon/PostgreSQL database that was originally created by
``Base.metadata.create_all`` without conflicting with tables that
already exist.

Revision ID: initial_baseline
Revises: none
Create Date: 2026-09-08 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "initial_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(20) NOT NULL DEFAULT 'citizen',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    notification_consent BOOLEAN NOT NULL DEFAULT FALSE,
    notification_lat DOUBLE PRECISION,
    notification_lng DOUBLE PRECISION,
    notification_radius_km DOUBLE PRECISION NOT NULL DEFAULT 25.0,
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email)
);
"""

WEATHER_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS weather_events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    event_type VARCHAR(20) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source VARCHAR(20) NOT NULL,
    source_url VARCHAR(2000),
    source_id VARCHAR(500),
    city VARCHAR(200),
    state VARCHAR(200),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    photos JSON DEFAULT '[]'::json,
    videos JSON DEFAULT '[]'::json,
    metadata JSON DEFAULT '{}'::json,
    verification_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    is_fake BOOLEAN NOT NULL DEFAULT FALSE,
    fake_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    category_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    duplicate_of_id INTEGER,
    reported_by_id INTEGER,
    verified_by_id INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    reported_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_weather_events_duplicate_of FOREIGN KEY (duplicate_of_id)
        REFERENCES weather_events (id),
    CONSTRAINT fk_weather_events_reported_by FOREIGN KEY (reported_by_id)
        REFERENCES users (id),
    CONSTRAINT fk_weather_events_verified_by FOREIGN KEY (verified_by_id)
        REFERENCES users (id)
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_users_id ON users (id);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username);",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);",
    "CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_id ON weather_events (id);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_title ON weather_events (title);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_event_type ON weather_events (event_type);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_severity ON weather_events (severity);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_source ON weather_events (source);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_source_id ON weather_events (source_id);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_city ON weather_events (city);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_state ON weather_events (state);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_verification_status ON weather_events (verification_status);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_is_fake ON weather_events (is_fake);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_reported_at ON weather_events (reported_at);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_location ON weather_events (latitude, longitude);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_type_severity ON weather_events (event_type, severity);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_state_type ON weather_events (state, event_type);",
]


def upgrade() -> None:
    op.execute(USERS_DDL)
    op.execute(WEATHER_EVENTS_DDL)
    for idx in INDEXES:
        op.execute(idx)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS weather_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")
