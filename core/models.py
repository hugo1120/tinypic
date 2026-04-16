from __future__ import annotations

from dataclasses import dataclass, field
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
