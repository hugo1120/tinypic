# TinyPic

<p align="center">
  <img src="favicon.png" alt="TinyPic" width="128">
</p>

<p align="center">
  <strong>批量漫画压缩与 CBZ 整理工具 | Batch Comic Compression and CBZ Packaging Tool</strong>
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

TinyPic 是一个面向 Windows 的桌面工具，用来把漫画文件夹或压缩包整理并压缩成更适合阅读器使用的 `CBZ`。它提供双页处理、白边/页码裁剪、批量任务和持久化设置，适合日常整理漫画库或给电纸书、平板阅读器减体积。

### 功能特性

#### 📦 输入与输出
- **输入类型**：文件夹、ZIP、CBZ、RAR、CBR、EPUB
- **输出类型**：CBZ
- **输出命名**：自动输出为同目录下的 `*_tinypic.cbz`
- **批量处理**：支持一次拖入多个任务，逐个处理并显示结果

#### ✂️ 页面处理
- **双页处理模式**：
  - `拆分双页`：检测宽图后按日漫顺序 `右 -> 左` 切成两页
  - `自动旋转`：宽图顺时针旋转 90 度，适合竖屏阅读器
  - `不处理`：保留原图页面结构
- **封面保护**：首张图片按封面处理，不做双页拆分
- **裁剪模式**：
  - `不裁剪`
  - `白边裁剪`
  - `白边 + 页码裁剪`
- **裁剪力度**：`0.0 - 3.0` 可调，白边裁剪和页码裁剪共用同一力度参数

#### 🗜️ 压缩与画质
- **压缩质量**：`60 - 95` 可调，默认 `72`
- **动态质量控制**：尽量避免裁剪后体积反而变大
- **灰度检测**：黑白漫画会按更合适的方式编码
- **MozJPEG 优化**：额外做无损 Huffman 优化
- **输出格式**：统一写入 JPEG 页面并打包为无压缩存储的 CBZ

#### ⚡ 性能与稳定性
- **多线程处理**：`1 - 8` 线程可调
- **低峰值内存**：文件夹、ZIP/CBZ、EPUB、RAR/CBR 都按需读取，避免整本预读进内存
- **EPUB 回退机制**：优先读取 OPF 清单；如果元数据损坏，会回退到图片扫描而不是直接失败
- **任务结果可见**：界面会显示压缩前后大小、压缩比例和单任务错误数量
- **单文件 EXE**：打包后为单个 `TinyPic.exe`，便于分发

#### 💾 设置记忆
- 会记住以下选项：
  - 压缩质量
  - 处理线程
  - 裁剪模式
  - 裁剪力度
  - 双页处理模式
- **源码运行**：配置写入项目根目录的 `config.json`
- **打包运行**：配置写入 `TinyPic.exe` 同目录的 `config.json`

### 技术栈

| 组件 | 技术 |
|------|------|
| GUI | PySide6 (Qt6) |
| 图像处理 | Pillow |
| JPEG 优化 | mozjpeg-lossless-optimization |
| RAR/CBR 解压 | 7-Zip（外部依赖） |
| 打包 | PyInstaller |

### 安装

#### 方式一：下载 Release
从 [Releases](../../releases) 下载 `TinyPic.exe`，双击运行。

#### 方式二：从源码运行
```bash
git clone https://github.com/hugo1120/tinypic.git
cd tinypic
pip install -r requirements.txt
python main.py
```

### 使用

1. 拖拽文件夹、`CBZ/ZIP/RAR/CBR/EPUB` 到窗口
2. 设置压缩质量、线程数、裁剪模式、裁剪力度、双页处理模式
3. 点击“开始处理”
4. 等待任务完成并查看每个任务的压缩结果

输出文件会保存在原文件同目录，文件名后缀为 `_tinypic.cbz`。

### 打包

#### 方式一：使用脚本
双击 `build.bat`。

注意：
- 脚本默认使用 `C:\Python313\python.exe`
- 脚本会清理旧产物，并把 PyInstaller 缓存放到项目目录内

#### 方式二：手动打包
```bash
python -m PyInstaller TinyPic.spec --clean --noconfirm
```

打包输出位于 `dist/TinyPic.exe`。

### 系统要求

- **操作系统**：Windows 10/11
- **RAR/CBR 支持**：需要安装 [7-Zip](https://www.7-zip.org/)
- **默认查找路径**：
  - `"C:\Program Files\7-Zip\7z.exe"`
  - `"C:\Program Files (x86)\7-Zip\7z.exe"`
  - `"D:\Program Files\7-Zip\7z.exe"`
  - `"D:\Program Files (x86)\7-Zip\7z.exe"`
- **源码运行环境**：Python 3.10+

---

## English

### Introduction

TinyPic is a Windows desktop tool for turning comic folders or archives into smaller, reader-friendly `CBZ` files. It provides spread handling, margin/page-number cropping, batch processing, and persistent settings, which makes it useful for organizing manga libraries or preparing files for e-readers and tablets.

### Features

#### 📦 Input and Output
- **Input types**: Folder, ZIP, CBZ, RAR, CBR, EPUB
- **Output type**: CBZ
- **Output naming**: Saved next to the source as `*_tinypic.cbz`
- **Batch workflow**: You can drag in multiple tasks and process them one by one

#### ✂️ Page Processing
- **Spread modes**:
  - `Split`: Detect wide pages and split them in manga order `right -> left`
  - `Rotate`: Rotate wide pages 90 degrees clockwise for portrait readers
  - `None`: Keep the original page layout
- **Cover protection**: The first image is treated as a cover and is not split
- **Crop modes**:
  - `None`
  - `Margins`
  - `Margins + Page Number`
- **Crop power**: Adjustable from `0.0 - 3.0`; the same value is shared by both margin cropping and page-number cropping

#### 🗜️ Compression and Quality
- **Compression quality**: Adjustable from `60 - 95`, default `72`
- **Dynamic quality control**: Reduces the chance of files becoming larger after processing
- **Grayscale detection**: Black-and-white comics are encoded more appropriately
- **MozJPEG optimization**: Applies additional lossless Huffman optimization
- **Output format**: Pages are written as JPEG and packaged into a store-only CBZ archive

#### ⚡ Performance and Reliability
- **Multi-threading**: Adjustable from `1 - 8` worker threads
- **Lower memory usage**: Folder, ZIP/CBZ, EPUB, and RAR/CBR sources are loaded on demand instead of fully preloading the whole book
- **EPUB fallback**: The app prefers OPF manifest order; if EPUB metadata is broken, it falls back to scanning image entries instead of failing immediately
- **Visible task results**: The UI shows original size, compressed size, compression ratio, and per-task error count
- **Single-file EXE**: Packaged output is a single `TinyPic.exe`

#### 💾 Settings Persistence
- TinyPic remembers:
  - Compression quality
  - Worker thread count
  - Crop mode
  - Crop power
  - Spread mode
- **Running from source**: settings are written to `config.json` in the repository root
- **Running from the packaged EXE**: settings are written to `config.json` next to `TinyPic.exe`

### Tech Stack

| Component | Technology |
|-----------|------------|
| GUI | PySide6 (Qt6) |
| Image Processing | Pillow |
| JPEG Optimization | mozjpeg-lossless-optimization |
| RAR/CBR Extraction | 7-Zip (external dependency) |
| Packaging | PyInstaller |

### Installation

#### Option 1: Download Release
Download `TinyPic.exe` from [Releases](../../releases) and run it.

#### Option 2: Run from Source
```bash
git clone https://github.com/hugo1120/tinypic.git
cd tinypic
pip install -r requirements.txt
python main.py
```

### Usage

1. Drag a folder or `CBZ/ZIP/RAR/CBR/EPUB` file into the window
2. Configure quality, worker threads, crop mode, crop power, and spread mode
3. Click `Start`
4. Wait for completion and review the result of each task

Output files are saved next to the source with the `_tinypic.cbz` suffix.

### Build

#### Option 1: Use the script
Double-click `build.bat`.

Notes:
- The script uses `C:\Python313\python.exe` by default
- It removes old build artifacts and stores the PyInstaller cache inside the project directory

#### Option 2: Build manually
```bash
python -m PyInstaller TinyPic.spec --clean --noconfirm
```

The packaged executable is generated at `dist/TinyPic.exe`.

### Requirements

- **OS**: Windows 10/11
- **RAR/CBR support**: Requires [7-Zip](https://www.7-zip.org/)
- **Default lookup paths**:
  - `"C:\Program Files\7-Zip\7z.exe"`
  - `"C:\Program Files (x86)\7-Zip\7z.exe"`
  - `"D:\Program Files\7-Zip\7z.exe"`
  - `"D:\Program Files (x86)\7-Zip\7z.exe"`
- **Source runtime**: Python 3.10+

---

## License

MIT License
