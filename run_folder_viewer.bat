@echo off
echo Starting Folder Size Viewer...
python folder_size_viewer.py
if errorlevel 1 (
    echo.
    echo Error: Python may not be installed or the script has an error.
    echo Please ensure Python 3 is installed from python.org
    pause
)