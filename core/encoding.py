from __future__ import annotations

import io

from PIL import Image

try:
    from mozjpeg_lossless_optimization import optimize_jpeg
except ImportError:  # pragma: no cover
    optimize_jpeg = None


def normalize_image_mode(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode in ("RGBA", "LA"):
            background.paste(img, mask=img.split()[-1])
            return background
        return img.convert("RGB")
    if img.mode == "L":
        return img.copy()
    if img.mode != "RGB":
        return img.convert("RGB")
    return img.copy()


def encode_jpeg(img: Image.Image, quality: int) -> bytes:
    output_buffer = io.BytesIO()
    save_kwargs = {
        "format": "JPEG",
        "quality": quality,
        "optimize": True,
    }
    if img.mode == "RGB":
        save_kwargs["subsampling"] = "4:2:0"
        save_kwargs["progressive"] = True

    img.save(output_buffer, **save_kwargs)
    data = output_buffer.getvalue()

    if optimize_jpeg:
        try:
            data = optimize_jpeg(data)
        except Exception:
            pass

    return data
