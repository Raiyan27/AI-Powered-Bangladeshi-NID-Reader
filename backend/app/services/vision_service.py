import json
import re
from pathlib import Path

import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.nid import NIDData
from app.services.image_service import ImageValidationError
from app.utils.image_utils import image_to_base64


class VisionExtractionError(Exception):
    """Raised when Vision AI extraction fails."""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _load_prompt_template() -> str:
    """Load the NID extraction prompt template from file."""
    prompt_path = Path(__file__).parent.parent / "prompts" / "nid_extraction.txt"
    return prompt_path.read_text(encoding="utf-8")


def _clean_json_response(content: str) -> str:
    """Strip markdown code fences and extra whitespace from model response.

    Vision models sometimes wrap JSON in ```json ... ``` blocks despite
    instructions not to. This strips those fences defensively.
    """
    content = content.strip()

    # Remove ```json ... ``` or ``` ... ``` fences
    content = re.sub(r"^```(?:json)?\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    content = content.strip()

    return content


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

    # Build prompt with OCR context
    prompt_template = _load_prompt_template()
    prompt = prompt_template.format(
        front_ocr_text=front_ocr_text or "(No text detected by OCR)",
        back_ocr_text=back_ocr_text or "(No text detected by OCR)",
    )

    # Encode images to base64 for the multimodal API
    front_b64 = image_to_base64(front_image_bytes)
    back_b64 = image_to_base64(back_image_bytes)

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
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json=payload,
                headers=headers,
            )

        if response.status_code != 200:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text[:500]}")
            raise VisionExtractionError(
                code="AI_EXTRACTION_FAILED",
                message="AI extraction service returned an error. Please try again.",
            )

        response_data = response.json()
        raw_content = response_data["choices"][0]["message"]["content"]

        logger.info("Vision AI response received, parsing JSON")
        logger.debug(f"Raw Vision AI response: {raw_content[:300]}")

        content = _clean_json_response(raw_content)

        nid_dict = json.loads(content)

        # Check if the document is a valid Bangladesh NID card
        is_nid = nid_dict.get("isBangladeshNID")
        
        # If explicitly false, or if it is null/missing and all fields are empty, raise error
        has_substantive_data = any(
            nid_dict.get(field) is not None and str(nid_dict.get(field)).strip() != ""
            for field in ["name", "nidNumber", "dateOfBirth"]
        )
        
        if is_nid is False or (is_nid is None and not has_substantive_data):
            raise ImageValidationError(
                code="INVALID_DOCUMENT_TYPE",
                message="The uploaded image is not a valid Bangladesh National ID (NID) card. Please upload a valid NID image."
            )

        # Only pass known NIDData fields to avoid unexpected key errors
        known_fields = {
            "name", "fatherName", "motherName",
            "dateOfBirth", "nidNumber", "presentAddress", "permanentAddress",
        }
        filtered = {k: v for k, v in nid_dict.items() if k in known_fields}

        return NIDData(**filtered)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Vision AI response as JSON: {e}")
        logger.error(f"Unparseable content: {raw_content[:500] if 'raw_content' in dir() else '(unavailable)'}")
        raise VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="AI model returned an unparseable response. Please try again.",
        )
    except ImageValidationError:
        raise
    except VisionExtractionError:
        raise
    except Exception as e:
        logger.error(f"Vision AI extraction failed: {e}", exc_info=True)
        raise VisionExtractionError(
            code="AI_EXTRACTION_FAILED",
            message="AI extraction failed. Please try again.",
        )
