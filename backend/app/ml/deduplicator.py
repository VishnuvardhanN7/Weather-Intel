import logging
import math
import re
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from collections import Counter

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weather_event import WeatherEvent
from app.core.config import settings

logger = logging.getLogger(__name__)


class Deduplicator:
    def __init__(self):
        self.distance_threshold_km = settings.DUPLICATE_DISTANCE_KM
        self.time_window_hours = settings.DUPLICATE_TIME_WINDOW_HOURS
        self.text_similarity_threshold = 0.6

    async def find_duplicate(self, db: AsyncSession, event: WeatherEvent) -> Optional[WeatherEvent]:
        candidates = await self._get_candidates(db, event)

        for candidate in candidates:
            similarity = self._calculate_similarity(event, candidate)
            if similarity >= self.text_similarity_threshold:
                logger.info(f"Duplicate found: event {event.id} -> candidate {candidate.id} (similarity: {similarity:.3f})")
                return candidate

        return None

    async def _get_candidates(self, db: AsyncSession, event: WeatherEvent) -> List[WeatherEvent]:
        time_window = timedelta(hours=self.time_window_hours)

        query = select(WeatherEvent).where(
            WeatherEvent.id != (event.id or 0),
            WeatherEvent.is_fake == False,
        )

        if event.reported_at:
            query = query.where(
                WeatherEvent.reported_at >= event.reported_at - time_window,
                WeatherEvent.reported_at <= event.reported_at + time_window,
            )

        if event.state:
            query = query.where(WeatherEvent.state == event.state)

        if event.latitude and event.longitude:
            lat_range = self.distance_threshold_km / 111.0
            lon_range = self.distance_threshold_km / (111.0 * math.cos(math.radians(event.latitude)))
            query = query.where(
                WeatherEvent.latitude.isnot(None),
                WeatherEvent.latitude >= event.latitude - lat_range,
                WeatherEvent.latitude <= event.latitude + lat_range,
                WeatherEvent.longitude >= event.longitude - lon_range,
                WeatherEvent.longitude <= event.longitude + lon_range,
            )

        if event.event_type:
            query = query.where(WeatherEvent.event_type == event.event_type)

        query = query.limit(20)
        result = await db.execute(query)
        return list(result.scalars().all())

    def _calculate_similarity(self, event: WeatherEvent, candidate: WeatherEvent) -> float:
        scores = []

        if event.latitude and event.longitude and candidate.latitude and candidate.longitude:
            dist = self._haversine_distance(
                event.latitude, event.longitude,
                candidate.latitude, candidate.longitude
            )
            location_score = max(0, 1 - (dist / self.distance_threshold_km))
            scores.append(("location", location_score, 0.3))

        if event.reported_at and candidate.reported_at:
            time_diff = abs((event.reported_at - candidate.reported_at).total_seconds()) / 3600
            time_score = max(0, 1 - (time_diff / self.time_window_hours))
            scores.append(("time", time_score, 0.2))

        text_score = self._text_similarity(event.title, candidate.title)
        scores.append(("title", text_score, 0.25))

        desc_score = self._text_similarity(event.description, candidate.description)
        scores.append(("description", desc_score, 0.15))

        if event.event_type and candidate.event_type:
            type_score = 1.0 if event.event_type == candidate.event_type else 0.0
            scores.append(("type", type_score, 0.1))

        if not scores:
            return 0.0

        weighted_sum = sum(score * weight for _, score, weight in scores)
        total_weight = sum(weight for _, _, weight in scores)

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _text_similarity(self, text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0

        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        jaccard = len(intersection) / len(union) if union else 0.0

        bigrams1 = set(self._get_bigrams(text1))
        bigrams2 = set(self._get_bigrams(text2))
        if bigrams1 and bigrams2:
            bigram_intersection = bigrams1 & bigrams2
            bigram_union = bigrams1 | bigrams2
            bigram_jaccard = len(bigram_intersection) / len(bigram_union) if bigram_union else 0.0
        else:
            bigram_jaccard = 0.0

        return 0.6 * jaccard + 0.4 * bigram_jaccard

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
            'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
            'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
            'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
            'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
            'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'and', 'but', 'or', 'if', 'while', 'that', 'this', 'these', 'those',
        }
        tokens = text.split()
        return [t for t in tokens if t not in stop_words and len(t) > 2]

    def _get_bigrams(self, text: str) -> List[str]:
        tokens = self._tokenize(text)
        return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]

    async def find_all_duplicates(self, db: AsyncSession) -> List[dict]:
        result = await db.execute(
            select(WeatherEvent)
            .where(WeatherEvent.duplicate_of_id.isnot(None))
            .order_by(WeatherEvent.created_at.desc())
            .limit(500)
        )
        duplicates = result.scalars().all()

        groups = {}
        for dup in duplicates:
            if dup.duplicate_of_id not in groups:
                groups[dup.duplicate_of_id] = []
            groups[dup.duplicate_of_id].append(dup.to_dict())

        return [
            {"original_id": orig_id, "duplicates": dups}
            for orig_id, dups in groups.items()
        ]


deduplicator = Deduplicator()