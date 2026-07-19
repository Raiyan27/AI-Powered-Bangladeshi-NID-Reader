"""Integration tests using the real NID sample images.

These tests exercise the full pipeline end-to-end but mock the Vision AI call
to avoid requiring an API key during CI. Run with:

    pytest tests/test_sample_nid.py -v
"""
import io
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.schemas.nid import NIDData

SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
NID_FRONT = SAMPLES_DIR / "NID_front.jpg"
NID_BACK = SAMPLES_DIR / "NID_back.jpg"

EXPECTED_DATA = {
    "name": "Md Rahim",
    "fatherName": "Abdul Karim",
    "motherName": "Amena Begum",
    "spouseName": None,
    "dateOfBirth": "1998-01-15",
    "nidNumber": "1234567890123",
    "address": "Dhaka, Bangladesh",
    "presentAddress": "Dhaka, Bangladesh",
    "permanentAddress": "Cumilla, Bangladesh",
    "bloodGroup": "O+",
}

client = TestClient(app)


def _load_image_bytes(path: Path) -> bytes:
    """Read image file as bytes, or create a blank placeholder if not found."""
    if path.exists():
        return path.read_bytes()
    img = Image.new("RGB", (800, 500), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _mock_vision_result() -> NIDData:
    return NIDData(**EXPECTED_DATA)


class TestNIDSampleIntegration:
    """Integration tests using sample NID images."""

    def test_sample_images_exist(self):
        assert NID_FRONT.exists(), f"NID_front.jpg not found at {NID_FRONT}"
        assert NID_BACK.exists(), f"NID_back.jpg not found at {NID_BACK}"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_full_pipeline_with_sample_images(self, mock_vision):
        """Complete pipeline with real NID images (Vision AI mocked)."""
        mock_vision.return_value = _mock_vision_result()

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", _load_image_bytes(NID_FRONT), "image/jpeg"),
                "back": ("NID_back.jpg", _load_image_bytes(NID_BACK), "image/jpeg"),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "warnings" in data

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_response_schema(self, mock_vision):
        """Verify all expected fields are present in the response."""
        mock_vision.return_value = _mock_vision_result()

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", _load_image_bytes(NID_FRONT), "image/jpeg"),
                "back": ("NID_back.jpg", _load_image_bytes(NID_BACK), "image/jpeg"),
            },
        )
        result = response.json()["data"]
        for field in ["name", "fatherName", "motherName", "spouseName", "dateOfBirth",
                      "nidNumber", "address", "presentAddress", "permanentAddress", "bloodGroup"]:
            assert field in result, f"Missing field: {field}"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_nid_number_extracted_correctly(self, mock_vision):
        mock_vision.return_value = _mock_vision_result()

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", _load_image_bytes(NID_FRONT), "image/jpeg"),
                "back": ("NID_back.jpg", _load_image_bytes(NID_BACK), "image/jpeg"),
            },
        )
        assert response.json()["data"]["nidNumber"] == "1234567890123"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_date_normalized_to_iso_format(self, mock_vision):
        """Vision AI may return date as '15 Jan 1998' — verify normalization to YYYY-MM-DD."""
        mock_vision.return_value = NIDData(
            name="Md Rahim",
            fatherName="Abdul Karim",
            motherName="Amena Begum",
            dateOfBirth="15 Jan 1998",  # Non-ISO format from Vision AI
            nidNumber="1234567890123",
            address="Dhaka, Bangladesh",
        )

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", _load_image_bytes(NID_FRONT), "image/jpeg"),
                "back": ("NID_back.jpg", _load_image_bytes(NID_BACK), "image/jpeg"),
            },
        )
        assert response.json()["data"]["dateOfBirth"] == "1998-01-15"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_spouse_name_field_present_in_response(self, mock_vision):
        """spouseName field must always be present in the response (null when absent)."""
        mock_vision.return_value = NIDData(name="Test User", spouseName=None)

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", _load_image_bytes(NID_FRONT), "image/jpeg"),
                "back": ("NID_back.jpg", _load_image_bytes(NID_BACK), "image/jpeg"),
            },
        )
        data = response.json()["data"]
        assert "spouseName" in data

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_single_image_auto_split(self, mock_vision):
        """Single combined NID image without back file should be auto-split."""
        mock_vision.return_value = _mock_vision_result()
        combined_path = SAMPLES_DIR / "NID.jpg"
        combined_bytes = _load_image_bytes(combined_path)

        response = client.post(
            "/extract",
            files={"front": ("NID.jpg", combined_bytes, "image/jpeg")},
        )
        assert response.status_code == 200
        assert response.json()["data"]["nidNumber"] == "1234567890123"

