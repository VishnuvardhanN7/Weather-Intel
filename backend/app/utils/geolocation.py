from typing import Optional, Dict
import math


INDIAN_CITY_COORDINATES = {
    "Aizawl": {"latitude": 23.7271, "longitude": 92.7176},
    "Agartala": {"latitude": 23.8315, "longitude": 91.2868},
    "Agra": {"latitude": 27.1767, "longitude": 78.0081},
    "Ahmedabad": {"latitude": 23.0225, "longitude": 72.5714},
    "Amritsar": {"latitude": 31.6340, "longitude": 74.8723},
    "Bengaluru": {"latitude": 12.9716, "longitude": 77.5946},
    "Bhopal": {"latitude": 23.2599, "longitude": 77.4126},
    "Bhubaneswar": {"latitude": 20.2961, "longitude": 85.8245},
    "Chandigarh": {"latitude": 30.7333, "longitude": 76.7794},
    "Chennai": {"latitude": 13.0827, "longitude": 80.2707},
    "Coimbatore": {"latitude": 11.0168, "longitude": 76.9558},
    "Dehradun": {"latitude": 30.3165, "longitude": 78.0322},
    "Delhi": {"latitude": 28.6139, "longitude": 77.2090},
    "New Delhi": {"latitude": 28.6139, "longitude": 77.2090},
    "Dimapur": {"latitude": 25.9022, "longitude": 93.7265},
    "Gangtok": {"latitude": 27.3389, "longitude": 88.6065},
    "Guwahati": {"latitude": 26.1445, "longitude": 91.7362},
    "Hyderabad": {"latitude": 17.3850, "longitude": 78.4867},
    "Imphal": {"latitude": 24.8170, "longitude": 93.9368},
    "Indore": {"latitude": 22.7196, "longitude": 75.8577},
    "Itanagar": {"latitude": 27.1044, "longitude": 93.6920},
    "Jaipur": {"latitude": 26.9124, "longitude": 75.7873},
    "Jammu": {"latitude": 32.7266, "longitude": 74.8570},
    "Jodhpur": {"latitude": 26.2389, "longitude": 73.0243},
    "Kanpur": {"latitude": 26.4499, "longitude": 80.3319},
    "Kochi": {"latitude": 9.9312, "longitude": 76.2673},
    "Kohima": {"latitude": 25.6586, "longitude": 94.1086},
    "Kolkata": {"latitude": 22.5726, "longitude": 88.3639},
    "Lucknow": {"latitude": 26.8467, "longitude": 80.9462},
    "Ludhiana": {"latitude": 30.9010, "longitude": 75.8573},
    "Madurai": {"latitude": 9.9252, "longitude": 78.1198},
    "Meerut": {"latitude": 28.9845, "longitude": 77.7064},
    "Mumbai": {"latitude": 19.0760, "longitude": 72.8777},
    "Nagpur": {"latitude": 21.1458, "longitude": 79.0882},
    "Nashik": {"latitude": 19.9975, "longitude": 73.7898},
    "Panaji": {"latitude": 15.4909, "longitude": 73.8278},
    "Patna": {"latitude": 25.6093, "longitude": 85.1376},
    "Prayagraj": {"latitude": 25.4358, "longitude": 81.8463},
    "Pune": {"latitude": 18.5204, "longitude": 73.8567},
    "Raipur": {"latitude": 21.2514, "longitude": 81.6296},
    "Rajkot": {"latitude": 22.3039, "longitude": 70.8022},
    "Ranchi": {"latitude": 23.3441, "longitude": 85.3096},
    "Shillong": {"latitude": 25.5788, "longitude": 91.8933},
    "Shimla": {"latitude": 31.1048, "longitude": 77.1734},
    "Srinagar": {"latitude": 34.0837, "longitude": 74.7973},
    "Surat": {"latitude": 21.1702, "longitude": 72.8311},
    "Thiruvananthapuram": {"latitude": 8.5241, "longitude": 76.9366},
    "Tiruchirappalli": {"latitude": 10.7905, "longitude": 78.7047},
    "Udaipur": {"latitude": 24.5854, "longitude": 73.7125},
    "Varanasi": {"latitude": 25.3176, "longitude": 82.9739},
    "Vadodara": {"latitude": 22.3072, "longitude": 73.1812},
    "Vijayawada": {"latitude": 16.5062, "longitude": 80.6480},
    "Visakhapatnam": {"latitude": 17.6868, "longitude": 83.2185},
    "Warangal": {"latitude": 17.9784, "longitude": 79.5941},
    "Ahmednagar": {"latitude": 19.0952, "longitude": 74.7496},
    "Aligarh": {"latitude": 27.8974, "longitude": 78.0880},
    "Allahabad": {"latitude": 25.4358, "longitude": 81.8463},
    "Bilaspur": {"latitude": 22.0797, "longitude": 82.1409},
    "Cuttack": {"latitude": 20.4625, "longitude": 85.8830},
    "Darjeeling": {"latitude": 27.0360, "longitude": 88.2627},
    "Dhanbad": {"latitude": 23.7957, "longitude": 86.4304},
    "Gwalior": {"latitude": 26.2183, "longitude": 78.1828},
    "Hubli": {"latitude": 15.3647, "longitude": 75.1240},
    "Jabalpur": {"latitude": 23.1815, "longitude": 79.9864},
    "Kolhapur": {"latitude": 16.7050, "longitude": 74.2433},
    "Mangalore": {"latitude": 12.9141, "longitude": 74.8560},
    "Mysuru": {"latitude": 12.2958, "longitude": 76.6394},
    "Nellore": {"latitude": 14.4426, "longitude": 79.9865},
    "Salem": {"latitude": 11.6643, "longitude": 78.1460},
    "Siliguri": {"latitude": 26.7271, "longitude": 88.3953},
    "Tirupati": {"latitude": 13.6288, "longitude": 79.4192},
    "Vellore": {"latitude": 12.9165, "longitude": 79.1325},
    "Warangal": {"latitude": 17.9784, "longitude": 79.5941},
}

INDIAN_STATE_CENTERS = {
    "Andhra Pradesh": {"latitude": 15.9129, "longitude": 79.7400},
    "Arunachal Pradesh": {"latitude": 28.2180, "longitude": 94.7278},
    "Assam": {"latitude": 26.2006, "longitude": 92.9376},
    "Bihar": {"latitude": 25.0961, "longitude": 85.3131},
    "Chhattisgarh": {"latitude": 21.2787, "longitude": 81.8661},
    "Goa": {"latitude": 15.2993, "longitude": 74.1240},
    "Gujarat": {"latitude": 22.2587, "longitude": 71.1924},
    "Haryana": {"latitude": 29.0588, "longitude": 76.0856},
    "Himachal Pradesh": {"latitude": 31.1048, "longitude": 77.1734},
    "Jharkhand": {"latitude": 23.6102, "longitude": 85.2799},
    "Karnataka": {"latitude": 15.3173, "longitude": 75.7139},
    "Kerala": {"latitude": 10.8505, "longitude": 76.2711},
    "Madhya Pradesh": {"latitude": 22.9734, "longitude": 78.6569},
    "Maharashtra": {"latitude": 19.7515, "longitude": 75.7139},
    "Manipur": {"latitude": 24.6637, "longitude": 93.9063},
    "Meghalaya": {"latitude": 25.4670, "longitude": 91.3662},
    "Mizoram": {"latitude": 23.1645, "longitude": 92.9376},
    "Nagaland": {"latitude": 26.1581, "longitude": 94.5624},
    "Odisha": {"latitude": 20.9517, "longitude": 85.0985},
    "Punjab": {"latitude": 31.1471, "longitude": 75.3412},
    "Rajasthan": {"latitude": 27.0238, "longitude": 74.2179},
    "Sikkim": {"latitude": 27.5330, "longitude": 88.5122},
    "Tamil Nadu": {"latitude": 11.1271, "longitude": 78.6569},
    "Telangana": {"latitude": 18.1124, "longitude": 79.0193},
    "Tripura": {"latitude": 23.9408, "longitude": 92.9902},
    "Uttar Pradesh": {"latitude": 26.8467, "longitude": 80.9462},
    "Uttarakhand": {"latitude": 30.0661, "longitude": 79.0193},
    "West Bengal": {"latitude": 22.9868, "longitude": 87.8550},
    "Delhi": {"latitude": 28.6139, "longitude": 77.2090},
    "Chandigarh": {"latitude": 30.7333, "longitude": 76.7794},
    "Jammu and Kashmir": {"latitude": 34.0837, "longitude": 74.7973},
    "Ladakh": {"latitude": 34.1526, "longitude": 77.5771},
    "Puducherry": {"latitude": 11.9416, "longitude": 79.8083},
    "Andaman and Nicobar Islands": {"latitude": 11.7401, "longitude": 92.6586},
    "Dadra and Nagar Haveli": {"latitude": 20.1809, "longitude": 73.0158},
    "Daman and Diu": {"latitude": 20.4283, "longitude": 72.8862},
    "Lakshadweep": {"latitude": 10.5667, "longitude": 72.6417},
}


def get_city_coordinates(city: str) -> dict:
    if city in INDIAN_CITY_COORDINATES:
        return INDIAN_CITY_COORDINATES[city]
    city_lower = city.lower()
    for key in INDIAN_CITY_COORDINATES:
        if key.lower() == city_lower:
            return INDIAN_CITY_COORDINATES[key]
    return {"latitude": None, "longitude": None}


def get_state_coordinates(state: str) -> dict:
    if state in INDIAN_STATE_CENTERS:
        return INDIAN_STATE_CENTERS[state]
    state_lower = state.lower()
    for key in INDIAN_STATE_CENTERS:
        if key.lower() == state_lower:
            return INDIAN_STATE_CENTERS[key]
    return {"latitude": None, "longitude": None}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def is_within_radius(
    event_lat: float,
    event_lng: float,
    user_lat: float,
    user_lng: float,
    radius_km: float,
) -> bool:
    """Pure trigger predicate for location-based weather alerts."""
    return haversine_distance(event_lat, event_lng, user_lat, user_lng) <= radius_km


def find_nearest_city(lat: float, lon: float, max_distance_km: float = 50) -> Optional[str]:
    nearest = None
    min_dist = float('inf')
    for city, coords in INDIAN_CITY_COORDINATES.items():
        if coords["latitude"] and coords["longitude"]:
            dist = haversine_distance(lat, lon, coords["latitude"], coords["longitude"])
            if dist < min_dist and dist <= max_distance_km:
                min_dist = dist
                nearest = city
    return nearest


def find_nearest_state(lat: float, lon: float) -> Optional[str]:
    nearest = None
    min_dist = float('inf')
    for state, coords in INDIAN_STATE_CENTERS.items():
        if coords["latitude"] and coords["longitude"]:
            dist = haversine_distance(lat, lon, coords["latitude"], coords["longitude"])
            if dist < min_dist:
                min_dist = dist
                nearest = state
    return nearest


def resolve_location(lat: Optional[float], lon: Optional[float], city: Optional[str], state: Optional[str]) -> dict:
    result = {"city": city, "state": state, "latitude": lat, "longitude": lon}

    if lat and lon:
        if not city:
            result["city"] = find_nearest_city(lat, lon)
        if not state:
            result["state"] = find_nearest_state(lat, lon)
    elif city and not (lat and lon):
        coords = get_city_coordinates(city)
        result["latitude"] = coords.get("latitude")
        result["longitude"] = coords.get("longitude")

    return result