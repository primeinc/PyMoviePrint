@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-PyMoviePrint.ps1"
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" echo Operation failed. See the error above.
pause
exit /b %RC%
