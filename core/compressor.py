"""
图片压缩核心模块 - 终极优化版 V2
解决裁剪后体积膨胀问题
"""
import io
import random
from pathlib import Path
from PIL import Image

from .encoding import encode_jpeg, normalize_image_mode

# 尝试导入 MozJPEG 优化库
try:
    from mozjpeg_lossless_optimization import optimize_jpeg
    HAS_MOZJPEG = True
except ImportError:
    HAS_MOZJPEG = False


# 支持的图片扩展名
SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}

# 默认质量 - 更激进
DEFAULT_QUALITY = 72


def is_image_file(filename: str) -> bool:
    """检查是否为支持的图片文件"""
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


def is_grayscale_image(img: Image.Image, sample_size: int = 2000) -> bool:
    """
    快速检测图片是否为灰度（黑白）
    使用纯 PIL + Python 随机采样，替代 numpy
    """
    if img.mode == 'L':
        return True
    if img.mode != 'RGB':
        return False

    w, h = img.size
    pixel_count = w * h

    img.load()  # 确保像素数据可用
    pixels = img.getdata()

    sample_count = min(sample_size, pixel_count)
    random.seed(42)
    indices = random.sample(range(pixel_count), sample_count)

    threshold = 15
    grayscale_count = 0
    for idx in indices:
        r, g, b = pixels[idx]
        if abs(r - g) < threshold and abs(r - b) < threshold:
            grayscale_count += 1

    return (grayscale_count / sample_count) > 0.92


def estimate_jpeg_quality(image_data: bytes) -> int:
    """
    估算原图的 JPEG 质量
    用于避免用更高质量重编码导致膨胀
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        if img.format != 'JPEG':
            return 95  # 非 JPEG 默认高质量
        
        # 通过文件大小和像素数估算质量
        pixels = img.width * img.height
        bytes_per_pixel = len(image_data) / pixels
        
        # 经验公式：低质量约 0.1-0.3 bytes/pixel，高质量约 0.5-1.0
        if bytes_per_pixel < 0.15:
            return 60
        elif bytes_per_pixel < 0.25:
            return 70
        elif bytes_per_pixel < 0.4:
            return 80
        elif bytes_per_pixel < 0.6:
            return 85
        else:
            return 90
    except Exception:
        return 80


def compress_image(
    image_data: bytes,
    quality: int = DEFAULT_QUALITY,
    crop_mode: str = 'none',
    crop_power: float = 1.0,
    force_grayscale: bool = False
) -> tuple[bytes, dict]:
    """
    高效压缩图片
    
    关键改进：
    1. 检测原图质量，避免用更高质量重编码
    2. 更激进的默认质量 (72)
    3. 灰度检测自动转换
    4. MozJPEG 无损优化
    5. 白边裁剪和页码裁剪
    """
    from .cropper import apply_crop
    
    original_size = len(image_data)
    
    # 估算原图质量
    original_quality = estimate_jpeg_quality(image_data)
    
    # 使用更低的质量（避免膨胀）
    actual_quality = min(quality, original_quality - 5)
    actual_quality = max(60, actual_quality)  # 不低于 60
    
    with Image.open(io.BytesIO(image_data)) as raw:
        img = normalize_image_mode(raw)
    
    # 应用裁剪
    img = apply_crop(img, crop_mode, crop_power)
    
    # 灰度检测
    is_gray = force_grayscale or (img.mode == 'RGB' and is_grayscale_image(img))
    if is_gray and img.mode == 'RGB':
        img = img.convert('L')
    
    compressed_data = encode_jpeg(img, actual_quality)
    
    compressed_size = len(compressed_data)
    
    stats = {
        'original_size': original_size,
        'compressed_size': compressed_size,
        'ratio': compressed_size / original_size if original_size > 0 else 1.0,
        'saved': original_size - compressed_size,
        'is_grayscale': img.mode == 'L',
        'quality_used': actual_quality,
        'original_quality': original_quality
    }
    
    return compressed_data, stats


__all__ = [
    'DEFAULT_QUALITY',
    'SUPPORTED_EXTENSIONS',
    'compress_image',
    'estimate_jpeg_quality',
    'is_grayscale_image',
    'is_image_file',
]
