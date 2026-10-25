@echo off
rem Console (ZongKongTai) Windows launcher.
rem Finds the first working Python 3.12+ from: python, py -3.
rem NOTE: keep this file ASCII-only and CRLF; cmd parses .bat in the
rem system ANSI codepage, UTF-8 Chinese comments become garbage commands.
setlocal
cd /d "%~dp0"
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 (
  python server.py --launcher %*
  goto end
)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if not errorlevel 1 (
  py -3 server.py --launcher %*
  goto end
)
echo [start.bat] No working Python 3.12+ found in PATH or py launcher.
echo Install Python 3.12+ from https://www.python.org/downloads/
pause
:end
