from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

import core.settings as settings_module
from core.settings import Settings


def test_settings_only_write_on_explicit_save(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)

    settings = Settings()
    settings.quality = 80

    assert not config_path.exists()

    settings.save()

    assert config_path.exists()
    assert '"quality": 80' in config_path.read_text(encoding="utf-8")


def test_settings_save_creates_parent_directory(tmp_path, monkeypatch):
    config_path = tmp_path / "nested" / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)

    settings = Settings()
    settings.quality = 80
    settings.save()

    assert config_path.exists()
    assert '"quality": 80' in config_path.read_text(encoding="utf-8")


def test_get_config_path_uses_executable_directory_when_frozen(tmp_path, monkeypatch):
    import core.settings as settings_module

    local_appdata = tmp_path / "LocalAppData"
    executable = tmp_path / "TinyPic.exe"

    monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))
    monkeypatch.setattr(settings_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(settings_module.sys, "executable", str(executable))

    assert settings_module.get_config_path() == executable.parent / "config.json"


def test_main_window_saves_settings_on_close(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)

    app = QApplication.instance() or QApplication([])

    from gui.main_window import MainWindow

    window = MainWindow()
    window.quality_slider.setValue(81)
    window.close()
    app.processEvents()

    assert config_path.exists()
    assert '"quality": 81' in config_path.read_text(encoding="utf-8")


def test_settings_clamp_thread_count_to_processing_cap(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)

    settings = Settings()
    max_threads = getattr(settings_module, "MAX_PROCESS_THREADS", None)

    assert max_threads is not None

    settings.num_threads = max_threads + 5

    assert settings.num_threads == max_threads


def test_settings_normalize_loaded_thread_count_to_processing_cap(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)
    max_threads = getattr(settings_module, "MAX_PROCESS_THREADS", None)

    assert max_threads is not None

    config_path.write_text('{\n  "num_threads": 100\n}', encoding="utf-8")

    settings = Settings()

    assert settings.num_threads == max_threads


def test_main_window_thread_slider_matches_processing_cap(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("core.settings.get_config_path", lambda: config_path)

    app = QApplication.instance() or QApplication([])
    max_threads = getattr(settings_module, "MAX_PROCESS_THREADS", None)

    assert max_threads is not None

    from gui.main_window import MainWindow

    window = MainWindow()

    assert window.thread_slider.minimum() == 1
    assert window.thread_slider.maximum() == max_threads

    window.close()
