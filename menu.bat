@echo off
setlocal enabledelayedexpansion
title Stock Images Generator Menu

:: Set console to UTF-8 mode to support emojis
chcp 65001 >nul

:: Check if virtual environment exists
if not exist .venv (
    echo Virtual environment not found. Running install.bat first...
    call install.bat
    if errorlevel 1 (
        echo Failed to set up virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat

:: Check if textual is installed
python -c "import textual" >nul 2>&1
if errorlevel 1 (
    echo Installing textual...
    pip install textual
    if errorlevel 1 (
        echo Failed to install textual.
        pause
        exit /b 1
    )
)

:: Set PYTHONIOENCODING to ensure proper Unicode output
set PYTHONIOENCODING=utf-8

:: Run the menu
python menu.py

:: Deactivate virtual environment
call .venv\Scripts\deactivate.bat

exit /b 0
