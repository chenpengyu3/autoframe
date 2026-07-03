@echo off
echo ========================================
echo  AutoFrame v2 - Automated Test Framework
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not available in PATH.
    pause
    exit /b 1
)

REM Create or activate venv
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo Examples:
echo   python -m autoframe run --url http://localhost:8080 --project C:\path\to\project
echo   python -m autoframe scan --url http://localhost:8080 --project C:\path\to\project
echo.
echo Starting AutoFrame...
echo.

set /p TARGET_URL="Target URL (example http://localhost:8080): "
if "%TARGET_URL%"=="" (
    echo Error: target URL is required.
    pause
    exit /b 1
)

set /p PROJECT_PATH="Project source path (press Enter to skip): "
if "%PROJECT_PATH%"=="" (
    python -m autoframe run --url %TARGET_URL% -v
) else (
    python -m autoframe run --url %TARGET_URL% --project "%PROJECT_PATH%" -v
)

echo.
echo Test report generated under reports/.
pause
