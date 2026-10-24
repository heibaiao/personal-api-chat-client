@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  Personal API Chat Client - 推送到 GitHub
echo ============================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [X] 没找到 git 命令。请先安装 Git for Windows 并重开窗口。
  pause
  exit /b 1
)

echo [1/4] 检查网络...
powershell -NoProfile -Command "if (Test-NetConnection github.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo [X] 连不上 github.com:443。请检查网络 / 代理后重试。
  pause
  exit /b 1
)

echo [2/4] 配置远程地址...
git remote get-url origin >nul 2>nul
if errorlevel 1 (
  git remote add origin https://github.com/heibaiao/personal-api-chat-client.git
) else (
  git remote set-url origin https://github.com/heibaiao/personal-api-chat-client.git
)
git remote -v

echo.
echo [3/4] 推送 main...
git push -u origin main
if errorlevel 1 goto :err

echo.
echo [4/4] 创建并推送标签 v1.0.0...
git tag -a v1.0.0 -m "V1.0 (αpiv0004)" 2>nul
git push origin v1.0.0
if errorlevel 1 (
  echo [!] 标签推送失败（可能已存在），继续。
)

echo.
echo ============================================
echo  完成！接下来手动做最后一步：
echo  1. 打开 https://github.com/heibaiao/personal-api-chat-client/releases
echo  2. Draft a new release - 选标签 v1.0.0
echo  3. 标题填 "V1.0 (αpiv0004)"
echo  4. 上传 dist\PersonalAPIChatClient-V1.0-portable-win64.zip
echo ============================================
pause
exit /b 0

:err
echo.
echo [X] 推送失败。常见原因：
echo   - 仓库还没在网页上创建
echo   - 需要登录：用 Personal Access Token 或 SSH
echo   - 网络/代理问题
echo 详细排查见 docs\PUBLISH.md 第 10 节。
pause
exit /b 1
