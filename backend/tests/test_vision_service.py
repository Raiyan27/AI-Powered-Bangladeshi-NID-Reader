"""Tests for the Vision AI service — retry, timeout, parsing, and error handling."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.vision_service import (
    VisionExtractionError,
    _clean_json_response,
    _parse_response,
    extract_with_vision,
)
from app.services.image_service import ImageValidationError
from app.schemas.nid import NIDData


# ---------------------------------------------------------------------------
# _clean_json_response
# ---------------------------------------------------------------------------

class TestCleanJsonResponse:
    def test_strips_json_fence(self):
        raw = "```json\n{\"name\": \"Test\"}\n```"
        assert _clean_json_response(raw) == '{"name": "Test"}'

    def test_strips_plain_fence(self):
        raw = "```\n{\"name\": \"Test\"}\n```"
        assert _clean_json_response(raw) == '{"name": "Test"}'

    def test_passthrough_plain_json(self):
        raw = '{"name": "Test"}'
        assert _clean_json_response(raw) == '{"name": "Test"}'

    def test_strips_whitespace(self):
        raw = "   {\"name\": \"Test\"}   "
        assert _clean_json_response(raw) == '{"name": "Test"}'


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------

class TestParseResponse:
    def _valid_payload(self, **overrides) -> str:
        data = {
            "isFrontBangladeshNID": True,
            "isBackBangladeshNID": True,
            "name": "Md Rahim",
            "fatherName": "Abdul Karim",
            "motherName": "Amena Begum",
            "spouseName": None,
            "dateOfBirth": "1998-01-15",
            "nidNumber": "1234567890",
            "presentAddress": "Dhaka",
            "permanentAddress": "Dhaka",
        }
        data.update(overrides)
        return json.dumps(data)

    def test_valid_response_parsed_correctly(self):
        result = _parse_response(self._valid_payload(), "req123")
        assert result.name == "Md Rahim"
        assert result.nidNumber == "1234567890"

    def test_spouse_name_extracted(self):
        payload = self._valid_payload(spouseName="Fatema Begum")
        result = _parse_response(payload, "req123")
        assert result.spouseName == "Fatema Begum"

    def test_blood_group_extracted(self):
        payload = self._valid_payload(bloodGroup="O+")
        result = _parse_response(payload, "req123")
        assert result.bloodGroup == "O+"

    def test_non_nid_document_raises_image_validation_error(self):
        payload = json.dumps({"isFrontBangladeshNID": False, "isBackBangladeshNID": False, "name": None})
        with pytest.raises(ImageValidationError) as exc:
            _parse_response(payload, "req123")
        assert exc.value.code == "INVALID_DOCUMENT_TYPE"

    def test_invalid_front_nid_raises_front_validation_error(self):
        payload = json.dumps({"isFrontBangladeshNID": False, "isBackBangladeshNID": True, "name": None})
        with pytest.raises(ImageValidationError) as exc:
            _parse_response(payload, "req123")
        assert exc.value.code == "INVALID_FRONT_IMAGE"

    def test_invalid_back_nid_raises_back_validation_error(self):
        payload = json.dumps({"isFrontBangladeshNID": True, "isBackBangladeshNID": False, "address": None})
        with pytest.raises(ImageValidationError) as exc:
            _parse_response(payload, "req123")
        assert exc.value.code == "INVALID_BACK_IMAGE"

    def test_null_is_nid_with_no_data_raises_image_validation_error(self):
        payload = json.dumps({
            "isFrontBangladeshNID": None,
            "isBackBangladeshNID": None,
            "name": None,
            "nidNumber": None,
            "dateOfBirth": None,
            "address": None
        })
        with pytest.raises(ImageValidationError):
            _parse_response(payload, "req123")

    def test_malformed_json_raises_vision_extraction_error(self):
        with pytest.raises(VisionExtractionError) as exc:
            _parse_response("this is not json", "req123")
        assert exc.value.code == "AI_EXTRACTION_FAILED"

    def test_unknown_fields_are_ignored(self):
        """Extra fields from the model should not cause errors."""
        payload = self._valid_payload(unknownField="should be ignored")
        result = _parse_response(payload, "req123")
        assert not hasattr(result, "unknownField")


# ---------------------------------------------------------------------------
# extract_with_vision — integration with retries
# ---------------------------------------------------------------------------

def _make_image() -> bytes:
    """Create a minimal valid 1x1 JPEG for testing."""
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


VALID_NID_JSON = json.dumps({
    "isFrontBangladeshNID": True,
    "isBackBangladeshNID": True,
    "name": "Md Rahim",
    "fatherName": "Abdul Karim",
    "motherName": "Amena Begum",
    "spouseName": None,
    "dateOfBirth": "1998-01-15",
    "nidNumber": "1234567890",
    "presentAddress": "Dhaka",
    "permanentAddress": "Dhaka",
})


def _mock_response(status_code: int, content: str) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = content
    mock.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    return mock


@pytest.mark.asyncio
class TestExtractWithVision:

    @patch("app.services.vision_service.get_settings")
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_missing_api_key_raises_immediately(self, mock_post, mock_settings):
        settings = MagicMock()
        settings.openrouter_api_key = ""
        mock_settings.return_value = settings

        with pytest.raises(VisionExtractionError) as exc:
            await extract_with_vision(_make_image(), _make_image())
        assert exc.value.code == "AI_EXTRACTION_FAILED"
        mock_post.assert_not_called()

    @patch("app.services.vision_service.get_settings")
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_successful_extraction(self, mock_post, mock_settings):
        settings = MagicMock()
        settings.openrouter_api_key = "test-key"
        settings.model = "test-model"
        settings.vision.max_tokens = 512
        settings.vision.temperature = 0.0
        settings.vision.timeout_s = 30.0
        settings.vision.retry_attempts = 1
        settings.vision.retry_delay_s = 0.0
        mock_settings.return_value = settings

        mock_post.return_value = _mock_response(200, VALID_NID_JSON)

        result = await extract_with_vision(_make_image(), _make_image())
        assert result.name == "Md Rahim"
        assert result.nidNumber == "1234567890"

    @patch("app.services.vision_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.vision_service.get_settings")
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_retries_on_500_then_succeeds(self, mock_post, mock_settings, mock_sleep):
        settings = MagicMock()
        settings.openrouter_api_key = "test-key"
        settings.model = "test-model"
        settings.vision.max_tokens = 512
        settings.vision.temperature = 0.0
        settings.vision.timeout_s = 30.0
        settings.vision.retry_attempts = 3
        settings.vision.retry_delay_s = 0.01
        mock_settings.return_value = settings

        # First call: 500 error; second call: success
        mock_post.side_effect = [
            _mock_response(500, "Server Error"),
            _mock_response(200, VALID_NID_JSON),
        ]

        result = await extract_with_vision(_make_image(), _make_image())
        assert result.name == "Md Rahim"
        assert mock_post.call_count == 2

    @patch("app.services.vision_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.vision_service.get_settings")
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_retries_on_429_rate_limit(self, mock_post, mock_settings, mock_sleep):
        settings = MagicMock()
        settings.openrouter_api_key = "test-key"
        settings.model = "test-model"
        settings.vision.max_tokens = 512
        settings.vision.temperature = 0.0
        settings.vision.timeout_s = 30.0
        settings.vision.retry_attempts = 3
        settings.vision.retry_delay_s = 0.01
        mock_settings.return_value = settings

        mock_post.side_effect = [
            _mock_response(429, "Rate Limited"),
            _mock_response(429, "Rate Limited"),
            _mock_response(200, VALID_NID_JSON),
        ]

        result = await extract_with_vision(_make_image(), _make_image())
        assert result.name == "Md Rahim"
        assert mock_post.call_count == 3

    @patch("app.services.vision_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.vision_service.get_settings")
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_exhausted_retries_raises_vision_error(self, mock_post, mock_settings, mock_sleep):
        settings = MagicMock()
        settings.openrouter_api_key = "test-key"
        settings.model = "test-model"
        settings.vision.max_tokens = 512
        settings.vision.temperature = 0.0
        settings.vision.timeout_s = 30.0
        settings.vision.retry_attempts = 2
        settings.vision.retry_delay_s = 0.01
        mock_settings.return_value = settings

        mock_post.side_effect = [
            _mock_response(500, "Server Error"),
            _mock_response(500, "Server Error"),
        ]

        with pytest.raises(VisionExtractionError) as exc:
            await extract_with_vision(_make_image(), _make_image())
        assert exc.value.code == "AI_EXTRACTION_FAILED"

    @patch("app.services.vision_service.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.services.vision_service.get_settings")
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_timeout_retried(self, mock_post, mock_settings, mock_sleep):
        settings = MagicMock()
        settings.openrouter_api_key = "test-key"
        settings.model = "test-model"
        settings.vision.max_tokens = 512
        settings.vision.temperature = 0.0
        settings.vision.timeout_s = 30.0
        settings.vision.retry_attempts = 2
        settings.vision.retry_delay_s = 0.01
        mock_settings.return_value = settings

        mock_post.side_effect = [
            httpx.TimeoutException("timed out"),
            _mock_response(200, VALID_NID_JSON),
        ]

        result = await extract_with_vision(_make_image(), _make_image())
        assert result.name == "Md Rahim"

    @patch("app.services.vision_service.get_settings")
    @patch("httpx.AsyncClient.post", new_callable=AsyncMock)
    async def test_permanent_4xx_not_retried(self, mock_post, mock_settings):
        """4xx errors (except 429) should not trigger retries."""
        settings = MagicMock()
        settings.openrouter_api_key = "test-key"
        settings.model = "test-model"
        settings.vision.max_tokens = 512
        settings.vision.temperature = 0.0
        settings.vision.timeout_s = 30.0
        settings.vision.retry_attempts = 3
        settings.vision.retry_delay_s = 0.01
        mock_settings.return_value = settings

        mock_post.return_value = _mock_response(401, "Unauthorized")

        with pytest.raises(VisionExtractionError):
            await extract_with_vision(_make_image(), _make_image())
        # Should only be called once — no retries on permanent errors
        assert mock_post.call_count == 1
