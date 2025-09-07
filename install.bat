@echo off
echo ====================================
echo YoFiles Installer
echo ====================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo Installing dependencies...
pip install send2trash pyinstaller

echo.
echo Building YoFiles executable...
pyinstaller --onefile --windowed --name=YoFiles folder_size_viewer.py

if exist dist\YoFiles.exe (
    echo.
    echo ====================================
    echo SUCCESS! YoFiles has been built!
    echo ====================================
    echo.
    echo Executable location: %cd%\dist\YoFiles.exe
    echo.
    echo You can:
    echo 1. Run it directly from dist\YoFiles.exe
    echo 2. Copy YoFiles.exe to any location you prefer
    echo 3. Create a desktop shortcut for easy access
    echo.
    
    choice /C YN /M "Would you like to run YoFiles now"
    if errorlevel 2 goto end
    if errorlevel 1 start dist\YoFiles.exe
) else (
    echo.
    echo ERROR: Build failed!
    echo Please check the error messages above.
)

:end
echo.
pause