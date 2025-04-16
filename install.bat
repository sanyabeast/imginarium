@echo off
setlocal

echo [1] Checking for virtual environment...

if not exist ".venv\" (
    echo [2] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [!] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo [2] Virtual environment already exists.
)

echo [3] Activating virtual environment...
call .venv\Scripts\activate.bat

if not defined VIRTUAL_ENV (
    echo [!] Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [4] Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo [!] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [✓] Setup complete. Virtual environment is ready!
echo [i] You can now run your Python scripts inside the virtual environment.
echo.
pause >nul
endlocal