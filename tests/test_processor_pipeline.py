from concurrent.futures import Future
from io import BytesIO
import zipfile

from PIL import Image
import pytest

from core.processor import TaskProcessor
from conftest import (
    create_epub_with_images,
    create_margin_image,
    create_rgb_image,
    create_spread_image,
    create_zip_archive,
    read_cbz_names,
)


def create_detailed_spread_bytes(quality: int = 95) -> bytes:
    image = Image.new("RGB", (240, 120))
    pixels = [
        (
            (x * 17 + y * 3) % 256,
            (x * 5 + y * 11) % 256,
            (x * 13 + y * 7) % 256,
        )
        for y in range(image.height)
        for x in range(image.width)
    ]
    image.putdata(pixels)
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality)
    return output.getvalue()


def test_folder_input_keeps_natural_order_and_output_name(tmp_path):
    book_dir = tmp_path / "Book"
    chapter_dir = book_dir / "chapter"
    chapter_dir.mkdir(parents=True)

    create_rgb_image(book_dir / "10.jpg", (120, 180), (255, 0, 0))
    create_rgb_image(chapter_dir / "2.jpg", (120, 180), (0, 255, 0))
    create_rgb_image(book_dir / "1.jpg", (120, 180), (0, 0, 255))

    processor = TaskProcessor(
        quality=72,
        num_threads=2,
        crop_mode="none",
        crop_power=0.0,
        spread_mode="none",
    )
    output_path, stats = processor.process(book_dir)

    assert output_path.name == "Book_tinypic.cbz"
    assert stats.processed_files == 3
    assert read_cbz_names(output_path) == ["1.jpg", "2.jpg", "3.jpg"]


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


def test_build_image_source_reads_nested_folder_entries_in_natural_order(tmp_path):
    from core.sources import build_image_source

    book_dir = tmp_path / "SourceBook"
    chapter_dir = book_dir / "chapter"
    chapter_dir.mkdir(parents=True)
    create_rgb_image(book_dir / "10.jpg", (120, 180), (1, 2, 3))
    create_rgb_image(chapter_dir / "2.jpg", (120, 180), (4, 5, 6))
    create_rgb_image(book_dir / "1.jpg", (120, 180), (7, 8, 9))

    items = list(build_image_source(book_dir))

    assert [item.index for item in items] == [0, 1, 2]
    assert [item.name for item in items] == ["1.jpg", "2.jpg", "10.jpg"]
    assert items[0].is_cover is True


def test_build_image_source_returns_cover_flag_and_stable_index(tmp_path):
    from core.sources import build_image_source

    book_dir = tmp_path / "SourceBook"
    book_dir.mkdir()
    create_rgb_image(book_dir / "001.jpg", (120, 180), (1, 2, 3))
    create_rgb_image(book_dir / "002.jpg", (120, 180), (4, 5, 6))

    items = list(build_image_source(book_dir))

    assert [item.index for item in items] == [0, 1]
    assert items[0].is_cover is True
    assert items[1].is_cover is False
    assert items[0].name == "001.jpg"


def test_build_image_source_reads_zip_entries_in_natural_order(tmp_path):
    from core.sources import build_image_source

    archive_path = tmp_path / "Book.cbz"
    create_zip_archive(
        archive_path,
        [
            ("10.jpg", (120, 180), (1, 2, 3)),
            ("chapter/2.jpg", (120, 180), (4, 5, 6)),
            ("1.jpg", (120, 180), (7, 8, 9)),
        ],
    )

    items = list(build_image_source(archive_path))

    assert [item.index for item in items] == [0, 1, 2]
    assert [item.name for item in items] == ["1.jpg", "2.jpg", "10.jpg"]
    assert items[0].is_cover is True


def test_build_image_source_defers_zip_entry_reads_until_loader_called(tmp_path, monkeypatch):
    import zipfile

    from core.sources import build_image_source

    archive_path = tmp_path / "Book.cbz"
    create_zip_archive(
        archive_path,
        [
            ("10.jpg", (120, 180), (1, 2, 3)),
            ("chapter/2.jpg", (120, 180), (4, 5, 6)),
            ("1.jpg", (120, 180), (7, 8, 9)),
        ],
    )

    read_calls = []
    original_read = zipfile.ZipFile.read

    def tracking_read(self, name, *args, **kwargs):
        read_calls.append(name)
        return original_read(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "read", tracking_read)

    items = list(build_image_source(archive_path))

    assert read_calls == []

    first_bytes = items[0].loader()

    assert first_bytes
    assert read_calls == ["1.jpg"]


def test_build_image_source_reads_epub_manifest_images(tmp_path):
    from core.sources import build_image_source

    epub_path = tmp_path / "Book.epub"
    create_epub_with_images(epub_path)

    items = list(build_image_source(epub_path))

    assert [item.index for item in items] == [0, 1]
    assert [item.name for item in items] == ["001.jpg", "002.jpg"]
    assert items[0].is_cover is True


def test_build_image_source_defers_epub_image_reads_until_loader_called(tmp_path, monkeypatch):
    from core.sources import build_image_source

    epub_path = tmp_path / "Book.epub"
    create_epub_with_images(epub_path)

    read_calls = []
    original_read = zipfile.ZipFile.read

    def tracking_read(self, name, *args, **kwargs):
        read_calls.append(name)
        return original_read(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "read", tracking_read)

    items = list(build_image_source(epub_path))

    assert read_calls == ["OEBPS/content.opf"]

    first_bytes = items[0].loader()

    assert first_bytes
    assert read_calls == ["OEBPS/content.opf", "OEBPS/images/001.jpg"]


def test_build_image_source_warns_when_epub_opf_parse_fails_but_falls_back(tmp_path):
    from core.sources import EpubSourceWarning, build_image_source

    epub_path = tmp_path / "BrokenBook.epub"
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", "<container/>")
        zf.writestr("OEBPS/content.opf", "<package><manifest><item")

        for name, color in (
            ("OEBPS/images/001.jpg", (10, 20, 30)),
            ("OEBPS/images/002.jpg", (40, 50, 60)),
        ):
            buffer = BytesIO()
            Image.new("RGB", (120, 180), color).save(buffer, format="JPEG", quality=92)
            zf.writestr(name, buffer.getvalue())

    with pytest.warns(EpubSourceWarning, match="OPF 解析失败"):
        items = list(build_image_source(epub_path))

    assert [item.name for item in items] == ["001.jpg", "002.jpg"]
    assert items[0].loader()


def test_build_image_source_defers_rar_file_reads_until_loader_called(tmp_path, monkeypatch):
    from core import sources

    archive_path = tmp_path / "Book.cbr"
    extracted_file = None
    temp_root = tmp_path / "rar-temp"

    class FakeTemporaryDirectory:
        def __init__(self):
            temp_root.mkdir(parents=True, exist_ok=True)
            self.name = str(temp_root)

        def cleanup(self):
            return None

    def fake_extract_rar_with_7zip(rar_path, dest_dir):
        nonlocal extracted_file
        assert rar_path == archive_path
        extracted_file = dest_dir / "001.jpg"
        extracted_file.parent.mkdir(parents=True, exist_ok=True)
        extracted_file.write_bytes(b"first")
        return [extracted_file]

    monkeypatch.setattr(sources, "extract_rar_with_7zip", fake_extract_rar_with_7zip)
    monkeypatch.setattr(sources.tempfile, "TemporaryDirectory", FakeTemporaryDirectory)

    items = list(sources.build_image_source(archive_path))

    assert extracted_file is not None
    extracted_file.write_bytes(b"second")

    assert items[0].loader() == b"second"


def test_cover_page_is_not_split_even_when_wide(tmp_path, processor_factory):
    book_dir = tmp_path / "CoverBook"
    book_dir.mkdir()
    create_spread_image(book_dir / "001.jpg", (255, 0, 0), (0, 255, 0))
    create_rgb_image(book_dir / "002.jpg", (120, 180), (0, 0, 255))

    output_path, _ = processor_factory(spread_mode="split").process(book_dir)

    assert read_cbz_names(output_path) == ["1.jpg", "2.jpg"]


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


def test_processor_collects_loader_errors_and_continues(tmp_path):
    from core.models import SourceImage

    good_image = tmp_path / "good.jpg"
    create_rgb_image(good_image, (120, 180), (1, 2, 3))

    items = [
        SourceImage(
            index=0,
            name="broken.jpg",
            is_cover=True,
            loader=lambda: (_ for _ in ()).throw(OSError("boom")),
        ),
        SourceImage(
            index=1,
            name="good.jpg",
            is_cover=False,
            loader=good_image.read_bytes,
        ),
    ]

    output_path = tmp_path / "loader-error.cbz"
    stats = TaskProcessor(
        quality=72,
        num_threads=2,
        crop_mode="none",
        crop_power=0.0,
        spread_mode="none",
    )._process_source_items(items, output_path)

    assert output_path.exists()
    assert stats.processed_files == 1
    assert len(stats.errors) == 1
    assert stats.errors[0].source_name == "broken.jpg"
    assert "boom" in stats.errors[0].message
    assert read_cbz_names(output_path) == ["1.jpg"]


def test_task_processor_clamps_thread_count_to_processing_cap():
    import core.settings as settings_module
    from core.processor import TaskProcessor

    max_threads = getattr(settings_module, "MAX_PROCESS_THREADS", None)

    assert max_threads is not None

    processor = TaskProcessor(
        quality=72,
        num_threads=max_threads + 5,
        crop_mode="none",
        crop_power=0.0,
        spread_mode="none",
    )

    assert processor.num_threads == max_threads


def test_processor_stops_before_consuming_ready_result_when_cancelled(tmp_path, monkeypatch):
    from core.models import SourceImage

    source_items = [
        SourceImage(
            index=0,
            name="001.jpg",
            is_cover=True,
            loader=lambda: b"unused",
        )
    ]
    page_path = tmp_path / "page.jpg"
    create_rgb_image(page_path, (120, 180), (2, 3, 4))
    page_bytes = page_path.read_bytes()

    processor = TaskProcessor(
        quality=72,
        num_threads=1,
        crop_mode="none",
        crop_power=0.0,
        spread_mode="none",
    )

    def fake_iter_processed_results(items):
        future = Future()
        future.set_result((0, False, [page_bytes], len(page_bytes)))
        processor.cancel()
        yield items[0], future

    monkeypatch.setattr(processor, "_iter_processed_results", fake_iter_processed_results)

    output_path = tmp_path / "cancelled.cbz"
    stats = processor._process_source_items(source_items, output_path)

    assert stats.processed_files == 0
    assert stats.errors == []
    assert read_cbz_names(output_path) == []


def test_split_mode_preserves_legacy_quality_offset():
    from core.compressor import estimate_jpeg_quality
    from core.encoding import encode_jpeg, normalize_image_mode
    from core.pipeline import PipelineOptions, process_image_bytes

    image_data = create_detailed_spread_bytes()
    options = PipelineOptions(
        quality=90,
        crop_mode="none",
        crop_power=0.0,
        spread_mode="split",
    )

    pages, _ = process_image_bytes(image_data, is_cover=False, options=options)
    expected_quality = max(60, min(options.quality, estimate_jpeg_quality(image_data) - 8))

    with Image.open(BytesIO(image_data)) as raw:
        image = normalize_image_mode(raw)

    width, height = image.size
    middle = width // 2
    expected_pages = [
        encode_jpeg(image.crop((middle, 0, width, height)), expected_quality),
        encode_jpeg(image.crop((0, 0, middle, height)), expected_quality),
    ]

    assert pages == expected_pages


def test_rotate_mode_preserves_legacy_quality_offset():
    from core.compressor import estimate_jpeg_quality
    from core.encoding import encode_jpeg, normalize_image_mode
    from core.pipeline import PipelineOptions, process_image_bytes

    image_data = create_detailed_spread_bytes()
    options = PipelineOptions(
        quality=90,
        crop_mode="none",
        crop_power=0.0,
        spread_mode="rotate",
    )

    pages, _ = process_image_bytes(image_data, is_cover=False, options=options)
    expected_quality = max(60, min(options.quality, estimate_jpeg_quality(image_data) - 8))

    with Image.open(BytesIO(image_data)) as raw:
        image = normalize_image_mode(raw)

    expected_pages = [
        encode_jpeg(image.transpose(Image.ROTATE_270), expected_quality),
    ]

    assert pages == expected_pages


def test_processor_module_drops_legacy_duplicate_helpers():
    import core.processor as processor

    legacy_module_helpers = [
        "find_7zip",
        "natural_sort_key",
        "is_wide_image",
        "split_and_compress",
        "rotate_and_compress",
        "extract_rar_with_7zip",
        "get_epub_images",
    ]
    legacy_task_methods = [
        "_build_image_jobs",
        "_process_images_parallel",
        "_write_results_to_cbz",
    ]

    for name in legacy_module_helpers:
        assert not hasattr(processor, name)

    for name in legacy_task_methods:
        assert not hasattr(processor.TaskProcessor, name)
