# Bangladesh NID Extractor

AI-powered application that extracts information from both sides of a Bangladesh National ID (NID) card and returns structured data in English.

## Overview

This application uses a hybrid AI pipeline combining:
- **PaddleOCR** for raw text extraction with confidence scoring
- **Vision LLM** (via OpenRouter) for semantic understanding and translation
- **OpenCV** for image preprocessing and quality enhancement

Users upload front and back images of an NID card. The system processes both sides, extracts key fields, and returns structured JSON with all text translated to English.

## Architecture

```
User → Web Interface → FastAPI REST API
                            │
                    ┌───────┴───────┐
                    │               │
              Image Validation   Request Mgmt
                    │
              Image Preprocessing
              (OpenCV + Pillow)
                    │
              ┌─────┴─────┐
              │            │
          PaddleOCR    Vision LLM
          (raw text)   (semantic)
              │            │
              └─────┬──────┘
                    │
            Merge & Validation
                    │
              JSON Response
```

### Pipeline Details

1. **Image Validation**: Checks format, size, dimensions, corruption
2. **Preprocessing**: Auto-rotate, deskew, contrast enhancement, denoising
3. **PaddleOCR**: Extracts raw text with bounding boxes and confidence scores
4. **Vision AI**: Analyzes images with OCR context for semantic extraction
5. **Merge Layer**: Combines results — OCR preferred for numbers, AI for names/addresses
6. **Validation**: Checks completeness, generates warnings for missing fields

## Extracted Fields

| Field | Description |
|-------|------------|
| name | Full name (English) |
| fatherName | Father's name (English) |
| motherName | Mother's name (English) |
| dateOfBirth | Date of birth (YYYY-MM-DD) |
| nidNumber | National ID number |
| presentAddress | Present address (English) |
| permanentAddress | Permanent address (English) |

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.12, FastAPI, Pydantic v2 |
| OCR | PaddleOCR |
| Image Processing | OpenCV, Pillow |
| AI Model | OpenRouter API (configurable model) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Deployment | Docker, Docker Compose |

## Installation

### Prerequisites
- Docker and Docker Compose
- OpenRouter API key ([get one here](https://openrouter.ai/keys))

### Quick Start (Docker)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd IDLC-TAP-task
   ```

2. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenRouter API key
   ```

3. Run with Docker:
   ```bash
   docker compose up --build
   ```

4. Open `http://localhost:3000` in your browser

### Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|------------|
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key |
| `OPENROUTER_MODEL` | No | `google/gemini-2.5-flash` | Vision model to use |

Additional configuration is in `config.yaml` at the project root.

## API Documentation

### Health Check
```
GET /health

Response: { "status": "ok" }
```

### Extract NID Information
```
POST /extract
Content-Type: multipart/form-data

Parameters:
  front: (file) Front side image of NID card
  back:  (file) Back side image of NID card
```

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
    "permanentAddress": "Cumilla, Bangladesh"
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
    "message": "Unsupported file format. Supported: jpg, jpeg, png."
  }
}
```

### Error Codes

| Code | Description |
|------|------------|
| `MISSING_FRONT_IMAGE` | Front image not provided |
| `MISSING_BACK_IMAGE` | Back image not provided |
| `INVALID_IMAGE_FORMAT` | Unsupported or corrupted file |
| `LOW_IMAGE_QUALITY` | Image too small or unreadable |
| `OCR_FAILED` | OCR engine failure |
| `AI_EXTRACTION_FAILED` | Vision AI failure |

## Configuration

The `config.yaml` file at the project root controls both frontend and backend settings:

```yaml
backend:
  max_upload_size_mb: 10
  supported_formats: [jpg, jpeg, png]

ocr:
  languages: [en, bn]
  confidence_threshold: 0.5

vision:
  default_model: "google/gemini-2.5-flash"
  temperature: 0.1
```

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

## AI Usage Documentation

### AI Tools Used During Development
- **Antigravity (Gemini)**: Primary AI coding assistant used for code generation and architecture design
- **OpenRouter API**: Runtime AI for NID card analysis (Vision LLM)

### How AI-Generated Code Was Verified
- All generated code was reviewed for correctness and security
- API contracts were validated against the specification
- Unit tests were written to verify validation and merge logic
- End-to-end testing with sample NID images
- Error handling paths were manually verified

### What Was Modified
- Image preprocessing parameters tuned for NID card characteristics
- Merge strategy refined based on OCR confidence behavior
- Prompt template iterated for accurate Bengali-to-English translation
- Security checks added for file uploads

## License

This project was built as a technical assessment for IDLC TAP.
