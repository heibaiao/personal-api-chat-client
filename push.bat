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

echo [2/4] Configuring remote and TLS...
"%GIT%" config http.sslBackend openssl
"%GIT%" remote get-url origin >nul 2>nul
if errorlevel 1 (
  "%GIT%" remote add origin https://github.com/heibaiao/personal-api-chat-client.git
) else (
  "%GIT%" remote set-url origin https://github.com/heibaiao/personal-api-chat-client.git
)
"%GIT%" remote -v

echo.
echo [3/4] Pushing main...
"%GIT%" push -u origin main 2>"%TEMP%\pacc_push_err.txt"
if errorlevel 1 (
  findstr /C:"rejected" /C:"fetch first" /C:"non-fast-forward" "%TEMP%\pacc_push_err.txt" >nul 2>nul
  if not errorlevel 1 goto :diverged
  echo.
  type "%TEMP%\pacc_push_err.txt"
  goto :pusherr
)

:afterpush
echo.
echo [4/4] Creating and pushing tag v1.0.0...
"%GIT%" tag -a v1.0.0 -m "V1.0" 2>nul
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

:diverged
echo.
echo [!] Remote already has commits that your local repo does not have
echo     (usually a README/LICENSE created on the GitHub website,
echo      or a previous partial push).
echo.
echo     Remote content:  %GIT% fetch origin ^&^& %GIT% log origin/main --oneline -5
echo.
set /p YN=  Overwrite remote with this local repo (force push)? [Y/N]:
if /i "!YN!"=="Y" (
  echo.
  echo     Force pushing...
  "%GIT%" push -u origin main --force
  if errorlevel 1 goto :pusherr
  goto :afterpush
)
echo.
echo     Aborted. Options:
echo       A. Keep remote files:  git pull --rebase origin main   then run push.bat again
echo       B. Keep local files:   git push -u origin main --force
goto :end

:pusherr
echo.
echo [X] Push failed. Common causes:
echo     - repository not created on github.com yet
echo     - not logged in (use a Personal Access Token or SSH)
echo     - network / proxy problem
echo   See docs\PUBLISH.md section 10.

:end
if exist "%TEMP%\pacc_push_err.txt" del "%TEMP%\pacc_push_err.txt" >nul 2>nul
echo.
pause
endlocal
