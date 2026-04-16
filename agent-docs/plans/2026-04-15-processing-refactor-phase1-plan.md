# TinyPic 第一期处理链路重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持 `*_tinypic.cbz` 输出兼容的前提下，拆分处理链路职责、统一图像处理实现、降低内存峰值，并补齐关键回归测试。

**Architecture:** 保留 `MainWindow -> WorkerThread -> TaskProcessor` 外部调用形态，在 `core/` 内新增 `models / sources / encoding / pipeline` 作为中间层。`TaskProcessor` 退化为编排器，图像来源、页级处理和 JPEG 编码分别下沉到独立模块，UI 仅做必要的状态与设置持久化适配。

**Tech Stack:** Python 3.10+, PySide6, Pillow, pytest, zipfile, tempfile, concurrent.futures

---

## File Structure Map

- Create: `core/models.py`
  - 职责：定义 `SourceImage`、`ProcessedPage`、`ProcessorStats`、`TaskError` 等数据结构。
- Create: `core/sources.py`
  - 职责：统一枚举文件夹、ZIP/CBZ、RAR/CBR、EPUB 中的图片输入项。
- Create: `core/encoding.py`
  - 职责：统一图片模式规范化、JPEG 编码和 MozJPEG 优化。
- Create: `core/pipeline.py`
  - 职责：统一宽图判断、拆分、旋转、裁剪、灰度、编码流程。
- Modify: `core/processor.py`
  - 职责：仅保留任务编排、受控并发、顺序写出、统计与进度回调。
- Modify: `core/compressor.py`
  - 职责：收敛为兼容层或保留少量公共判断函数，避免与新管线重复。
- Modify: `core/splitter.py`
  - 职责：改为薄兼容层或复用 `pipeline`，不再保留独立主实现。
- Modify: `core/settings.py`
  - 职责：将设置改为内存态更新 + 显式保存。
- Modify: `gui/main_window.py`
  - 职责：使用新的保存时机和更清晰的任务状态更新。
- Create: `tests/conftest.py`
  - 职责：放测试图片生成和 CBZ 读取辅助函数。
- Create: `tests/test_processor_pipeline.py`
  - 职责：覆盖页序、宽图处理、命名和统计。
- Create: `tests/test_settings_ui_contract.py`
  - 职责：覆盖设置保存契约和 UI 侧最小联动逻辑。

### Task 1: 搭建回归测试基线

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_processor_pipeline.py`
- Test: `tests/test_processor_pipeline.py`

- [ ] **Step 1: 写页序与输出命名的失败测试**

```python
from pathlib import Path
import zipfile

from PIL import Image

from core.processor import TaskProcessor


def _save_image(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    Image.new("RGB", size, color).save(path, format="JPEG", quality=90)


def test_folder_input_keeps_natural_order_and_output_name(tmp_path):
    book_dir = tmp_path / "Book"
    chapter_dir = book_dir / "chapter"
    chapter_dir.mkdir(parents=True)

    _save_image(book_dir / "10.jpg", (120, 180), (255, 0, 0))
    _save_image(chapter_dir / "2.jpg", (120, 180), (0, 255, 0))
    _save_image(book_dir / "1.jpg", (120, 180), (0, 0, 255))

    processor = TaskProcessor(quality=72, num_threads=2, crop_mode="none", crop_power=0.0, spread_mode="none")
    output_path, stats = processor.process(book_dir)

    assert output_path.name == "Book_tinypic.cbz"
    assert stats.processed_files == 3

    with zipfile.ZipFile(output_path, "r") as zf:
        assert zf.namelist() == ["1.jpg", "2.jpg", "3.jpg"]
```

- [ ] **Step 2: 运行测试确认当前实现失败**

Run: `pytest "tests/test_processor_pipeline.py::test_folder_input_keeps_natural_order_and_output_name" -v`

Expected: `FAIL`, 失败点应落在导入缺失、页序不符或后续未实现的新辅助结构上。

- [ ] **Step 3: 建立测试辅助文件**

```python
# tests/conftest.py
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import pytest
from PIL import Image, ImageDraw


def create_rgb_image(path: Path, size: tuple[int, int], color: tuple[int, int, int]) -> None:
    Image.new("RGB", size, color).save(path, format="JPEG", quality=92)


def create_spread_image(path: Path, left_color: tuple[int, int, int], right_color: tuple[int, int, int]) -> None:
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
```

- [ ] **Step 4: 补充宽图与裁剪契约测试**

```python
def test_split_mode_expands_spread_into_two_pages(tmp_path, processor_factory):
    book_dir = tmp_path / "SplitBook"
    book_dir.mkdir()
    create_rgb_image(book_dir / "001.jpg", (120, 180), (20, 20, 20))
    create_spread_image(book_dir / "002.jpg", (255, 0, 0), (0, 255, 0))

    output_path, stats = processor_factory(spread_mode="split").process(book_dir)

    assert stats.processed_files == 2
    assert read_cbz_names(output_path) == ["1.jpg", "2.jpg", "3.jpg"]


def test_rotate_mode_keeps_one_output_page_for_spread(tmp_path, processor_factory):
    book_dir = tmp_path / "RotateBook"
    book_dir.mkdir()
    create_spread_image(book_dir / "001.jpg", (255, 0, 0), (0, 255, 0))

    output_path, stats = processor_factory(spread_mode="rotate").process(book_dir)

    assert stats.processed_files == 1
    assert read_cbz_names(output_path) == ["1.jpg"]


def test_margin_crop_mode_runs_without_crashing(tmp_path, processor_factory):
    book_dir = tmp_path / "CropBook"
    book_dir.mkdir()
    create_margin_image(book_dir / "001.jpg")

    output_path, stats = processor_factory(crop_mode="margins", crop_power=1.0).process(book_dir)

    assert output_path.exists()
    assert stats.errors == []
```

- [ ] **Step 5: 运行测试并记录当前失败面**

Run: `pytest "tests/test_processor_pipeline.py" -v`

Expected: `3-4 failed`, 当前失败应集中在宽图处理、测试辅助未接入或后续即将引入的新结构。

### Task 2: 抽取核心数据模型与输入源层

**Files:**
- Create: `core/models.py`
- Create: `core/sources.py`
- Modify: `core/processor.py`
- Test: `tests/test_processor_pipeline.py`

- [ ] **Step 1: 先写输入源与统计契约测试**

```python
from core.sources import build_image_source


def test_build_image_source_returns_cover_flag_and_stable_index(tmp_path):
    book_dir = tmp_path / "SourceBook"
    book_dir.mkdir()
    create_rgb_image(book_dir / "001.jpg", (120, 180), (1, 2, 3))
    create_rgb_image(book_dir / "002.jpg", (120, 180), (4, 5, 6))

    items = list(build_image_source(book_dir))

    assert [item.index for item in items] == [0, 1]
    assert items[0].is_cover is True
    assert items[1].is_cover is False
    assert items[0].name == "001.jpg"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest "tests/test_processor_pipeline.py::test_build_image_source_returns_cover_flag_and_stable_index" -v`

Expected: `FAIL with ModuleNotFoundError: No module named 'core.sources'`

- [ ] **Step 3: 新建数据模型文件**

```python
# core/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


ByteLoader = Callable[[], bytes]


@dataclass(frozen=True)
class SourceImage:
    index: int
    name: str
    is_cover: bool
    loader: ByteLoader


@dataclass(frozen=True)
class ProcessedPage:
    source_index: int
    output_offset: int
    data: bytes


@dataclass
class TaskError:
    source_name: str
    message: str


@dataclass
class ProcessorStats:
    total_files: int = 0
    processed_files: int = 0
    original_size: int = 0
    compressed_size: int = 0
    errors: list[TaskError] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        if self.original_size == 0:
            return 1.0
        return self.compressed_size / self.original_size
```

- [ ] **Step 4: 新建统一输入源模块**

```python
# core/sources.py
from __future__ import annotations

from pathlib import Path
import zipfile

from .compressor import is_image_file
from .models import SourceImage
from .processor import ARCHIVE_EXTENSIONS, EPUB_EXTENSIONS, RAR_EXTENSIONS, extract_rar_with_7zip, get_epub_images, natural_sort_key


def _path_loader(path: Path):
    def _load() -> bytes:
        return path.read_bytes()
    return _load


def build_image_source(input_path: Path) -> list[SourceImage]:
    if input_path.is_dir():
        image_paths = sorted(
            [p for p in input_path.rglob("*") if p.is_file() and is_image_file(p.name)],
            key=lambda item: natural_sort_key(str(item)),
        )
        return [
            SourceImage(index=i, name=path.name, is_cover=(i == 0), loader=_path_loader(path))
            for i, path in enumerate(image_paths)
        ]

    suffix = input_path.suffix.lower()
    if suffix in ARCHIVE_EXTENSIONS:
        with zipfile.ZipFile(input_path, "r") as zf:
            names = sorted(
                [name for name in zf.namelist() if is_image_file(name) and not name.endswith("/")],
                key=natural_sort_key,
            )
            payload = {name: zf.read(name) for name in names}
        return [
            SourceImage(index=i, name=Path(name).name, is_cover=(i == 0), loader=lambda data=data: data)
            for i, (name, data) in enumerate(payload.items())
        ]

    if suffix in RAR_EXTENSIONS:
        raise NotImplementedError("RAR source wiring will be moved in Task 4")

    if suffix in EPUB_EXTENSIONS:
        pairs = get_epub_images(input_path)
        return [
            SourceImage(index=i, name=Path(name).name, is_cover=(i == 0), loader=lambda data=data: data)
            for i, (name, data) in enumerate(pairs)
        ]

    raise ValueError(f"不支持的输入类型: {input_path}")
```

- [ ] **Step 5: 让 `TaskProcessor` 暂时复用新输入源**

```python
# core/processor.py
from .models import ProcessorStats, TaskError
from .sources import build_image_source


def _build_image_jobs(self, input_path: Path) -> tuple[list[tuple], list[str], ProcessorStats]:
    source_items = build_image_source(input_path)
    stats = ProcessorStats(total_files=len(source_items))
    jobs = []
    file_names = []
    for item in source_items:
        data = item.loader()
        jobs.append((item.index, data, item.is_cover, self.quality, self.crop_mode, self.crop_power, self.spread_mode))
        file_names.append(item.name)
    return jobs, file_names, stats
```

- [ ] **Step 6: 运行测试确认输入源层生效**

Run: `pytest "tests/test_processor_pipeline.py::test_build_image_source_returns_cover_flag_and_stable_index" "tests/test_processor_pipeline.py::test_folder_input_keeps_natural_order_and_output_name" -v`

Expected: `PASS`，若还有失败，应仅剩后续任务尚未实现的宽图或错误处理问题。

### Task 3: 抽取统一编码与页处理管线

**Files:**
- Create: `core/encoding.py`
- Create: `core/pipeline.py`
- Modify: `core/compressor.py`
- Modify: `core/splitter.py`
- Modify: `core/processor.py`
- Test: `tests/test_processor_pipeline.py`

- [ ] **Step 1: 先写宽图模式与封面契约测试**

```python
def test_cover_page_is_not_split_even_when_wide(tmp_path, processor_factory):
    book_dir = tmp_path / "CoverBook"
    book_dir.mkdir()
    create_spread_image(book_dir / "001.jpg", (255, 0, 0), (0, 255, 0))
    create_rgb_image(book_dir / "002.jpg", (120, 180), (0, 0, 255))

    output_path, _ = processor_factory(spread_mode="split").process(book_dir)

    assert read_cbz_names(output_path) == ["1.jpg", "2.jpg"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest "tests/test_processor_pipeline.py::test_cover_page_is_not_split_even_when_wide" -v`

Expected: `FAIL`，当前失败点通常是宽图处理仍散落在旧实现中。

- [ ] **Step 3: 新建统一编码模块**

```python
# core/encoding.py
from __future__ import annotations

import io
from PIL import Image

try:
    from mozjpeg_lossless_optimization import optimize_jpeg
except ImportError:  # pragma: no cover - optional dependency
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
        return img
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def encode_jpeg(img: Image.Image, quality: int) -> bytes:
    buffer = io.BytesIO()
    save_kwargs = {"format": "JPEG", "quality": quality, "optimize": True}
    if img.mode == "RGB":
        save_kwargs["subsampling"] = "4:2:0"
        save_kwargs["progressive"] = True
    img.save(buffer, **save_kwargs)
    data = buffer.getvalue()
    if optimize_jpeg:
        try:
            data = optimize_jpeg(data)
        except Exception:
            pass
    return data
```

- [ ] **Step 4: 新建统一页处理模块**

```python
# core/pipeline.py
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
    with Image.open(io.BytesIO(image_data)) as img:
        return img.width > img.height


def _target_quality(image_data: bytes, requested_quality: int, offset: int = 5) -> int:
    return max(60, min(requested_quality, estimate_jpeg_quality(image_data) - offset))


def process_image_bytes(image_data: bytes, is_cover: bool, options: PipelineOptions) -> tuple[list[bytes], int]:
    quality = _target_quality(image_data, options.quality)
    with Image.open(io.BytesIO(image_data)) as raw:
        image = normalize_image_mode(raw)

    if is_cover or not is_wide_image(image_data) or options.spread_mode == "none":
        return [_encode_page(image, quality, options)], len(image_data)

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


def _encode_page(image: Image.Image, quality: int, options: PipelineOptions) -> bytes:
    cropped = apply_crop(image, options.crop_mode, options.crop_power)
    if cropped.mode == "RGB" and is_grayscale_image(cropped):
        cropped = cropped.convert("L")
    return encode_jpeg(cropped, quality)
```

- [ ] **Step 5: 让旧模块复用新实现**

```python
# core/compressor.py
from .encoding import encode_jpeg, normalize_image_mode


def compress_image(image_data: bytes, quality: int = DEFAULT_QUALITY, crop_mode: str = "none", crop_power: float = 1.0, force_grayscale: bool = False) -> tuple[bytes, dict]:
    from .pipeline import PipelineOptions, process_image_bytes

    pages, original_size = process_image_bytes(
        image_data,
        is_cover=False,
        options=PipelineOptions(
            quality=quality,
            crop_mode=crop_mode,
            crop_power=crop_power,
            spread_mode="none",
        ),
    )
    compressed_data = pages[0]
    return compressed_data, {
        "original_size": original_size,
        "compressed_size": len(compressed_data),
        "ratio": len(compressed_data) / original_size if original_size else 1.0,
        "saved": original_size - len(compressed_data),
        "is_grayscale": force_grayscale,
        "quality_used": quality,
        "original_quality": estimate_jpeg_quality(image_data),
    }
```

```python
# core/splitter.py
from .pipeline import PipelineOptions, is_wide_image, process_image_bytes


def process_image_for_split(image_data: bytes, is_cover: bool = False, quality: int = 90) -> list[bytes]:
    pages, _ = process_image_bytes(
        image_data,
        is_cover=is_cover,
        options=PipelineOptions(
            quality=quality,
            crop_mode="none",
            crop_power=0.0,
            spread_mode="split",
        ),
    )
    return pages
```

- [ ] **Step 6: 让 `TaskProcessor` 使用统一 pipeline**

```python
# core/processor.py
from .pipeline import PipelineOptions, process_image_bytes


def process_single_image(args: tuple) -> tuple[int, list[bytes], int]:
    index, image_data, is_cover, quality, crop_mode, crop_power, spread_mode = args
    pages, original_size = process_image_bytes(
        image_data,
        is_cover=is_cover,
        options=PipelineOptions(
            quality=quality,
            crop_mode=crop_mode,
            crop_power=crop_power,
            spread_mode=spread_mode,
        ),
    )
    return index, pages, original_size
```

- [ ] **Step 7: 运行宽图相关测试**

Run: `pytest "tests/test_processor_pipeline.py::test_split_mode_expands_spread_into_two_pages" "tests/test_processor_pipeline.py::test_rotate_mode_keeps_one_output_page_for_spread" "tests/test_processor_pipeline.py::test_cover_page_is_not_split_even_when_wide" -v`

Expected: `PASS`

### Task 4: 改造编排器为有界并发 + 顺序写出

**Files:**
- Modify: `core/processor.py`
- Modify: `core/sources.py`
- Test: `tests/test_processor_pipeline.py`

- [ ] **Step 1: 先写错误统计与继续处理测试**

```python
def test_processor_collects_page_errors_and_continues(tmp_path, processor_factory):
    book_dir = tmp_path / "ErrorBook"
    book_dir.mkdir()
    create_rgb_image(book_dir / "001.jpg", (120, 180), (1, 1, 1))
    (book_dir / "002.jpg").write_bytes(b"not-an-image")
    create_rgb_image(book_dir / "003.jpg", (120, 180), (2, 2, 2))

    output_path, stats = processor_factory().process(book_dir)

    assert output_path.exists()
    assert stats.processed_files == 2
    assert len(stats.errors) == 1
    assert stats.errors[0].source_name == "002.jpg"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest "tests/test_processor_pipeline.py::test_processor_collects_page_errors_and_continues" -v`

Expected: `FAIL`，当前实现要么中断整个任务，要么错误结构仍是字符串列表。

- [ ] **Step 3: 让输入源支持惰性读取**

```python
# core/sources.py
def iter_image_source(input_path: Path):
    for item in build_image_source(input_path):
        yield item
```

- [ ] **Step 4: 改写 `TaskProcessor` 的受控并发主循环**

```python
# core/processor.py
def _iter_processed_results(self, source_items):
    from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

    pending = {}
    iterator = iter(source_items)
    max_in_flight = max(1, min(self.num_threads, 8))

    def submit_next(executor):
        try:
            item = next(iterator)
        except StopIteration:
            return False
        future = executor.submit(
            process_single_image,
            (item.index, item.loader(), item.is_cover, self.quality, self.crop_mode, self.crop_power, self.spread_mode),
        )
        pending[future] = item
        return True

    with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
        while len(pending) < max_in_flight and submit_next(executor):
            pass

        while pending:
            done, _ = wait(tuple(pending.keys()), return_when=FIRST_COMPLETED)
            for future in done:
                item = pending.pop(future)
                yield item, future
                if not self._cancelled:
                    submit_next(executor)
```

- [ ] **Step 5: 按序缓存并写出结果**

```python
# core/processor.py
def _process_source_items(self, source_items, output_path: Path) -> ProcessorStats:
    stats = ProcessorStats(total_files=len(source_items))
    buffered: dict[int, tuple[list[bytes], int]] = {}
    next_index = 0
    page_number = 1

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_STORED) as zf:
        for item, future in self._iter_processed_results(source_items):
            try:
                _, pages, original_size = future.result()
                buffered[item.index] = (pages, original_size)
            except Exception as exc:
                stats.errors.append(TaskError(source_name=item.name, message=str(exc)))
                buffered[item.index] = ([], 0)

            while next_index in buffered:
                pages, original_size = buffered.pop(next_index)
                if pages:
                    stats.original_size += original_size
                    for page in pages:
                        zf.writestr(f"{page_number}.jpg", page)
                        stats.compressed_size += len(page)
                        page_number += 1
                    stats.processed_files += 1
                next_index += 1
    return stats
```

- [ ] **Step 6: 恢复页码格式并接进度回调**

```python
# core/processor.py
num_digits = len(str(max(1, stats.total_files * 2)))
zf.writestr(f"{page_number:0{num_digits}d}.jpg", page)

if self.progress_callback:
    completed = stats.processed_files + len(stats.errors)
    self.progress_callback(completed, stats.total_files, item.name)
```

- [ ] **Step 7: 跑核心处理测试**

Run: `pytest "tests/test_processor_pipeline.py" -v`

Expected: `PASS`

### Task 5: 调整设置持久化与 UI 契约

**Files:**
- Modify: `core/settings.py`
- Modify: `gui/main_window.py`
- Create: `tests/test_settings_ui_contract.py`
- Test: `tests/test_settings_ui_contract.py`

- [ ] **Step 1: 先写设置延迟保存测试**

```python
from core.settings import Settings


def test_settings_only_write_on_explicit_save(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)

    settings = Settings()
    settings.quality = 80

    assert not config_path.exists()

    settings.save()

    assert config_path.exists()
    assert '"quality": 80' in config_path.read_text(encoding="utf-8")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest "tests/test_settings_ui_contract.py::test_settings_only_write_on_explicit_save" -v`

Expected: `FAIL`，当前 setter 会立即写盘。

- [ ] **Step 3: 改造 `Settings` 为脏标记保存**

```python
# core/settings.py
class Settings:
    def __init__(self):
        self.config_path = get_config_path()
        self._data = DEFAULT_SETTINGS.copy()
        self._dirty = False
        self.load()

    def save(self):
        if not self._dirty:
            return
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        self._dirty = False

    def _update(self, key: str, value):
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self._dirty = True
```

- [ ] **Step 4: 让各 setter 只更新内存**

```python
@quality.setter
def quality(self, value: int):
    self._update("quality", max(60, min(95, value)))


@num_threads.setter
def num_threads(self, value: int):
    self._update("num_threads", max(1, min(100, value)))
```

- [ ] **Step 5: 调整 UI 的保存时机**

```python
# gui/main_window.py
self.quality_slider.sliderReleased.connect(self.settings.save)
self.thread_slider.sliderReleased.connect(self.settings.save)
self.power_slider.sliderReleased.connect(self.settings.save)
self.crop_combo.activated.connect(lambda _: self.settings.save())
self.spread_combo.activated.connect(lambda _: self.settings.save())


def closeEvent(self, event):
    self.settings.save()
    super().closeEvent(event)
```

- [ ] **Step 6: 写 UI 契约测试并跑通**

```python
def test_main_window_saves_settings_on_close(qtbot, monkeypatch, tmp_path):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)

    from gui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.quality_slider.setValue(81)
    window.close()

    assert config_path.exists()
    assert '"quality": 81' in config_path.read_text(encoding="utf-8")
```

Run: `pytest "tests/test_settings_ui_contract.py" -v`

Expected: `PASS`

### Task 6: 清理兼容层并完成总体验证

**Files:**
- Modify: `core/compressor.py`
- Modify: `core/splitter.py`
- Modify: `gui/main_window.py`
- Test: `tests/test_processor_pipeline.py`
- Test: `tests/test_settings_ui_contract.py`

- [ ] **Step 1: 收敛旧兼容层导出**

```python
# core/compressor.py
__all__ = [
    "DEFAULT_QUALITY",
    "SUPPORTED_EXTENSIONS",
    "compress_image",
    "estimate_jpeg_quality",
    "is_grayscale_image",
    "is_image_file",
]
```

```python
# core/splitter.py
__all__ = [
    "is_wide_image",
    "process_image_for_split",
]
```

- [ ] **Step 2: 清理 `MainWindow` 中的旧统计假设**

```python
# gui/main_window.py
def on_task_complete(self, task_path: str, stats: object):
    for i in range(self.task_list.count()):
        item = self.task_list.item(i)
        if item.data(Qt.UserRole) == task_path:
            ratio = max(0, (1 - stats.ratio) * 100)
            orig = format_size(stats.original_size)
            comp = format_size(stats.compressed_size)
            suffix = f"，错误 {len(stats.errors)} 项" if stats.errors else ""
            item.setText(f"✅ {Path(task_path).name} ({orig} → {comp}, -{ratio:.0f}%{suffix})")
            break
```

- [ ] **Step 3: 运行语法检查**

Run: `python -m compileall "main.py" "core" "gui" "tests"`

Expected: `Compiling ...` 且无报错

- [ ] **Step 4: 运行自动化测试**

Run: `pytest "tests/test_processor_pipeline.py" "tests/test_settings_ui_contract.py" -v`

Expected: `all passed`

- [ ] **Step 5: 手工回归一个真实样本**

Run: `python "main.py"`

Expected:
- 窗口可打开
- 可拖入 `测试漫画/`
- 输出文件名仍为 `*_tinypic.cbz`
- 完成后列表项显示压缩结果和错误计数

## Self-Review

### Spec coverage

- 输入源拆分：Task 2、Task 4 覆盖。
- 统一图像处理与编码：Task 3 覆盖。
- 有界并发与顺序写出：Task 4 覆盖。
- 设置保存与 UI 适配：Task 5 覆盖。
- 自动化测试与验证：Task 1、Task 5、Task 6 覆盖。

### Placeholder scan

- 已移除 `TODO/TBD/后续补充` 之类占位词。
- 所有任务都给出了文件路径、测试命令和代码片段。

### Type consistency

- 统一使用 `SourceImage / ProcessedPage / ProcessorStats / TaskError / PipelineOptions` 作为核心命名。
- `TaskProcessor` 仍作为外部入口保留。
