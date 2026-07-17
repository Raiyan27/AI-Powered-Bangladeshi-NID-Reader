import json
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.nid import NIDData
from app.utils.image_utils import image_to_base64


class VisionExtractionError(Exception):
    """Raised when Vision AI extraction fails."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _load_prompt_template() -> str:
    """Load the NID extraction prompt template."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "nid_extraction.txt"
    return prompt_path.read_text(encoding="utf-8")


async def extract_with_vision(
    front_image_bytes: bytes,
    back_image_bytes: bytes,
    front_ocr_text: str,
    back_ocr_text: str,
) -> NIDData:
    """Send images + OCR text to OpenRouter Vision API and extract NID data.

    Uses the configured model to analyze both NID card sides and return
    structured extraction results.
    """
    settings = get_settings()

    if not settings.openrouter_api_key:
        raise VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="OpenRouter API key is not configured.",
        )

    # Build prompt with OCR text
    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        front_ocr_text=front_ocr_text or "(No text detected)",
        back_ocr_text=back_ocr_text or "(No text detected)",
    )

    # Encode images as base64
    front_b64 = image_to_base64(front_image_bytes)
    back_b64 = image_to_base64(back_image_bytes)

    # Build OpenRouter API request
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
                        "image_url": {
                            "url": f"data:image/png;base64,{front_b64}",
                        },
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{back_b64}",
                        },
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
    }

    logger.info(f"Sending Vision AI request to OpenRouter (model: {settings.model})")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            )

        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            raise VisionExtractionError(
                code="AI_EXTRACTION_FAILED",
                message="AI extraction service returned an error. Please try again.",
            )

        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]

        logger.info("Vision AI response received, parsing JSON")

        # Clean response - remove markdown code fences if present
        content = content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()

        nid_data = json.loads(content)
        return NIDData(**nid_data)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Vision AI response as JSON: {e}")
        raise VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="AI model returned an unparseable response.",
        )
    except VisionExtractionError:
        raise
    except Exception as e:
        logger.error(f"Vision AI extraction failed: {e}")
        raise VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="AI extraction failed. Please try again.",
        )
