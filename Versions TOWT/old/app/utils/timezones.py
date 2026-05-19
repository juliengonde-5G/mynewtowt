"""Timezone utilities for myTOWT — port-based timezone resolution and conversion."""
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# ─── Default IANA timezone per country code (ISO 3166-1 alpha-2) ───
# For countries with multiple zones, we pick the most likely port timezone.
COUNTRY_TIMEZONES = {
    "AD": "Europe/Andorra",
    "AE": "Asia/Dubai",
    "AG": "America/Antigua",
    "AI": "America/Anguilla",
    "AL": "Europe/Tirane",
    "AO": "Africa/Luanda",
    "AR": "America/Buenos_Aires",
    "AW": "America/Aruba",
    "BB": "America/Barbados",
    "BE": "Europe/Brussels",
    "BJ": "Africa/Porto-Novo",
    "BL": "America/St_Barthelemy",
    "BM": "Atlantic/Bermuda",
    "BR": "America/Sao_Paulo",
    "BS": "America/Nassau",
    "CA": "America/Halifax",
    "CI": "Africa/Abidjan",
    "CL": "America/Santiago",
    "CM": "Africa/Douala",
    "CN": "Asia/Shanghai",
    "CO": "America/Bogota",
    "CR": "America/Costa_Rica",
    "CU": "America/Havana",
    "CV": "Atlantic/Cape_Verde",
    "CW": "America/Curacao",
    "CY": "Asia/Nicosia",
    "DE": "Europe/Berlin",
    "DK": "Europe/Copenhagen",
    "DM": "America/Dominica",
    "DO": "America/Santo_Domingo",
    "DZ": "Africa/Algiers",
    "EC": "America/Guayaquil",
    "EE": "Europe/Tallinn",
    "EG": "Africa/Cairo",
    "ES": "Europe/Madrid",
    "FI": "Europe/Helsinki",
    "FO": "Atlantic/Faroe",
    "FR": "Europe/Paris",
    "GA": "Africa/Libreville",
    "GB": "Europe/London",
    "GD": "America/Grenada",
    "GF": "America/Cayenne",
    "GH": "Africa/Accra",
    "GI": "Europe/Gibraltar",
    "GP": "America/Guadeloupe",
    "GR": "Europe/Athens",
    "GT": "America/Guatemala",
    "GY": "America/Guyana",
    "HN": "America/Tegucigalpa",
    "HR": "Europe/Zagreb",
    "HT": "America/Port-au-Prince",
    "IE": "Europe/Dublin",
    "IL": "Asia/Jerusalem",
    "IN": "Asia/Kolkata",
    "IS": "Atlantic/Reykjavik",
    "IT": "Europe/Rome",
    "JM": "America/Jamaica",
    "JP": "Asia/Tokyo",
    "KE": "Africa/Nairobi",
    "KN": "America/St_Kitts",
    "KR": "Asia/Seoul",
    "KY": "America/Cayman",
    "LC": "America/St_Lucia",
    "LB": "Asia/Beirut",
    "LR": "Africa/Monrovia",
    "LT": "Europe/Vilnius",
    "LV": "Europe/Riga",
    "LY": "Africa/Tripoli",
    "MA": "Africa/Casablanca",
    "MC": "Europe/Monaco",
    "ME": "Europe/Podgorica",
    "MF": "America/Marigot",
    "MG": "Indian/Antananarivo",
    "MQ": "America/Martinique",
    "MR": "Africa/Nouakchott",
    "MT": "Europe/Malta",
    "MU": "Indian/Mauritius",
    "MX": "America/Mexico_City",
    "MY": "Asia/Kuala_Lumpur",
    "MZ": "Africa/Maputo",
    "NA": "Africa/Windhoek",
    "NC": "Pacific/Noumea",
    "NG": "Africa/Lagos",
    "NI": "America/Managua",
    "NL": "Europe/Amsterdam",
    "NO": "Europe/Oslo",
    "NZ": "Pacific/Auckland",
    "OM": "Asia/Muscat",
    "PA": "America/Panama",
    "PE": "America/Lima",
    "PF": "Pacific/Tahiti",
    "PH": "Asia/Manila",
    "PK": "Asia/Karachi",
    "PL": "Europe/Warsaw",
    "PM": "America/Miquelon",
    "PR": "America/Puerto_Rico",
    "PT": "Europe/Lisbon",
    "RE": "Indian/Reunion",
    "RO": "Europe/Bucharest",
    "RU": "Europe/Moscow",
    "SA": "Asia/Riyadh",
    "SE": "Europe/Stockholm",
    "SG": "Asia/Singapore",
    "SI": "Europe/Ljubljana",
    "SK": "Europe/Bratislava",
    "SL": "Africa/Freetown",
    "SN": "Africa/Dakar",
    "SR": "America/Paramaribo",
    "SX": "America/Lower_Princes",
    "TG": "Africa/Lome",
    "TH": "Asia/Bangkok",
    "TN": "Africa/Tunis",
    "TR": "Europe/Istanbul",
    "TT": "America/Port_of_Spain",
    "TW": "Asia/Taipei",
    "TZ": "Africa/Dar_es_Salaam",
    "UA": "Europe/Kiev",
    "US": "America/New_York",
    "UY": "America/Montevideo",
    "VC": "America/St_Vincent",
    "VE": "America/Caracas",
    "VG": "America/Tortola",
    "VI": "America/Virgin",
    "VN": "Asia/Ho_Chi_Minh",
    "YT": "Indian/Mayotte",
    "ZA": "Africa/Johannesburg",
}

PARIS_TZ = ZoneInfo("Europe/Paris")
UTC_TZ = ZoneInfo("UTC")


def get_port_timezone(country_code: str, zone_code: str | None = None) -> str:
    """Return IANA timezone string for a port.
    Uses zone_code if set on the port, otherwise falls back to country default."""
    if zone_code:
        return zone_code
    return COUNTRY_TIMEZONES.get(country_code, "UTC")


def get_port_tz_info(country_code: str, zone_code: str | None = None) -> ZoneInfo:
    """Return ZoneInfo object for a port."""
    iana = get_port_timezone(country_code, zone_code)
    try:
        return ZoneInfo(iana)
    except Exception:
        return UTC_TZ


def utc_offset_label(tz_name: str) -> str:
    """Return a human-readable UTC offset label like 'UTC+2' for a timezone."""
    try:
        zi = ZoneInfo(tz_name)
        now = datetime.now(zi)
        offset = now.utcoffset()
        if offset is None:
            return "UTC"
        total_seconds = int(offset.total_seconds())
        hours, remainder = divmod(abs(total_seconds), 3600)
        minutes = remainder // 60
        sign = "+" if total_seconds >= 0 else "-"
        if minutes:
            return f"UTC{sign}{hours}:{minutes:02d}"
        return f"UTC{sign}{hours}" if total_seconds != 0 else "UTC"
    except Exception:
        return "UTC"


def convert_time_str(time_str: str, from_tz: str, to_tz: str, ref_date=None) -> str:
    """Convert a HH:MM time string from one timezone to another.
    Returns the converted HH:MM string.
    ref_date is used for DST-accurate conversion (defaults to today)."""
    if not time_str or ":" not in time_str:
        return time_str
    try:
        parts = time_str.split(":")
        hour, minute = int(parts[0]), int(parts[1])
        if ref_date is None:
            ref_date = datetime.now(UTC_TZ).date()

        from_zi = ZoneInfo(from_tz)
        to_zi = ZoneInfo(to_tz)

        dt = datetime(ref_date.year, ref_date.month, ref_date.day, hour, minute, tzinfo=from_zi)
        converted = dt.astimezone(to_zi)
        return converted.strftime("%H:%M")
    except Exception:
        return time_str


def convert_datetime_str(dt_str: str, from_tz: str, to_tz: str) -> str:
    """Convert a datetime-local string (YYYY-MM-DDTHH:MM) between timezones.
    Returns the converted datetime-local string."""
    if not dt_str or "T" not in dt_str:
        return dt_str
    try:
        from_zi = ZoneInfo(from_tz)
        to_zi = ZoneInfo(to_tz)
        dt = datetime.fromisoformat(dt_str).replace(tzinfo=from_zi)
        converted = dt.astimezone(to_zi)
        return converted.strftime("%Y-%m-%dT%H:%M")
    except Exception:
        return dt_str


# Pre-computed timezone choices for templates
TIMEZONE_CHOICES = [
    ("UTC", "UTC"),
    ("Europe/Paris", "Paris"),
    ("port_local", "Port local"),
]
