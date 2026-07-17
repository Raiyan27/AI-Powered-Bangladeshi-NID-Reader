"""Tests for image and data validation logic."""
import pytest
from app.services.image_service import validate_image, ImageValidationError
from app.services.validation_service import validate_extraction
from app.schemas.nid import NIDData


class TestImageValidation:
    """Test image validation rules."""

    def test_reject_unsupported_format(self):
        with pytest.raises(ImageValidationError) as exc:
            validate_image(b"fake data", "test.gif")
        assert exc.value.code == "INVALID_IMAGE_FORMAT"

    def test_reject_bmp_format(self):
        with pytest.raises(ImageValidationError) as exc:
            validate_image(b"fake data", "test.bmp")
        assert exc.value.code == "INVALID_IMAGE_FORMAT"

    def test_reject_empty_extension(self):
        with pytest.raises(ImageValidationError) as exc:
            validate_image(b"fake data", "noextension")
        assert exc.value.code == "INVALID_IMAGE_FORMAT"

    def test_reject_corrupted_file(self):
        with pytest.raises(ImageValidationError) as exc:
            validate_image(b"not an image at all", "test.png")
        assert exc.value.code == "INVALID_IMAGE_FORMAT"

    def test_reject_oversized_file(self):
        """File larger than max_upload_size_mb should be rejected."""
        # Create a file > 10MB
        large_data = b"x" * (11 * 1024 * 1024)
        with pytest.raises(ImageValidationError) as exc:
            validate_image(large_data, "large.png")
        assert exc.value.code == "INVALID_IMAGE_FORMAT"


class TestNIDValidation:
    """Test NID data validation."""

    def test_complete_data_no_warnings(self):
        data = NIDData(
            name="Md Rahim",
            fatherName="Abdul Karim",
            motherName="Amena Begum",
            dateOfBirth="1998-01-15",
            nidNumber="1234567890123",
            presentAddress="Dhaka, Bangladesh",
            permanentAddress="Cumilla, Bangladesh",
        )
        warnings = validate_extraction(data)
        assert len(warnings) == 0

    def test_missing_fields_generate_warnings(self):
        data = NIDData(name="Md Rahim")
        warnings = validate_extraction(data)
        assert any("Father's name" in w for w in warnings)
        assert any("Mother's name" in w for w in warnings)
        assert any("NID number" in w for w in warnings)

    def test_invalid_nid_number_format(self):
        data = NIDData(
            name="Test",
            nidNumber="12345",  # Invalid: not 10, 13, or 17 digits
        )
        warnings = validate_extraction(data)
        assert any("NID number" in w and "invalid" in w for w in warnings)

    def test_valid_nid_number_formats(self):
        # 10 digits
        data = NIDData(name="Test", nidNumber="1234567890")
        warnings = validate_extraction(data)
        assert not any("NID number" in w and "invalid" in w for w in warnings)

        # 13 digits
        data = NIDData(name="Test", nidNumber="1234567890123")
        warnings = validate_extraction(data)
        assert not any("NID number" in w and "invalid" in w for w in warnings)

        # 17 digits
        data = NIDData(name="Test", nidNumber="12345678901234567")
        warnings = validate_extraction(data)
        assert not any("NID number" in w and "invalid" in w for w in warnings)

    def test_invalid_date_format(self):
        data = NIDData(name="Test", dateOfBirth="15-01-1998")
        warnings = validate_extraction(data)
        assert any("Date of birth" in w for w in warnings)

    def test_valid_date_format(self):
        data = NIDData(name="Test", dateOfBirth="1998-01-15")
        warnings = validate_extraction(data)
        assert not any("Date of birth" in w and "format" in w for w in warnings)

    def test_empty_string_treated_as_missing(self):
        data = NIDData(name="", fatherName="  ")
        warnings = validate_extraction(data)
        assert any("Name" in w and "could not be detected" in w for w in warnings)
        assert any("Father's name" in w for w in warnings)
