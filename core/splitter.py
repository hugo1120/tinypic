"""
双页裁剪模块
日漫阅读顺序：右 -> 左
"""
import io
from pathlib import Path
from PIL import Image


def is_wide_image(image_data: bytes) -> bool:
    """
    判断图片是否为宽图（双页）
    宽 > 高 则为宽图
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        return img.width > img.height
    except Exception:
        return False


def is_wide_image_file(path: Path) -> bool:
    """判断文件是否为宽图"""
    try:
        with Image.open(path) as img:
            return img.width > img.height
    except Exception:
        return False


def split_double_page(image_data: bytes, reading_order: str = 'rtl') -> tuple[bytes, bytes]:
    """
    将双页图片切分为两张单页
    
    Args:
        image_data: 原始图片数据
        reading_order: 阅读顺序
            - 'rtl': 从右到左（日漫，默认）- 返回 (右半, 左半)
            - 'ltr': 从左到右（欧美漫画）- 返回 (左半, 右半)
    
    Returns:
        (第一页, 第二页) 的字节数据
    """
    img = Image.open(io.BytesIO(image_data))
    
    # 确保是 RGB 模式
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        if img.mode in ('RGBA', 'LA'):
            background.paste(img, mask=img.split()[-1])
            img = background
        else:
            img = img.convert('RGB')
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    w, h = img.size
    mid = w // 2
    
    # 裁剪
    left_half = img.crop((0, 0, mid, h))
    right_half = img.crop((mid, 0, w, h))
    
    # 根据阅读顺序返回
    if reading_order == 'rtl':
        # 日漫：先右后左
        first_page, second_page = right_half, left_half
    else:
        # 欧美漫画：先左后右
        first_page, second_page = left_half, right_half
    
    # 转为字节
    first_buffer = io.BytesIO()
    second_buffer = io.BytesIO()
    
    first_page.save(first_buffer, format='JPEG', quality=95, optimize=True)
    second_page.save(second_buffer, format='JPEG', quality=95, optimize=True)
    
    return first_buffer.getvalue(), second_buffer.getvalue()


def process_image_for_split(
    image_data: bytes,
    is_cover: bool = False,
    quality: int = 90
) -> list[bytes]:
    """
    处理单张图片，根据是否为双页返回结果
    
    Args:
        image_data: 原始图片数据
        is_cover: 是否为封面（封面不裁剪）
        quality: JPEG 质量
    
    Returns:
        图片数据列表（1张或2张）
    """
    from .compressor import compress_image
    
    # 封面不裁剪
    if is_cover:
        compressed, _ = compress_image(image_data, quality)
        return [compressed]
    
    # 判断是否为双页
    if is_wide_image(image_data):
        # 双页，切分
        return list(split_double_page(image_data, 'rtl'))
    else:
        # 单页，只压缩
        compressed, _ = compress_image(image_data, quality)
        return [compressed]
