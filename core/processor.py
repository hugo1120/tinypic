"""处理链任务编排。"""

import zipfile
from pathlib import Path
from typing import Callable, Optional
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from .compressor import DEFAULT_QUALITY
from .models import ProcessorStats, TaskError
from .pipeline import PipelineOptions, process_image_bytes
from .settings import MAX_PROCESS_THREADS
from .sources import (
    ARCHIVE_EXTENSIONS,
    EPUB_EXTENSIONS,
    RAR_EXTENSIONS,
    build_image_source,
)

OUTPUT_SUFFIX = "_tinypic"

def process_single_image(args: tuple) -> tuple[int, bool, list[bytes], int]:
    """处理单张图片（供多线程调用）"""
    index, image_source, is_cover, quality, crop_mode, crop_power, spread_mode = args
    image_data = image_source() if callable(image_source) else image_source
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
    return (index, len(pages) > 1, pages, original_size)


class TaskProcessor:
    """任务处理器"""

    def __init__(
        self,
        quality: int = DEFAULT_QUALITY,
        num_threads: int = 4,
        crop_mode: str = 'none',
        crop_power: float = 1.0,
        spread_mode: str = 'split',
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ):
        self.quality = quality
        self.num_threads = max(1, min(MAX_PROCESS_THREADS, num_threads))
        self.crop_mode = crop_mode
        self.crop_power = crop_power
        self.spread_mode = spread_mode
        self.progress_callback = progress_callback
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def process(self, input_path: Path) -> tuple[Path, ProcessorStats]:
        self._cancelled = False
        suffix = input_path.suffix.lower()

        if input_path.is_dir():
            return self._process_input_path(input_path)
        if suffix in ARCHIVE_EXTENSIONS or suffix in RAR_EXTENSIONS or suffix in EPUB_EXTENSIONS:
            return self._process_input_path(input_path)
        raise ValueError(f"不支持的输入类型: {input_path}")

    def _process_input_path(self, input_path: Path) -> tuple[Path, ProcessorStats]:
        output_path = self._build_output_path(input_path)
        source_items = list(build_image_source(input_path))
        stats = self._process_source_items(source_items, output_path)
        return output_path, stats

    def _build_output_path(self, input_path: Path) -> Path:
        if input_path.is_dir():
            return input_path.parent / f"{input_path.name}{OUTPUT_SUFFIX}.cbz"

        stem = input_path.stem
        if stem.endswith(OUTPUT_SUFFIX):
            stem = stem[:-len(OUTPUT_SUFFIX)]
        return input_path.parent / f"{stem}{OUTPUT_SUFFIX}.cbz"

    def _iter_processed_results(self, source_items):
        pending = {}
        iterator = iter(source_items)
        max_in_flight = max(1, min(self.num_threads, MAX_PROCESS_THREADS))

        def submit_next(executor):
            try:
                item = next(iterator)
            except StopIteration:
                return False
            future = executor.submit(
                process_single_image,
                (
                    item.index,
                    item.loader,
                    item.is_cover,
                    self.quality,
                    self.crop_mode,
                    self.crop_power,
                    self.spread_mode,
                ),
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
                    if self._cancelled:
                        executor.shutdown(wait=False, cancel_futures=True)
                        return
                    submit_next(executor)

    def _process_source_items(self, source_items, output_path: Path) -> ProcessorStats:
        stats = ProcessorStats(total_files=len(source_items))
        buffered: dict[int, tuple[list[bytes], int] | None] = {}
        next_index = 0
        page_number = 1
        completed = 0
        num_digits = len(str(max(1, stats.total_files * 2)))

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zf:
            for item, future in self._iter_processed_results(source_items):
                if self._cancelled:
                    break
                completed += 1
                try:
                    _, _, pages, original_size = future.result()
                    buffered[item.index] = (pages, original_size)
                except Exception as exc:
                    stats.errors.append(TaskError(source_name=item.name, message=str(exc)))
                    buffered[item.index] = None

                if self.progress_callback:
                    self.progress_callback(completed, stats.total_files, item.name)

                while next_index in buffered:
                    entry = buffered.pop(next_index)
                    if entry:
                        pages, original_size = entry
                        stats.original_size += original_size
                        for page in pages:
                            zf.writestr(f"{page_number:0{num_digits}d}.jpg", page)
                            stats.compressed_size += len(page)
                            page_number += 1
                        stats.processed_files += 1
                    next_index += 1

        return stats
    
