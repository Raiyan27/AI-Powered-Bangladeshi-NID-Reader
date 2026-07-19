"""Translation normalization service.

Provides utilities to normalize and clean field values extracted from NID cards.
The actual Bengali-to-English translation is handled by the Vision AI model.
This service handles post-processing and normalization of extracted values.
"""

import re

from app.core.logging import logger


_MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

_MONTH_FULL_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


_BENGALI_DIGITS_MAP = {
    "০": "0", "১": "1", "২": "2", "৩": "3", "৪": "4",
    "৫": "5", "৬": "6", "৭": "7", "৮": "8", "৯": "9",
}


def convert_bengali_digits(text: str | None) -> str | None:
    """Convert Bengali Unicode digits to standard English ASCII digits."""
    if not text:
        return text
    return "".join(_BENGALI_DIGITS_MAP.get(char, char) for char in text)


def normalize_date(date_str: str | None) -> str | None:
    """Normalize date strings to YYYY-MM-DD format.

    Handles common formats like:
    - '15 Jan 1998'
    - '1998-01-15'
    - '15/01/1998'
    - '15-01-1998'
    """
    if not date_str:
        return None

    date_str = convert_bengali_digits(date_str)
    date_str = date_str.strip()

    # Already in YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str

    # DD Mon YYYY (e.g., "15 Jan 1998")
    match = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", date_str)
    if match:
        day, month_str, year = match.groups()
        month_key = month_str[:3].lower()
        month = _MONTH_MAP.get(month_key)
        if month:
            return f"{year}-{month}-{int(day):02d}"

    # DD/MM/YYYY or DD-MM-YYYY
    match = re.match(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$", date_str)
    if match:
        day, month, year = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # YYYY/MM/DD or YYYY-MM-DD
    match = re.match(r"^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$", date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    logger.warning(f"Could not normalize date string: '{date_str}'")
    return date_str


def normalize_nid_number(nid_str: str | None) -> str | None:
    """Strip non-numeric characters from NID number strings.

    Bangladesh NID numbers are 10, 13, or 17 digits.
    """
    if not nid_str:
        return None

    nid_str = convert_bengali_digits(nid_str)
    cleaned = re.sub(r"[^\d]", "", nid_str)
    if re.match(r"^\d{10}$|^\d{13}$|^\d{17}$", cleaned):
        return cleaned

    # Return cleaned even if format is unexpected — validation layer will warn
    return cleaned if cleaned else nid_str


def normalize_name(name: str | None) -> str | None:
    """Normalize a name string: strip extra whitespace, title-case if all-caps."""
    if not name:
        return None

    name = name.strip()
    name = re.sub(r"\s+", " ", name)  # Collapse internal whitespace

    # If the name is entirely uppercase, convert to title case
    if name.isupper():
        name = name.title()

    return name or None


def normalize_address(address: str | None) -> str | None:
    """Normalize address strings: strip and collapse whitespace."""
    if not address:
        return None

    address = address.strip()
    address = re.sub(r"\s+", " ", address)
    return address or None


def normalize_blood_group(bg: str | None) -> str | None:
    """Normalize blood group strings (e.g. 'O+', 'A+', 'B+', 'AB+', 'O-', 'A-', 'B-', 'AB-')."""
    if not bg:
        return None

    bg = bg.strip().upper()
    bg = convert_bengali_digits(bg)

    # Detect Rh factor: positive (+) vs negative (-)
    is_negative = bool(re.search(r"(\-|NEG|VE\-|\-\s*VE)", bg))
    is_positive = bool(re.search(r"(\+|POS|VE\+|\+\s*VE)", bg))

    # ABO group matching — AB MUST precede A and B to prevent partial prefix matches
    match_group = re.search(r"\b(AB|A|B|O)\b", bg)
    if not match_group:
        match_group = re.search(r"(AB|A|B|O)", bg)

    if match_group:
        abo = match_group.group(1)
        if is_negative and not is_positive:
            return f"{abo}-"
        if is_positive:
            return f"{abo}+"
        # Direct sign attachment fallback
        sign_match = re.search(r"([\+\-])", bg)
        if sign_match:
            return f"{abo}{sign_match.group(1)}"
        return abo

    return bg if bg else None
