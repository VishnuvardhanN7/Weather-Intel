import re
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Any, List


def generate_unique_id() -> str:
    return str(uuid.uuid4())


def hash_string(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sanitize_text(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_date(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt)


def parse_date(date_str: str, fmt: str = "%Y-%m-%d") -> Optional[datetime]:
    try:
        return datetime.strptime(date_str, fmt)
    except ValueError:
        return None


def chunk_list(lst: list, chunk_size: int) -> List[list]:
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_list(nested_list: list) -> list:
    flat = []
    for item in nested_list:
        if isinstance(item, list):
            flat.extend(flatten_list(item))
        else:
            flat.append(item)
    return flat


def safe_get(d: dict, *keys: str, default: Any = None) -> Any:
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def snake_to_camel(name: str) -> str:
    components = name.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def camel_to_snake(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def extract_numbers(text: str) -> List[float]:
    pattern = r'-?\d+(?:\.\d+)?'
    matches = re.findall(pattern, text)
    return [float(m) for m in matches]


def extract_urls(text: str) -> List[str]:
    pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    return re.findall(pattern, text)


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def remove_duplicates_preserve_order(lst: list) -> list:
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def calculate_percentage(part: float, total: float) -> float:
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def format_large_number(num: int) -> str:
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def classify_indian_state_from_city(city: str) -> Optional[str]:
    from app.utils.geolocation import INDIAN_CITY_COORDINATES
    city_lower = city.lower()
    city_to_state = {
        "mumbai": "Maharashtra",
        "pune": "Maharashtra",
        "nagpur": "Maharashtra",
        "nashik": "Maharashtra",
        "ahmedabad": "Gujarat",
        "surat": "Gujarat",
        "rajkot": "Gujarat",
        "vadodara": "Gujarat",
        "jaipur": "Rajasthan",
        "jodhpur": "Rajasthan",
        "udaipur": "Rajasthan",
        "lucknow": "Uttar Pradesh",
        "kanpur": "Uttar Pradesh",
        "agra": "Uttar Pradesh",
        "varanasi": "Uttar Pradesh",
        "meerut": "Uttar Pradesh",
        "prayagraj": "Uttar Pradesh",
        "bhopal": "Madhya Pradesh",
        "indore": "Madhya Pradesh",
        "jabalpur": "Madhya Pradesh",
        "gwalior": "Madhya Pradesh",
        "patna": "Bihar",
        "ranchi": "Jharkhand",
        "dhanbad": "Jharkhand",
        "kolkata": "West Bengal",
        "siliguri": "West Bengal",
        "chennai": "Tamil Nadu",
        "coimbatore": "Tamil Nadu",
        "madurai": "Tamil Nadu",
        "salem": "Tamil Nadu",
        "tiruchirappalli": "Tamil Nadu",
        "tirupati": "Andhra Pradesh",
        "vijayawada": "Andhra Pradesh",
        "visakhapatnam": "Andhra Pradesh",
        "hyderabad": "Telangana",
        "warangal": "Telangana",
        "bengaluru": "Karnataka",
        "mysuru": "Karnataka",
        "hubli": "Karnataka",
        "mangalore": "Karnataka",
        "thiruvananthapuram": "Kerala",
        "kochi": "Kerala",
        "bhubaneswar": "Odisha",
        "cuttack": "Odisha",
        "chandigarh": "Chandigarh",
        "delhi": "Delhi",
        "new delhi": "Delhi",
        "guwahati": "Assam",
        "shillong": "Meghalaya",
        "imphal": "Manipur",
        "agartala": "Tripura",
        "aizawl": "Mizoram",
        "kohima": "Nagaland",
        "gangtok": "Sikkim",
        "shimla": "Himachal Pradesh",
        "dehradun": "Uttarakhand",
        "srinagar": "Jammu and Kashmir",
        "jammu": "Jammu and Kashmir",
        "amritsar": "Punjab",
        "ludhiana": "Punjab",
        "panaji": "Goa",
        "dimapur": "Nagaland",
        "raipur": "Chhattisgarh",
        "bilaspur": "Chhattisgarh",
        "nellore": "Andhra Pradesh",
        "vellore": "Tamil Nadu",
        "kolhapur": "Maharashtra",
        "ahmednagar": "Maharashtra",
        "darjeeling": "West Bengal",
        "aligarh": "Uttar Pradesh",
    }
    return city_to_state.get(city_lower)