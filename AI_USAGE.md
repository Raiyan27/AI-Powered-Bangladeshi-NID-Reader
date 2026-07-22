# AI Usage Documentation

This document outlines the AI tools used during the development of the **Bangladesh NID Extractor** project, providing sample prompts, verification methodologies, and detailed explanations of manual code modifications.

---

## 1. AI Tools Used

| Tool / Model | Category | Primary Use Case |
|---|---|---|
| **Antigravity (Google DeepMind)** | Agentic AI Coding Assistant | Full repository scaffolding, FastAPI backend architecture, Next.js UI development, Docker setup, and unit/integration test suites. |
| **Google Gemini (3.1 Flash Lite via OpenRouter)** | Runtime Vision LLM | End-to-end multimodal semantic document parsing, Bengali-to-English translation, and structured field extraction at runtime. |
| **Claude 4.6 Sonnet** | Conversational AI | Initial prompt engineering design, schema drafting, and comparative pipeline analysis (OCR vs Vision-only). |

---

## 2. Example Prompts

### Prompt 1: Architecture & Service Scaffolding
> *"Design a production-ready document extraction backend using Python 3.12, FastAPI, and OpenRouter API for processing Bangladesh National ID (NID) cards. The system must support uploading front and back images (or a single combined image), perform OpenCV image preprocessing (deskewing, contrast enhancement, auto-rotation), call a Vision LLM, normalize Bengali digits and dates, and return validated Pydantic JSON responses."*

### Prompt 2: Vision LLM System Prompt Engineering
> *"Write a precise system prompt for a Vision LLM extracting information from Bangladesh NID cards. It must handle both Bengali and English text, old laminated cards, and smart cards. Specify exact output fields (name, fatherName, motherName, spouseName, dateOfBirth, nidNumber, presentAddress, permanentAddress). Require Bengali digit conversion (০-৯ to 0-9), ISO 8601 date formatting (YYYY-MM-DD), returning null for missing fields, and strict JSON output without markdown backticks."*

### Prompt 3: Frontend Interface & Modern UI Design
> *"Build a modern, accessible Next.js App Router application using TypeScript and Tailwind CSS for NID extraction. Include a drag-and-drop file upload component for front and back images, image previews, upload progress/loading states, an interactive structured JSON viewer, and distinct alert banners for validation warnings and API errors."*

### Prompt 4: Comprehensive Test Suite & API Mocking
> *"Write unit and integration tests using pytest for a FastAPI backend. Include tests for API health endpoints, multipart file upload validation (format, file size, low resolution detection), Vision service retry logic with exponential backoff, and full extraction workflows using mocked OpenRouter API responses."*

---

## 3. Verification of AI-Generated Code

All AI-generated code underwent multi-stage verification before being integrated:

1. **Automated Unit & Integration Testing**:
   - Executed `pytest tests/ -v` covering endpoint handling, image validation guardrails, date/NID normalisation logic, and mocked API failure cases.
2. **Ground-Truth Empirical Testing**:
   - Ran extraction against real Bangladeshi NID test images (`samples/NID_front.jpg` and `samples/NID_back.jpg`).
   - Verified output JSON fields against ground truth reference files (`samples/NID.json`).
3. **Static Analysis & Code Quality Audits**:
   - Enforced type hints (`mypy` compliant patterns) and Pydantic v2 schema compliance.
   - Cleaned redundant exception handling and ensured non-blocking async execution.
4. **Container & Deployment Verification**:
   - Tested full stack deployment via `docker compose up --build`.
   - Verified CORS configuration and frontend-to-backend API communication inside isolated Docker networks.

---

## 4. Modified AI Code & Rationale

| Modified Area | Initial AI Generation | Final Manual Implementation | Reason for Modification |
|---|---|---|---|
| **Pipeline Architecture** | Dual EasyOCR + Vision LLM hybrid pipeline. | Vision LLM-only pipeline with OpenCV preprocessing. | EasyOCR added ~1 GB container bloat, 10–15s latency, and frequent misreads on Bengali numbers. Vision LLM directly read images faster and more accurately. |
| **Image Uploader Requirement** | Rigid validation requiring *both* `front` AND `back` images as separate mandatory files. | Flexible validation allowing single combined NID images (where `front` contains both sides). | Real-world users often upload a single photo containing both sides of the NID card. |
| **API Resilience** | Single `httpx` POST call without retry or error handling. | Integrated `tenacity` retry decorator with exponential backoff and `X-Request-Id` request tracing. | Handled transient OpenRouter API rate limits (`429`) and server errors (`5xx`) reliably. |
| **Field Normalisation** | Raw LLM string passthrough. | Custom regex post-processors for date standardisation (`YYYY-MM-DD`), name title-casing, and digit cleaning. | Prevented occasional LLM inconsistencies (e.g., `DD/MM/YYYY` dates or trailing spaces). |

---
