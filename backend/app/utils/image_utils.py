from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_image(data: bytes) -> str:
    if not data:
        raise ValueError("The uploaded image is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 10 MB or smaller.")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
            if image.format not in ALLOWED_FORMATS:
                raise ValueError("Upload a JPEG, PNG, or WebP image.")
            return Image.MIME[image.format]
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Upload a valid JPEG, PNG, or WebP image.") from exc

