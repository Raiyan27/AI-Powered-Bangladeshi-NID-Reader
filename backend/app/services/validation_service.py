import re

from app.core.logging import logger
from app.schemas.nid import NIDData


def validate_extraction(data: NIDData) -> list[str]:
    """Validate extracted NID data and generate warnings for missing or invalid fields.

    Does NOT fail on partial extraction — returns warnings instead.
    """
    warnings: list[str] = []

    field_labels = {
        "name": "Name",
        "fatherName": "Father's name",
        "motherName": "Mother's name",
        "dateOfBirth": "Date of birth",
        "nidNumber": "NID number",
        "presentAddress": "Present address",
        "permanentAddress": "Permanent address",
    }

    # Check for missing fields
    for field, label in field_labels.items():
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            warnings.append(f"{label} could not be detected")

    # Validate NID number format
    if data.nidNumber:
        cleaned_nid = re.sub(r'\s', '', data.nidNumber)
        if not re.match(r'^\d{10}$|^\d{13}$|^\d{17}$', cleaned_nid):
            warnings.append(
                f"NID number '{data.nidNumber}' may be invalid. "
                "Expected 10, 13, or 17 digits."
            )

    # Validate date format
    if data.dateOfBirth:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', data.dateOfBirth):
            warnings.append(
                f"Date of birth '{data.dateOfBirth}' is not in expected YYYY-MM-DD format."
            )

    if warnings:
        logger.info(f"Validation produced {len(warnings)} warnings: {warnings}")

    return warnings
