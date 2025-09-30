# services/validators.py
# Validators for service-related fields

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from PIL import Image


def validate_image_file_extension(value):
    """Validate that the uploaded file is an image with an allowed extension.

    Args:
        value: Uploaded file

    Raises:
        ValidationError: If file extension is not allowed

    """
    allowed_extensions = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ext = value.name.lower().split(".")[-1]

    if f".{ext}" not in allowed_extensions:
        raise ValidationError(
            _(
                "Unsupported file extension. Allowed extensions are: jpg, jpeg, png, gif, webp.",
            ),
            code="unsupported_file_extension",
        )


def validate_image_file_size(value):
    """Validate that the uploaded image file size is within limits.

    Args:
        value: Uploaded file

    Raises:
        ValidationError: If file size exceeds limit

    """
    max_size_mb = 5  # Maximum file size in MB
    max_size_bytes = max_size_mb * 1024 * 1024

    if value.size > max_size_bytes:
        raise ValidationError(
            _(
                "File size must be under %(max_size)d MB. Current file size is %(current_size)d MB.",
            ),
            code="file_size_exceeded",
            params={
                "max_size": max_size_mb,
                "current_size": round(value.size / (1024 * 1024), 2),
            },
        )


def validate_image_dimensions(value):
    """Validate that the uploaded image dimensions are within limits.

    Args:
        value: Uploaded file

    Raises:
        ValidationError: If image dimensions exceed limits

    """
    max_width = 2000  # Maximum width in pixels
    max_height = 2000  # Maximum height in pixels

    try:
        # Open image to check dimensions
        image = Image.open(value)
        width, height = image.size

        if width > max_width or height > max_height:
            raise ValidationError(
                _(
                    "Image dimensions must be under %(max_width)sx%(max_height)s pixels. "
                    "Current dimensions are %(width)sx%(height)s pixels.",
                ),
                code="image_dimensions_exceeded",
                params={
                    "max_width": max_width,
                    "max_height": max_height,
                    "width": width,
                    "height": height,
                },
            )
    except Exception:
        # If we can't open the image, it's probably not a valid image file
        raise ValidationError(
            _("Invalid image file. Please upload a valid image."),
            code="invalid_image_file",
        )


def validate_image_aspect_ratio(value):
    """Validate that the uploaded image has an acceptable aspect ratio.

    Args:
        value: Uploaded file

    Raises:
        ValidationError: If aspect ratio is outside acceptable range

    """
    min_ratio = 0.5  # Minimum aspect ratio (portrait)
    max_ratio = 2.0  # Maximum aspect ratio (landscape)

    try:
        # Open image to check aspect ratio
        image = Image.open(value)
        width, height = image.size
        aspect_ratio = width / height

        if aspect_ratio < min_ratio or aspect_ratio > max_ratio:
            raise ValidationError(
                _(
                    "Image aspect ratio must be between %(min_ratio)s and %(max_ratio)s. "
                    "Current aspect ratio is %(aspect_ratio)s.",
                ),
                code="invalid_aspect_ratio",
                params={
                    "min_ratio": min_ratio,
                    "max_ratio": max_ratio,
                    "aspect_ratio": round(aspect_ratio, 2),
                },
            )
    except Exception:
        # If we can't open the image, it's probably not a valid image file
        raise ValidationError(
            _("Invalid image file. Please upload a valid image."),
            code="invalid_image_file",
        )
