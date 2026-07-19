import asyncio
import json
import re
import uuid
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.nid import NIDData
from app.services.image_service import ImageValidationError
from app.utils.image_utils import image_to_base64


class VisionExtractionError(Exception):
    """Raised when Vision AI extraction fails unrecoverably."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _load_prompt() -> str:
    """Load the NID extraction prompt from file."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "nid_extraction.txt"
    return prompt_path.read_text(encoding="utf-8")


def _clean_json_response(content: str) -> str:
    """Strip markdown code fences and extra whitespace from model response.

    Vision models sometimes wrap JSON in ```json ... ``` blocks despite
    instructions not to. This strips those fences defensively.
    """
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    return content.strip()


async def extract_with_vision(
    front_image_bytes: bytes,
    back_image_bytes: bytes,
) -> NIDData:
    """Send NID card images to the OpenRouter Vision API and return extracted data.

    Implements retry with exponential backoff for transient failures (5xx, 429,
    timeouts). Raises VisionExtractionError on permanent failure after all retries.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="OpenRouter API key is not configured.",
        )

    prompt = _load_prompt()
    front_b64 = image_to_base64(front_image_bytes)
    back_b64 = image_to_base64(back_image_bytes)
    request_id = uuid.uuid4().hex[:12]

    payload = {
        "model": settings.model,
        "max_tokens": settings.vision.max_tokens,
        "temperature": settings.vision.temperature,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{front_b64}"},
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{back_b64}"},
                    },
                ],
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://nid-extractor.local",
        "X-Title": "Bangladesh NID Extractor",
        "X-Request-Id": request_id,
    }

    logger.info(
        f"Vision AI request started (id={request_id}, model={settings.model}, "
        f"attempts_allowed={settings.vision.retry_attempts})"
    )

    last_error: Exception | None = None

    for attempt in range(1, settings.vision.retry_attempts + 1):
        try:
            raw_content = await _call_api(payload, headers, settings.vision.timeout_s, request_id, attempt, settings.vision_api_url)
            return _parse_response(raw_content, request_id)

        except VisionExtractionError:
            raise  # Permanent errors — do not retry

        except ImageValidationError:
            raise  # Non-NID document — do not retry

        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_error = e
            logger.warning(f"[{request_id}] Attempt {attempt} failed (network/timeout): {e}")

        except _RetryableError as e:
            last_error = e
            logger.warning(f"[{request_id}] Attempt {attempt} failed (retryable {e.status_code}): {e.message}")

        if attempt < settings.vision.retry_attempts:
            delay = settings.vision.retry_delay_s * (2 ** (attempt - 1))  # Exponential backoff
            logger.info(f"[{request_id}] Retrying in {delay:.1f}s (attempt {attempt + 1}/{settings.vision.retry_attempts})")
            await asyncio.sleep(delay)

    logger.error(f"[{request_id}] All {settings.vision.retry_attempts} attempts exhausted. Last error: {last_error}")
    raise VisionExtractionError(
        code="AI_EXTRACTION_FAILED",
        message="AI extraction failed after multiple retries. Please try again later.",
    )


class _RetryableError(Exception):
    """Internal signal for retryable HTTP errors."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


async def _call_api(payload: dict, headers: dict, timeout_s: float, request_id: str, attempt: int, api_url: str) -> str:
    """Perform a single HTTP call to OpenRouter. Returns raw response content string."""
    timeout = httpx.Timeout(connect=10.0, read=timeout_s, write=30.0, pool=5.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            api_url,
            json=payload,
            headers=headers,
        )

    logger.info(f"[{request_id}] Attempt {attempt}: HTTP {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        raw_content: str = data["choices"][0]["message"]["content"]
        logger.debug(f"[{request_id}] Raw response preview: {raw_content[:200]}")
        return raw_content

    if response.status_code == 429:
        raise _RetryableError(429, "Rate limit reached")

    if response.status_code >= 500:
        raise _RetryableError(response.status_code, f"Server error: {response.text[:200]}")

    # 4xx errors other than 429 are permanent
    logger.error(f"[{request_id}] Permanent API error {response.status_code}: {response.text[:300]}")
    raise VisionExtractionError(
        code="AI_EXTRACTION_FAILED",
        message="AI extraction service returned an error. Please check your API key and model configuration.",
    )


def _parse_response(raw_content: str, request_id: str) -> NIDData:
    """Parse the Vision AI JSON response into NIDData."""
    content = _clean_json_response(raw_content)

    try:
        nid_dict = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"[{request_id}] JSON parse error: {e}. Content: {content[:300]}")
        raise VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="AI model returned an unparseable response. Please try again.",
        )

    # Validate front and back document types separately
    is_front_nid = nid_dict.get("isFrontBangladeshNID")
    is_back_nid = nid_dict.get("isBackBangladeshNID")

    has_front_data = any(
        nid_dict.get(f) not in (None, "")
        for f in ["name", "nidNumber", "dateOfBirth"]
    )
    has_back_data = any(
        nid_dict.get(f) not in (None, "")
        for f in ["address", "presentAddress", "permanentAddress"]
    )

    front_invalid = is_front_nid is False or (is_front_nid is None and not has_front_data)
    back_invalid = is_back_nid is False or (is_back_nid is None and not has_back_data)

    if front_invalid and back_invalid:
        raise ImageValidationError(
            code="INVALID_DOCUMENT_TYPE",
            message="The uploaded images are not valid Bangladesh NID card sides. Please upload valid NID images.",
        )
    elif front_invalid:
        raise ImageValidationError(
            code="INVALID_FRONT_IMAGE",
            message="The front image is not a valid Bangladesh NID front side. Please reupload the front image.",
        )
    elif back_invalid:
        raise ImageValidationError(
            code="INVALID_BACK_IMAGE",
            message="The back image is not a valid Bangladesh NID back side. Please reupload the back image.",
        )

    known_fields = {
        "name", "fatherName", "motherName", "spouseName",
        "dateOfBirth", "nidNumber",
        "address", "presentAddress", "permanentAddress",
    }
    filtered = {k: v for k, v in nid_dict.items() if k in known_fields}
    logger.info(f"[{request_id}] Parsed fields: {list(k for k, v in filtered.items() if v is not None)}")
    return NIDData(**filtered)
