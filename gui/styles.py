"""
GUI 样式定义
"""

# 主题颜色
COLORS = {
    'primary': '#6366f1',       # 靛蓝色
    'primary_hover': '#4f46e5',
    'success': '#22c55e',
    'danger': '#ef4444',
    'danger_hover': '#dc2626',
    'background': '#1e1e2e',
    'surface': '#2a2a3e',
    'surface_hover': '#3a3a4e',
    'border': '#3a3a4e',
    'text': '#e2e2e2',
    'text_secondary': '#a0a0a0',
}

# 全局样式表
STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 14px;
}}

QLabel {{
    color: {COLORS['text']};
}}

QLabel#title {{
    font-size: 24px;
    font-weight: bold;
    color: {COLORS['primary']};
}}

QLabel#subtitle {{
    font-size: 12px;
    color: {COLORS['text_secondary']};
}}

/* 拖拽区域 */
QFrame#dropZone {{
    background-color: {COLORS['surface']};
    border: 2px dashed {COLORS['border']};
    border-radius: 12px;
}}

QFrame#dropZone:hover {{
    border-color: {COLORS['primary']};
    background-color: {COLORS['surface_hover']};
}}

/* 任务列表 */
QListWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 8px;
}}

QListWidget::item {{
    background-color: transparent;
    padding: 8px;
    border-radius: 4px;
    margin: 2px 0;
}}

QListWidget::item:hover {{
    background-color: {COLORS['surface_hover']};
}}

QListWidget::item:selected {{
    background-color: {COLORS['primary']};
}}

/* 按钮 */
QPushButton {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-weight: bold;
    font-size: 14px;
}}

QPushButton:hover {{
    background-color: {COLORS['primary_hover']};
}}

QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['text_secondary']};
}}

QPushButton#dangerButton {{
    background-color: {COLORS['danger']};
}}

QPushButton#dangerButton:hover {{
    background-color: {COLORS['danger_hover']};
}}

/* 滑块 */
QSlider::groove:horizontal {{
    height: 8px;
    background-color: {COLORS['surface']};
    border-radius: 4px;
}}

QSlider::handle:horizontal {{
    width: 20px;
    height: 20px;
    margin: -6px 0;
    background-color: {COLORS['primary']};
    border-radius: 10px;
}}

QSlider::sub-page:horizontal {{
    background-color: {COLORS['primary']};
    border-radius: 4px;
}}

/* 进度条 */
QProgressBar {{
    background-color: {COLORS['surface']};
    border: none;
    border-radius: 8px;
    height: 16px;
    text-align: center;
    color: {COLORS['text']};
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 8px;
}}

/* SpinBox */
QSpinBox {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    padding: 6px 12px;
    color: {COLORS['text']};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 20px;
    background-color: {COLORS['surface_hover']};
    border: none;
}}
"""
