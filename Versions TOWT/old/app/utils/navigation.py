"""
Haversine distance calculation for port-to-port orthodromic distance.
"""
import math


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate orthodromic distance in nautical miles between two points."""
    R = 3440.065  # Earth radius in NM
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def compute_nav_days(distance_nm: float, speed_knots: float = 8.0) -> float:
    """Compute navigation days from distance and speed."""
    if not distance_nm or not speed_knots or speed_knots <= 0:
        return 0
    hours = distance_nm / speed_knots
    return round(hours / 24, 2)
