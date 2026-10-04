"""
IMD Specific Location & District Mapping Helper (PS-26069).
Maps IMD station IDs, district names, and state codes to standard Indian locations.
"""

from typing import Dict, Optional, Any
from app.core.location_registry import get_location_by_city, get_all_locations

# Mapping of IMD District names / codes to primary location registry
IMD_DISTRICT_MAP: Dict[str, Dict[str, Any]] = {
    "DELHI": {"city": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    "MUMBAI": {"city": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
    "BENGALURU URBAN": {"city": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    "CHENNAI": {"city": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    "KOLKATA": {"city": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639},
    "HYDERABAD": {"city": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867},
    "PUNE": {"city": "Pune", "state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567},
    "AHMEDABAD": {"city": "Ahmedabad", "state": "Gujarat", "latitude": 23.0225, "longitude": 72.5714},
    "JAIPUR": {"city": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873},
    "LUCKNOW": {"city": "Lucknow", "state": "Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462},
    "KRISHNA": {"city": "Vijayawada", "state": "Andhra Pradesh", "latitude": 16.5062, "longitude": 80.6480},
    "KAMRUP METROPOLITAN": {"city": "Guwahati", "state": "Assam", "latitude": 26.1445, "longitude": 91.7362},
    "ERNAKULAM": {"city": "Kochi", "state": "Kerala", "latitude": 9.9312, "longitude": 76.2673},
    "VISAKHAPATNAM": {"city": "Visakhapatnam", "state": "Andhra Pradesh", "latitude": 17.6868, "longitude": 83.2185},
    "PATNA": {"city": "Patna", "state": "Bihar", "latitude": 25.6093, "longitude": 85.1376},
}


def resolve_imd_location(name_or_code: str, state: Optional[str] = None) -> Dict[str, Any]:
    """Resolve an IMD district, city, or station name to normalized coordinates and metadata."""
    clean_name = name_or_code.strip().upper()
    if clean_name in IMD_DISTRICT_MAP:
        return IMD_DISTRICT_MAP[clean_name]

    # Try matching location registry
    matched = get_location_by_city(name_or_code)
    if matched:
        return matched

    # Fallback default location format
    return {
        "city": name_or_code.title(),
        "state": state.title() if state else "India",
        "latitude": 20.5937,
        "longitude": 78.9629,
    }
