import re
import logging
from typing import Tuple, List
from collections import Counter

logger = logging.getLogger(__name__)

FAKE_INDICATOR_KEYWORDS = [
    "urgent", "share widely", "forward to everyone", "breaking",
    "just confirmed", "100% true", "government hiding",
    "share before deleted", "whatsapp forwarded", "unverified",
    "please retweet", "help needed urgently", "donation",
    "send money", "click this link", "free money",
    "congratulations", "you won", "claim now",
    "miracle cure", "secret method", "hidden truth",
    "exposed", "conspiracy", "cover up",
    "act now", "limited time", "don't miss",
    "forward to 10 people", "share this immediately",
    "fake", "hoax", "prank", "satire",
]

LEGITIMATE_INDICATOR_KEYWORDS = [
    "imd", "india meteorological department", "weather department",
    "national disaster", "ndrf", "sdrf", "disaster management",
    "official", "confirmed", "measured", "recorded",
    "alert issued", "warning issued", "advisory",
    "government", "state government", "district administration",
    "rainfall recorded", "temperature recorded",
    "flood warning", "evacuation order",
    "according to data", "weather stations", "radar",
    "satellite imagery", "forecast model",
    "emergency services", "relief operations",
]

SUSPICIOUS_PATTERNS = [
    (r"share\s+(this|it)\s+(before|now|widely|everyone)", 0.3),
    (r"forward\s+to\s+\d+\s+people", 0.4),
    (r"click\s+(here|this\s+link)", 0.2),
    (r"send\s+(money|rs|₹|\$)", 0.5),
    (r"won\s+(a\s+)?(prize|lottery|money)", 0.6),
    (r"miracle", 0.3),
    (r"conspiracy", 0.2),
    (r"act\s+now", 0.2),
    (r"\d+%\s+true", 0.3),
    (r"urgent.*share", 0.2),
    (r"deleted\s+(soon|today|tomorrow)", 0.3),
]


class FakeDetector:
    def __init__(self):
        self.confidence_threshold = 0.7
        self.fake_keyword_weights = self._build_keyword_weights()

    def _build_keyword_weights(self) -> dict:
        weights = {}
        for kw in FAKE_INDICATOR_KEYWORDS:
            weights[kw.lower()] = 0.15
        for kw in LEGITIMATE_INDICATOR_KEYWORDS:
            weights[kw.lower()] = -0.12
        return weights

    def predict(self, title: str, description: str) -> Tuple[bool, float]:
        text = f"{title} {description}".lower()
        score = 0.0
        signals = []

        keyword_score, keyword_matches = self._analyze_keywords(text)
        score += keyword_score
        signals.extend(keyword_matches)

        pattern_score, pattern_matches = self._analyze_patterns(text)
        score += pattern_score
        signals.extend(pattern_matches)

        structural_score, structural_signals = self._analyze_structure(title, description)
        score += structural_score
        signals.extend(structural_signals)

        source_score, source_signals = self._analyze_source_credibility(description)
        score += source_score
        signals.extend(source_signals)

        sentiment_score, sentiment_signal = self._analyze_sentiment(text)
        score += sentiment_score
        if sentiment_signal:
            signals.append(sentiment_signal)

        confidence = self._normalize_score(score)

        is_fake = confidence >= self.confidence_threshold

        logger.debug(f"FakeDetector score: {confidence:.3f}, is_fake: {is_fake}, signals: {signals}")
        return is_fake, confidence

    def _analyze_keywords(self, text: str) -> Tuple[float, List[str]]:
        score = 0.0
        matches = []
        words = re.findall(r'\b\w+\b', text)

        for word in words:
            if word in self.fake_keyword_weights:
                w = self.fake_keyword_weights[word]
                score += w
                if abs(w) > 0.1:
                    matches.append(f"keyword:{word}")

        bigrams = []
        tokens = text.split()
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i+1]}"
            if bigram in self.fake_keyword_weights:
                score += self.fake_keyword_weights[bigram]
                matches.append(f"bigram:{bigram}")

        return score, matches

    def _analyze_patterns(self, text: str) -> Tuple[float, List[str]]:
        score = 0.0
        matches = []
        for pattern, weight in SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                score += weight
                matches.append(f"pattern:{pattern[:30]}")
        return score, matches

    def _analyze_structure(self, title: str, description: str) -> Tuple[float, List[str]]:
        score = 0.0
        signals = []

        if len(title) > 150:
            score += 0.1
            signals.append("long_title")
        if title.isupper():
            score += 0.15
            signals.append("all_caps_title")

        exclamation_count = (title + description).count('!')
        if exclamation_count > 3:
            score += 0.1
            signals.append("excessive_exclamation")

        question_marks = (title + description).count('?')
        if question_marks > 2:
            score += 0.05
            signals.append("excessive_questions")

        url_count = len(re.findall(r'https?://\S+', description))
        if url_count > 2:
            score += 0.15
            signals.append("multiple_urls")

        has_emoji = bool(re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF]', title + description))
        if has_emoji:
            score += 0.05
            signals.append("has_emoji")

        return score, signals

    def _analyze_source_credibility(self, description: str) -> Tuple[float, List[str]]:
        score = 0.0
        signals = []
        text = description.lower()

        credible_sources = [
            "imd", "india meteorological", "ndrf", "sdrf",
            "disaster management authority", "met department",
            "weather department", "national disaster",
            "ndma", "state disaster",
        ]
        for source in credible_sources:
            if source in text:
                score -= 0.2
                signals.append(f"credible_source:{source}")
                break

        social_media_mentions = [
            "whatsapp", "facebook", "telegram", "instagram",
            "twitter", "forwarded", "shared",
        ]
        for mention in social_media_mentions:
            if mention in text:
                score += 0.1
                signals.append(f"social_media:{mention}")
                break

        return score, signals

    def _analyze_sentiment(self, text: str) -> Tuple[float, str]:
        fear_words = [
            "scary", "terrifying", "horrifying", "catastrophic",
            "apocalyptic", "end of the world", "biblical",
            "unprecedented", "never before", "worst ever",
        ]
        urgency_words = [
            "urgent", "immediately", "right now", "don't wait",
            "before it's too late", "last chance",
        ]

        fear_count = sum(1 for w in fear_words if w in text)
        urgency_count = sum(1 for w in urgency_words if w in text)

        score = 0.0
        signal = None
        if fear_count > 2:
            score += 0.2
            signal = f"high_fear_sentiment:{fear_count}"
        if urgency_count > 2:
            score += 0.15
            signal = signal or f"high_urgency_sentiment:{urgency_count}"

        return score, signal

    def _normalize_score(self, raw_score: float) -> float:
        import math
        normalized = 1 / (1 + math.exp(-raw_score * 2))
        return max(0.0, min(1.0, normalized))

    def batch_predict(self, events: List[dict]) -> List[dict]:
        results = []
        for event in events:
            is_fake, confidence = self.predict(
                event.get("title", ""),
                event.get("description", ""),
            )
            results.append({
                "is_fake": is_fake,
                "confidence": confidence,
            })
        return results


fake_detector = FakeDetector()