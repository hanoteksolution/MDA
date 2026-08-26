"""Attach real product photos for demo catalog SKUs.

Downloads curated Unsplash images into media storage so the UI does not
depend on placeholder hosts (picsum/placehold are blocked by resolve_product_image_url).
Falls back to a generated JPEG when the network is unavailable.
"""

from __future__ import annotations

import io
import logging
import urllib.request
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

# Curated product photos (Unsplash) keyed by demo SKU.
DEMO_PRODUCT_IMAGE_URLS: dict[str, str] = {
    "DEMO-POS-WATER": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?auto=format&fit=crop&w=800&q=80",
    "DEMO-POS-SNACK": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=80",
    "DEMO-POS-TOWEL": "https://images.unsplash.com/photo-1631889993959-41b4e9c6e3c5?auto=format&fit=crop&w=800&q=80",
    "DEMO-POS-SHAKE": "https://images.unsplash.com/photo-1579722820308-d74e571900a9?auto=format&fit=crop&w=800&q=80",
    "DEMO-JUICE": "https://images.unsplash.com/photo-1622597467836-f3285f2131b8?auto=format&fit=crop&w=800&q=80",
    "DEMO-SODA": "https://images.unsplash.com/photo-1629203851122-3726ecdf080e?auto=format&fit=crop&w=800&q=80",
    "DEMO-CHKN": "https://images.unsplash.com/photo-1598103442097-8b74394b95c6?auto=format&fit=crop&w=800&q=80",
    "DEMO-PASTA": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?auto=format&fit=crop&w=800&q=80",
}

_PLACEHOLDER_HOSTS = (
    "picsum.photos",
    "placeholder.com",
    "placehold.co",
    "via.placeholder",
)


def _needs_image(image: str | None) -> bool:
    if not image or not str(image).strip():
        return True
    lower = str(image).lower()
    return any(host in lower for host in _PLACEHOLDER_HOSTS)


def _download_bytes(url: str, *, timeout: float = 12.0) -> bytes | None:
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "MDA-DemoSeeder/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            if data and len(data) > 500:
                return data
    except Exception as exc:  # noqa: BLE001 — seed must not fail on image fetch
        logger.warning("Demo product image download failed for %s: %s", url, exc)
    return None


def _generate_jpeg(*, name: str, sku: str, color: tuple[int, int, int]) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    w, h = 640, 640
    img = Image.new("RGB", (w, h), color)
    draw = ImageDraw.Draw(img)
    # Soft panels
    draw.rectangle((40, 40, w - 40, h - 40), outline=(255, 255, 255), width=3)
    draw.rectangle((0, h - 160, w, h), fill=(20, 24, 32))
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        font_sku = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except OSError:
        font_title = ImageFont.load_default()
        font_sku = font_title
    title = (name or "Product")[:42]
    draw.text((48, h - 130), title, fill=(255, 255, 255), font=font_title)
    draw.text((48, h - 70), sku or "", fill=(180, 190, 200), font=font_sku)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


_FALLBACK_COLORS: dict[str, tuple[int, int, int]] = {
    "DEMO-POS-WATER": (56, 140, 200),
    "DEMO-POS-SNACK": (210, 140, 60),
    "DEMO-POS-TOWEL": (70, 130, 120),
    "DEMO-POS-SHAKE": (120, 80, 160),
    "DEMO-JUICE": (230, 140, 40),
    "DEMO-SODA": (40, 90, 180),
    "DEMO-CHKN": (180, 90, 50),
    "DEMO-PASTA": (200, 160, 60),
}


def ensure_product_image(product, *, force: bool = False) -> str:
    """Ensure ``product.image`` points at a usable media file or HTTPS photo.

    Returns the stored image path/URL (may be unchanged).
    """
    sku = (getattr(product, "sku", None) or "").strip()
    if not force and not _needs_image(getattr(product, "image", None)):
        return product.image or ""

    url = DEMO_PRODUCT_IMAGE_URLS.get(sku)
    data = _download_bytes(url) if url else None
    if data is None:
        color = _FALLBACK_COLORS.get(sku, (80, 110, 140))
        data = _generate_jpeg(name=product.name, sku=sku, color=color)

    filename = f"products/demo/{sku.lower() or product.id}.jpg"
    if default_storage.exists(filename):
        try:
            default_storage.delete(filename)
        except Exception:  # noqa: BLE001
            pass
    saved = default_storage.save(filename, ContentFile(data))
    stored = default_storage.url(saved)
    # Prefer relative media path for portability across hosts
    if stored.startswith("http"):
        # Keep absolute if storage returns full URL
        path = stored
    else:
        path = stored if stored.startswith("/") else f"/media/{saved}"

    product.image = path
    product.save(update_fields=["image", "updated_at"])
    return path


def ensure_images_for_skus(*, products) -> int:
    updated = 0
    for product in products:
        before = product.image or ""
        after = ensure_product_image(product)
        if after and after != before:
            updated += 1
        elif _needs_image(before) and after:
            updated += 1
    return updated
