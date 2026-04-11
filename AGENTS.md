# Repository Guidelines

## 项目结构与模块组织
`main.py` 是应用入口，负责启动 PySide6 窗口。`gui/` 存放界面层代码，如 `main_window.py` 和样式定义；`core/` 存放处理链路，包括压缩、裁剪、分页排序、配置持久化等逻辑。`TinyPic.spec` 与 `build.bat` 用于打包，`config.json` 保存本地设置。`测试漫画/` 可作为手工回归样本，`Releases/` 和 `参考代码/` 分别存放发布产物与参考资料。

## 构建、测试与开发命令
先安装依赖：

```bash
pip install -r requirements.txt
```

本地运行桌面应用：

```bash
python main.py
```

快速做语法检查：

```bash
python -m compileall main.py core gui
```

打包可执行文件：

```bash
python -m PyInstaller TinyPic.spec --clean --noconfirm
```

Windows 下也可直接运行 `build.bat`；它会清理旧产物并调用固定的 `C:\Python313\python.exe`。

## 编码风格与命名约定
遵循现有 Python 风格：4 空格缩进，导入顺序按标准库、第三方、本地模块分组。模块级函数与变量使用 `snake_case`，Qt 窗口和组件类使用 `PascalCase`。注释和 docstring 保持简洁，默认使用中文，与现有代码一致。仓库当前未配置 Black、Ruff 或 Flake8，提交前请自行检查可读性、重复逻辑和未使用代码。

## 测试指南
仓库当前没有自动化测试框架和覆盖率门槛。修改后至少执行 `python main.py`，并使用 `测试漫画/` 或等效样本覆盖文件夹、CBZ/ZIP、RAR/CBR、EPUB 输入路径，确认输出文件名仍为 `*_tinypic.cbz`。如果新增可稳定单测的纯逻辑模块，建议补充 `tests/test_<module>.py`。

## 提交与 Pull Request 规范
最近提交以简短祈使句为主，中文和英文前缀都存在，例如 `解决...`、`Update README: ...`。保持一次提交只做一件事，标题直接描述行为或修复点。提交 PR 时请包含：变更摘要、手工验证步骤、关联 issue（如有）；涉及 `gui/` 的改动补充截图或录屏；若调整 7-Zip 路径、打包流程或 `config.json` 行为，请明确说明兼容性影响。

## 配置与安全提示
RAR/CBR 处理依赖本机 7-Zip，相关路径逻辑在 `core/processor.py`。不要提交个人环境专用路径或临时测试产物；若修改配置默认值，请同步更新 `README.md`。
