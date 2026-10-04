"""
Incident Clusterer — groups related weather reports into unified incidents.

Clusters reports using:
  - geographic proximity (haversine distance)
  - temporal proximity (time window)
  - event category match
  - semantic similarity (title/description)
  - city/state match
  - source relationship

Built on the existing Deduplicator but adds:
  - incident_id assignment
  - multi-report clustering (not just pairwise dupes)
  - source count tracking
  - cluster confidence
"""

from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime, timedelta
import math, re

INCIDENT_CLUSTERER_VERSION = "incident-clusterer-v1"

DEFAULT_MAX_DISTANCE_KM = 20.0
DEFAULT_TIME_WINDOW_HOURS = 6.0
DEFAULT_SIMILARITY_THRESHOLD = 0.45

# Common English stopwords (shared with deduplicator logic)
_STOPWORDS = {
    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'then', 'else', 'when',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'of', 'in', 'on',
    'at', 'to', 'for', 'with', 'by', 'from', 'as', 'into', 'over', 'under',
    'have', 'has', 'had', 'will', 'would', 'can', 'could', 'should', 'may',
    'might', 'must', 'this', 'that', 'these', 'those', 'it', 'its', 'he',
    'she', 'we', 'they', 'them', 'his', 'her', 'their', 'there', 'here',
}


class IncidentCluster:
    """Represents a cluster of related weather events forming one incident."""

    def __init__(self, primary: Dict[str, Any], cluster_id: int | None = None):
        self.cluster_id = cluster_id
        self.events: List[Dict[str, Any]] = [primary]
        self.primary_event = primary
        self.source_types: Set[str] = {primary.get('source', '') or ''}
        self.created_at = primary.get('reported_at')
        self.updated_at = self.created_at

    def add_event(self, event: Dict[str, Any]):
        self.events.append(event)
        self.source_types.add(event.get('source', '') or '')
        if event.get('reported_at'):
            if not self.updated_at or event['reported_at'] > self.updated_at:
                self.updated_at = event['reported_at']
            if not self.created_at or event['reported_at'] < self.created_at:
                self.created_at = event['reported_at']

    @property
    def report_count(self) -> int:
        return len(self.events)

    @property
    def source_count(self) -> int:
        return len(self.source_types)

    @property
    def is_corroborated(self) -> bool:
        return self.source_count >= 2

    def summarize(self) -> dict:
        primary = self.primary_event
        return {
            "cluster_id": self.cluster_id,
            "title": primary.get('title'),
            "event_type": primary.get('event_type'),
            "city": primary.get('city'),
            "state": primary.get('state'),
            "latitude": primary.get('latitude'),
            "longitude": primary.get('longitude'),
            "severity": primary.get('severity'),
            "report_count": self.report_count,
            "source_count": self.source_count,
            "source_types": sorted(self.source_types),
            "is_corroborated": self.is_corroborated,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "event_ids": [e.get('id') for e in self.events],
        }


class IncidentClusterer:
    def __init__(
        self,
        max_distance_km: float = DEFAULT_MAX_DISTANCE_KM,
        time_window_hours: float = DEFAULT_TIME_WINDOW_HOURS,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ):
        self.max_distance_km = max_distance_km
        self.time_window_hours = time_window_hours
        self.similarity_threshold = similarity_threshold
        self.version = INCIDENT_CLUSTERER_VERSION

    def cluster_events(self, events: List[Dict[str, Any]]) -> List[IncidentCluster]:
        """Group a list of event dicts into incident clusters."""
        events = [e for e in events if e is not None]

        # Sort newest first — earlier events become the primary/anchor
        events.sort(key=lambda e: (e.get('reported_at') or ''), reverse=True)

        clusters: List[IncidentCluster] = []
        assignments: Dict[Any, int] = {}

        for event in events:
            if event.get('id') is not None and event['id'] in assignments:
                continue

            best_cluster = None
            best_similarity = 0.0

            for cluster in clusters:
                if cluster.events[0].get('id') == event.get('id'):
                    continue
                similarity = self._similarity_to_cluster(event, cluster)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_cluster = cluster

            if best_cluster and best_similarity >= self.similarity_threshold:
                best_cluster.add_event(event)
                if event.get('id') is not None:
                    assignments[event['id']] = id(best_cluster)
            else:
                new_cluster = IncidentCluster(event)
                clusters.append(new_cluster)
                if event.get('id') is not None:
                    assignments[event['id']] = id(new_cluster)

        for idx, cluster in enumerate(clusters, start=1):
            cluster.cluster_id = idx

        return clusters

    def _similarity_to_cluster(self, event: Dict[str, Any], cluster: IncidentCluster) -> float:
        """Overall similarity between an event and cluster members."""
        members = cluster.events

        # Geographic proximity
        loc_scores = []
        for member in members:
            loc_scores.append(self._location_similarity(event, member))
        loc_score = max(loc_scores) if loc_scores else 0.0

        # Temporal proximity
        time_scores = []
        for member in members:
            time_scores.append(self._time_similarity(event, member))
        time_score = max(time_scores) if time_scores else 0.0

        # Category match
        cat_match = 1.0 if event.get('event_type') == cluster.primary_event.get('event_type') else (
            0.5 if event.get('event_type') in ('flooding', 'rainfall') and
                   cluster.primary_event.get('event_type') in ('flooding', 'rainfall')
            else 0.0
        )

        # Semantic text similarity
        text_scores = []
        for member in members:
            text_scores.append(self._text_similarity(event.get('title') or '', member.get('title') or ''))
        text_score = max(text_scores) if text_scores else 0.0

        # Weighted combination
        weight = {
            'location': 0.35,
            'time': 0.20,
            'category': 0.15,
            'text': 0.30,
        }
        return (
            loc_score * weight['location']
            + time_score * weight['time']
            + cat_match * weight['category']
            + text_score * weight['text']
        )

    def _location_similarity(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        lat1, lng1 = a.get('latitude'), a.get('longitude')
        lat2, lng2 = b.get('latitude'), b.get('longitude')

        if lat1 is not None and lng1 is not None and lat2 is not None and lng2 is not None:
            dist = self._haversine(lat1, lng1, lat2, lng2)
            return max(0.0, 1.0 - dist / self.max_distance_km)

        city1 = (a.get('city') or '').lower().strip()
        city2 = (b.get('city') or '').lower().strip()
        if city1 and city2 and city1 == city2:
            return 0.8
        state1 = (a.get('state') or '').lower().strip()
        state2 = (b.get('state') or '').lower().strip()
        if state1 and state2 and state1 == state2:
            return 0.5
        return 0.0

    def _time_similarity(self, a: Dict[str, Any], b: Dict[str, Any]) -> float:
        t1 = self._parse_dt(a.get('reported_at'))
        t2 = self._parse_dt(b.get('reported_at'))
        if t1 is None or t2 is None:
            return 0.0
        diff_hours = abs((t2 - t1).total_seconds() / 3600)
        return max(0.0, 1.0 - diff_hours / self.time_window_hours)

    def _text_similarity(self, text1: str, text2: str) -> float:
        t1 = self._tokenize(text1)
        t2 = self._tokenize(text2)
        if not t1 or not t2:
            return 0.0
        set1, set2 = set(t1), set(t2)
        jaccard = len(set1 & set2) / len(set1 | set2)

        big1 = set(zip(t1, t1[1:]))
        big2 = set(zip(t2, t2[1:]))
        bigram_jaccard = len(big1 & big2) / len(big1 | big2) if (big1 or big2) else 0.0

        return 0.6 * jaccard + 0.4 * bigram_jaccard

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        return [t for t in text.split() if t not in _STOPWORDS and len(t) > 2]

    def _parse_dt(self, value) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
            except Exception:
                return None
        return None

    def _haversine(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlng / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    async def find_related_reports(
        self,
        db,
        event,
        max_distance_km: float = None,
        time_window_hours: float = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Find existing events related to the given event using database query
        candidates + in-memory scoring. Returns related event dicts sorted by
        similarity, highest first.
        """
        from sqlalchemy import select, or_, and_, func
        from app.models.weather_event import WeatherEvent

        dist_km = max_distance_km or self.max_distance_km
        window_h = time_window_hours or self.time_window_hours

        event_lat = getattr(event, 'latitude', None)
        event_lng = getattr(event, 'longitude', None)
        event_time = getattr(event, 'reported_at', None)
        event_state = getattr(event, 'state', None)
        event_type = getattr(event, 'event_type', None)

        conditions = [WeatherEvent.id != getattr(event, 'id', -1)]
        if event_state:
            conditions.append(WeatherEvent.state == event_state)
        if event_type:
            conditions.append(WeatherEvent.event_type == event_type)

        if event_time is not None:
            start = event_time - timedelta(hours=window_h)
            end = event_time + timedelta(hours=window_h)
            conditions.append(WeatherEvent.reported_at.between(start, end))

        if event_lat is not None and event_lng is not None:
            lat_range = dist_km / 111.0
            lng_range = dist_km / (111.0 * math.cos(math.radians(event_lat)) or 1)
            conditions.append(WeatherEvent.latitude.between(event_lat - lat_range, event_lat + lat_range))
            conditions.append(WeatherEvent.longitude.between(event_lng - lng_range, event_lng + lng_range))

        query = select(WeatherEvent).where(and_(*conditions)).limit(limit)
        result = await db.execute(query)
        candidates = result.scalars().all()

        scored = []
        for candidate in candidates:
            sim = self._similarity_to_cluster(
                self._event_to_dict(event),
                self._event_to_dict(candidate),
            )
            if sim >= self.similarity_threshold:
                scored.append((sim, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [dict({"similarity": round(sim, 3)}, **self._event_to_dict(cand)) for sim, cand in scored[:10]]

    def _event_to_dict(self, event) -> dict:
        from app.models.weather_event import WeatherEvent
        if isinstance(event, dict):
            return event
        return {
            "id": getattr(event, 'id', None),
            "title": getattr(event, 'title', ''),
            "description": getattr(event, 'description', ''),
            "event_type": getattr(event, 'event_type', None),
            "severity": getattr(event, 'severity', None),
            "source": getattr(event, 'source', None),
            "city": getattr(event, 'city', None),
            "state": getattr(event, 'state', None),
            "latitude": getattr(event, 'latitude', None),
            "longitude": getattr(event, 'longitude', None),
            "reported_at": getattr(event, 'reported_at', None),
            "verification_status": getattr(event, 'verification_status', None),
        }


incident_clusterer = IncidentClusterer()