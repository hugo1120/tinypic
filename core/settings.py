"""
设置管理模块
打包后保存到 exe 同目录
"""
import json
import sys
from pathlib import Path


def get_config_path() -> Path:
    """获取配置文件路径（打包后保存到 exe 同目录）"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys.executable).parent
    else:
        base_path = Path(__file__).parent.parent
    return base_path / 'config.json'


# 裁剪模式选项
CROP_MODES = {
    'none': '不裁剪',
    'margins': '白边裁剪',
    'margins+page': '白边+页码裁剪',
}

# 默认设置
DEFAULT_SETTINGS = {
    'quality': 72,
    'num_threads': 8,
    'crop_mode': 'margins',      # 裁剪模式
    'crop_power': 1.0,           # 裁剪力度 0-3
}


class Settings:
    """设置管理器，自动保存/加载配置"""
    
    def __init__(self):
        self.config_path = get_config_path()
        self._data = DEFAULT_SETTINGS.copy()
        self.load()
    
    def load(self):
        """加载配置文件"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception:
                pass
    
    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    @property
    def quality(self) -> int:
        return self._data.get('quality', 72)
    
    @quality.setter
    def quality(self, value: int):
        self._data['quality'] = max(60, min(95, value))
        self.save()
    
    @property
    def num_threads(self) -> int:
        return self._data.get('num_threads', 8)
    
    @num_threads.setter
    def num_threads(self, value: int):
        self._data['num_threads'] = max(1, min(100, value))
        self.save()
    
    @property
    def crop_mode(self) -> str:
        return self._data.get('crop_mode', 'margins')
    
    @crop_mode.setter
    def crop_mode(self, value: str):
        if value in CROP_MODES:
            self._data['crop_mode'] = value
            self.save()
    
    @property
    def crop_power(self) -> float:
        return self._data.get('crop_power', 1.0)
    
    @crop_power.setter
    def crop_power(self, value: float):
        self._data['crop_power'] = max(0.0, min(3.0, value))
        self.save()
