"""
TinyPic - 批量图片压缩工具
入口文件
"""
import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.main_window import MainWindow


def get_resource_path(relative_path: str) -> str:
    """获取资源文件路径（兼容打包后的 exe）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后的临时目录
        base_path = Path(sys._MEIPASS)
    else:
        # 开发环境
        base_path = Path(__file__).parent
    return str(base_path / relative_path)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TinyPic")
    
    # 设置应用图标
    icon_path = get_resource_path('favicon.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
