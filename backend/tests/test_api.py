"""Tests for API endpoints."""
import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app


client = TestClient(app)


def _create_test_image(width: int = 200, height: int = 200, format: str = "PNG") -> bytes:
    """Create a minimal valid test image."""
    img = Image.new("RGB", (width, height), color="white")
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    return buffer.getvalue()


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestExtractEndpoint:
    """Test the /extract endpoint validation."""

    def test_missing_front_image(self):
        back_data = _create_test_image()
        response = client.post(
            "/extract",
            files={"back": ("back.png", back_data, "image/png")},
        )
        assert response.status_code in (422, 400)

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_missing_back_image_auto_split_on_combined_scan(self, mock_vision):
        """Omitting back image on a combined scan (height > width) auto-splits and succeeds."""
        from app.schemas.nid import NIDData
        mock_vision.return_value = NIDData(name="Test User")
        combined_data = _create_test_image(width=200, height=300)
        response = client.post(
            "/extract",
            files={"front": ("combined.png", combined_data, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test User"

    def test_missing_back_image_on_single_card_returns_error(self):
        """Omitting back image on a single front card (width > height) returns MISSING_BACK_IMAGE."""
        single_card_data = _create_test_image(width=300, height=200)
        response = client.post(
            "/extract",
            files={"front": ("front_only.png", single_card_data, "image/png")},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "MISSING_BACK_IMAGE"

    def test_invalid_file_format(self):
        front_data = _create_test_image()
        response = client.post(
            "/extract",
            files={
                "front": ("front.gif", b"fake gif data", "image/gif"),
                "back": ("back.png", front_data, "image/png"),
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_IMAGE_FORMAT"

    def test_response_structure_on_error(self):
        """Error responses must have success, error.code, error.message."""
        response = client.post(
            "/extract",
            files={
                "front": ("front.bmp", b"fake", "image/bmp"),
                "back": ("back.png", _create_test_image(), "image/png"),
            },
        )
        data = response.json()
        assert "success" in data
        assert data["success"] is False
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_invalid_document_type(self, mock_vision):
        """Vision AI detecting a non-NID document returns 400 with INVALID_DOCUMENT_TYPE."""
        from app.services.image_service import ImageValidationError
        mock_vision.side_effect = ImageValidationError(
            code="INVALID_DOCUMENT_TYPE",
            message="The uploaded image is not a valid Bangladesh National ID (NID) card.",
        )
        front_data = _create_test_image()
        back_data = _create_test_image()
        response = client.post(
            "/extract",
            files={
                "front": ("front.png", front_data, "image/png"),
                "back": ("back.png", back_data, "image/png"),
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_DOCUMENT_TYPE"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_vision_api_failure_returns_500(self, mock_vision):
        """Vision API permanent failure returns 500 with AI_EXTRACTION_FAILED."""
        from app.services.vision_service import VisionExtractionError
        mock_vision.side_effect = VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="AI extraction service returned an error.",
        )
        front_data = _create_test_image()
        back_data = _create_test_image()
        response = client.post(
            "/extract",
            files={
                "front": ("front.png", front_data, "image/png"),
                "back": ("back.png", back_data, "image/png"),
            },
        )
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert data["error"]["code"] == "AI_EXTRACTION_FAILED"

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_successful_extraction_has_data_and_warnings(self, mock_vision):
        """Successful extraction returns success=True with data and warnings keys."""
        from app.schemas.nid import NIDData
        mock_vision.return_value = NIDData(
            name="Md Rahim",
            fatherName="Abdul Karim",
            motherName="Amena Begum",
            dateOfBirth="1998-01-15",
            nidNumber="1234567890",
            presentAddress="Dhaka",
            permanentAddress="Dhaka",
        )
        front_data = _create_test_image()
        back_data = _create_test_image()
        response = client.post(
            "/extract",
            files={
                "front": ("front.png", front_data, "image/png"),
                "back": ("back.png", back_data, "image/png"),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "warnings" in data
        assert isinstance(data["warnings"], list)
