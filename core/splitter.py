"""
双页裁剪模块
日漫阅读顺序：右 -> 左
"""
from pathlib import Path

from PIL import Image

from .pipeline import PipelineOptions, is_wide_image, process_image_bytes


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
    options = PipelineOptions(
        quality=95,
        crop_mode='none',
        crop_power=0.0,
        spread_mode='split',
    )
    pages, _ = process_image_bytes(image_data, is_cover=False, options=options)
    if reading_order == 'rtl':
        return pages[0], pages[1]
    return pages[1], pages[0]


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
    pages, _ = process_image_bytes(
        image_data,
        is_cover=is_cover,
        options=PipelineOptions(
            quality=quality,
            crop_mode='none',
            crop_power=0.0,
            spread_mode='split',
        ),
    )
    return pages


__all__ = [
    'is_wide_image',
    'process_image_for_split',
]
