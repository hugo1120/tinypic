"""
图片压缩核心模块 - 终极优化版 V2
解决裁剪后体积膨胀问题
"""
import io
from pathlib import Path
from PIL import Image
import numpy as np

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
    """
    if img.mode == 'L':
        return True
    if img.mode != 'RGB':
        return False
    
    arr = np.array(img)
    h, w = arr.shape[:2]
    
    np.random.seed(42)
    sample_count = min(sample_size, h * w)
    indices = np.random.choice(h * w, sample_count, replace=False)
    
    rows = indices // w
    cols = indices % w
    samples = arr[rows, cols]
    
    r, g, b = samples[:, 0], samples[:, 1], samples[:, 2]
    
    diff_rg = np.abs(r.astype(int) - g.astype(int))
    diff_rb = np.abs(r.astype(int) - b.astype(int))
    
    threshold = 15
    grayscale_ratio = np.mean((diff_rg < threshold) & (diff_rb < threshold))
    
    return grayscale_ratio > 0.92


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
    
    img = Image.open(io.BytesIO(image_data))
    
    # 处理透明通道
    if img.mode in ('RGBA', 'P', 'LA'):
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
    
    # 应用裁剪
    img = apply_crop(img, crop_mode, crop_power)
    
    # 灰度检测
    is_gray = force_grayscale or (img.mode == 'RGB' and is_grayscale_image(img))
    if is_gray and img.mode == 'RGB':
        img = img.convert('L')
    
    # 压缩
    output_buffer = io.BytesIO()
    
    save_kwargs = {
        'format': 'JPEG',
        'quality': actual_quality,
        'optimize': True,
    }
    
    if img.mode == 'RGB':
        save_kwargs['subsampling'] = '4:2:0'
        save_kwargs['progressive'] = True
    
    img.save(output_buffer, **save_kwargs)
    compressed_data = output_buffer.getvalue()
    
    # MozJPEG 无损优化
    if HAS_MOZJPEG:
        try:
            compressed_data = optimize_jpeg(compressed_data)
        except Exception:
            pass
    
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
