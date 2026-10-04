"""
AI Engine Abstraction Module for Weather Platform.

Contains modular AI Engines:
- Engine 1: Event Organization (IndicBERT text adapter & CLIP image adapter)
- Engine 2: Fake News Detection (wrapping existing fake_detector)
- Engine 3: Deduplication (wrapping existing deduplicator)
"""

from app.ai.event_organization import (
    BaseEventOrganizationEngine,
    IndicBERTEventOrganizer,
    CLIPEventOrganizer,
    event_organization_engine,
)
from app.ai.fake_news_engine import BaseFakeNewsEngine, fake_news_engine
from app.ai.deduplication_engine import BaseDeduplicationEngine, deduplication_engine

__all__ = [
    "BaseEventOrganizationEngine",
    "IndicBERTEventOrganizer",
    "CLIPEventOrganizer",
    "event_organization_engine",
    "BaseFakeNewsEngine",
    "fake_news_engine",
    "BaseDeduplicationEngine",
    "deduplication_engine",
]
