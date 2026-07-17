"""Integration test using the real NID sample images.

These tests exercise the full pipeline end-to-end but mock the Vision AI call
to avoid requiring an API key during CI. Run with:

    pytest tests/test_sample_nid.py -v

To run against the live API (requires OPENROUTER_API_KEY):

    pytest tests/test_sample_nid.py -v --live
"""
import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.schemas.nid import NIDData

# Path to sample images split from samples/NID.jpg
SAMPLES_DIR = Path(__file__).resolve().parents[2] / "samples"
NID_FRONT = SAMPLES_DIR / "NID_front.jpg"
NID_BACK = SAMPLES_DIR / "NID_back.jpg"

# Expected extraction result based on NID.json
EXPECTED_DATA = {
    "name": "Md Rahim",
    "fatherName": "Abdul Karim",
    "motherName": "Amena Begum",
    "dateOfBirth": "1998-01-15",
    "nidNumber": "1234567890123",
    "presentAddress": "Dhaka, Bangladesh",
    "permanentAddress": "Dhaka, Bangladesh",
}

client = TestClient(app)


def _load_image_bytes(path: Path) -> bytes:
    """Read image file as bytes, or create a blank placeholder if not found."""
    if path.exists():
        return path.read_bytes()
    # Fallback: create blank white image for CI environments without samples
    img = Image.new("RGB", (800, 500), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _mock_vision_result() -> NIDData:
    """Return a mock Vision AI result matching the expected NID data."""
    return NIDData(**EXPECTED_DATA)


class TestNIDSampleIntegration:
    """Integration tests using the sample NID images."""

    def test_sample_images_exist(self):
        """Verify that split sample images are available."""
        assert NID_FRONT.exists(), (
            f"NID_front.jpg not found at {NID_FRONT}. "
            "Run the image-splitting script first."
        )
        assert NID_BACK.exists(), (
            f"NID_back.jpg not found at {NID_BACK}. "
            "Run the image-splitting script first."
        )

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_full_pipeline_with_sample_images(self, mock_vision):
        """Test the complete pipeline with real NID sample images (mocked Vision AI)."""
        mock_vision.return_value = _mock_vision_result()

        front_bytes = _load_image_bytes(NID_FRONT)
        back_bytes = _load_image_bytes(NID_BACK)

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", front_bytes, "image/jpeg"),
                "back": ("NID_back.jpg", back_bytes, "image/jpeg"),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "warnings" in data

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_response_matches_expected_schema(self, mock_vision):
        """Verify the response structure matches the NID.json expected output."""
        mock_vision.return_value = _mock_vision_result()

        front_bytes = _load_image_bytes(NID_FRONT)
        back_bytes = _load_image_bytes(NID_BACK)

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", front_bytes, "image/jpeg"),
                "back": ("NID_back.jpg", back_bytes, "image/jpeg"),
            },
        )

        assert response.status_code == 200
        data = response.json()

        # All expected fields must be present in the response
        result = data["data"]
        for field in ["name", "fatherName", "motherName", "dateOfBirth", "nidNumber",
                      "presentAddress", "permanentAddress"]:
            assert field in result, f"Missing field: {field}"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_nid_number_extracted_correctly(self, mock_vision):
        """Verify the NID number is correctly extracted from the sample."""
        mock_vision.return_value = _mock_vision_result()

        front_bytes = _load_image_bytes(NID_FRONT)
        back_bytes = _load_image_bytes(NID_BACK)

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", front_bytes, "image/jpeg"),
                "back": ("NID_back.jpg", back_bytes, "image/jpeg"),
            },
        )

        data = response.json()
        assert data["success"] is True
        # NID number from the sample card
        assert data["data"]["nidNumber"] == "1234567890123"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_date_normalized_to_iso_format(self, mock_vision):
        """Vision AI may return date as '15 Jan 1998' — verify normalization to YYYY-MM-DD."""
        mock_vision.return_value = NIDData(
            name="Md Rahim",
            fatherName="Abdul Karim",
            motherName="Amena Begum",
            dateOfBirth="15 Jan 1998",  # Non-ISO format from Vision AI
            nidNumber="1234567890123",
            presentAddress="Dhaka, Bangladesh, Dhaka",
            permanentAddress="Dhaka, Bangladesh, Dhaka",
        )

        front_bytes = _load_image_bytes(NID_FRONT)
        back_bytes = _load_image_bytes(NID_BACK)

        response = client.post(
            "/extract",
            files={
                "front": ("NID_front.jpg", front_bytes, "image/jpeg"),
                "back": ("NID_back.jpg", back_bytes, "image/jpeg"),
            },
        )

        data = response.json()
        assert data["success"] is True
        # Date must be normalized to YYYY-MM-DD
        assert data["data"]["dateOfBirth"] == "1998-01-15"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_single_image_extract_endpoint(self, mock_vision):
        """Test endpoint with a single combined NID image without providing the 'back' file."""
        mock_vision.return_value = _mock_vision_result()

        combined_path = SAMPLES_DIR / "NID.jpg"
        combined_bytes = _load_image_bytes(combined_path)

        response = client.post(
            "/extract",
            files={
                "front": ("NID.jpg", combined_bytes, "image/jpeg"),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["nidNumber"] == "1234567890123"

