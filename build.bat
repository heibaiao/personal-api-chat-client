@echo off
chcp 65001 >nul
setlocal

echo [1/4] Syntax check...
python -m py_compile deepseek_chat.py || goto :err

echo [2/4] Build onedir...
pyinstaller -D -w --name PACC-V1.0 --version-file version_info.txt ^
  --clean --noconfirm ^
  --collect-all openai --collect-all httpx --collect-all httpcore --collect-all matplotlib ^
  --hidden-import matplotlib.backends.backend_agg ^
  --hidden-import matplotlib.mathtext ^
  --hidden-import matplotlib.font_manager deepseek_chat.py || goto :err

echo [3/4] Stage portable folder...
set DST=dist\PersonalAPIChatClient-V1.0-portable
if exist "%DST%" rmdir /s /q "%DST%"
move "dist\PACC-V1.0" "%DST%"
xcopy "assets" "%DST%\assets\" /E /I /Q /Y >nul
if exist "使用说明.txt" copy /y "使用说明.txt" "%DST%\" >nul

echo [4/4] Zip...
powershell -NoProfile -Command "Compress-Archive -Path '%DST%' -DestinationPath 'dist\PersonalAPIChatClient-V1.0-portable-win64.zip' -Force"

echo.
echo Done: dist\PersonalAPIChatClient-V1.0-portable-win64.zip
goto :eof

:err
echo Build failed, see errors above.
exit /b 1
