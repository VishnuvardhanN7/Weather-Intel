import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class NotificationType(str, enum.Enum):
    ALERT = "alert"
    VERIFICATION = "verification"
    SYSTEM = "system"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("weather_events.id"), nullable=True)
    type = Column("type", String(50), nullable=False, default=NotificationType.SYSTEM.value)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(String(50), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", foreign_keys=[user_id])
    event = relationship("WeatherEvent", foreign_keys=[event_id])

    __table_args__ = (
        Index("ix_notifications_user_read", "user_id", "is_read"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }