from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
import zipfile

from .compressor import is_image_file
from .models import SourceImage

ARCHIVE_EXTENSIONS = {'.zip', '.cbz'}
RAR_EXTENSIONS = {'.rar', '.cbr'}
EPUB_EXTENSIONS = {'.epub'}


class EpubSourceWarning(UserWarning):
    """EPUB 解析已回退到保底扫描时的诊断 warning。"""


def natural_sort_key(value: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def source_sort_key(value: str) -> tuple[list[int | str], list[int | str]]:
    normalized = value.replace("\\", "/")
    return natural_sort_key(Path(normalized).name), natural_sort_key(normalized)


def _path_loader(path: Path):
    def _load() -> bytes:
        return path.read_bytes()

    return _load


def _archive_entry_loader(archive_path: Path, entry_name: str):
    def _load() -> bytes:
        with zipfile.ZipFile(archive_path, 'r') as zf:
            return zf.read(entry_name)

    return _load


def _retained_path_loader(path: Path, keepalive):
    def _load() -> bytes:
        keepalive  # 保持临时目录存活到实际读取发生时
        return path.read_bytes()

    return _load


def find_7zip() -> str | None:
    possible_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        r"D:\Program Files\7-Zip\7z.exe",
        r"D:\Program Files (x86)\7-Zip\7z.exe",
    ]

    path_7z = shutil.which("7z")
    if path_7z:
        return path_7z

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


SEVENZIP_PATH = find_7zip()


def extract_rar_with_7zip(rar_path: Path, dest_dir: Path) -> list[Path]:
    if not SEVENZIP_PATH:
        raise RuntimeError("未找到 7-Zip，请安装 7-Zip 到默认路径")

    cmd = [
        SEVENZIP_PATH,
        'x',
        '-y',
        f'-o{dest_dir}',
        str(rar_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )
    if result.returncode != 0:
        raise RuntimeError(f"7-Zip 解压失败: {result.stderr.decode('utf-8', errors='ignore')}")

    image_files = []
    for root, _, files in os.walk(dest_dir):
        for filename in files:
            if is_image_file(filename):
                image_files.append(Path(root) / filename)
    image_files.sort(key=lambda item: source_sort_key(str(item.relative_to(dest_dir))))
    return image_files


def get_epub_image_entries(epub_path: Path) -> list[str]:
    image_entries: list[str] = []

    with zipfile.ZipFile(epub_path, 'r') as zf:
        archive_names = [name for name in zf.namelist() if not name.endswith('/')]
        archive_name_set = set(archive_names)
        opf_path = next((name for name in archive_names if name.endswith('.opf')), None)
        if opf_path:
            try:
                opf_content = zf.read(opf_path).decode('utf-8')
                root = ET.fromstring(opf_content)
                opf_dir = str(Path(opf_path).parent)
                if opf_dir == '.':
                    opf_dir = ''

                for elem in root.iter():
                    if 'manifest' in elem.tag.lower():
                        for item in elem:
                            href = item.get('href', '')
                            media_type = item.get('media-type', '')
                            if media_type.startswith('image/'):
                                full_path = f"{opf_dir}/{href}" if opf_dir else href
                                full_path = full_path.replace('\\', '/')
                                if full_path in archive_name_set:
                                    image_entries.append(full_path)
                                else:
                                    fallback = next((name for name in archive_names if name.endswith(href)), None)
                                    if fallback:
                                        image_entries.append(fallback)
            except Exception as exc:
                warnings.warn(
                    f"EPUB OPF 解析失败，已回退到图片扫描: {epub_path.name} ({exc})",
                    EpubSourceWarning,
                    stacklevel=2,
                )

        if not image_entries:
            all_images = [name for name in archive_names if is_image_file(name)]
            all_images.sort(key=source_sort_key)
            image_entries.extend(all_images)

    return image_entries


def build_image_source(input_path: Path) -> list[SourceImage]:
    if input_path.is_dir():
        image_paths = [
            path for path in input_path.rglob("*")
            if path.is_file() and is_image_file(path.name)
        ]
        image_paths.sort(key=lambda item: source_sort_key(str(item.relative_to(input_path))))

        return [
            SourceImage(
                index=index,
                name=path.name,
                is_cover=(index == 0),
                loader=_path_loader(path),
            )
            for index, path in enumerate(image_paths)
        ]

    suffix = input_path.suffix.lower()
    if suffix in ARCHIVE_EXTENSIONS:
        with zipfile.ZipFile(input_path, 'r') as zf:
            entries = [
                name for name in zf.namelist()
                if is_image_file(name) and not name.endswith('/')
            ]
            entries.sort(key=source_sort_key)
        return [
            SourceImage(
                index=index,
                name=Path(name).name,
                is_cover=(index == 0),
                loader=_archive_entry_loader(input_path, name),
            )
            for index, name in enumerate(entries)
        ]

    if suffix in EPUB_EXTENSIONS:
        entries = get_epub_image_entries(input_path)
        return [
            SourceImage(
                index=index,
                name=Path(name).name,
                is_cover=(index == 0),
                loader=_archive_entry_loader(input_path, name),
            )
            for index, name in enumerate(entries)
        ]

    if suffix in RAR_EXTENSIONS:
        temp_dir = tempfile.TemporaryDirectory()
        try:
            image_files = extract_rar_with_7zip(input_path, Path(temp_dir.name))
        except Exception:
            temp_dir.cleanup()
            raise
        return [
            SourceImage(
                index=index,
                name=path.name,
                is_cover=(index == 0),
                loader=_retained_path_loader(path, temp_dir),
            )
            for index, path in enumerate(image_files)
        ]

    raise ValueError(f"不支持的输入类型: {input_path}")


def iter_image_source(input_path: Path):
    for item in build_image_source(input_path):
        yield item
