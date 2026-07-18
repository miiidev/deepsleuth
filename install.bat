@echo off
setlocal enabledelayedexpansion

set SCRIPT_VERSION=1.0
set WEIGHTS_URL=https://github.com/miiidev/deepsleuth/releases/download/v%SCRIPT_VERSION%/weights-v%SCRIPT_VERSION%.zip
set WEIGHTS_DIR=weights
set MIN_PYTHON=3.11
set MIN_NODE=18

echo DeepSleuth Installer v%SCRIPT_VERSION%
echo ================================
echo.

call :step1_prereqs
if %ERRORLEVEL% neq 0 exit /b 1
call :step2_venv
if %ERRORLEVEL% neq 0 exit /b 1
call :step3_deps
if %ERRORLEVEL% neq 0 exit /b 1
call :step4_weights
if %ERRORLEVEL% neq 0 exit /b 1
call :step5_frontend
if %ERRORLEVEL% neq 0 exit /b 1
call :step6_done
exit /b 0

:step1_prereqs
echo [1/6] Checking prerequisites...
call :check_python
if %ERRORLEVEL% neq 0 exit /b 1
call :check_node
if %ERRORLEVEL% neq 0 exit /b 1
call :check_cuda
exit /b 0

:check_python
set PYTHON=
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%i in ('py -3.11 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2^>nul') do (
        set PYTHON=py -3.11
        echo   Python: %%i
        exit /b 0
    )
)
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python -c "import sys; v=sys.version_info; assert v.major==3 and v.minor>=11, 'need 3.11+'" 2>nul
    if %ERRORLEVEL% equ 0 (
        set PYTHON=python
        for /f "tokens=*" %%i in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do (
            echo   Python: %%i
            exit /b 0
        )
    )
)
echo [ERROR] Python 3.11+ not found. Install from https://python.org
exit /b 1

:check_node
where node >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VER=%%i
for /f "tokens=1 delims=v" %%i in ("%NODE_VER%") do set NODE_MAJOR=%%i
for /f "tokens=1 delims=." %%i in ("%NODE_MAJOR%") do set NODE_MAJOR=%%i
if %NODE_MAJOR% lss %MIN_NODE% (
    echo [ERROR] Node.js 18+ required (found %NODE_VER%)
    exit /b 1
)
echo   Node: %NODE_VER%
exit /b 0

:check_cuda
where nvidia-smi >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set HAS_CUDA=1
    echo   CUDA: detected
) else (
    set HAS_CUDA=0
    echo   CUDA: not detected (CPU-only mode)
)
exit /b 0

:step2_venv
echo [2/6] Creating virtual environment...
if exist .venv (
    echo   .venv already exists, skipping.
    exit /b 0
)
%PYTHON% -m venv .venv
echo   Virtual environment created.
exit /b 0

:activate_venv
call .venv\Scripts\activate.bat
exit /b 0

:step3_deps
echo [3/6] Installing dependencies...
call :activate_venv
python -m pip install --upgrade pip -q

if "%HAS_CUDA%"=="1" (
    echo   Installing PyTorch with CUDA support...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
) else (
    echo   Installing CPU-only PyTorch...
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
)
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyTorch installation failed.
    exit /b 1
)

echo   Installing remaining packages...
pip install -e .
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Package installation failed.
    exit /b 1
)
exit /b 0

:step4_weights
echo [4/6] Downloading model weights...
if exist "%WEIGHTS_DIR%\xception_best.pth" (
    if exist "%WEIGHTS_DIR%\face_landmarker.task" (
        for %%f in ("%WEIGHTS_DIR%\xception_best.pth") do if %%~zf gtr 0 (
            for %%g in ("%WEIGHTS_DIR%\face_landmarker.task") do if %%~zg gtr 0 (
                echo   Weights already present, skipping.
                exit /b 0
            )
        )
    )
)
if not exist "%WEIGHTS_DIR%" mkdir "%WEIGHTS_DIR%"
echo   Downloading from %WEIGHTS_URL%
curl -L --max-time 120 --progress-bar -o "%TEMP%\weights.zip" "%WEIGHTS_URL%"
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Weight download failed.
    exit /b 1
)
tar -xf "%TEMP%\weights.zip" -C "%WEIGHTS_DIR%" 2>nul || (
    rem fallback if tar not available — use PowerShell
    powershell -Command "Expand-Archive -Path '%TEMP%\weights.zip' -DestinationPath '%WEIGHTS_DIR%' -Force"
)
del "%TEMP%\weights.zip" 2>nul
echo   Weights extracted to %WEIGHTS_DIR%/
exit /b 0

:step5_frontend
echo [5/6] Building frontend...
if not exist frontend (
    echo   frontend/ not found, skipping build.
    exit /b 0
)
pushd frontend
call npm install --silent
if %ERRORLEVEL% neq 0 (
    popd
    echo [ERROR] npm install failed.
    exit /b 1
)
call npm run build
if %ERRORLEVEL% neq 0 (
    popd
    echo [ERROR] Frontend build failed.
    exit /b 1
)
popd
echo   Frontend built.
exit /b 0

:step6_done
echo [6/6] Installation complete!
echo.
echo DeepSleuth installed successfully!
echo.
echo   Run:  deepsleuth
echo   Or:   python -m backend.cli
echo.
echo   Open http://127.0.0.1:8000 in your browser.
exit /b 0

