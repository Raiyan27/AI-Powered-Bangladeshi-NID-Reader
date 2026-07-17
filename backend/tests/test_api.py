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
        data = response.json()
        assert data["status"] == "ok"


class TestExtractEndpoint:
    """Test the /extract endpoint validation."""

    def test_missing_front_image(self):
        back_data = _create_test_image()
        response = client.post(
            "/extract",
            files={"back": ("back.png", back_data, "image/png")},
        )
        assert response.status_code == 422 or response.status_code == 400

    @patch("app.services.extraction_service.extract_with_vision", new_callable=AsyncMock)
    def test_missing_back_image(self, mock_vision):
        """Omitting the back image is now allowed and treated as a single NID image upload."""
        from app.schemas.nid import NIDData
        mock_vision.return_value = NIDData(name="Test User")
        front_data = _create_test_image()
        response = client.post(
            "/extract",
            files={"front": ("front.png", front_data, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test User"


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
