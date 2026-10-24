@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "GIT="
for %%P in ("%ProgramFiles%\Git\cmd\git.exe" "%ProgramFiles(x86)%\Git\cmd\git.exe" "%LOCALAPPDATA%\Programs\Git\cmd\git.exe") do (
  if not defined GIT if exist %%P set "GIT=%%~P"
)
if not defined GIT (
  for /f "delims=" %%G in ('where git 2^>nul') do if not defined GIT set "GIT=%%G"
)

echo ============================================
echo  Personal API Chat Client - push to GitHub
echo ============================================
echo.

if not defined GIT (
  echo [X] git not found.
  echo     Install Git for Windows: https://git-scm.com/download/win
  goto :end
)
echo git: %GIT%
echo.

echo [1/4] Checking network...
powershell -NoProfile -Command "if (Test-NetConnection github.com -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo [X] Cannot reach github.com:443.
  echo     Check network / proxy / VPN, then run this again.
  goto :end
)

echo [2/4] Configuring remote...
"%GIT%" remote get-url origin >nul 2>nul
if errorlevel 1 (
  "%GIT%" remote add origin https://github.com/heibaiao/personal-api-chat-client.git
) else (
  "%GIT%" remote set-url origin https://github.com/heibaiao/personal-api-chat-client.git
)
"%GIT%" remote -v

echo.
echo [3/4] Pushing main...
"%GIT%" push -u origin main
if errorlevel 1 goto :pusherr

echo.
echo [4/4] Creating and pushing tag v1.0.0...
"%GIT%" tag -a v1.0.0 -m "V1.0 (apiv0004)" 2>nul
"%GIT%" push origin v1.0.0
if errorlevel 1 echo [!] Tag push skipped or already exists.

echo.
echo ============================================
echo  Done. Last manual step:
echo   1. Open https://github.com/heibaiao/personal-api-chat-client/releases
echo   2. Draft a new release, choose tag v1.0.0
echo   3. Upload PersonalAPIChatClient-V1.0-portable-win64.zip
echo ============================================
goto :end

:pusherr
echo.
echo [X] Push failed. Common causes:
echo     - repository not created on github.com yet
echo     - not logged in (use a Personal Access Token or SSH)
echo     - network / proxy problem
echo   See docs\PUBLISH.md section 10.

:end
echo.
pause
endlocal
