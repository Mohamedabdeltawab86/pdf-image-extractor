@echo off
echo Creating release package...

:: Set version
set VERSION=1.0.0

:: Create release directory
mkdir "release"

:: Copy executable and required files
copy "dist\PDF Image Extractor.exe" "release\"
copy "README.md" "release\"
copy "LICENSE" "release\"

:: Create ZIP file
powershell Compress-Archive -Path "release\*" -DestinationPath "PDF_Image_Extractor_v%VERSION%.zip" -Force

:: Cleanup
rmdir /s /q "release"

echo Release package created: PDF_Image_Extractor_v%VERSION%.zip
pause 