import uuid
import re


def generate_safe_filename(original_filename: str) -> str:
    """Generate a safe filename preserving extension."""
    ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "png"
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    return safe_name


def get_file_extension(filename: str) -> str:
    """Extract lowercase file extension without dot."""
    if "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return ""


def sanitize_filename(filename: str) -> str:
    """Remove potentially dangerous characters from filename."""
    return re.sub(r'[^\w\-.]', '_', filename)
