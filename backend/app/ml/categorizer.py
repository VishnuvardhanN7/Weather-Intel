"""
Hybrid Weather Event Categorizer
---------------------------------
Classifies weather reports into:

    rainfall
    thunderstorm
    flooding
    heatwave
    fog
    dust_storm
    strong_winds
    cyclone
    other

Designed for:
- Social media reports
- IMD-related posts
- OpenWeather observations
- Citizen reports
- English + common Hindi/Hinglish weather terms
- Hashtags
- Disaster/event severity detection
"""

import re
import logging
from typing import Tuple, Optional, List

logger = logging.getLogger(__name__)


# ============================================================
# WEATHER EVENT PATTERNS
# ============================================================

WEATHER_PATTERNS = {

    # --------------------------------------------------------
    # RAINFALL
    # --------------------------------------------------------
    "rainfall": [
        # English
        "rain",
        "rainfall",
        "raining",
        "rainy",
        "heavy rain",
        "heavy rainfall",
        "light rain",
        "light rainfall",
        "moderate rain",
        "moderate rainfall",
        "continuous rain",
        "continuous rainfall",
        "intense rain",
        "intense rainfall",
        "very heavy rain",
        "very heavy rainfall",
        "downpour",
        "showers",
        "rain showers",
        "precipitation",
        "monsoon",
        "cloudburst",
        "rain alert",
        "rain warning",
        "rainfall recorded",
        "mm rainfall",

        # Hinglish
        "baarish",
        "barish",
        "tez baarish",
        "tez barish",
        "bhari baarish",
        "bhari barish",
        "musaldhar baarish",
        "musaldhar barish",
        "lagatar baarish",
        "lagatar barish",
        "tez barish",

        # Hindi
        "बारिश",
        "वर्षा",
        "भारी बारिश",
        "तेज बारिश",
        "मूसलाधार बारिश",
        "लगातार बारिश",
        "वर्षा की संभावना",
        "भारी वर्षा",
        "तेज वर्षा",
        "मूसलाधार वर्षा",
    ],

    # --------------------------------------------------------
    # THUNDERSTORM
    # --------------------------------------------------------
    "thunderstorm": [
        "thunderstorm",
        "thunder storm",
        "thunder",
        "lightning",
        "electrical storm",
        "thunder and lightning",
        "lightning strike",
        "thunder clap",
        "thunderclap",
        "storm lightning",
        "thunderstorm warning",
        "thunderstorm alert",
        "severe thunderstorm",

        # Hindi / Hinglish
        "आंधी तूफान",
        "बिजली गिरने",
        "आकाशीय बिजली",
        "गरज",
        "गरज के साथ",
        "बिजली चमक",
        "गरज चमक",
        "aandhi",
        "andhi",
        "bijli girne",
        "bijli chamak",
        "garaj",
        "garaj chamak",
    ],

    # --------------------------------------------------------
    # FLOODING
    # --------------------------------------------------------
    "flooding": [
        # English
        "flood",
        "flooding",
        "flooded",
        "flash flood",
        "flash flooding",
        "flash floods",
        "flood water",
        "floodwater",
        "flood waters",
        "inundated",
        "inundation",
        "submerged",
        "submergence",
        "overflow",
        "river overflow",
        "river overflowing",
        "water level rising",
        "water level increased",
        "rising water level",
        "roads flooded",
        "road flooded",
        "streets flooded",
        "roads submerged",
        "road submerged",
        "streets submerged",
        "flood affected",
        "flood affected area",
        "flood warning",
        "flood alert",
        "flood emergency",
        "relief camp",
        "embankment breach",
        "embankment breached",
        "dam overflow",
        "dam breach",
        "dam breached",
        "river breached",
        "urban flood",
        "urban flooding",
        "waterlogging",
        "water logged",
        "waterlogged",
        "severe waterlogging",
        "water entered homes",
        "water entered houses",
        "homes flooded",
        "houses flooded",
        "city submerged",
        "village submerged",
        "flood waters entered homes",
        "floodwater entered homes",

        # Hinglish
        "baadh",
        "baadh ka paani",
        "baadh ki sthiti",
        "baadh ka khatra",
        "baadh prabhavit",
        "baadhgrast",
        "jalbharav",
        "paani bhar gaya",
        "sadak par paani",
        "sadkein doob gayi",
        "sadakein doob gayi",
        "ghar mein paani",
        "ghar me paani",
        "nadi ufaan",
        "nadi ufaan par",
        "nadi ka paani badha",

        # Hindi
        "बाढ़",
        "बाढ़ का पानी",
        "बाढ़ की स्थिति",
        "बाढ़ का खतरा",
        "बाढ़ प्रभावित",
        "बाढ़ग्रस्त",
        "जलभराव",
        "जलभराव की स्थिति",
        "जलमग्न",
        "पानी भर गया",
        "पानी भर गया है",
        "सड़क पर पानी",
        "सड़कों पर पानी",
        "सड़कें जलमग्न",
        "सड़कें डूब गई",
        "सड़कें डूब गईं",
        "घर में पानी",
        "घरों में पानी",
        "नदी का जलस्तर",
        "नदी उफान",
        "नदी उफान पर",
        "नदी का पानी बढ़ा",
        "बाढ़ का खतरा",
        "नदी में उफान",
    ],

    # --------------------------------------------------------
    # HEATWAVE
    # --------------------------------------------------------
    "heatwave": [
        "heatwave",
        "heat wave",
        "extreme heat",
        "severe heat",
        "intense heat",
        "scorching heat",
        "blistering heat",
        "temperature rise",
        "temperature soared",
        "temperature exceeded",
        "record temperature",
        "highest temperature",
        "heat alert",
        "heat warning",
        "heatwave warning",
        "heat stroke",
        "heatstroke",
        "dehydration",
        "very hot",
        "extremely hot",

        # Hindi / Hinglish
        "लू",
        "हीटवेव",
        "भीषण गर्मी",
        "तेज गर्मी",
        "गर्मी की लहर",
        "गर्मी बढ़ी",
        "लू का प्रकोप",
        "loo",
        "garmi",
        "bhishan garmi",
        "tez garmi",
    ],

    # --------------------------------------------------------
    # FOG
    # --------------------------------------------------------
    "fog": [
        "fog",
        "foggy",
        "dense fog",
        "thick fog",
        "heavy fog",
        "mist",
        "misty",
        "reduced visibility",
        "low visibility",
        "poor visibility",
        "zero visibility",
        "visibility dropped",
        "fog warning",
        "fog advisory",
        "dense fog warning",

        # Hindi / Hinglish
        "कोहरा",
        "घना कोहरा",
        "धुंध",
        "दृश्यता कम",
        "कम दृश्यता",
        "kohra",
        "ghana kohra",
        "dhund",
        "kam drishyata",
    ],

    # --------------------------------------------------------
    # DUST STORM
    # --------------------------------------------------------
    "dust_storm": [
        "dust storm",
        "duststorm",
        "sandstorm",
        "sand storm",
        "blowing dust",
        "dust haze",
        "dust cloud",
        "dust devil",
        "windblown dust",
        "dust storm warning",
        "dust storm alert",

        # Hindi / Hinglish
        "धूल भरी आंधी",
        "धूल का तूफान",
        "धूल भरी हवा",
        "रेतीला तूफान",
        "धूल उड़ना",
        "dhool bhari aandhi",
        "dhool bhari andhi",
        "dhool ka toofan",
    ],

    # --------------------------------------------------------
    # STRONG WINDS
    # --------------------------------------------------------
    "strong_winds": [
        # IMPORTANT:
        # Do NOT include generic "wind".
        # Normal OpenWeather wind measurements must remain "other".

        "strong wind",
        "strong winds",
        "high wind",
        "high winds",
        "gust",
        "gusts",
        "strong gust",
        "strong gusts",
        "gusty winds",
        "very strong winds",
        "powerful winds",
        "damaging winds",
        "wind damage",
        "windstorm",
        "gale",
        "gale force",
        "squall",
        "storm force winds",
        "uprooted trees",
        "trees uprooted",
        "roofs blown",
        "wind warning",
        "high wind warning",

        # Hindi / Hinglish
        "तेज हवाएं",
        "तेज हवा",
        "आंधी",
        "जोरदार हवाएं",
        "जोरदार हवा",
        "हवा की रफ्तार तेज",
        "तेज रफ्तार हवाएं",
        "tez hawa",
        "tez hawayein",
        "aandhi",
        "andhi",
    ],

    # --------------------------------------------------------
    # CYCLONE
    # --------------------------------------------------------
    "cyclone": [
        "cyclone",
        "cyclonic storm",
        "severe cyclonic storm",
        "tropical cyclone",
        "tropical storm",
        "hurricane",
        "typhoon",
        "deep depression",
        "cyclone warning",
        "cyclone alert",
        "cyclone landfall",
        "storm surge",
        "eye of the storm",
        "landfall",
        "cyclonic circulation",

        # Hindi / Hinglish
        "चक्रवात",
        "चक्रवाती तूफान",
        "चक्रवात की चेतावनी",
        "चक्रवात का खतरा",
        "chakravaat",
        "chakravat",
        "cyclone alert",
    ],
}


# ============================================================
# SEVERITY PATTERNS
# ============================================================

SEVERITY_PATTERNS = {

    # --------------------------------------------------------
    # CRITICAL
    # --------------------------------------------------------
    "critical": [
        "catastrophic",
        "devastating",
        "disaster",
        "massive flooding",
        "extreme flooding",
        "catastrophic flooding",
        "flash flood",
        "flash flooding",
        "death",
        "deaths",
        "killed",
        "destroyed",
        "submerged completely",
        "evacuation order",
        "emergency",
        "flood emergency",
        "red alert",
        "extremely severe",
        "severe cyclonic storm",
        "unprecedented",
        "historic disaster",
        "dam breach",
        "dam breached",
        "embankment breach",
        "embankment breached",
        "river breached",
        "severe flooding",
        "critical flooding",

        # Hindi
        "बाढ़ आपातकाल",
        "लाल चेतावनी",
        "निकासी आदेश",
        "निकासी",
        "तबाही",
        "भयंकर बाढ़",
        "गंभीर बाढ़",
    ],

    # --------------------------------------------------------
    # HIGH
    # --------------------------------------------------------
    "high": [
        "heavy rain",
        "heavy rainfall",
        "very heavy rain",
        "very heavy rainfall",
        "intense rain",
        "intense rainfall",
        "flood",
        "flooding",
        "flooded",
        "flash flood",
        "inundated",
        "inundation",
        "submerged",
        "waterlogging",
        "severe waterlogging",
        "cyclone",
        "cyclonic storm",
        "storm surge",
        "landfall",
        "strong winds",
        "damaging winds",
        "severe thunderstorm",
        "severe",
        "major",
        "dangerous",
        "warning",
        "orange alert",
        "evacuation",
        "significant damage",
        "river overflow",
        "rising water level",

        # Hindi / Hinglish
        "भारी बारिश",
        "मूसलाधार बारिश",
        "तेज बारिश",
        "बाढ़",
        "जलमग्न",
        "जलभराव",
        "गंभीर",
        "खतरा",
    ],

    # --------------------------------------------------------
    # MODERATE
    # --------------------------------------------------------
    "moderate": [
        "moderate",
        "moderate rain",
        "moderate rainfall",
        "affected",
        "impact",
        "damage",
        "disruption",
        "watch",
        "advisory",
        "caution",
        "alert",
        "rain alert",
        "weather warning",
        "yellow alert",
    ],

    # --------------------------------------------------------
    # LOW
    # --------------------------------------------------------
    "low": [
        "light rain",
        "light rainfall",
        "drizzle",
        "mild",
        "minor",
        "slight",
        "normal",
        "expected",
        "forecast",
        "possible",
        "chance of rain",
        "partly cloudy",
        "cloudy",
        "clear sky",
    ],
}


# ============================================================
# NORMAL / NON-EVENT WEATHER
# ============================================================

NORMAL_WEATHER_PATTERNS = [
    "clear sky",
    "clear skies",
    "few clouds",
    "scattered clouds",
    "broken clouds",
    "overcast",
    "cloudy",
    "partly cloudy",
    "mostly cloudy",
    "fair weather",
    "normal weather",
    "temperature",
    "wind speed",
    "humidity",
    "pressure",
    "visibility",
    "feels like",
]


# ============================================================
# CATEGORIZER
# ============================================================

class Categorizer:
    """
    Hybrid rule-based weather event classifier.

    Returns:
        Tuple[event_type, confidence]

    Example:
        ("rainfall", 0.98)
        ("flooding", 0.95)
        (None, 0.0)
    """

    def __init__(self):
        self.patterns = WEATHER_PATTERNS
        self.severity_patterns = SEVERITY_PATTERNS

    # ========================================================
    # PUBLIC API
    # ========================================================

    def categorize(
        self,
        title: str,
        description: str
    ) -> Tuple[Optional[str], float]:

        text = self._normalize_text(
            f"{title or ''} {description or ''}"
        )

        if not text.strip():
            return None, 0.0

        # ----------------------------------------------------
        # 1. Calculate category scores
        # ----------------------------------------------------

        scores = {}

        for category, patterns in self.patterns.items():

            score = self._category_score(
                text,
                patterns
            )

            if score > 0:
                scores[category] = score

        # ----------------------------------------------------
        # 2. No weather event detected
        # ----------------------------------------------------

        if not scores:
            return None, 0.0

        # ----------------------------------------------------
        # 3. Cyclone gets highest priority
        # ----------------------------------------------------

        if self._contains_any(
            text,
            self.patterns["cyclone"]
        ):

            cyclone_score = scores.get(
                "cyclone",
                0
            )

            if cyclone_score > 0:

                confidence = min(
                    0.85 + cyclone_score * 0.05,
                    1.0
                )

                return (
                    "cyclone",
                    round(confidence, 3)
                )

        # ----------------------------------------------------
        # 4. Flooding gets priority over rainfall
        # ----------------------------------------------------
        #
        # Example:
        # "Heavy rain caused flooding"
        #
        # Actual incident = flooding.
        # ----------------------------------------------------

        if self._contains_any(
            text,
            self.patterns["flooding"]
        ):

            flood_score = scores.get(
                "flooding",
                0
            )

            confidence = self._score_to_confidence(
                flood_score
            )

            return (
                "flooding",
                round(confidence, 3)
            )

        # ----------------------------------------------------
        # 5. Select highest scoring category
        # ----------------------------------------------------

        best_category = max(
            scores,
            key=scores.get
        )

        best_score = scores[best_category]

        # ----------------------------------------------------
        # 6. Resolve common category conflicts
        # ----------------------------------------------------

        best_category = self._resolve_conflicts(
            text,
            best_category,
            scores
        )

        confidence = self._score_to_confidence(
            scores.get(
                best_category,
                best_score
            )
        )

        # ----------------------------------------------------
        # 7. Ignore normal observations
        # ----------------------------------------------------

        if self._is_normal_observation(
            text,
            best_category
        ):
            return None, 0.0

        return (
            best_category,
            round(confidence, 3)
        )

    # ========================================================
    # CATEGORY SCORING
    # ========================================================

    def _category_score(
        self,
        text: str,
        patterns: List[str]
    ) -> float:

        score = 0.0

        for pattern in patterns:

            pattern_lower = pattern.lower()

            if pattern_lower not in text:
                continue

            words = pattern_lower.split()

            # More specific phrases get higher weight.
            if len(words) >= 4:
                score += 4.0

            elif len(words) == 3:
                score += 3.0

            elif len(words) == 2:
                score += 2.0

            else:
                score += 1.0

        return score

    # ========================================================
    # CONFIDENCE
    # ========================================================

    def _score_to_confidence(
        self,
        score: float
    ) -> float:

        if score <= 0:
            return 0.0

        if score >= 6:
            return 0.98

        if score >= 4:
            return 0.95

        if score >= 3:
            return 0.90

        if score >= 2:
            return 0.80

        return 0.65

    # ========================================================
    # CONFLICT RESOLUTION
    # ========================================================

    def _resolve_conflicts(
        self,
        text: str,
        best_category: str,
        scores: dict
    ) -> str:

        # ----------------------------------------------------
        # Flooding > Rainfall
        # ----------------------------------------------------

        if (
            scores.get("flooding", 0) > 0
            and scores.get("rainfall", 0) > 0
        ):
            return "flooding"

        # ----------------------------------------------------
        # Cyclone > Strong Winds
        # ----------------------------------------------------

        if (
            scores.get("cyclone", 0) > 0
            and scores.get("strong_winds", 0) > 0
        ):
            return "cyclone"

        # ----------------------------------------------------
        # Dust Storm > Strong Winds
        # ----------------------------------------------------

        if (
            scores.get("dust_storm", 0) > 0
            and scores.get("strong_winds", 0) > 0
        ):
            return "dust_storm"

        # ----------------------------------------------------
        # Thunderstorm > Strong Winds
        # ----------------------------------------------------

        if (
            scores.get("thunderstorm", 0) > 0
            and scores.get("strong_winds", 0) > 0
        ):
            return "thunderstorm"

        return best_category

    # ========================================================
    # NORMAL WEATHER DETECTION
    # ========================================================

    def _is_normal_observation(
        self,
        text: str,
        category: str
    ) -> bool:

        # ----------------------------------------------------
        # Generic wind measurements are NOT strong-wind events.
        # Example:
        # "Wind speed: 2.06 m/s"
        # ----------------------------------------------------

        if category == "strong_winds":

            explicit_strong_wind = self._contains_any(
                text,
                [
                    "strong wind",
                    "strong winds",
                    "high wind",
                    "high winds",
                    "strong gust",
                    "strong gusts",
                    "gusty winds",
                    "damaging winds",
                    "wind damage",
                    "gale",
                    "squall",
                    "wind warning",
                    "high wind warning",
                    "तेज हवा",
                    "तेज हवाएं",
                    "जोरदार हवा",
                    "जोरदार हवाएं",
                    "आंधी",
                    "tez hawa",
                    "tez hawayein",
                    "aandhi",
                    "andhi",
                ]
            )

            if not explicit_strong_wind:
                return True

        # ----------------------------------------------------
        # Clear-sky observations are NOT rainfall events.
        # ----------------------------------------------------

        if (
            category == "rainfall"
            and "clear sky" in text
            and not self._contains_any(
                text,
                [
                    "rain",
                    "rainfall",
                    "raining",
                    "baarish",
                    "barish",
                    "बारिश",
                    "वर्षा",
                ]
            )
        ):
            return True

        return False

    # ========================================================
    # TEXT NORMALIZATION
    # ========================================================

    def _normalize_text(
        self,
        text: str
    ) -> str:

        text = text or ""

        # ----------------------------------------------------
        # Convert CamelCase hashtags BEFORE lowercase.
        #
        # #HeavyRain
        #       ↓
        # Heavy Rain
        #
        # #FlashFlood
        #       ↓
        # Flash Flood
        #
        # #RainAlert2026
        #       ↓
        # Rain Alert 2026
        # ----------------------------------------------------

        def normalize_hashtag(match):

            tag = match.group(1)

            # Split CamelCase
            tag = re.sub(
                r"([a-z])([A-Z])",
                r"\1 \2",
                tag
            )

            # Split letters + numbers
            tag = re.sub(
                r"([A-Za-z])([0-9])",
                r"\1 \2",
                tag
            )

            return " " + tag + " "

        text = re.sub(
            r"#([A-Za-z][A-Za-z0-9_]*)",
            normalize_hashtag,
            text
        )

        # ----------------------------------------------------
        # Lowercase after hashtag processing
        # ----------------------------------------------------

        text = text.lower()

        # ----------------------------------------------------
        # Normalize underscores, pipes and slashes
        # ----------------------------------------------------

        text = re.sub(
            r"[_|/]+",
            " ",
            text
        )

        # ----------------------------------------------------
        # Normalize punctuation
        # ----------------------------------------------------

        text = re.sub(
            r"[,:;()\[\]{}]+",
            " ",
            text
        )

        # ----------------------------------------------------
        # Normalize whitespace
        # ----------------------------------------------------

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    # ========================================================
    # HELPER
    # ========================================================

    def _contains_any(
        self,
        text: str,
        patterns: List[str]
    ) -> bool:

        return any(
            pattern.lower() in text
            for pattern in patterns
        )

    # ========================================================
    # SEVERITY
    # ========================================================

    def get_severity(
        self,
        title: str,
        description: str
    ) -> Tuple[str, float]:

        text = self._normalize_text(
            f"{title or ''} {description or ''}"
        )

        # ----------------------------------------------------
        # CRITICAL DISASTER OVERRIDES
        # ----------------------------------------------------

        critical_event_terms = [
            "severe flooding",
            "extreme flooding",
            "massive flooding",
            "catastrophic flooding",
            "flash flood",
            "flash flooding",
            "flood emergency",
            "evacuation order",
            "red alert",
            "dam breach",
            "dam breached",
            "embankment breach",
            "embankment breached",
            "river breached",
            "extremely severe",
            "severe cyclonic storm",
            "critical flooding",
            "catastrophic",
            "devastating",
            "historic disaster",
            "unprecedented",
            "deaths",
            "killed",
            "destroyed",

            # Hindi
            "भयंकर बाढ़",
            "गंभीर बाढ़",
            "बाढ़ आपातकाल",
            "निकासी आदेश",
            "लाल चेतावनी",
        ]

        if self._contains_any(
            text,
            critical_event_terms
        ):
            return "critical", 0.95

        # ----------------------------------------------------
        # HIGH SEVERITY EVENT OVERRIDES
        # ----------------------------------------------------

        high_event_terms = [
            "flood",
            "flooding",
            "flooded",
            "inundated",
            "inundation",
            "submerged",
            "waterlogging",
            "severe waterlogging",
            "heavy rain",
            "heavy rainfall",
            "very heavy rain",
            "very heavy rainfall",
            "intense rain",
            "intense rainfall",
            "cyclone",
            "cyclonic storm",
            "storm surge",
            "landfall",
            "strong winds",
            "damaging winds",
            "severe thunderstorm",
            "river overflow",
            "rising water level",
            "orange alert",
            "evacuation",

            # Hindi
            "भारी बारिश",
            "मूसलाधार बारिश",
            "तेज बारिश",
            "बाढ़",
            "जलमग्न",
            "जलभराव",
            "निकासी",
            "खतरा",
        ]

        if self._contains_any(
            text,
            high_event_terms
        ):
            return "high", 0.90

        # ----------------------------------------------------
        # Standard severity pattern scoring
        # ----------------------------------------------------

        scores = {}

        for severity, patterns in self.severity_patterns.items():

            score = 0

            for pattern in patterns:

                if pattern.lower() in text:
                    score += 1

            if score > 0:
                scores[severity] = score

        # ----------------------------------------------------
        # No severity signal
        # ----------------------------------------------------

        if not scores:
            return "low", 0.5

        # ----------------------------------------------------
        # Priority:
        #
        # critical > high > moderate > low
        # ----------------------------------------------------

        if "critical" in scores:
            best = "critical"

        elif "high" in scores:
            best = "high"

        elif "moderate" in scores:
            best = "moderate"

        else:
            best = "low"

        confidence = min(
            scores[best] / 3.0,
            1.0
        )

        return (
            best,
            round(confidence, 3)
        )

    # ========================================================
    # BATCH API
    # ========================================================

    def batch_categorize(
        self,
        events: List[dict]
    ) -> List[dict]:

        results = []

        for event in events:

            category, confidence = self.categorize(
                event.get("title", ""),
                event.get("description", "")
            )

            severity, severity_confidence = self.get_severity(
                event.get("title", ""),
                event.get("description", "")
            )

            results.append({
                "event_type": category,
                "category_confidence": confidence,
                "severity": severity,
                "severity_confidence": severity_confidence,
            })

        return results


# ============================================================
# GLOBAL INSTANCE
# ============================================================

categorizer = Categorizer()