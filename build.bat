@echo off
echo Cleaning previous builds...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "*.spec" del /f /q *.spec

echo Installing required packages...
pip install pyinstaller pillow python-pptx pymupdf pyqt5 qtawesome

echo Creating spec file and building...
pyinstaller --name "PDF Image Extractor" ^
    --onefile ^
    --noconsole ^
    --icon "resources/icons/logo.ico" ^
    --add-data "resources;resources" ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "pptx" ^
    --hidden-import "fitz" ^
    main.py

echo Build complete!
pause 