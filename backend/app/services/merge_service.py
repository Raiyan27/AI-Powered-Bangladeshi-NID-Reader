import re

from app.core.logging import logger
from app.schemas.nid import NIDData, OCROutput


def merge_results(
    ocr_front: OCROutput,
    ocr_back: OCROutput,
    vision_result: NIDData,
) -> tuple[NIDData, list[str]]:
    """Merge OCR and Vision AI results using confidence-based strategy.

    Rules:
    - Numeric fields (nidNumber, dateOfBirth): prefer high-confidence OCR
    - Text fields (names, addresses): prefer Vision AI semantic understanding
    - Generate warnings when OCR and Vision disagree on numeric fields

    Returns (merged NIDData, list of warning strings).
    """
    warnings: list[str] = []

    # Try to extract numeric fields from OCR
    ocr_nid_number = _extract_nid_from_ocr(ocr_front, ocr_back)
    ocr_dob = _extract_date_from_ocr(ocr_front, ocr_back)

    merged = NIDData(
        name=vision_result.name,
        fatherName=vision_result.fatherName,
        motherName=vision_result.motherName,
        dateOfBirth=vision_result.dateOfBirth,
        nidNumber=vision_result.nidNumber,
        presentAddress=vision_result.presentAddress,
        permanentAddress=vision_result.permanentAddress,
    )

    # NID Number: prefer high-confidence OCR if available
    if ocr_nid_number:
        if vision_result.nidNumber and ocr_nid_number != vision_result.nidNumber:
            warnings.append(
                "NID number confidence mismatch between OCR and AI extraction. "
                f"OCR: {ocr_nid_number}, AI: {vision_result.nidNumber}"
            )
            # Still prefer OCR for numeric data
            merged.nidNumber = ocr_nid_number
        elif not vision_result.nidNumber:
            merged.nidNumber = ocr_nid_number

    # Date of Birth: prefer OCR if high confidence
    if ocr_dob:
        if vision_result.dateOfBirth and ocr_dob != vision_result.dateOfBirth:
            warnings.append(
                "Date of birth mismatch between OCR and AI extraction. "
                f"OCR: {ocr_dob}, AI: {vision_result.dateOfBirth}"
            )
        elif not vision_result.dateOfBirth:
            merged.dateOfBirth = ocr_dob

    logger.info(f"Merge completed with {len(warnings)} warnings")
    return merged, warnings


def _extract_nid_from_ocr(front: OCROutput, back: OCROutput) -> str | None:
    """Extract NID number from OCR results.

    NID numbers are typically 10, 13, or 17 digit numeric strings.
    """
    all_results = front.results + back.results

    for result in sorted(all_results, key=lambda r: r.confidence, reverse=True):
        # Clean text: remove spaces, dashes
        cleaned = re.sub(r'[\s\-]', '', result.text)

        # Check if it's a plausible NID number (10, 13, or 17 digits)
        if re.match(r'^\d{10}$|^\d{13}$|^\d{17}$', cleaned):
            logger.info(f"Found NID number via OCR: {cleaned} (confidence: {result.confidence:.2f})")
            return cleaned

    return None


def _extract_date_from_ocr(front: OCROutput, back: OCROutput) -> str | None:
    """Extract date of birth from OCR results.

    Looks for date patterns and normalizes to YYYY-MM-DD format.
    """
    all_results = front.results + back.results
    date_patterns = [
        # DD Mon YYYY, DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
        r'(\d{1,2})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{4})',
        # YYYY-MM-DD
        r'(\d{4})\s*[/\-\.]\s*(\d{1,2})\s*[/\-\.]\s*(\d{1,2})',
    ]

    for result in sorted(all_results, key=lambda r: r.confidence, reverse=True):
        text = result.text.strip()

        # Try DD/MM/YYYY or DD-MM-YYYY pattern
        match = re.search(date_patterns[0], text)
        if match:
            day, month, year = match.groups()
            day, month = int(day), int(month)
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year}-{month:02d}-{day:02d}"

        # Try YYYY-MM-DD pattern
        match = re.search(date_patterns[1], text)
        if match:
            year, month, day = match.groups()
            month, day = int(month), int(day)
            if 1 <= day <= 31 and 1 <= month <= 12:
                return f"{year}-{month:02d}-{day:02d}"

    return None
