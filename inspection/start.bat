@echo off
chcp 65001 >nul
title Inspection System - Laptop Test
color 0A

echo =========================================
echo   Safety Inspection System - Laptop Test
echo =========================================
echo.

REM ---- Check Python ----
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo.

REM ---- Install dependencies ----
echo [1/4] Installing core packages...
pip install ultralytics opencv-python pyyaml requests Pillow --quiet
echo   Done
echo.

echo [2/4] Installing imageio-ffmpeg (full FFmpeg with H.265)...
pip install imageio-ffmpeg --quiet
echo   Done
echo.

echo [3/4] Installing PyTorch...
nvidia-smi >nul 2>&1
if %errorlevel% equ 0 (
    echo   NVIDIA GPU detected, installing GPU version...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 --quiet
) else (
    echo   No NVIDIA GPU, installing CPU version...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu --quiet
)
echo   Done
echo.

REM ---- Generate laptop config ----
echo [4/4] Generating test config...
python -c "import yaml,os;f=open('config.yaml','r',encoding='utf-8');cfg=yaml.safe_load(f);f.close();cfg['model']['device']='cuda' if os.system('nvidia-smi >nul 2>&1')==0 else 'cpu';cfg['model']['inference_fps']=1;cfg['nvr']['channels']=cfg['nvr']['channels'][:1];[ch.update({'tier':'A'}) for ch in cfg['nvr']['channels']];[v.update({'enabled':True}) if k in ['fire_smoke','no_helmet'] else v.update({'enabled':False}) for k,v in cfg['scenes'].items()];f=open('config_laptop.yaml','w',encoding='utf-8');yaml.dump(cfg,f,allow_unicode=True,default_flow_style=False);f.close();print('  Config: '+str(len(cfg['nvr']['channels']))+' camera(s), device='+cfg['model']['device'])"
echo.

REM ---- Start ----
echo =========================================
echo   Starting inspection system...
echo   Press Ctrl+C to stop
echo =========================================
echo.

python detector.py config_laptop.yaml

pause
