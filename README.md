# TinyPic

<p align="center">
  <img src="favicon.png" alt="TinyPic" width="128">
</p>

<p align="center">
  <strong>批量漫画压缩工具 | Batch Comic Compression Tool</strong>
</p>

<p align="center">
  <a href="#中文">中文</a> •
  <a href="#english">English</a>
</p>

<p align="center">
  <b>中文</b>: <a href="#功能特性">功能</a> • <a href="#安装">安装</a> • <a href="#使用">使用</a> • <a href="#打包">打包</a>
  <br>
  <b>English</b>: <a href="#features">Features</a> • <a href="#installation">Installation</a> • <a href="#usage">Usage</a> • <a href="#build">Build</a>
</p>

---

## 中文

### 简介

TinyPic 是一款专为漫画/图片压缩设计的桌面工具，支持批量处理，自动双页裁剪，白边去除，视觉无损压缩。

### 功能特性

#### 📦 格式支持
- **输入**: 文件夹、ZIP、CBZ、RAR、CBR、EPUB
- **输出**: CBZ (ZIP 格式漫画包)

#### ✂️ 智能裁剪
- **双页切分**: 自动检测宽图并按日漫顺序（右→左）切分
- **自动旋转**: 宽图顺时针旋转 90°，适合阅读器全屏查看
- **白边裁剪**: 去除图片四周空白边距，节省 5-15% 体积
- **页码裁剪**: 智能检测并移除底部页码，额外节省 2-5%
- **裁剪力度**: 0-3 可调，越高越激进

#### 📖 双页处理
- **拆分双页**: 自动切分为左右单页（日漫阅读顺序）
- **自动旋转**: 宽幅双页旋转 90°，适配竖屏阅读器
- **不处理**: 保留原图不做双页处理

#### 🗜️ 高效压缩
- **动态质量**: 根据原图质量自动调整，避免重编码膨胀
- **灰度检测**: 自动识别黑白漫画并转换格式
- **MozJPEG 优化**: Huffman 表优化，无损再压缩
- **色度抽样**: 4:2:0 抽样 + 渐进式 JPEG

#### ⚡ 性能优化
- **快速启动**: EXE 体积优化至 ~32 MB，启动时间大幅缩短
- **多线程处理**: 1-100 线程可调
- **7-Zip 集成**: 调用本地安装的 7-Zip 解压 RAR 文件

#### 💾 设置持久化
- 所有设置自动保存到 `config.json`

### 技术栈

| 组件 | 技术 |
|------|------|
| GUI | PySide6 (Qt6) |
| 图像处理 | Pillow |
| JPEG 优化 | mozjpeg-lossless-optimization |
| RAR 解压 | 7-Zip (外部) |
| 打包 | PyInstaller |

### 安装

#### 方式一：下载 Release
从 [Releases](../../releases) 下载 `TinyPic.exe`，双击运行。

#### 方式二：从源码运行
```bash
# 克隆仓库
git clone https://github.com/hugo1120/tinypic.git
cd tinypic

# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 使用

1. 拖拽漫画文件夹或压缩包到窗口
2. 调整压缩质量 (60-95)
3. 选择裁剪模式
4. 选择双页处理模式（拆分 / 旋转 / 不处理）
5. 点击「开始处理」

输出文件保存在原文件同目录，文件名后缀 `_tinypic.cbz`。

### 打包

双击 `build.bat` 或运行：
```bash
python -m PyInstaller TinyPic.spec --clean
```

---

### 系统要求

- **操作系统**: Windows 10/11
- **RAR 支持**: 需要安装 [7-Zip](https://www.7-zip.org/)
  - 默认查找路径:
    - `"C:\Program Files\7-Zip\7z.exe"`
    - `"C:\Program Files (x86)\7-Zip\7z.exe"`

---

## English

### Introduction

TinyPic is a desktop tool designed for batch comic/image compression with automatic double-page splitting, margin cropping, and visually lossless compression.

### Features

#### 📦 Format Support
- **Input**: Folder, ZIP, CBZ, RAR, CBR, EPUB
- **Output**: CBZ (ZIP-based comic archive)
- *Note: RAR/CBR support requires 7-Zip installed*

#### ✂️ Smart Cropping
- **Double-page Split**: Auto-detect wide images and split in manga order (right→left)
- **Auto Rotate**: Rotate wide images 90° clockwise for e-reader full-screen viewing
- **Margin Cropping**: Remove white/black margins, save 5-15% size
- **Page Number Cropping**: Intelligently detect and remove bottom page numbers, save 2-5% more
- **Cropping Power**: Adjustable 0-3, higher = more aggressive

#### 📖 Spread Processing
- **Split**: Auto-split wide pages into left/right (manga reading order)
- **Rotate**: Rotate wide pages 90° for portrait e-readers
- **None**: Keep original double pages as-is

#### 🗜️ Efficient Compression
- **Dynamic Quality**: Auto-adjust based on source quality to avoid bloat
- **Grayscale Detection**: Auto-convert B&W comics
- **MozJPEG Optimization**: Huffman table optimization for lossless re-compression
- **Chroma Subsampling**: 4:2:0 + Progressive JPEG

#### ⚡ Performance
- **Fast Startup**: Optimized to ~32 MB EXE with significantly faster launch times
- **Multi-threading**: 1-100 threads configurable
- **7-Zip Integration**: Direct RAR processing (requires 7-Zip)

#### 💾 Settings Persistence
- All settings auto-saved to `config.json`

### Tech Stack

| Component | Technology |
|-----------|------------|
| GUI | PySide6 (Qt6) |
| Image Processing | Pillow |
| JPEG Optimization | mozjpeg-lossless-optimization |
| RAR Extraction | 7-Zip (external) |
| Packaging | PyInstaller |

### Installation

#### Option 1: Download Release
Download `TinyPic.exe` from [Releases](../../releases) and run.

#### Option 2: Run from Source
```bash
# Clone repository
git clone https://github.com/hugo1120/tinypic.git
cd tinypic

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

### Usage

1. Drag comic folders or archives into the window
2. Adjust compression quality (60-95)
3. Select cropping mode
4. Select spread processing mode (Split / Rotate / None)
5. Click "Start Processing"

Output files are saved in the same directory with `_tinypic.cbz` suffix.

### Build

Double-click `build.bat` or run:
```bash
python -m PyInstaller TinyPic.spec --clean
```

---

## License

MIT License

## Requirements

- **OS**: Windows 10/11
- **RAR Support**: Requires [7-Zip](https://www.7-zip.org/) installed
  - Default paths checked:
    - `"C:\Program Files\7-Zip\7z.exe"`
    - `"C:\Program Files (x86)\7-Zip\7z.exe"`
- **Source Code**: Python 3.10+
