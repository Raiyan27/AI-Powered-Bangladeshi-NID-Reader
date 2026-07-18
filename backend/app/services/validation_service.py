import re

from app.core.logging import logger
from app.schemas.nid import NIDData

# Required fields — missing ones generate warnings.
# presentAddress and permanentAddress are optional (only present on new-format smart cards).
_REQUIRED_FIELDS = {
    "name": "Name",
    "fatherName": "Father's name",
    "motherName": "Mother's name",
    "dateOfBirth": "Date of birth",
    "nidNumber": "NID number",
    "address": "Address",
}

# Optional fields — not warned when absent.
# spouseName, presentAddress, permanentAddress


def validate_extraction(data: NIDData) -> list[str]:
    """Validate extracted NID data and return a list of human-readable warnings.

    Does NOT raise exceptions — partial extractions are valid responses.
    """
    warnings: list[str] = []

    # Missing required fields
    for field, label in _REQUIRED_FIELDS.items():
        value = getattr(data, field)
        if not value or (isinstance(value, str) and not value.strip()):
            warnings.append(f"{label} could not be detected")

    # NID number format: 10, 13, or 17 digits
    if data.nidNumber:
        cleaned_nid = re.sub(r"\s", "", data.nidNumber)
        if not re.fullmatch(r"\d{10}|\d{13}|\d{17}", cleaned_nid):
            warnings.append(
                f"NID number '{data.nidNumber}' may be invalid. "
                "Expected 10, 13, or 17 digits."
            )

    # Date of birth: must be YYYY-MM-DD
    if data.dateOfBirth:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data.dateOfBirth):
            warnings.append(
                f"Date of birth '{data.dateOfBirth}' is not in expected YYYY-MM-DD format."
            )
        else:
            # Sanity range check
            year = int(data.dateOfBirth[:4])
            if not (1900 <= year <= 2030):
                warnings.append(
                    f"Date of birth year '{year}' is outside the expected range (1900–2030)."
                )

    if warnings:
        logger.info(f"Validation produced {len(warnings)} warnings: {warnings}")

    return warnings
