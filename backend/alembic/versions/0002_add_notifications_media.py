"""Add notifications, report_media and user location columns

Adds:
  • ``users.notification_consent / notification_lat / notification_lng /
    notification_radius_km`` — opt-in location-based alerts
  • ``notifications`` table — persisted bell / drawer source
  • ``report_media`` table — citizen evidence stored in the database

All statements are idempotent (``IF NOT EXISTS``) so the migration can
be run against an existing Neon database that was originally bootstrapped
with ``Base.metadata.create_all`` without destroying data or failing
when tables already exist.

Revision ID: add_notifications_media
Revises: initial_baseline
Create Date: 2026-09-08 01:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "add_notifications_media"
down_revision: Union[str, None] = "initial_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_SQL = [
    # ----------------------------------------------------------------
    # User location columns (may already exist on dev DB)
    # ----------------------------------------------------------------
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_consent BOOLEAN NOT NULL DEFAULT FALSE;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_lat DOUBLE PRECISION;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_lng DOUBLE PRECISION;",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS notification_radius_km DOUBLE PRECISION NOT NULL DEFAULT 25.0;",

    # ----------------------------------------------------------------
    # Notifications table
    # ----------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL,
        event_id INTEGER,
        type VARCHAR(50) NOT NULL DEFAULT 'system',
        title VARCHAR(500) NOT NULL,
        message TEXT NOT NULL,
        severity VARCHAR(50),
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users (id),
        CONSTRAINT fk_notifications_event FOREIGN KEY (event_id) REFERENCES weather_events (id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_notifications_id ON notifications (id);",
    "CREATE INDEX IF NOT EXISTS ix_notifications_user_id ON notifications (user_id);",
    "CREATE INDEX IF NOT EXISTS ix_notifications_created_at ON notifications (created_at);",
    "CREATE INDEX IF NOT EXISTS ix_notifications_user_read ON notifications (user_id, is_read);",

    # ----------------------------------------------------------------
    # Report media table (DB-backed evidence)
    # ----------------------------------------------------------------
    """
    CREATE TABLE IF NOT EXISTS report_media (
        id SERIAL PRIMARY KEY,
        event_id INTEGER,
        uploaded_by_id INTEGER,
        filename VARCHAR(255) NOT NULL,
        content_type VARCHAR(100) NOT NULL,
        media_type VARCHAR(20) NOT NULL,
        size_bytes INTEGER NOT NULL DEFAULT 0,
        data BYTEA NOT NULL,
        created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_report_media_event FOREIGN KEY (event_id) REFERENCES weather_events (id),
        CONSTRAINT fk_report_media_uploaded_by FOREIGN KEY (uploaded_by_id) REFERENCES users (id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_report_media_id ON report_media (id);",
    "CREATE INDEX IF NOT EXISTS ix_report_media_event_id ON report_media (event_id);",
    "CREATE INDEX IF NOT EXISTS ix_report_media_uploaded_by_id ON report_media (uploaded_by_id);",
]


def upgrade() -> None:
    for stmt in UPGRADE_SQL:
        op.execute(stmt)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS report_media;")
    op.execute("DROP TABLE IF EXISTS notifications;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS notification_radius_km;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS notification_lng;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS notification_lat;")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS notification_consent;")
