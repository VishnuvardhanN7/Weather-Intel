import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, Float
from sqlalchemy.orm import relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    CITIZEN = "citizen"
    ANALYST = "analyst"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CITIZEN, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Location-based weather alert preferences (opt-in, self-provided).
    notification_consent = Column(Boolean, default=False, nullable=False)
    notification_lat = Column(Float, nullable=True)
    notification_lng = Column(Float, nullable=True)
    notification_radius_km = Column(Float, default=25.0, nullable=False)

    reported_events = relationship("WeatherEvent", foreign_keys="WeatherEvent.reported_by_id", back_populates="reported_by")
    verified_events = relationship("WeatherEvent", foreign_keys="WeatherEvent.verified_by_id", back_populates="verified_by")

    def to_dict(self, include_password: bool = False):
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value if self.role else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "notification_consent": self.notification_consent,
            "notification_lat": self.notification_lat,
            "notification_lng": self.notification_lng,
            "notification_radius_km": self.notification_radius_km,
        }
        if include_password:
            data["hashed_password"] = self.hashed_password
        return data