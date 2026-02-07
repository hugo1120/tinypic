"""
图片裁剪模块
参考 KCC (Kindle Comic Converter) 实现
支持：白边裁剪、页码裁剪
"""
from PIL import Image, ImageOps, ImageFilter
import numpy as np
from typing import Optional, Tuple, Literal


def threshold_from_power(power: float) -> int:
    """根据力度计算阈值"""
    return int(240 - (power * 64))


def group_close_values(vals, max_dist_tolerated: float) -> list:
    """将相近的值分组"""
    groups = []
    group_start = -1
    group_end = 0
    
    for i in range(len(vals)):
        dist = vals[i] - group_end
        if group_start == -1:
            group_start = vals[i]
            group_end = vals[i]
        elif dist <= max_dist_tolerated:
            group_end = vals[i]
        else:
            groups.append((group_start, group_end))
            group_start = -1
            group_end = -1
            
    if group_start != -1:
        groups.append((group_start, group_end))
        
    return groups


def detect_background_color(img: Image.Image) -> str:
    """检测背景颜色（白色或黑色）"""
    if img.mode != 'L':
        gray = ImageOps.grayscale(img)
    else:
        gray = img
    
    # 采样四个角
    w, h = gray.size
    corners = [
        gray.getpixel((5, 5)),
        gray.getpixel((w-6, 5)),
        gray.getpixel((5, h-6)),
        gray.getpixel((w-6, h-6)),
    ]
    avg = sum(corners) / 4
    return 'white' if avg > 128 else 'black'


def ignore_pixels_near_edge(bw_img: Image.Image) -> None:
    """忽略边缘附近的噪点"""
    w, h = bw_img.size
    edge_boxes = [
        (0, 0, w, int(0.02 * h)),           # 顶部
        (0, int(0.98 * h), w, h),           # 底部
        (0, 0, int(0.02 * w), h),           # 左侧
        (int(0.98 * w), 0, w, h)            # 右侧
    ]
    
    for box in edge_boxes:
        edge = bw_img.crop(box)
        if not edge.height or not edge.width:
            continue
        hist = edge.histogram()
        imperfections = hist[255] / (edge.height * edge.width)
        if 0 < imperfections < 0.02:
            bw_img.paste(im=0, box=box)


def crop_margins(img: Image.Image, power: float = 1.0) -> Image.Image:
    """
    白边裁剪
    
    Args:
        img: PIL 图片
        power: 裁剪力度 (0-3)，越高越激进
        
    Returns:
        裁剪后的图片
    """
    if power <= 0:
        return img
    
    # 自动检测背景色
    bg_color = detect_background_color(img)
    
    # 转灰度
    if img.mode != 'L':
        gray = ImageOps.grayscale(img)
    else:
        gray = img.copy()
    
    # 黑色背景需要反转
    if bg_color != 'white':
        gray = ImageOps.invert(gray)
    
    # 自动对比度 + 模糊降噪
    gray = ImageOps.autocontrast(gray, 1).filter(ImageFilter.BoxBlur(1))
    
    # 二值化
    threshold = threshold_from_power(power)
    bw_img = gray.point(lambda p: 255 if p <= threshold else 0)
    
    # 忽略边缘噪点
    ignore_pixels_near_edge(bw_img)
    
    # 获取边界框
    bbox = bw_img.getbbox()
    
    if bbox:
        return img.crop(bbox)
    return img


def crop_page_number(img: Image.Image, power: float = 1.0) -> Image.Image:
    """
    页码裁剪（裁剪底部页码）
    
    Args:
        img: PIL 图片
        power: 裁剪力度 (0-3)
        
    Returns:
        裁剪后的图片
    """
    if power <= 0:
        return img
    
    # 页码尺寸假设（相对于图片尺寸的百分比）
    max_shape_size = (0.015 * 3, 0.02)
    min_shape_size = (0.003, 0.006)
    window_h_size = max_shape_size[1] * 1.25
    max_dist = (0.01, 0.002)
    
    # 自动检测背景色
    bg_color = detect_background_color(img)
    
    # 转灰度
    if img.mode != 'L':
        gray = ImageOps.grayscale(img)
    else:
        gray = img.copy()
    
    if bg_color != 'white':
        gray = ImageOps.invert(gray)
    
    gray = ImageOps.autocontrast(gray, 1).filter(ImageFilter.BoxBlur(1))
    
    threshold = threshold_from_power(power)
    bw_img = gray.point(lambda p: 255 if p <= threshold else 0)
    ignore_pixels_near_edge(bw_img)
    
    bw_bbox = bw_img.getbbox()
    if not bw_bbox:
        return img
    
    left, top_y_pos, right, bot_y_pos = bw_bbox
    
    # 检查底部窗口区域
    window_h = int(img.size[1] * window_h_size)
    if window_h <= 0:
        return img
    
    img_part = gray.crop((left, bot_y_pos - window_h, right, bot_y_pos))
    
    # 检测底部区域的物体
    img_part_mat = np.array(img_part)
    window_groups = []
    
    for i in range(img_part.size[1]):
        row = img_part_mat[i] if i < img_part_mat.shape[0] else []
        if len(row) == 0:
            continue
        indices = np.where(row <= threshold)[0]
        row_groups = [(g[0], g[1], i, i) for g in group_close_values(indices, img.size[0] * max_dist[0])]
        window_groups.extend(row_groups)
    
    if not window_groups:
        return img
    
    window_groups = np.array(window_groups)
    boxes = merge_boxes(window_groups, (img.size[0] * max_dist[0], img.size[1] * max_dist[1]))
    
    # 过滤小物体
    boxes = [box for box in boxes 
             if box[1] - box[0] >= img.size[0] * min_shape_size[0]
             and box[3] - box[2] >= img.size[1] * min_shape_size[1]]
    
    # 找最底部的物体
    lowest_boxes = [box for box in boxes if box[3] == window_h - 1]
    
    if not lowest_boxes:
        return img
    
    min_y = min(box[2] for box in lowest_boxes)
    boxes_in_range = [box for box in boxes if box[3] >= min_y]
    
    max_shape = (img.size[0] * max_shape_size[0], max(img.size[1] * max_shape_size[1], 3))
    
    # 判断是否应该裁剪
    should_crop = (
        len(boxes_in_range) == 1
        and (boxes_in_range[0][1] - boxes_in_range[0][0] <= max_shape[0])
        and (boxes_in_range[0][3] - boxes_in_range[0][2] <= max_shape[1])
    )
    
    if should_crop:
        crop_y = bot_y_pos - (window_h - boxes_in_range[0][2] + 1)
        cropped = img.crop((0, 0, img.size[0], crop_y))
        return cropped
    
    return img


def merge_boxes(boxes: np.ndarray, max_dist: Tuple[float, float]) -> list:
    """合并相近的边界框"""
    boxes = list(boxes)
    j = 0
    
    while j < len(boxes) - 1:
        g1 = boxes[j]
        intersecting = []
        other = []
        
        for i in range(j + 1, len(boxes)):
            g2 = boxes[i]
            if box_intersect(g1, g2, max_dist):
                intersecting.append(g2)
            else:
                other.append(g2)
        
        if intersecting:
            all_boxes = np.array([g1] + intersecting)
            merged = [
                np.min(all_boxes[:, 0]),
                np.max(all_boxes[:, 1]),
                np.min(all_boxes[:, 2]),
                np.max(all_boxes[:, 3])
            ]
            other.append(merged)
            boxes = boxes[:j] + other
            j = 0
        else:
            j += 1
    
    return boxes


def box_intersect(box1, box2, max_dist: Tuple[float, float]) -> bool:
    """判断两个边界框是否相交（包括距离容差）"""
    return not (
        box2[0] - max_dist[0] > box1[1]
        or box2[1] + max_dist[0] < box1[0]
        or box2[2] - max_dist[1] > box1[3]
        or box2[3] + max_dist[1] < box1[2]
    )


def apply_crop(img: Image.Image, mode: str, power: float = 1.0) -> Image.Image:
    """
    应用裁剪
    
    Args:
        img: PIL 图片
        mode: 裁剪模式 ('none', 'margins', 'margins+page')
        power: 裁剪力度 (0-3)
        
    Returns:
        裁剪后的图片
    """
    if mode == 'none' or power <= 0:
        return img
    
    result = img
    
    # 白边裁剪
    if mode in ('margins', 'margins+page'):
        result = crop_margins(result, power)
    
    # 页码裁剪
    if mode == 'margins+page':
        result = crop_page_number(result, power)
    
    return result
