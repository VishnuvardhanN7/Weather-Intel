import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, LargeBinary, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"


class ReportMedia(Base):
    """Citizen report evidence stored in the database.

    Files are persisted as BYTEA (LargeBinary) so that evidence survives
    container restarts and is only served through an authenticated endpoint.
    """

    __tablename__ = "report_media"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("weather_events.id"), nullable=True, index=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    media_type = Column(String(20), nullable=False)
    size_bytes = Column(Integer, nullable=False, default=0)
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    event = relationship("WeatherEvent", foreign_keys=[event_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "event_id": self.event_id,
            "uploaded_by_id": self.uploaded_by_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "media_type": self.media_type,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "url": f"/api/media/{self.id}/content",
        }