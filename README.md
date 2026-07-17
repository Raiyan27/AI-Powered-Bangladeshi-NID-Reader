# Bangladesh NID Extractor

An AI-powered web application that extracts structured information from Bangladesh National ID (NID) cards. Supports Bengali, English, and mixed-text cards.

## Overview

Users upload the **front** and **back** images of an NID card. The system:
1. **Validates** the images (format, size, dimensions)
2. **Preprocesses** them using OpenCV (deskew, denoise, contrast enhancement)
3. **Runs OCR** with EasyOCR to extract raw Bengali + English text and confidence scores
4. **Analyzes** both images with a Vision LLM via OpenRouter (e.g., Gemini 2.5 Flash)
5. **Merges** OCR and AI results using a confidence-based strategy
6. **Normalizes** field values (date format, name casing, NID digit cleanup)
7. **Returns** a structured JSON response

## Architecture

```
User
 │
 ▼
Next.js Frontend (TypeScript + Tailwind CSS)
 │
 │  POST /extract  (multipart/form-data)
 ▼
FastAPI Backend
 │
 ├─ Image Validation (Pillow)
 ├─ Image Preprocessing (OpenCV + Pillow)
 │   └─ Auto-rotate, resize, deskew, CLAHE contrast, denoise
 │
 ├─ EasyOCR Engine (Bengali + English)
 │   └─ Text + bounding boxes + confidence scores
 │
 ├─ Vision LLM (OpenRouter API)
 │   └─ Reads Bengali + English text from images
 │   └─ Uses OCR as supporting reference
 │
 ├─ Merge Layer
 │   └─ Numeric fields (NID#, DOB): prefer high-confidence OCR
 │   └─ Text fields (names, addresses): prefer Vision AI
 │
 ├─ Translation/Normalization Layer
 │   └─ Date → YYYY-MM-DD, NID → digits-only, names → title case
 │
 └─ Pydantic Validation + Warnings
     └─ Returns warnings for missing fields, format mismatches
```

**Why both OCR and Vision AI?**
- EasyOCR is fast and supports both Bengali and English natively for structured fields like NID numbers and dates
- Vision LLMs (e.g., Gemini) excel at understanding Bengali semantics, names, and addresses
- Combining both gives higher accuracy than either alone

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # FastAPI endpoints
│   │   ├── core/config.py         # Settings from YAML + env vars
│   │   ├── core/logging.py        # Structured logging
│   │   ├── prompts/nid_extraction.txt  # Vision AI prompt
│   │   ├── schemas/               # Pydantic models
│   │   └── services/
│   │       ├── image_service.py   # Validation + preprocessing
│   │       ├── ocr_service.py     # EasyOCR wrapper (Bengali + English)
│   │       ├── vision_service.py  # OpenRouter Vision API
│   │       ├── merge_service.py   # Merge strategy
│   │       ├── translation_service.py  # Normalization
│   │       ├── extraction_service.py   # Pipeline orchestrator
│   │       └── validation_service.py   # Output validation
│   ├── tests/                     # Pytest unit + integration tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx               # Main upload page
│   │   ├── layout.tsx             # App layout + SEO
│   │   └── components/
│   │       ├── FileUpload.tsx     # Drag & drop image uploader
│   │       ├── ResultViewer.tsx   # Structured result display
│   │       └── ErrorDisplay.tsx   # Error + warnings display
│   └── Dockerfile
│
├── samples/
│   ├── NID.jpg          # Original NID sample (front + back combined)
│   ├── NID_front.jpg    # Split front image for testing
│   ├── NID_back.jpg     # Split back image for testing
│   └── NID.json         # Expected extraction output for the sample
│
├── config.yaml          # Application configuration
├── docker-compose.yml   # Docker orchestration
└── .env.example         # Environment variable template
```

## Installation (Local Development)

### Prerequisites

- Python 3.12+
- Node.js 20+
- An [OpenRouter](https://openrouter.ai/) API key

### Backend

```bash
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
copy .env.example .env
# Edit .env and set OPENROUTER_API_KEY and OPENROUTER_MODEL

# Start the backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install

# Set the API URL for local development
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start the dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Docker Setup

```bash
# 1. Copy the environment file
copy .env.example .env

# 2. Set your API key in .env
# OPENROUTER_API_KEY=your_key_here
# OPENROUTER_MODEL=google/gemini-3.1-flash-lite

# 3. Build and start everything
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | Yes | — | Your OpenRouter API key |
| `OPENROUTER_MODEL` | No | `google/gemini-3.1-flash-lite` | Vision model to use |

## API Documentation

### `GET /health`

Returns service health status.

```json
{ "status": "ok" }
```

### `POST /extract`

Extracts NID information from uploaded images.

**Content-Type:** `multipart/form-data`

**Fields:**
- `front` — Front side image (JPG/JPEG/PNG, max 10 MB)
- `back` — Back side image (JPG/JPEG/PNG, max 10 MB)

**Success Response:**
```json
{
  "success": true,
  "data": {
    "name": "Md Rahim",
    "fatherName": "Abdul Karim",
    "motherName": "Amena Begum",
    "dateOfBirth": "1998-01-15",
    "nidNumber": "1234567890123",
    "presentAddress": "Dhaka, Bangladesh",
    "permanentAddress": "Dhaka, Bangladesh"
  },
  "warnings": []
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_IMAGE_FORMAT",
    "message": "Unsupported file format '.gif'. Supported: jpg, jpeg, png."
  }
}
```

**Error Codes:**

| Code | Description |
|---|---|
| `MISSING_FRONT_IMAGE` | Front image not provided |
| `MISSING_BACK_IMAGE` | Back image not provided |
| `INVALID_IMAGE_FORMAT` | Wrong file format or corrupted file |
| `LOW_IMAGE_QUALITY` | Image too small or resolution too low |
| `OCR_FAILED` | EasyOCR could not process the image |
| `AI_EXTRACTION_FAILED` | Vision AI API error |
| `INTERNAL_ERROR` | Unexpected server error |

## Testing

```bash
cd backend
pytest tests/ -v
```

The test suite includes:
- **API tests**: endpoint validation, error responses
- **Merge tests**: OCR + Vision AI merge logic
- **Validation tests**: field validation, warning generation
- **Integration tests**: full pipeline with sample NID images (Vision AI mocked)
- **Translation tests**: date normalization, NID number cleaning

## Testing with the Sample NID

The `samples/` directory contains a real NID card image (already split into front/back):

```bash
# Using curl
curl -X POST http://localhost:8000/extract \
  -F "front=@samples/NID_front.jpg" \
  -F "back=@samples/NID_back.jpg"
```

Expected output is in `samples/NID.json`.

## AI Usage Documentation

### AI Tools Used During Development

- **Antigravity (Google DeepMind)** — Used for code generation, architecture planning, and iterative refinement
- **OpenRouter / Gemini 2.5 Flash** — Used as the Vision LLM for NID information extraction at runtime

### Prompts Used

The extraction prompt is in [`backend/app/prompts/nid_extraction.txt`](backend/app/prompts/nid_extraction.txt).

Key prompt engineering decisions:
- Instructed the model to prefer image content over OCR text (OCR is reference only)
- Provided concrete Bengali → English transliteration examples from the sample card
- Required strict ISO date format (`YYYY-MM-DD`) to simplify post-processing
- Required JSON-only output (no markdown, no explanations)

### Verification

All generated code was verified by:
1. Running the full test suite (`pytest tests/ -v`)
2. Manual testing with `samples/NID_front.jpg` and `samples/NID_back.jpg`
3. Comparing output against `samples/NID.json` (ground truth)
4. Reviewing each service file for correctness, type safety, and edge cases

### Manual Modifications

- OCR service: migrated from PaddleOCR (English-only) to EasyOCR (Bengali + English) for native multilingual support
- Merge service: tuned confidence thresholds and warning messages
- Prompt: multiple iterations to improve Bengali name transliteration accuracy
- Translation service: added date normalization for `DD Mon YYYY` format (common Vision AI output)
