import re

from app.core.logging import logger
from app.schemas.nid import NIDData, OCROutput
from app.services.translation_service import normalize_date


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
        # Clean text: remove spaces, dashes, colons, and dots
        cleaned = re.sub(r'[\s\-\:\.]', '', result.text)

        # Match a sequence of exactly 10, 13, or 17 digits (ensuring no surrounding digits)
        match = re.search(r'(?<!\d)(\d{10}|\d{13}|\d{17})(?!\d)', cleaned)
        if match:
            nid = match.group(1)
            logger.info(f"Found NID number via OCR: {nid} (confidence: {result.confidence:.2f})")
            return nid

    return None


def _extract_date_from_ocr(front: OCROutput, back: OCROutput) -> str | None:
    """Extract date of birth from OCR results.

    Looks for date patterns and normalizes to YYYY-MM-DD format.
    """
    all_results = front.results + back.results
    patterns = [
        # DD Mon YYYY / DD Month YYYY (e.g. "15 Jan 1998", "27 July 2002")
        r'\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b',
        # DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{4}\b',
        # YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
        r'\b\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}\b',
    ]

    for result in sorted(all_results, key=lambda r: r.confidence, reverse=True):
        text = result.text.strip()
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                candidate = match.group(0)
                normalized = normalize_date(candidate)
                if normalized and re.match(r'^\d{4}-\d{2}-\d{2}$', normalized):
                    logger.info(f"Found Date of Birth via OCR: {normalized} (confidence: {result.confidence:.2f})")
                    return normalized

    return None
