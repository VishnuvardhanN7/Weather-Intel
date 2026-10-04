"""
Configurable Location Registry for Big-Data Weather Collectors.
Contains normalized coordinates and state metadata for 50+ major Indian cities.
"""

from typing import List, Dict, Optional

INDIAN_LOCATIONS: List[Dict[str, any]] = [
    {"city": "Delhi", "state": "Delhi", "latitude": 28.6139, "longitude": 77.2090},
    {"city": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777},
    {"city": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946},
    {"city": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707},
    {"city": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639},
    {"city": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867},
    {"city": "Pune", "state": "Maharashtra", "latitude": 18.5204, "longitude": 73.8567},
    {"city": "Ahmedabad", "state": "Gujarat", "latitude": 23.0225, "longitude": 72.5714},
    {"city": "Jaipur", "state": "Rajasthan", "latitude": 26.9124, "longitude": 75.7873},
    {"city": "Lucknow", "state": "Uttar Pradesh", "latitude": 26.8467, "longitude": 80.9462},
    {"city": "Bhopal", "state": "Madhya Pradesh", "latitude": 23.2599, "longitude": 77.4126},
    {"city": "Patna", "state": "Bihar", "latitude": 25.6093, "longitude": 85.1376},
    {"city": "Guwahati", "state": "Assam", "latitude": 26.1445, "longitude": 91.7362},
    {"city": "Kochi", "state": "Kerala", "latitude": 9.9312, "longitude": 76.2673},
    {"city": "Indore", "state": "Madhya Pradesh", "latitude": 22.7196, "longitude": 75.8577},
    {"city": "Nagpur", "state": "Maharashtra", "latitude": 21.1458, "longitude": 79.0882},
    {"city": "Thiruvananthapuram", "state": "Kerala", "latitude": 8.5241, "longitude": 76.9366},
    {"city": "Visakhapatnam", "state": "Andhra Pradesh", "latitude": 17.6868, "longitude": 83.2185},
    {"city": "Varanasi", "state": "Uttar Pradesh", "latitude": 25.3176, "longitude": 82.9739},
    {"city": "Amritsar", "state": "Punjab", "latitude": 31.6340, "longitude": 74.8723},
    {"city": "Vijayawada", "state": "Andhra Pradesh", "latitude": 16.5062, "longitude": 80.6480},
    {"city": "Bhubaneswar", "state": "Odisha", "latitude": 20.2961, "longitude": 85.8245},
    {"city": "Chandigarh", "state": "Chandigarh", "latitude": 30.7333, "longitude": 76.7794},
    {"city": "Dehradun", "state": "Uttarakhand", "latitude": 30.3165, "longitude": 78.0322},
    {"city": "Srinagar", "state": "Jammu and Kashmir", "latitude": 34.0837, "longitude": 74.7973},
    {"city": "Jammu", "state": "Jammu and Kashmir", "latitude": 32.7266, "longitude": 74.8570},
    {"city": "Ranchi", "state": "Jharkhand", "latitude": 23.3441, "longitude": 85.3096},
    {"city": "Raipur", "state": "Chhattisgarh", "latitude": 21.2514, "longitude": 81.6296},
    {"city": "Surat", "state": "Gujarat", "latitude": 21.1702, "longitude": 72.8311},
    {"city": "Vadodara", "state": "Gujarat", "latitude": 22.3072, "longitude": 73.1812},
    {"city": "Coimbatore", "state": "Tamil Nadu", "latitude": 11.0168, "longitude": 76.9558},
    {"city": "Madurai", "state": "Tamil Nadu", "latitude": 9.9252, "longitude": 78.1198},
    {"city": "Mysuru", "state": "Karnataka", "latitude": 12.2958, "longitude": 76.6394},
    {"city": "Mangaluru", "state": "Karnataka", "latitude": 12.9141, "longitude": 74.8560},
    {"city": "Tirupati", "state": "Andhra Pradesh", "latitude": 13.6288, "longitude": 79.4192},
    {"city": "Guntur", "state": "Andhra Pradesh", "latitude": 16.3067, "longitude": 80.4365},
    {"city": "Rajahmundry", "state": "Andhra Pradesh", "latitude": 17.0005, "longitude": 81.8040},
    {"city": "Nellore", "state": "Andhra Pradesh", "latitude": 14.4426, "longitude": 79.9865},
    {"city": "Kakinada", "state": "Andhra Pradesh", "latitude": 16.9891, "longitude": 82.2475},
    {"city": "Warangal", "state": "Telangana", "latitude": 17.9784, "longitude": 79.5941},
    {"city": "Agra", "state": "Uttar Pradesh", "latitude": 27.1767, "longitude": 78.0081},
    {"city": "Kanpur", "state": "Uttar Pradesh", "latitude": 26.4499, "longitude": 80.3319},
    {"city": "Prayagraj", "state": "Uttar Pradesh", "latitude": 25.4358, "longitude": 81.8463},
    {"city": "Meerut", "state": "Uttar Pradesh", "latitude": 28.9845, "longitude": 77.7064},
    {"city": "Ludhiana", "state": "Punjab", "latitude": 30.9010, "longitude": 75.8573},
    {"city": "Jodhpur", "state": "Rajasthan", "latitude": 26.2389, "longitude": 73.0243},
    {"city": "Udaipur", "state": "Rajasthan", "latitude": 24.5854, "longitude": 73.7125},
    {"city": "Kota", "state": "Rajasthan", "latitude": 25.2138, "longitude": 75.8648},
]


def get_all_locations() -> List[Dict[str, any]]:
    """Return all unique locations in registry."""
    seen = set()
    unique = []
    for loc in INDIAN_LOCATIONS:
        if loc["city"] not in seen:
            seen.add(loc["city"])
            unique.append(loc)
    return unique


def get_location_by_city(city: str) -> Optional[Dict[str, any]]:
    c_lower = city.lower()
    for loc in get_all_locations():
        if loc["city"].lower() == c_lower:
            return loc
    return None


def get_locations_by_names(names: List[str]) -> List[Dict[str, any]]:
    """Return matching location dicts for a list of city names or slugs."""
    name_set = {n.strip().lower() for n in names if n.strip()}
    matches = []
    for loc in get_all_locations():
        if loc["city"].lower() in name_set or loc["city"].lower().replace(" ", "_") in name_set:
            matches.append(loc)
    return matches

