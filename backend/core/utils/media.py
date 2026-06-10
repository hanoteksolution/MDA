import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def resolve_product_image_url(image: str, request=None) -> str:
    """Return a browser-usable URL for a product image path or external URL."""
    if not image:
        return ""
    if image.startswith("http://") or image.startswith("https://"):
        return image
    path = image if image.startswith("/") else f"{settings.MEDIA_URL.rstrip('/')}/{image.lstrip('/')}"
    if not path.startswith("/"):
        path = f"/{path}"
    if request:
        return request.build_absolute_uri(path)
    return path


def save_product_image(*, uploaded_file) -> str:
    content_type = getattr(uploaded_file, "content_type", "") or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError("Invalid image type. Use JPEG, PNG, WebP, or GIF.")

    if uploaded_file.size > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 5 MB or smaller.")

    ext = Path(uploaded_file.name).suffix.lower().lstrip(".")
    if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
        ext = "jpg"
    filename = f"products/{uuid.uuid4().hex}.{ext}"
    saved_path = default_storage.save(filename, uploaded_file)
    return default_storage.url(saved_path)
