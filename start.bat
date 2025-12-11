@echo off
title EZClips - Starting...
color 0A

echo.
echo ========================================
echo    EZClips - Video Clip Extractor
echo ========================================
echo.

REM Check Python
echo [1/2] Checking Python...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo [OK] Python found!

REM Check FFmpeg
echo [2/2] Checking FFmpeg...
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    color 0C
    echo [ERROR] FFmpeg is not installed or not in PATH!
    echo.
    echo Please install FFmpeg:
    echo 1. Download from: https://www.gyan.dev/ffmpeg/builds/
    echo 2. Extract the archive
    echo 3. Add the 'bin' folder to your system PATH
    echo.
    echo Or use chocolatey: choco install ffmpeg
    echo.
    pause
    exit /b 1
)
echo [OK] FFmpeg found!

echo.
echo ========================================
echo    Starting EZClips...
echo ========================================
echo.

REM Start GUI without terminal window
start "" pythonw.exe gui.py

REM Wait a moment then close this window
timeout /t 2 /nobreak >nul
exit