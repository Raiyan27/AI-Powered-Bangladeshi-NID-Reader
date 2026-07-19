from pydantic import BaseModel


class NIDData(BaseModel):
    """Extracted NID card information."""
    name: str | None = None
    fatherName: str | None = None
    motherName: str | None = None
    spouseName: str | None = None
    dateOfBirth: str | None = None
    nidNumber: str | None = None
    address: str | None = None
    presentAddress: str | None = None
    permanentAddress: str | None = None
    bloodGroup: str | None = None
