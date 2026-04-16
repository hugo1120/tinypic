from __future__ import annotations

import shutil
import textwrap
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


_TMP_ROOT = Path("C:/Users/Hugo/.codex/memories/tinypic-pytest-tmp")
_TMP_ROOT.mkdir(parents=True, exist_ok=True)


def create_rgb_image(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    Image.new("RGB", size, color).save(path, format="JPEG", quality=92)


def create_spread_image(
    path: Path,
    left_color: tuple[int, int, int],
    right_color: tuple[int, int, int],
) -> None:
    image = Image.new("RGB", (240, 120), left_color)
    right = Image.new("RGB", (120, 120), right_color)
    image.paste(right, (120, 0))
    image.save(path, format="JPEG", quality=92)


def create_margin_image(path: Path) -> None:
    image = Image.new("RGB", (180, 240), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 20, 150, 210), fill=(0, 0, 0))
    image.save(path, format="JPEG", quality=92)


def read_cbz_names(cbz_path: Path) -> list[str]:
    with zipfile.ZipFile(cbz_path, "r") as zf:
        return zf.namelist()


def create_zip_archive(path: Path, image_specs: list[tuple[str, tuple[int, int], tuple[int, int, int]]]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as zf:
        for name, size, color in image_specs:
            buffer = BytesIO()
            Image.new("RGB", size, color).save(buffer, format="JPEG", quality=92)
            zf.writestr(name, buffer.getvalue())


def create_epub_with_images(path: Path) -> None:
    container_xml = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
          <rootfiles>
            <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
          </rootfiles>
        </container>
        """
    )
    content_opf = textwrap.dedent(
        """\
        <?xml version="1.0" encoding="UTF-8"?>
        <package xmlns="http://www.idpf.org/2007/opf" version="3.0">
          <manifest>
            <item id="img1" href="images/001.jpg" media-type="image/jpeg"/>
            <item id="img2" href="images/002.jpg" media-type="image/jpeg"/>
          </manifest>
        </package>
        """
    )

    images = {
        "OEBPS/images/001.jpg": ((120, 180), (10, 20, 30)),
        "OEBPS/images/002.jpg": ((120, 180), (40, 50, 60)),
    }

    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", container_xml)
        zf.writestr("OEBPS/content.opf", content_opf)
        for name, (size, color) in images.items():
            buffer = BytesIO()
            Image.new("RGB", size, color).save(buffer, format="JPEG", quality=92)
            zf.writestr(name, buffer.getvalue())


@pytest.fixture
def processor_factory():
    from core.processor import TaskProcessor

    def _build(**overrides):
        options = {
            "quality": 72,
            "num_threads": 2,
            "crop_mode": "none",
            "crop_power": 0.0,
            "spread_mode": "none",
        }
        options.update(overrides)
        return TaskProcessor(**options)

    return _build


@pytest.fixture
def tmp_path():
    path = _TMP_ROOT / f"case-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
