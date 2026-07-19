# Bangladesh NID Extractor

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://ai-powered-bangladeshi-nid-reader.vercel.app)

**Live Preview:** [https://ai-powered-bangladeshi-nid-reader.vercel.app](https://ai-powered-bangladeshi-nid-reader.vercel.app)

An AI-powered web application that extracts structured information from Bangladesh National ID (NID) cards. Supports Bengali, English, and mixed-text cards, including both old laminated and new smart-card formats.

## Overview

Users upload the **front** and **back** images of an NID card (or a single combined image). The system:

1. **Validates** the images (format, size, dimensions)
2. **Preprocesses** them using OpenCV + Pillow (EXIF rotation, deskew, white balance, brightness normalisation, CLAHE contrast enhancement, sharpening, denoising)
3. **Analyses** both images with a Vision LLM via OpenRouter (e.g., Gemini 2.5 Flash)
4. **Normalises** field values (date format, name casing, NID digit cleanup)
5. **Returns** a structured JSON response

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
 │   └─ Format check, size limit, dimension check
 │
 ├─ Image Preprocessing (OpenCV + Pillow)
 │   └─ EXIF auto-rotate, intelligent resize, deskew
 │   └─ White balance, brightness normalisation, CLAHE contrast
 │   └─ Unsharp-mask sharpening, denoising, JPEG compression
 │
 ├─ Vision LLM (OpenRouter API)
 │   └─ Reads Bengali + English text directly from images
 │   └─ Retry with exponential backoff (configurable attempts)
 │   └─ Per-request tracing via X-Request-Id header
 │
 ├─ Normalisation Layer
 │   └─ Date → YYYY-MM-DD, NID → digits-only, names → title case
 │
 └─ Pydantic Validation + Warnings
     └─ Returns warnings for missing fields, format mismatches
```

**Why Vision AI only?**

Vision LLMs (e.g., Gemini 2.5 Flash) can read Bengali and English text directly from images with high accuracy. A separate OCR layer was previously used to provide text hints but added significant complexity, model download overhead (~1 GB for EasyOCR), and slow cold-start times without a reliable accuracy improvement over the Vision model alone.

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
│   │       ├── image_service.py   # Validation + preprocessing pipeline
│   │       ├── vision_service.py  # OpenRouter Vision API + retry logic
│   │       ├── translation_service.py  # Field normalisation
│   │       ├── extraction_service.py   # Pipeline orchestrator
│   │       └── validation_service.py   # Output validation + warnings
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
# OPENROUTER_MODEL=google/gemini-2.5-flash

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
| `OPENROUTER_MODEL` | No | `google/gemini-3.1-flash-lite` | Vision LLM model to use |
| `OPENROUTER_API_URL` | No | `https://openrouter.ai/api/v1/chat/completions` | Vision API endpoint URL |
| `APP_ENV` | No | `dev` | Environment mode (`dev` or `prod`) |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed CORS origins |
| `NEXT_PUBLIC_API_URL` | No | `http://localhost:8000` | Backend API URL for frontend |

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
- `front` — Front side image (JPG/JPEG/PNG, max 10 MB). If this is a combined front+back image, the `back` field can be omitted.
- `back` — Back side image (JPG/JPEG/PNG, max 10 MB). Optional if `front` contains both sides.

**Success Response:**
```json
{
  "success": true,
  "data": {
    "name": "Md. Junaed",
    "fatherName": "Md. Alomgir Hossain",
    "motherName": "Mst. Rina Begum",
    "spouseName": null,
    "dateOfBirth": "2005-01-15",
    "nidNumber": "9011042852",
    "presentAddress": "Bhairab Bazar, Station Road, Bhairab, Kishoreganj - 2311",
    "permanentAddress": "Bhairab Bazar, Station Road, Bhairab, Kishoreganj - 2311"
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
| `INVALID_IMAGE_FORMAT` | Wrong file format or corrupted file |
| `LOW_IMAGE_QUALITY` | Image too small or resolution too low |
| `INVALID_DOCUMENT_TYPE` | Uploaded image is not a Bangladesh NID card |
| `AI_EXTRACTION_FAILED` | Vision AI API error (after retries) |
| `INTERNAL_ERROR` | Unexpected server error |

## Testing

```bash
cd backend
pytest tests/ -v
```

The test suite includes:
- **API tests**: endpoint validation, error responses, Vision AI failure handling
- **Vision service tests**: retry logic, timeout handling, malformed responses, rate limits
- **Validation tests**: field validation, warning generation, date range checks
- **Integration tests**: full pipeline with sample NID images (Vision AI mocked)
- **Translation tests**: date normalisation, NID number cleaning

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

### Prompt Engineering

The extraction prompt is in [`backend/app/prompts/nid_extraction.txt`](backend/app/prompts/nid_extraction.txt).

Key prompt design decisions:
- Defines the AI's role as a precise document analysis specialist
- Covers both old (laminated) and new (smart card) Bangladesh NID formats explicitly
- Contains explicit Bengali digit conversion rules (০১২৩→0123)
- Requires strict ISO date format (`YYYY-MM-DD`) for deterministic post-processing
- Instructs the model to set fields to `null` when uncertain (never guess)
- Requires JSON-only output (no markdown, no explanations)
- Handles edge cases: rotated images, glare, blur, partial crops, perspective distortion

### Verification

All generated code was verified by:
1. Running the full test suite (`pytest tests/ -v`)
2. Manual testing with `samples/NID_front.jpg` and `samples/NID_back.jpg`
3. Comparing output against `samples/NID.json` (ground truth)
4. Reviewing each service file for correctness, type safety, and edge cases

### Manual Modifications

- Migrated from EasyOCR + merge pipeline to Vision AI-only architecture
- Added retry with exponential backoff for transient API failures
- Added per-request UUID tracing for debugging
- Enhanced preprocessing with white balance, gamma normalisation, and sharpening
- Prompt redesigned from scratch to remove OCR text dependencies
