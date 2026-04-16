from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image

from .compressor import estimate_jpeg_quality, is_grayscale_image
from .cropper import apply_crop
from .encoding import encode_jpeg, normalize_image_mode


@dataclass(frozen=True)
class PipelineOptions:
    quality: int
    crop_mode: str
    crop_power: float
    spread_mode: str


def is_wide_image(image_data: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            return img.width > img.height
    except Exception:
        return False


def _target_quality(image_data: bytes, requested_quality: int, offset: int = 5) -> int:
    return max(60, min(requested_quality, estimate_jpeg_quality(image_data) - offset))


def _encode_page(image: Image.Image, quality: int, options: PipelineOptions) -> bytes:
    cropped = apply_crop(image, options.crop_mode, options.crop_power)
    if cropped.mode == "RGB" and is_grayscale_image(cropped):
        cropped = cropped.convert("L")
    return encode_jpeg(cropped, quality)


def process_image_bytes(image_data: bytes, is_cover: bool, options: PipelineOptions) -> tuple[list[bytes], int]:
    with Image.open(io.BytesIO(image_data)) as raw:
        image = normalize_image_mode(raw)

    if is_cover or not is_wide_image(image_data) or options.spread_mode == "none":
        quality = _target_quality(image_data, options.quality)
        return [_encode_page(image, quality, options)], len(image_data)

    quality = _target_quality(image_data, options.quality, offset=8)
    if options.spread_mode == "rotate":
        rotated = image.transpose(Image.ROTATE_270)
        return [_encode_page(rotated, quality, options)], len(image_data)

    width, height = image.size
    middle = width // 2
    right_half = image.crop((middle, 0, width, height))
    left_half = image.crop((0, 0, middle, height))
    return [
        _encode_page(right_half, quality, options),
        _encode_page(left_half, quality, options),
    ], len(image_data)
