from pydantic import BaseModel


class NIDData(BaseModel):
    """Extracted NID card information."""
    name: str | None = None
    fatherName: str | None = None
    motherName: str | None = None
    dateOfBirth: str | None = None
    nidNumber: str | None = None
    presentAddress: str | None = None
    permanentAddress: str | None = None


class OCRResult(BaseModel):
    """Single OCR detection result."""
    text: str
    confidence: float
    position: list[float] = []


class OCROutput(BaseModel):
    """Complete OCR output for one image."""
    results: list[OCRResult] = []
    raw_text: str = ""
    avg_confidence: float = 0.0
