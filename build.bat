@echo off
chcp 65001 >nul
title TinyPic 打包工具
color 0A

echo.
echo  ╔══════════════════════════════════════╗
echo  ║        TinyPic 打包脚本              ║
echo  ║                                      ║
echo  ║  窗口图标: favicon.png               ║
echo  ║  EXE图标:  favicon.ico               ║
echo  ╚══════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo [1/3] 清理旧文件...
if exist "dist\TinyPic.exe" del /f "dist\TinyPic.exe"

echo [2/3] 正在打包 (需要1-2分钟)...
echo.
C:\Python313\python.exe -m PyInstaller TinyPic.spec --clean --noconfirm

echo.
if %ERRORLEVEL% EQU 0 (
    echo  ╔══════════════════════════════════════╗
    echo  ║           打包成功！                 ║
    echo  ╚══════════════════════════════════════╝
    echo.
    echo  输出文件: %~dp0dist\TinyPic.exe
    echo.
    
    echo [3/3] 打开输出目录...
    explorer /select,"%~dp0dist\TinyPic.exe"
) else (
    echo  ╔══════════════════════════════════════╗
    echo  ║           打包失败！                 ║
    echo  ╚══════════════════════════════════════╝
    echo.
    echo  请检查上方错误信息
)

echo.
pause
