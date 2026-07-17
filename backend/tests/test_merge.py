"""Tests for the merge service logic."""
import pytest
from app.services.merge_service import merge_results, _extract_nid_from_ocr, _extract_date_from_ocr
from app.schemas.nid import NIDData, OCRResult, OCROutput


class TestMergeResults:
    """Test the OCR + Vision merge strategy."""

    def _make_ocr(self, results: list[OCRResult] | None = None) -> OCROutput:
        results = results or []
        raw_text = "\n".join(r.text for r in results)
        avg_conf = sum(r.confidence for r in results) / len(results) if results else 0.0
        return OCROutput(results=results, raw_text=raw_text, avg_confidence=avg_conf)

    def test_vision_preferred_for_names(self):
        """Names should come from Vision AI, not OCR."""
        ocr = self._make_ocr()
        vision = NIDData(name="Md Rahim", fatherName="Abdul Karim")

        merged, warnings = merge_results(ocr, ocr, vision)
        assert merged.name == "Md Rahim"
        assert merged.fatherName == "Abdul Karim"

    def test_ocr_nid_preferred_over_vision(self):
        """High-confidence OCR NID number should override Vision."""
        front_ocr = self._make_ocr([
            OCRResult(text="1234567890123", confidence=0.98, position=[100, 200])
        ])
        vision = NIDData(nidNumber="1234567890124")  # Slightly different

        merged, warnings = merge_results(front_ocr, self._make_ocr(), vision)
        assert merged.nidNumber == "1234567890123"
        assert len(warnings) > 0
        assert "NID number" in warnings[0]

    def test_vision_nid_used_when_no_ocr_nid(self):
        """If OCR doesn't find NID, use Vision result."""
        vision = NIDData(nidNumber="9876543210123")
        merged, warnings = merge_results(self._make_ocr(), self._make_ocr(), vision)
        assert merged.nidNumber == "9876543210123"

    def test_warning_on_nid_mismatch(self):
        """Should generate warning when OCR and Vision NID numbers differ."""
        front_ocr = self._make_ocr([
            OCRResult(text="1111111111111", confidence=0.95, position=[100, 200])
        ])
        vision = NIDData(nidNumber="2222222222222")

        _, warnings = merge_results(front_ocr, self._make_ocr(), vision)
        assert any("NID number" in w and "mismatch" in w for w in warnings)

    def test_no_warning_when_nid_matches(self):
        """No warning when OCR and Vision agree on NID."""
        front_ocr = self._make_ocr([
            OCRResult(text="1234567890123", confidence=0.98, position=[100, 200])
        ])
        vision = NIDData(nidNumber="1234567890123")

        _, warnings = merge_results(front_ocr, self._make_ocr(), vision)
        assert not any("NID number" in w for w in warnings)


class TestNIDExtraction:
    """Test NID number extraction from OCR."""

    def _make_ocr(self, results: list[OCRResult]) -> OCROutput:
        raw_text = "\n".join(r.text for r in results)
        avg_conf = sum(r.confidence for r in results) / len(results) if results else 0.0
        return OCROutput(results=results, raw_text=raw_text, avg_confidence=avg_conf)

    def test_extract_13_digit_nid(self):
        ocr = self._make_ocr([
            OCRResult(text="1234567890123", confidence=0.95, position=[0, 0])
        ])
        assert _extract_nid_from_ocr(ocr, OCROutput()) == "1234567890123"

    def test_extract_10_digit_nid(self):
        ocr = self._make_ocr([
            OCRResult(text="1234567890", confidence=0.95, position=[0, 0])
        ])
        assert _extract_nid_from_ocr(ocr, OCROutput()) == "1234567890"

    def test_extract_17_digit_nid(self):
        ocr = self._make_ocr([
            OCRResult(text="12345678901234567", confidence=0.95, position=[0, 0])
        ])
        assert _extract_nid_from_ocr(ocr, OCROutput()) == "12345678901234567"

    def test_no_nid_in_text(self):
        ocr = self._make_ocr([
            OCRResult(text="Some random text", confidence=0.95, position=[0, 0])
        ])
        assert _extract_nid_from_ocr(ocr, OCROutput()) is None


class TestDateExtraction:
    """Test date extraction from OCR."""

    def _make_ocr(self, results: list[OCRResult]) -> OCROutput:
        raw_text = "\n".join(r.text for r in results)
        avg_conf = sum(r.confidence for r in results) / len(results) if results else 0.0
        return OCROutput(results=results, raw_text=raw_text, avg_confidence=avg_conf)

    def test_extract_dd_mm_yyyy(self):
        ocr = self._make_ocr([
            OCRResult(text="15/01/1998", confidence=0.95, position=[0, 0])
        ])
        assert _extract_date_from_ocr(ocr, OCROutput()) == "1998-01-15"

    def test_extract_date_with_dashes(self):
        ocr = self._make_ocr([
            OCRResult(text="15-01-1998", confidence=0.95, position=[0, 0])
        ])
        assert _extract_date_from_ocr(ocr, OCROutput()) == "1998-01-15"

    def test_no_date_found(self):
        ocr = self._make_ocr([
            OCRResult(text="No date here", confidence=0.95, position=[0, 0])
        ])
        assert _extract_date_from_ocr(ocr, OCROutput()) is None
