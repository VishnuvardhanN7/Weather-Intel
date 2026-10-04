"""
Contradiction Detection — flags when sources disagree about an event.

Detects:
  - direct negation pairs (e.g., "no rainfall" vs "heavy rain")
  - conflicting claims in related reports
"""

from typing import List, Dict, Any, Tuple
import re

CONTRADICTION_VERSION = "contradiction-v1"

NEGATION_TERMS = [
    "no", "not", "none", "unlikely", "denied", "refuted", "disputed",
    "never", "absence of", "lack of", "no sign", "no evidence",
    "नहीं", "नहि", "कबी",  # Hindi/Hinglish negations
]

POSITIVE_TERMS = [
    "heavy", "severe", "confirmed", "reported", "witnessed", "observed",
    "strong", "intense", "widespread", "flood", "rain", "storm",
    "बारिश", "बाढ़", "भारी", "तेज़",  # Hindi positives
]


def detect_contradictions(texts: List[str]) -> dict:
    """
    Given list of report texts, detect whether any contradict each other.
    Returns {has_conflict, conflicting_pairs, description}
    """
    if len(texts) < 2:
        return {
            "has_conflict": False,
            "conflicting_pairs": [],
            "description": "Insufficient reports to detect contradiction",
        }

    conflicts = []
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            t1, t2 = texts[i] or "", texts[j] or ""
            t1_l, t2_l = t1.lower(), t2.lower()

            has_neg1 = any(term in t1_l for term in NEGATION_TERMS)
            has_neg2 = any(term in t2_l for term in NEGATION_TERMS)
            has_pos1 = any(term in t1_l for term in POSITIVE_TERMS)
            has_pos2 = any(term in t2_l for term in POSITIVE_TERMS)

            if (has_neg1 and has_pos2) or (has_neg2 and has_pos1):
                conflicts.append((i, j))

    if conflicts:
        return {
            "has_conflict": True,
            "conflicting_pairs": conflicts,
            "description": f"Detected {len(conflicts)} conflicting report pairs. "
                           "Marked NEEDS REVIEW — do not auto-verify.",
        }
    return {
        "has_conflict": False,
        "conflicting_pairs": [],
        "description": "No contradictions detected",
    }