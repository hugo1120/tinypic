"""
设置管理模块
打包后优先保存到 exe 同目录
"""
import json
import sys
from pathlib import Path


def get_config_path() -> Path:
    """获取配置文件路径（打包后优先保存到 exe 同目录）"""
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

# 双页处理模式选项
SPREAD_MODES = {
    'split': '拆分双页',
    'rotate': '自动旋转',
    'none': '不处理',
}

# 默认设置
MAX_PROCESS_THREADS = 8

DEFAULT_SETTINGS = {
    'quality': 72,
    'num_threads': MAX_PROCESS_THREADS,
    'crop_mode': 'margins',      # 裁剪模式
    'crop_power': 1.0,           # 裁剪力度 0-3
    'spread_mode': 'split',      # 双页处理模式: split/rotate/none
}


class Settings:
    """设置管理器，自动保存/加载配置"""
    
    def __init__(self):
        self.config_path = get_config_path()
        self._data = DEFAULT_SETTINGS.copy()
        self._dirty = False
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
        normalized = self._normalize_data(self._data)
        self._dirty = normalized != self._data
        self._data = normalized
    
    def save(self):
        """保存配置到文件"""
        if not self._dirty:
            return
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            self._dirty = False
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _update(self, key: str, value):
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self._dirty = True

    @staticmethod
    def _normalize_data(data: dict) -> dict:
        normalized = DEFAULT_SETTINGS.copy()
        normalized.update(data)
        normalized['quality'] = max(60, min(95, normalized.get('quality', DEFAULT_SETTINGS['quality'])))
        normalized['num_threads'] = max(1, min(MAX_PROCESS_THREADS, normalized.get('num_threads', DEFAULT_SETTINGS['num_threads'])))
        if normalized.get('crop_mode') not in CROP_MODES:
            normalized['crop_mode'] = DEFAULT_SETTINGS['crop_mode']
        normalized['crop_power'] = max(0.0, min(3.0, normalized.get('crop_power', DEFAULT_SETTINGS['crop_power'])))
        if normalized.get('spread_mode') not in SPREAD_MODES:
            normalized['spread_mode'] = DEFAULT_SETTINGS['spread_mode']
        return normalized
    
    @property
    def quality(self) -> int:
        return self._data.get('quality', 72)
    
    @quality.setter
    def quality(self, value: int):
        self._update('quality', max(60, min(95, value)))
    
    @property
    def num_threads(self) -> int:
        return self._data.get('num_threads', MAX_PROCESS_THREADS)
    
    @num_threads.setter
    def num_threads(self, value: int):
        self._update('num_threads', max(1, min(MAX_PROCESS_THREADS, value)))
    
    @property
    def crop_mode(self) -> str:
        return self._data.get('crop_mode', 'margins')
    
    @crop_mode.setter
    def crop_mode(self, value: str):
        if value in CROP_MODES:
            self._update('crop_mode', value)
    
    @property
    def crop_power(self) -> float:
        return self._data.get('crop_power', 1.0)

    @crop_power.setter
    def crop_power(self, value: float):
        self._update('crop_power', max(0.0, min(3.0, value)))

    @property
    def spread_mode(self) -> str:
        return self._data.get('spread_mode', 'split')

    @spread_mode.setter
    def spread_mode(self, value: str):
        if value in SPREAD_MODES:
            self._update('spread_mode', value)
