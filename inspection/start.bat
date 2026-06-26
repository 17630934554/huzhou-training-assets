@echo off
title Safety Inspection AI
color 0A

echo =========================================
echo   Safety Inspection AI System
echo =========================================
echo.

REM ---- Check Python ----
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Install Python 3.11 first.
    pause
    exit /b 1
)

python --version
echo.

REM ---- Install dependencies ----
echo [1/3] Installing core packages...
pip install ultralytics opencv-python pyyaml requests Pillow --quiet
echo   Done
echo.

echo [2/3] Installing imageio-ffmpeg (H.265 support)...
pip install imageio-ffmpeg --quiet
echo   Done
echo.

echo [3/3] Installing PyTorch CPU...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --quiet
echo   Done
echo.

REM ---- Validate config ----
echo.
echo Validating config.yaml...
python -c "import yaml; yaml.safe_load(open('config.yaml','r',encoding='utf-8')); print('  Config OK')"
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] config.yaml has syntax error!
    echo Do NOT edit config.yaml with Notepad - it breaks indentation.
    echo Run: git pull   to get a fresh copy.
    pause
    exit /b 1
)
echo.

REM ---- Start ----
echo =========================================
echo   Starting inspection system...
echo   Press Ctrl+C to stop
echo =========================================
echo.

python detector.py

pause
