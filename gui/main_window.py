"""
TinyPic 主窗口 - 蓝黑主题
支持多线程设置、裁剪模式设置
"""
import os
import sys
from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPushButton,
    QSlider, QProgressBar, QFrame, QComboBox
)
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap

from core.processor import TaskProcessor, ProcessorStats
from core.settings import Settings, CROP_MODES


def get_resource_path(relative_path: str) -> str:
    """获取资源文件路径（兼容打包后的 exe）"""
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent.parent
    return str(base_path / relative_path)


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


# 蓝黑主题样式
STYLE = """
QMainWindow, QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}
QLabel#title {
    font-size: 28px;
    font-weight: bold;
    color: #58a6ff;
}
QLabel#subtitle {
    font-size: 13px;
    color: #8b949e;
}
QFrame#dropZone {
    background-color: #161b22;
    border: 2px dashed #30363d;
    border-radius: 12px;
}
QFrame#dropZone:hover {
    border-color: #58a6ff;
    background-color: #1c2128;
}
QListWidget {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 8px;
}
QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}
QListWidget::item:hover {
    background-color: #21262d;
}
QListWidget::item:selected {
    background-color: #1f6feb;
}
QPushButton {
    background-color: #238636;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2ea043;
}
QPushButton:disabled {
    background-color: #21262d;
    color: #484f58;
}
QPushButton#dangerButton {
    background-color: #da3633;
}
QPushButton#dangerButton:hover {
    background-color: #f85149;
}
QPushButton#secondaryButton {
    background-color: #21262d;
    border: 1px solid #30363d;
}
QPushButton#secondaryButton:hover {
    background-color: #30363d;
}
QSlider::groove:horizontal {
    height: 8px;
    background-color: #21262d;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -5px 0;
    background-color: #58a6ff;
    border-radius: 9px;
}
QSlider::sub-page:horizontal {
    background-color: #1f6feb;
    border-radius: 4px;
}
QProgressBar {
    background-color: #21262d;
    border: none;
    border-radius: 8px;
    height: 14px;
    text-align: center;
    color: #e6edf3;
}
QProgressBar::chunk {
    background-color: #1f6feb;
    border-radius: 8px;
}
QComboBox {
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    color: #e6edf3;
    min-width: 120px;
}
QComboBox:hover {
    border-color: #58a6ff;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #21262d;
    border: 1px solid #30363d;
    selection-background-color: #1f6feb;
    color: #e6edf3;
}
"""


class WorkerThread(QThread):
    """后台处理线程"""
    progress = Signal(int, int, str)
    task_complete = Signal(str, object)
    all_complete = Signal()
    error = Signal(str, str)
    
    def __init__(self, tasks: List[Path], quality: int, num_threads: int, 
                 crop_mode: str, crop_power: float):
        super().__init__()
        self.tasks = tasks
        self.quality = quality
        self.num_threads = num_threads
        self.crop_mode = crop_mode
        self.crop_power = crop_power
        self.processor = None
        self._cancelled = False
    
    def run(self):
        self._cancelled = False
        for task_path in self.tasks:
            if self._cancelled:
                break
            
            self.processor = TaskProcessor(
                quality=self.quality,
                num_threads=self.num_threads,
                crop_mode=self.crop_mode,
                crop_power=self.crop_power,
                progress_callback=lambda c, t, f: self.progress.emit(c, t, f)
            )
            
            try:
                output_path, stats = self.processor.process(task_path)
                self.task_complete.emit(str(task_path), stats)
            except Exception as e:
                self.error.emit(str(task_path), str(e))
        
        self.all_complete.emit()
    
    def cancel(self):
        self._cancelled = True
        if self.processor:
            self.processor.cancel()


class DropZone(QFrame):
    """拖拽区域"""
    files_dropped = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("+")
        icon.setStyleSheet("font-size: 48px; font-weight: bold; color: #58a6ff; background-color: transparent;")
        icon.setAlignment(Qt.AlignCenter)
        
        text = QLabel("拖拽文件夹或 CBZ/ZIP/RAR/EPUB 到这里")
        text.setAlignment(Qt.AlignCenter)
        text.setStyleSheet("color: #8b949e;")
        
        layout.addWidget(icon)
        layout.addWidget(text)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir() or path.suffix.lower() in ('.cbz', '.zip', '.rar', '.cbr', '.epub'):
                paths.append(path)
        if paths:
            self.files_dropped.emit(paths)


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.worker = None
        self.pending_tasks: List[Path] = []
        
        self.setup_ui()
        self.setStyleSheet(STYLE)
        self.set_icon()
    
    def set_icon(self):
        """设置窗口图标"""
        icon_path = get_resource_path('favicon.png')
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
    
    def setup_ui(self):
        self.setWindowTitle("TinyPic - 批量图片压缩")
        self.setMinimumSize(620, 620)
        self.resize(700, 700)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        # 标题
        title = QLabel("TinyPic")
        title.setObjectName("title")
        subtitle = QLabel("自动双页裁剪 + 视觉无损压缩")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        
        # 拖拽区域
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self.on_files_dropped)
        layout.addWidget(self.drop_zone)
        
        # 质量设置
        quality_layout = QHBoxLayout()
        quality_label = QLabel("压缩质量:")
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(60, 95)
        self.quality_slider.setValue(self.settings.quality)
        self.quality_slider.setFixedWidth(150)
        self.quality_slider.valueChanged.connect(self.on_quality_changed)
        
        self.quality_value = QLabel(str(self.settings.quality))
        self.quality_value.setFixedWidth(28)
        
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_value)
        quality_layout.addStretch()
        layout.addLayout(quality_layout)
        
        # 线程数设置
        thread_layout = QHBoxLayout()
        thread_label = QLabel("处理线程:")
        self.thread_slider = QSlider(Qt.Horizontal)
        self.thread_slider.setRange(1, 100)
        self.thread_slider.setValue(self.settings.num_threads)
        self.thread_slider.setFixedWidth(150)
        self.thread_slider.valueChanged.connect(self.on_thread_changed)
        
        self.thread_value = QLabel(str(self.settings.num_threads))
        self.thread_value.setFixedWidth(28)
        
        thread_layout.addWidget(thread_label)
        thread_layout.addWidget(self.thread_slider)
        thread_layout.addWidget(self.thread_value)
        thread_layout.addStretch()
        layout.addLayout(thread_layout)
        
        # 裁剪模式设置
        crop_layout = QHBoxLayout()
        crop_label = QLabel("裁剪模式:")
        self.crop_combo = QComboBox()
        for mode, name in CROP_MODES.items():
            self.crop_combo.addItem(name, mode)
        # 设置当前选中
        current_index = list(CROP_MODES.keys()).index(self.settings.crop_mode)
        self.crop_combo.setCurrentIndex(current_index)
        self.crop_combo.currentIndexChanged.connect(self.on_crop_mode_changed)
        
        crop_layout.addWidget(crop_label)
        crop_layout.addWidget(self.crop_combo)
        crop_layout.addStretch()
        layout.addLayout(crop_layout)
        
        # 裁剪力度设置
        power_layout = QHBoxLayout()
        power_label = QLabel("裁剪力度:")
        self.power_slider = QSlider(Qt.Horizontal)
        self.power_slider.setRange(0, 30)  # 0-3.0，精度 0.1
        self.power_slider.setValue(int(self.settings.crop_power * 10))
        self.power_slider.setFixedWidth(150)
        self.power_slider.valueChanged.connect(self.on_power_changed)
        
        self.power_value = QLabel(f"{self.settings.crop_power:.1f}")
        self.power_value.setFixedWidth(28)
        
        power_layout.addWidget(power_label)
        power_layout.addWidget(self.power_slider)
        power_layout.addWidget(self.power_value)
        power_layout.addStretch()
        layout.addLayout(power_layout)
        
        # 任务列表
        list_label = QLabel("任务列表")
        list_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(list_label)
        
        self.task_list = QListWidget()
        self.task_list.setMinimumHeight(100)
        layout.addWidget(self.task_list)
        
        # 进度
        self.progress_label = QLabel("就绪")
        self.progress_label.setStyleSheet("color: #8b949e;")
        layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.clicked.connect(self.clear_tasks)
        
        self.start_btn = QPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_processing)
        
        self.stop_btn = QPushButton("终止")
        self.stop_btn.setObjectName("dangerButton")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setVisible(False)
        
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.start_btn)
        layout.addLayout(btn_layout)
    
    def on_quality_changed(self, value: int):
        self.quality_value.setText(str(value))
        self.settings.quality = value
    
    def on_thread_changed(self, value: int):
        self.thread_value.setText(str(value))
        self.settings.num_threads = value
    
    def on_crop_mode_changed(self, index: int):
        mode = self.crop_combo.itemData(index)
        self.settings.crop_mode = mode
    
    def on_power_changed(self, value: int):
        power = value / 10.0
        self.power_value.setText(f"{power:.1f}")
        self.settings.crop_power = power
    
    def on_files_dropped(self, paths: List[Path]):
        for path in paths:
            if not any(str(t) == str(path) for t in self.pending_tasks):
                self.pending_tasks.append(path)
                icon = "📁" if path.is_dir() else "📦"
                item = QListWidgetItem(f"{icon} {path.name}")
                item.setData(Qt.UserRole, str(path))
                item.setToolTip(str(path))
                self.task_list.addItem(item)
        self.update_status()
    
    def clear_tasks(self):
        self.pending_tasks.clear()
        self.task_list.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("就绪")
    
    def update_status(self):
        count = len(self.pending_tasks)
        if count > 0:
            self.progress_label.setText(f"已添加 {count} 个任务")
        else:
            self.progress_label.setText("就绪")
    
    def start_processing(self):
        if not self.pending_tasks:
            return
        
        self.start_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.stop_btn.setVisible(True)
        self.drop_zone.setEnabled(False)
        self.quality_slider.setEnabled(False)
        self.thread_slider.setEnabled(False)
        self.crop_combo.setEnabled(False)
        self.power_slider.setEnabled(False)
        
        self.worker = WorkerThread(
            tasks=self.pending_tasks.copy(),
            quality=self.settings.quality,
            num_threads=self.settings.num_threads,
            crop_mode=self.settings.crop_mode,
            crop_power=self.settings.crop_power
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.task_complete.connect(self.on_task_complete)
        self.worker.all_complete.connect(self.on_all_complete)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def stop_processing(self):
        if self.worker:
            self.worker.cancel()
            self.progress_label.setText("正在终止...")
    
    def on_progress(self, current: int, total: int, filename: str):
        percent = int(current / total * 100) if total > 0 else 0
        self.progress_bar.setValue(percent)
        self.progress_label.setText(f"处理中: {filename} ({current}/{total})")
    
    def on_task_complete(self, task_path: str, stats: ProcessorStats):
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.data(Qt.UserRole) == task_path:
                ratio = (1 - stats.ratio) * 100
                orig = format_size(stats.original_size)
                comp = format_size(stats.compressed_size)
                item.setText(f"✅ {Path(task_path).name} ({orig} → {comp}, -{ratio:.0f}%)")
                break
    
    def on_error(self, task_path: str, error_msg: str):
        for i in range(self.task_list.count()):
            item = self.task_list.item(i)
            if item.data(Qt.UserRole) == task_path:
                item.setText(f"❌ {Path(task_path).name} - {error_msg}")
                break
    
    def on_all_complete(self):
        self.start_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.stop_btn.setVisible(False)
        self.drop_zone.setEnabled(True)
        self.quality_slider.setEnabled(True)
        self.thread_slider.setEnabled(True)
        self.crop_combo.setEnabled(True)
        self.power_slider.setEnabled(True)
        self.progress_label.setText("全部完成！")
        self.progress_bar.setValue(100)
        self.pending_tasks.clear()
