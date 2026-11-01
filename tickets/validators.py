from django.utils.translation import gettext_lazy as _
from pathlib import Path

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


def validate_attachment(upload):
    if upload.size > 5 * 1024 * 1024:
        raise ValidationError(_("Attachments must be 5 MB or smaller."))
    suffix = Path(upload.name).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".pdf"}:
        raise ValidationError(_("Only PNG, JPEG and PDF files are allowed."))
    try:
        if suffix == ".pdf":
            if upload.read(5) != b"%PDF-":
                raise ValidationError(_("The file is not a PDF."))
        else:
            image = Image.open(upload)
            if (
                image.format not in {"PNG", "JPEG"}
                or image.width * image.height > 25_000_000
            ):
                raise ValidationError(
                    _("Invalid image or image exceeds 25 megapixels.")
                )
            if (image.format == "PNG") != (suffix == ".png"):
                raise ValidationError(
                    _("The image content does not match its extension.")
                )
            image.verify()
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        SyntaxError,
        ValueError,
    ):
        raise ValidationError(_("The image could not be validated.")) from None
    finally:
        upload.seek(0)
    return upload
