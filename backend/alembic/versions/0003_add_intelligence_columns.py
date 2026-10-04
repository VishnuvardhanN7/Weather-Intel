"""Add intelligence scoring columns to weather_events

Adds:
  • ``weather_events.incident_id`` — incident clustering group id
  • ``weather_events.verification_score`` — 0-100 verification score
  • ``weather_events.priority_score`` — 0-100 prioritisation score
  • ``weather_events.source_trust_score`` — 0-100 source reliability
  • ``weather_events.data_quality_score`` — 0-100 report completeness
  • ``weather_events.lifecycle`` — NEW/ACTIVE/VERIFIED/RESOLVED/STALE/REJECTED

All statements are idempotent so this can run against the existing Neon
or dev database without destroying data. The values are backfilled lazily
by the intelligence pipeline when an event is read or ingested.

Revision ID: add_intelligence_columns
Revises: add_notifications_media
Create Date: 2026-09-10 01:00:00
"""
from typing import Sequence, Union
from alembic import op

revision: str = "add_intelligence_columns"
down_revision: Union[str, None] = "add_notifications_media"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = [
    "ALTER TABLE weather_events ADD COLUMN IF NOT EXISTS incident_id INTEGER;",
    "ALTER TABLE weather_events ADD COLUMN IF NOT EXISTS verification_score DOUBLE PRECISION DEFAULT 0.0;",
    "ALTER TABLE weather_events ADD COLUMN IF NOT EXISTS priority_score DOUBLE PRECISION DEFAULT 0.0;",
    "ALTER TABLE weather_events ADD COLUMN IF NOT EXISTS source_trust_score DOUBLE PRECISION DEFAULT 0.0;",
    "ALTER TABLE weather_events ADD COLUMN IF NOT EXISTS data_quality_score DOUBLE PRECISION DEFAULT 0.0;",
    "ALTER TABLE weather_events ADD COLUMN IF NOT EXISTS lifecycle VARCHAR(50);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_incident_id ON weather_events (incident_id);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_verification_score ON weather_events (verification_score);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_priority_score ON weather_events (priority_score);",
    "CREATE INDEX IF NOT EXISTS ix_weather_events_lifecycle ON weather_events (lifecycle);",
]


def upgrade() -> None:
    for stmt in UPGRADE_SQL:
        op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_weather_events_lifecycle;")
    op.execute("DROP INDEX IF EXISTS ix_weather_events_priority_score;")
    op.execute("DROP INDEX IF EXISTS ix_weather_events_verification_score;")
    op.execute("DROP INDEX IF EXISTS ix_weather_events_incident_id;")
    op.execute("ALTER TABLE weather_events DROP COLUMN IF EXISTS lifecycle;")
    op.execute("ALTER TABLE weather_events DROP COLUMN IF EXISTS data_quality_score;")
    op.execute("ALTER TABLE weather_events DROP COLUMN IF EXISTS source_trust_score;")
    op.execute("ALTER TABLE weather_events DROP COLUMN IF EXISTS priority_score;")
    op.execute("ALTER TABLE weather_events DROP COLUMN IF EXISTS verification_score;")
    op.execute("ALTER TABLE weather_events DROP COLUMN IF EXISTS incident_id;")