"""
文件/压缩包处理模块
支持：文件夹、ZIP、CBZ、RAR、CBR、EPUB
使用 7-Zip 解压 RAR（无需 UnRAR）
支持：白边裁剪、页码裁剪
"""
import re
import io
import os
import sys
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Callable, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import xml.etree.ElementTree as ET

from .compressor import (
    compress_image, is_image_file, is_grayscale_image,
    estimate_jpeg_quality, DEFAULT_QUALITY, HAS_MOZJPEG
)
from .cropper import apply_crop

# 尝试导入 MozJPEG
try:
    from mozjpeg_lossless_optimization import optimize_jpeg
except ImportError:
    optimize_jpeg = None


# 文件名后缀
OUTPUT_SUFFIX = '_tinypic'

# 支持的格式
ARCHIVE_EXTENSIONS = {'.zip', '.cbz'}
RAR_EXTENSIONS = {'.rar', '.cbr'}
EPUB_EXTENSIONS = {'.epub'}


def find_7zip() -> Optional[str]:
    """查找 7-Zip 可执行文件"""
    possible_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        r"D:\Program Files\7-Zip\7z.exe",
        r"D:\Program Files (x86)\7-Zip\7z.exe",
    ]
    
    import shutil
    path_7z = shutil.which("7z")
    if path_7z:
        return path_7z
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


SEVENZIP_PATH = find_7zip()


def natural_sort_key(s: str):
    """自然排序键"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]


def is_wide_image(image_data: bytes) -> bool:
    """判断是否为宽图（双页）"""
    try:
        img = Image.open(io.BytesIO(image_data))
        return img.width > img.height
    except Exception:
        return False


def split_and_compress(
    image_data: bytes, 
    base_quality: int = DEFAULT_QUALITY,
    crop_mode: str = 'none',
    crop_power: float = 1.0
) -> Tuple[bytes, bytes]:
    """将双页切分并压缩（日漫顺序：右→左）"""
    original_quality = estimate_jpeg_quality(image_data)
    actual_quality = min(base_quality, original_quality - 8)
    actual_quality = max(60, actual_quality)
    
    img = Image.open(io.BytesIO(image_data))
    
    # 模式转换
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert('RGB')
    elif img.mode == 'L':
        pass
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    is_gray = img.mode == 'L' or (img.mode == 'RGB' and is_grayscale_image(img))
    
    w, h = img.size
    mid = w // 2
    
    right_half = img.crop((mid, 0, w, h))
    left_half = img.crop((0, 0, mid, h))
    
    # 应用裁剪
    right_half = apply_crop(right_half, crop_mode, crop_power)
    left_half = apply_crop(left_half, crop_mode, crop_power)
    
    if is_gray:
        if right_half.mode == 'RGB':
            right_half = right_half.convert('L')
        if left_half.mode == 'RGB':
            left_half = left_half.convert('L')
    
    def save_optimized(img_part):
        buf = io.BytesIO()
        save_kwargs = {
            'format': 'JPEG',
            'quality': actual_quality,
            'optimize': True,
        }
        if img_part.mode == 'RGB':
            save_kwargs['subsampling'] = '4:2:0'
            save_kwargs['progressive'] = True
        
        img_part.save(buf, **save_kwargs)
        data = buf.getvalue()
        
        if optimize_jpeg:
            try:
                data = optimize_jpeg(data)
            except Exception:
                pass
        
        return data
    
    return save_optimized(right_half), save_optimized(left_half)


def process_single_image(args: tuple) -> Tuple[int, bool, List[bytes], int]:
    """处理单张图片（供多线程调用）"""
    index, image_data, is_cover, quality, crop_mode, crop_power = args
    original_size = len(image_data)
    
    if is_cover or not is_wide_image(image_data):
        # 单页：压缩 + 裁剪
        compressed, _ = compress_image(image_data, quality, crop_mode, crop_power)
        return (index, False, [compressed], original_size)
    else:
        # 双页：切分 + 压缩 + 裁剪
        first, second = split_and_compress(image_data, quality, crop_mode, crop_power)
        return (index, True, [first, second], original_size)


def extract_rar_with_7zip(rar_path: Path, dest_dir: Path) -> List[Path]:
    """使用 7-Zip 解压 RAR 文件"""
    if not SEVENZIP_PATH:
        raise RuntimeError("未找到 7-Zip，请安装 7-Zip 到默认路径")
    
    cmd = [
        SEVENZIP_PATH,
        'x',
        '-y',
        f'-o{dest_dir}',
        str(rar_path)
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    )
    
    if result.returncode != 0:
        raise RuntimeError(f"7-Zip 解压失败: {result.stderr.decode('utf-8', errors='ignore')}")
    
    image_files = []
    for root, dirs, files in os.walk(dest_dir):
        for f in files:
            if is_image_file(f):
                image_files.append(Path(root) / f)
    
    image_files.sort(key=lambda x: natural_sort_key(x.name))
    return image_files


def get_epub_images(epub_path: Path) -> List[Tuple[str, bytes]]:
    """从 EPUB 中提取图片"""
    images = []
    
    with zipfile.ZipFile(epub_path, 'r') as zf:
        opf_path = None
        for name in zf.namelist():
            if name.endswith('.opf'):
                opf_path = name
                break
        
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
                                if opf_dir:
                                    full_path = f"{opf_dir}/{href}"
                                else:
                                    full_path = href
                                full_path = full_path.replace('\\', '/')
                                
                                try:
                                    data = zf.read(full_path)
                                    images.append((full_path, data))
                                except KeyError:
                                    for name in zf.namelist():
                                        if name.endswith(href):
                                            data = zf.read(name)
                                            images.append((name, data))
                                            break
            except Exception:
                pass
        
        if not images:
            all_images = [
                n for n in zf.namelist()
                if is_image_file(n) and not n.endswith('/')
            ]
            all_images.sort(key=natural_sort_key)
            
            for name in all_images:
                data = zf.read(name)
                images.append((name, data))
    
    return images


class ProcessorStats:
    """处理统计信息"""
    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.original_size = 0
        self.compressed_size = 0
        self.errors = []
    
    @property
    def ratio(self) -> float:
        if self.original_size == 0:
            return 1.0
        return self.compressed_size / self.original_size


class TaskProcessor:
    """任务处理器"""
    
    def __init__(
        self,
        quality: int = DEFAULT_QUALITY,
        num_threads: int = 4,
        crop_mode: str = 'none',
        crop_power: float = 1.0,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ):
        self.quality = quality
        self.num_threads = max(1, min(100, num_threads))
        self.crop_mode = crop_mode
        self.crop_power = crop_power
        self.progress_callback = progress_callback
        self._cancelled = False
    
    def cancel(self):
        self._cancelled = True
    
    def process(self, input_path: Path) -> Tuple[Path, ProcessorStats]:
        self._cancelled = False
        suffix = input_path.suffix.lower()
        
        if input_path.is_dir():
            return self._process_folder(input_path)
        elif suffix in ARCHIVE_EXTENSIONS:
            return self._process_archive(input_path)
        elif suffix in RAR_EXTENSIONS:
            return self._process_rar(input_path)
        elif suffix in EPUB_EXTENSIONS:
            return self._process_epub(input_path)
        else:
            raise ValueError(f"不支持的输入类型: {input_path}")
    
    def _process_images_parallel(
        self, 
        image_data_list: List[Tuple],
        file_names: List[str]
    ) -> Tuple[dict, ProcessorStats]:
        """并行处理图片列表"""
        stats = ProcessorStats()
        stats.total_files = len(image_data_list)
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = {executor.submit(process_single_image, args): args[0] for args in image_data_list}
            
            completed = 0
            for future in as_completed(futures):
                if self._cancelled:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                try:
                    result = future.result()
                    index = result[0]
                    results[index] = result
                    completed += 1
                    
                    if self.progress_callback:
                        self.progress_callback(completed, stats.total_files, file_names[index])
                except Exception as e:
                    index = futures[future]
                    stats.errors.append(f"{file_names[index]}: {e}")
        
        return results, stats
    
    def _write_results_to_cbz(
        self, 
        output_path: Path, 
        results: dict, 
        stats: ProcessorStats
    ) -> None:
        """将处理结果写入 CBZ"""
        num_digits = len(str(len(results) * 2))
        page = 1
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_STORED) as zf:
            for i in sorted(results.keys()):
                _, is_double, compressed_list, original_size = results[i]
                stats.original_size += original_size
                
                for compressed in compressed_list:
                    zf.writestr(f"{page:0{num_digits}d}.jpg", compressed)
                    stats.compressed_size += len(compressed)
                    page += 1
                
                stats.processed_files += 1
    
    def _process_folder(self, folder_path: Path) -> Tuple[Path, ProcessorStats]:
        """处理文件夹"""
        image_files = [
            p for p in folder_path.rglob('*')
            if p.is_file() and is_image_file(p.name)
        ]
        image_files.sort(key=lambda x: natural_sort_key(x.name))
        
        output_path = folder_path.parent / f"{folder_path.name}{OUTPUT_SUFFIX}.cbz"
        
        image_data_list = []
        file_names = []
        for i, img_path in enumerate(image_files):
            with open(img_path, 'rb') as f:
                data = f.read()
            is_cover = (i == 0)
            image_data_list.append((i, data, is_cover, self.quality, self.crop_mode, self.crop_power))
            file_names.append(img_path.name)
        
        results, stats = self._process_images_parallel(image_data_list, file_names)
        self._write_results_to_cbz(output_path, results, stats)
        
        return output_path, stats
    
    def _process_archive(self, archive_path: Path) -> Tuple[Path, ProcessorStats]:
        """处理 ZIP/CBZ"""
        stem = archive_path.stem
        if stem.endswith(OUTPUT_SUFFIX):
            stem = stem[:-len(OUTPUT_SUFFIX)]
        output_path = archive_path.parent / f"{stem}{OUTPUT_SUFFIX}.cbz"
        
        with zipfile.ZipFile(archive_path, 'r') as zf_in:
            entries = [
                n for n in zf_in.namelist()
                if is_image_file(n) and not n.endswith('/')
            ]
            entries.sort(key=natural_sort_key)
            
            image_data_list = []
            file_names = []
            for i, entry in enumerate(entries):
                data = zf_in.read(entry)
                is_cover = (i == 0)
                image_data_list.append((i, data, is_cover, self.quality, self.crop_mode, self.crop_power))
                file_names.append(Path(entry).name)
        
        results, stats = self._process_images_parallel(image_data_list, file_names)
        self._write_results_to_cbz(output_path, results, stats)
        
        return output_path, stats
    
    def _process_rar(self, rar_path: Path) -> Tuple[Path, ProcessorStats]:
        """处理 RAR/CBR（使用 7-Zip）"""
        stem = rar_path.stem
        if stem.endswith(OUTPUT_SUFFIX):
            stem = stem[:-len(OUTPUT_SUFFIX)]
        output_path = rar_path.parent / f"{stem}{OUTPUT_SUFFIX}.cbz"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            image_files = extract_rar_with_7zip(rar_path, temp_path)
            
            if not image_files:
                raise ValueError("RAR 中没有找到图片")
            
            image_data_list = []
            file_names = []
            for i, img_path in enumerate(image_files):
                with open(img_path, 'rb') as f:
                    data = f.read()
                is_cover = (i == 0)
                image_data_list.append((i, data, is_cover, self.quality, self.crop_mode, self.crop_power))
                file_names.append(img_path.name)
            
            results, stats = self._process_images_parallel(image_data_list, file_names)
            self._write_results_to_cbz(output_path, results, stats)
        
        return output_path, stats
    
    def _process_epub(self, epub_path: Path) -> Tuple[Path, ProcessorStats]:
        """处理 EPUB"""
        stem = epub_path.stem
        if stem.endswith(OUTPUT_SUFFIX):
            stem = stem[:-len(OUTPUT_SUFFIX)]
        output_path = epub_path.parent / f"{stem}{OUTPUT_SUFFIX}.cbz"
        
        epub_images = get_epub_images(epub_path)
        
        if not epub_images:
            raise ValueError("EPUB 中没有找到图片")
        
        image_data_list = []
        file_names = []
        for i, (name, data) in enumerate(epub_images):
            is_cover = (i == 0)
            image_data_list.append((i, data, is_cover, self.quality, self.crop_mode, self.crop_power))
            file_names.append(Path(name).name)
        
        results, stats = self._process_images_parallel(image_data_list, file_names)
        self._write_results_to_cbz(output_path, results, stats)
        
        return output_path, stats
